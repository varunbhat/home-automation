"""Eufy device implementations."""

from typing import Dict, Optional

from maneyantra.core.rabbitmq_bus import RabbitMQEventBus
from maneyantra.plugins.devices.base import Device
from maneyantra.types.devices import (
    DeviceInfo,
    DeviceType,
    DeviceCapability,
    DeviceState,
)


class EufyCamera(Device):
    """Eufy security camera."""

    def __init__(
        self,
        eufy_device,
        plugin_id: str,
        event_bus: RabbitMQEventBus,
    ):
        # Determine capabilities
        capabilities = [
            DeviceCapability.VIDEO_STREAM,
            DeviceCapability.MOTION_DETECTION,
            DeviceCapability.PERSON_DETECTION,
        ]

        if hasattr(eufy_device, "has_battery") and eufy_device.has_battery:
            capabilities.append(DeviceCapability.BATTERY)

        if hasattr(eufy_device, "has_audio") and eufy_device.has_audio:
            capabilities.append(DeviceCapability.AUDIO)

        # Create device info
        device_info = DeviceInfo(
            id=eufy_device.serial_number,
            name=eufy_device.name,
            type=DeviceType.CAMERA,
            capabilities=capabilities,
            manufacturer="Eufy",
            model=eufy_device.model,
            sw_version=getattr(eufy_device, "software_version", None),
            hw_version=getattr(eufy_device, "hardware_version", None),
            plugin_id=plugin_id,
        )

        super().__init__(device_info, event_bus)

        self.eufy_device = eufy_device

    async def execute_command(self, command: str, params: Optional[Dict] = None) -> None:
        """Execute a command on the camera."""
        params = params or {}

        if command == "start_stream":
            # Start video stream
            stream_url = await self.eufy_device.start_stream()
            await self.event_bus.publish(
                f"device.{self.info.id}.stream",
                {"stream_url": stream_url},
            )

        elif command == "stop_stream":
            # Stop video stream
            await self.eufy_device.stop_stream()

        elif command == "enable_motion_detection":
            await self.eufy_device.set_motion_detection(True)

        elif command == "disable_motion_detection":
            await self.eufy_device.set_motion_detection(False)

        elif command == "trigger_alarm":
            duration = params.get("duration", 10)
            await self.eufy_device.trigger_alarm(duration)

        else:
            raise ValueError(f"Unknown command: {command}")

    async def refresh_state(self) -> DeviceState:
        """Refresh state from the physical device."""
        # Update device state from Eufy
        await self.eufy_device.update()

        # Build state
        new_state = {
            "online": self.eufy_device.is_online,
            "motion": getattr(self.eufy_device, "motion_detected", False),
        }

        # Battery level if available
        if hasattr(self.eufy_device, "battery_level"):
            new_state["battery"] = self.eufy_device.battery_level

        # Custom attributes
        new_state["custom"] = {
            "person_detected": getattr(self.eufy_device, "person_detected", False),
            "recording": getattr(self.eufy_device, "is_recording", False),
            "streaming": getattr(self.eufy_device, "is_streaming", False),
        }

        # Update state
        await self.update_state(new_state)

        return self.state


class EufySensor(Device):
    """Eufy sensor (motion, door/window)."""

    def __init__(
        self,
        eufy_device,
        plugin_id: str,
        event_bus: RabbitMQEventBus,
    ):
        # Determine device type and capabilities
        device_type_str = eufy_device.device_type.lower()

        if "motion" in device_type_str:
            device_type = DeviceType.MOTION_SENSOR
            capabilities = [DeviceCapability.MOTION_DETECTION]
        elif "door" in device_type_str or "window" in device_type_str or "contact" in device_type_str:
            device_type = DeviceType.DOOR_SENSOR
            capabilities = [DeviceCapability.CONTACT]
        else:
            device_type = DeviceType.SENSOR
            capabilities = []

        # Add battery capability if available
        if hasattr(eufy_device, "has_battery") and eufy_device.has_battery:
            capabilities.append(DeviceCapability.BATTERY)

        # Create device info
        device_info = DeviceInfo(
            id=eufy_device.serial_number,
            name=eufy_device.name,
            type=device_type,
            capabilities=capabilities,
            manufacturer="Eufy",
            model=eufy_device.model,
            sw_version=getattr(eufy_device, "software_version", None),
            hw_version=getattr(eufy_device, "hardware_version", None),
            plugin_id=plugin_id,
        )

        super().__init__(device_info, event_bus)

        self.eufy_device = eufy_device

    async def execute_command(self, command: str, params: Optional[Dict] = None) -> None:
        """Execute a command on the sensor."""
        # Most sensors don't support commands, but we'll handle any that do
        raise ValueError(f"Sensors do not support commands: {command}")

    async def refresh_state(self) -> DeviceState:
        """Refresh state from the physical device."""
        # Update device state from Eufy
        await self.eufy_device.update()

        # Build state
        new_state = {
            "online": self.eufy_device.is_online,
        }

        # Motion detected
        if DeviceCapability.MOTION_DETECTION in self.info.capabilities:
            new_state["motion"] = getattr(self.eufy_device, "motion_detected", False)

        # Contact state (door/window open/closed)
        if DeviceCapability.CONTACT in self.info.capabilities:
            new_state["contact"] = getattr(self.eufy_device, "is_open", False)

        # Battery level if available
        if hasattr(self.eufy_device, "battery_level"):
            new_state["battery"] = self.eufy_device.battery_level

        # Temperature/humidity if available
        if hasattr(self.eufy_device, "temperature"):
            new_state["temperature"] = self.eufy_device.temperature

        if hasattr(self.eufy_device, "humidity"):
            new_state["humidity"] = self.eufy_device.humidity

        # Update state
        await self.update_state(new_state)

        return self.state
