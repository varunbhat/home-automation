"""TP-Link device implementations."""

from typing import Dict, Optional
from kasa import Device as KasaDevice

from maneyantra.core.rabbitmq_bus import RabbitMQEventBus
from maneyantra.plugins.devices.base import Device
from maneyantra.types.devices import (
    DeviceInfo,
    DeviceType,
    DeviceCapability,
    DeviceState,
    ColorValue,
)


class TpLinkLight(Device):
    """TP-Link smart bulb."""

    def __init__(
        self,
        kasa_device: KasaDevice,
        plugin_id: str,
        event_bus: RabbitMQEventBus,
    ):
        # Determine capabilities
        capabilities = [DeviceCapability.ON_OFF]

        if kasa_device.is_dimmable:
            capabilities.append(DeviceCapability.BRIGHTNESS)

        if kasa_device.is_color:
            capabilities.append(DeviceCapability.COLOR)

        if kasa_device.is_variable_color_temp:
            capabilities.append(DeviceCapability.COLOR_TEMPERATURE)

        # Create device info
        device_info = DeviceInfo(
            id=kasa_device.device_id or kasa_device.mac.replace(":", ""),
            name=kasa_device.alias,
            type=DeviceType.LIGHT,
            capabilities=capabilities,
            manufacturer="TP-Link",
            model=kasa_device.model,
            sw_version=kasa_device.hw_info.get("sw_ver"),
            hw_version=kasa_device.hw_info.get("hw_ver"),
            plugin_id=plugin_id,
        )

        super().__init__(device_info, event_bus)

        self.kasa_device = kasa_device

    async def execute_command(self, command: str, params: Optional[Dict] = None) -> None:
        """Execute a command on the light."""
        params = params or {}

        if command == "turn_on":
            await self.kasa_device.turn_on()

        elif command == "turn_off":
            await self.kasa_device.turn_off()

        elif command == "toggle":
            if self.state.on:
                await self.kasa_device.turn_off()
            else:
                await self.kasa_device.turn_on()

        elif command == "set_brightness":
            brightness = params.get("brightness", 100)
            await self.kasa_device.set_brightness(brightness)

        elif command == "set_color_temperature":
            temp = params.get("temperature", 4000)
            await self.kasa_device.set_color_temp(temp)

        elif command == "set_hsv":
            hue = params.get("hue", 0)
            saturation = params.get("saturation", 100)
            value = params.get("value", 100)
            await self.kasa_device.set_hsv(hue, saturation, value)

        else:
            raise ValueError(f"Unknown command: {command}")

        # Update state after command
        await self.update_state({"on": self.kasa_device.is_on})

    async def refresh_state(self) -> DeviceState:
        """Refresh state from the physical device."""
        await self.kasa_device.update()

        # Build state
        new_state = {
            "online": True,
            "on": self.kasa_device.is_on,
        }

        if self.kasa_device.is_dimmable:
            new_state["brightness"] = self.kasa_device.brightness

        if self.kasa_device.is_color:
            hsv = self.kasa_device.hsv
            if hsv:
                new_state["color"] = ColorValue(
                    hue=int(hsv.hue),
                    saturation=int(hsv.saturation),
                    value=int(hsv.value),
                )

        if self.kasa_device.is_variable_color_temp:
            new_state["color_temperature"] = self.kasa_device.color_temp

        # Update state
        await self.update_state(new_state)

        return self.state


class TpLinkPlug(Device):
    """TP-Link smart plug/switch."""

    def __init__(
        self,
        kasa_device: KasaDevice,
        plugin_id: str,
        event_bus: RabbitMQEventBus,
    ):
        # Determine capabilities
        capabilities = [DeviceCapability.ON_OFF]

        if hasattr(kasa_device, "emeter_realtime"):
            capabilities.append(DeviceCapability.POWER_MONITORING)
            capabilities.append(DeviceCapability.ENERGY_MONITORING)

        # Create device info
        device_info = DeviceInfo(
            id=kasa_device.device_id or kasa_device.mac.replace(":", ""),
            name=kasa_device.alias,
            type=DeviceType.PLUG,
            capabilities=capabilities,
            manufacturer="TP-Link",
            model=kasa_device.model,
            sw_version=kasa_device.hw_info.get("sw_ver"),
            hw_version=kasa_device.hw_info.get("hw_ver"),
            plugin_id=plugin_id,
        )

        super().__init__(device_info, event_bus)

        self.kasa_device = kasa_device

    async def execute_command(self, command: str, params: Optional[Dict] = None) -> None:
        """Execute a command on the plug."""
        params = params or {}

        if command == "turn_on":
            await self.kasa_device.turn_on()

        elif command == "turn_off":
            await self.kasa_device.turn_off()

        elif command == "toggle":
            if self.state.on:
                await self.kasa_device.turn_off()
            else:
                await self.kasa_device.turn_on()

        else:
            raise ValueError(f"Unknown command: {command}")

        # Update state after command
        await self.update_state({"on": self.kasa_device.is_on})

    async def refresh_state(self) -> DeviceState:
        """Refresh state from the physical device."""
        await self.kasa_device.update()

        # Build state
        new_state = {
            "online": True,
            "on": self.kasa_device.is_on,
        }

        # Get energy monitoring data if available
        if hasattr(self.kasa_device, "emeter_realtime"):
            try:
                emeter = await self.kasa_device.get_emeter_realtime()
                new_state["power"] = emeter.get("power_mw", 0) / 1000  # mW to W
                new_state["voltage"] = emeter.get("voltage_mv", 0) / 1000  # mV to V
                new_state["current"] = emeter.get("current_ma", 0) / 1000  # mA to A

                # Get total energy consumption
                stats = await self.kasa_device.get_emeter_monthly()
                if stats:
                    # Get current month's energy
                    current_month = max(stats.keys())
                    new_state["energy"] = stats[current_month]

            except Exception as e:
                self._logger.warning(f"Error reading emeter data: {e}")

        # Update state
        await self.update_state(new_state)

        return self.state
