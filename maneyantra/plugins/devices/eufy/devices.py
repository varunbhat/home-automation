"""Eufy device implementations."""

import aiohttp
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
        eufy_device: Dict,
        plugin_id: str,
        event_bus: RabbitMQEventBus,
        bridge_url: str,
        session: aiohttp.ClientSession,
    ):
        # Determine capabilities
        capabilities = [
            DeviceCapability.VIDEO_STREAM,
            DeviceCapability.MOTION_DETECTION,
            DeviceCapability.PERSON_DETECTION,
        ]

        # Battery support for battery-powered cameras
        if eufy_device.get("battery", 0) > 0:
            capabilities.append(DeviceCapability.BATTERY)

        # Create device info
        device_info = DeviceInfo(
            id=eufy_device.get("serial"),
            name=eufy_device.get("name"),
            type=DeviceType.CAMERA,
            capabilities=capabilities,
            manufacturer="Eufy",
            model=eufy_device.get("model"),
            sw_version=None,
            hw_version=None,
            plugin_id=plugin_id,
        )

        super().__init__(device_info, event_bus)

        self.eufy_device = eufy_device
        self.station_serial = eufy_device.get("station_serial")
        self.bridge_url = bridge_url
        self.session = session

    async def execute_command(self, command: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Execute a command on the camera."""
        params = params or {}
        serial = self.eufy_device.get("serial")

        if command == "start_stream":
            async with self.session.post(
                f"{self.bridge_url}/devices/{serial}/command",
                json={"command": "start_stream"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stream_url = data.get("stream_url")
                    if not stream_url:
                        raise RuntimeError("Bridge did not return stream_url")

                    await self.update_state({"stream_url": stream_url})
                    return {"stream_url": stream_url}
                else:
                    error_text = await resp.text()
                    raise RuntimeError(f"Bridge error: {error_text}")

        elif command == "stop_stream":
            async with self.session.post(
                f"{self.bridge_url}/devices/{serial}/command",
                json={"command": "stop_stream"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    await self.update_state({"stream_url": None})
                    return {"success": True}
                else:
                    raise RuntimeError(f"Failed to stop stream")

        elif command == "get_snapshot":
            return {
                "snapshot_url": f"{self.bridge_url}/devices/{serial}/snapshot"
            }

        else:
            raise ValueError(f"Unknown camera command: {command}")

    async def refresh_state(self) -> DeviceState:
        """Refresh state from the physical device."""
        # State is updated via bridge events, not polling
        state_data = self.eufy_device.get("state", {})

        # Build state
        new_state = {
            "online": state_data.get("enabled", False),
            "motion": state_data.get("motion_detected", False),
        }

        # Battery level - only include if device has battery capability
        battery = self.eufy_device.get("battery", 0)
        if DeviceCapability.BATTERY in self.info.capabilities:
            new_state["battery"] = battery

        # Update state
        await self.update_state(new_state)

        return self.state


class EufySensor(Device):
    """Eufy sensor (motion, door/window)."""

    def __init__(
        self,
        eufy_device: Dict,
        plugin_id: str,
        event_bus: RabbitMQEventBus,
    ):
        # Determine device type and capabilities based on Eufy type code
        device_type_code = eufy_device.get("type", 0)
        model = eufy_device.get("model", "")

        # Type 2 = Entry/Door Sensor (T8900)
        # Type 10 = Motion Sensor (T8910)
        if device_type_code == 10 or "T8910" in model:
            device_type = DeviceType.MOTION_SENSOR
            capabilities = [DeviceCapability.MOTION_DETECTION]
        elif device_type_code == 2 or "T8900" in model:
            device_type = DeviceType.DOOR_SENSOR
            capabilities = [DeviceCapability.CONTACT]
        else:
            device_type = DeviceType.SENSOR
            capabilities = []

        # Add battery capability - Eufy sensors are battery-powered
        capabilities.append(DeviceCapability.BATTERY)

        # Create device info
        device_info = DeviceInfo(
            id=eufy_device.get("serial"),
            name=eufy_device.get("name"),
            type=device_type,
            capabilities=capabilities,
            manufacturer="Eufy",
            model=model,
            sw_version=None,
            hw_version=None,
            plugin_id=plugin_id,
        )

        super().__init__(device_info, event_bus)

        self.eufy_device = eufy_device

    async def execute_command(self, command: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Execute a command on the sensor."""
        # Most sensors don't support commands, but we'll handle any that do
        raise ValueError(f"Sensors do not support commands: {command}")

    async def refresh_state(self) -> DeviceState:
        """Refresh state from the physical device."""
        # State is updated via bridge events, not polling
        state_data = self.eufy_device.get("state", {})

        # Build state
        new_state = {
            "online": state_data.get("enabled", False),
        }

        # Motion detected
        if DeviceCapability.MOTION_DETECTION in self.info.capabilities:
            new_state["motion"] = state_data.get("motion_detected", False)

        # Contact state (door/window open/closed)
        # Note: Eufy Entry Sensors report as open/closed
        if DeviceCapability.CONTACT in self.info.capabilities:
            new_state["contact"] = state_data.get("open", False)

        # Battery level - always include even if 0
        new_state["battery"] = self.eufy_device.get("battery", 0)

        # Update state
        await self.update_state(new_state)

        return self.state
