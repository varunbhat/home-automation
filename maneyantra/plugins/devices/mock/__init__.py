"""Mock devices plugin for testing the UI."""

import logging
from typing import Dict, Any, Optional

from maneyantra.plugins.devices.base import BaseDevicePlugin, Device
from maneyantra.core.plugin import PluginMetadata, PluginType
from maneyantra.types.devices import (
    DeviceInfo,
    DeviceState,
    DeviceType,
    DeviceCapability,
    DeviceCommand,
)

logger = logging.getLogger(__name__)


class MockDevicesPlugin(BaseDevicePlugin):
    """Plugin that provides mock devices for UI testing."""

    def __init__(self, plugin_id: str, config: Dict[str, Any], event_bus):
        metadata = PluginMetadata(
            name="Mock Devices",
            version="1.0.0",
            plugin_type=PluginType.DEVICE,
            description="Mock devices for UI testing",
            capabilities=["lights", "switches", "sensors", "cameras", "plugs"],
        )
        super().__init__(plugin_id, metadata, config, event_bus)

    async def initialize(self) -> None:
        """Initialize the plugin."""
        logger.info("Mock devices plugin initialized")

    async def start(self) -> None:
        """Start the plugin and register mock devices."""
        logger.info("Starting mock devices plugin...")

        # Create test devices
        test_devices = [
            (
                DeviceInfo(
                    id="mock-light-1",
                    name="Living Room Light",
                    type=DeviceType.LIGHT,
                    capabilities=[
                        DeviceCapability.ON_OFF,
                        DeviceCapability.BRIGHTNESS,
                        DeviceCapability.COLOR,
                    ],
                    manufacturer="Philips",
                    model="Hue A19",
                    plugin_id=self.plugin_id,
                    room="Living Room",
                    tags=["smart", "rgb"],
                ),
                DeviceState(
                    online=True,
                    on=True,
                    brightness=75,
                    color={"hue": 210, "saturation": 80, "value": 75},
                ),
            ),
            (
                DeviceInfo(
                    id="mock-light-2",
                    name="Bedroom Light",
                    type=DeviceType.LIGHT,
                    capabilities=[
                        DeviceCapability.ON_OFF,
                        DeviceCapability.BRIGHTNESS,
                        DeviceCapability.COLOR_TEMPERATURE,
                    ],
                    manufacturer="IKEA",
                    model="Tradfri E27",
                    plugin_id=self.plugin_id,
                    room="Bedroom",
                    tags=["smart"],
                ),
                DeviceState(
                    online=True,
                    on=False,
                    brightness=50,
                    color_temperature=4000,
                ),
            ),
            (
                DeviceInfo(
                    id="mock-switch-1",
                    name="Kitchen Switch",
                    type=DeviceType.SWITCH,
                    capabilities=[DeviceCapability.ON_OFF],
                    manufacturer="TP-Link",
                    model="HS200",
                    plugin_id=self.plugin_id,
                    room="Kitchen",
                ),
                DeviceState(
                    online=True,
                    on=True,
                ),
            ),
            (
                DeviceInfo(
                    id="mock-sensor-1",
                    name="Living Room Sensor",
                    type=DeviceType.SENSOR,
                    capabilities=[
                        DeviceCapability.TEMPERATURE,
                        DeviceCapability.HUMIDITY,
                        DeviceCapability.BATTERY,
                    ],
                    manufacturer="Aqara",
                    model="Temp & Humidity",
                    plugin_id=self.plugin_id,
                    room="Living Room",
                ),
                DeviceState(
                    online=True,
                    temperature=22.5,
                    humidity=45,
                    battery=87,
                ),
            ),
            (
                DeviceInfo(
                    id="mock-camera-1",
                    name="Front Door Camera",
                    type=DeviceType.CAMERA,
                    capabilities=[
                        DeviceCapability.VIDEO_STREAM,
                        DeviceCapability.MOTION_DETECTION,
                        DeviceCapability.PERSON_DETECTION,
                    ],
                    manufacturer="Eufy",
                    model="2C Pro",
                    plugin_id=self.plugin_id,
                    room="Entrance",
                    tags=["security"],
                ),
                DeviceState(
                    online=True,
                    motion=False,
                    battery=65,
                ),
            ),
            (
                DeviceInfo(
                    id="mock-plug-1",
                    name="Coffee Maker",
                    type=DeviceType.PLUG,
                    capabilities=[
                        DeviceCapability.ON_OFF,
                        DeviceCapability.POWER_MONITORING,
                        DeviceCapability.ENERGY_MONITORING,
                    ],
                    manufacturer="TP-Link",
                    model="HS110",
                    plugin_id=self.plugin_id,
                    room="Kitchen",
                ),
                DeviceState(
                    online=True,
                    on=False,
                    power=0.0,
                    energy=12.5,
                    voltage=120.2,
                    current=0.0,
                ),
            ),
        ]

        # Register devices
        for info, state in test_devices:
            # Create Device object
            device = Device(device_info=info, event_bus=self.event_bus)
            device.state = state

            # Add device using base class method (handles discovery publishing)
            await self.add_device(device)
            logger.info(f"Registered mock device: {info.name} ({info.id})")

        logger.info(f"Mock devices plugin started with {len(self.devices)} devices")

    async def stop(self) -> None:
        """Stop the plugin."""
        logger.info("Stopping mock devices plugin...")
        self.devices.clear()

    async def discover_devices(self) -> None:
        """Discover devices (no-op for mock plugin)."""
        logger.info("Mock plugin discovery requested - devices already registered")

    async def execute_command(
        self, device_id: str, command: DeviceCommand
    ) -> Optional[DeviceState]:
        """Execute a command on a device."""
        if device_id not in self.devices:
            logger.error(f"Device not found: {device_id}")
            return None

        device = self.devices[device_id]
        logger.info(f"Executing command on {device.info.name}: {command.command}")

        # Simulate command execution
        new_state = device.state.model_copy(deep=True)

        if command.command == "turn_on":
            new_state.on = True
        elif command.command == "turn_off":
            new_state.on = False
        elif command.command == "toggle":
            new_state.on = not device.state.on
        elif command.command == "set_brightness":
            if command.params and "brightness" in command.params:
                new_state.brightness = int(command.params["brightness"])
        elif command.command == "set_color_temperature":
            if command.params and "temperature" in command.params:
                new_state.color_temperature = int(command.params["temperature"])
        elif command.command == "set_hsv":
            if command.params:
                new_state.color = {
                    "hue": int(command.params.get("hue", 0)),
                    "saturation": int(command.params.get("saturation", 0)),
                    "value": int(command.params.get("value", 0)),
                }

        # Update device state
        device.state = new_state

        # Publish state update
        await self.event_bus.publish_device_state(device_id, new_state)

        return new_state


# Plugin entry point
def create_plugin(config: Dict[str, Any], event_bus) -> MockDevicesPlugin:
    """Create and return the plugin instance."""
    return MockDevicesPlugin(config, event_bus)
