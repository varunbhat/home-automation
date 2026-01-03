"""Base device plugin implementation."""

import asyncio
import logging
from abc import abstractmethod
from typing import Dict, List, Optional

from maneyantra.core.plugin import PluginBase, PluginMetadata, PluginType
from maneyantra.core.rabbitmq_bus import RabbitMQEventBus
from maneyantra.types.devices import DeviceInfo, DeviceState, DeviceCommand, DeviceCapability


class Device:
    """
    Base device class.

    Each device wraps a physical or virtual device and provides:
    - State management
    - Command execution
    - RabbitMQ communication
    """

    def __init__(
        self,
        device_info: DeviceInfo,
        event_bus: RabbitMQEventBus,
    ):
        self.info = device_info
        self.event_bus = event_bus
        self.state = DeviceState()

        self._logger = logging.getLogger(f"device.{device_info.id}")

    @abstractmethod
    async def execute_command(self, command: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Execute a command on the device.

        Args:
            command: Command name (e.g., 'turn_on', 'set_brightness')
            params: Command parameters

        Returns:
            Optional dict with command-specific data (e.g., stream_url)
        """
        pass

    @abstractmethod
    async def refresh_state(self) -> DeviceState:
        """
        Refresh device state from the physical device.

        Returns:
            Updated device state
        """
        pass

    async def update_state(self, new_state: Dict) -> None:
        """
        Update device state and publish to RabbitMQ.

        Args:
            new_state: Partial state update
        """
        # Update state
        for key, value in new_state.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)

        # Publish to RabbitMQ
        await self.event_bus.publish_device_state(
            self.info.id,
            self.state.model_dump(exclude_none=True),
        )

    async def set_available(self, available: bool) -> None:
        """
        Update device availability.

        Args:
            available: Whether device is online/available
        """
        self.state.online = available
        await self.event_bus.publish_device_available(self.info.id, available)

    def has_capability(self, capability: DeviceCapability) -> bool:
        """Check if device has a capability."""
        return capability in self.info.capabilities


class BaseDevicePlugin(PluginBase):
    """
    Base class for device plugins.

    Device plugins are responsible for:
    - Discovering devices
    - Managing device lifecycle
    - Handling device commands via RabbitMQ
    - Publishing device state updates
    """

    def __init__(
        self,
        plugin_id: str,
        metadata: PluginMetadata,
        config: Dict,
        event_bus: RabbitMQEventBus,
    ):
        super().__init__(plugin_id, metadata, config, event_bus)

        self.devices: Dict[str, Device] = {}
        self._command_task: Optional[asyncio.Task] = None

    @abstractmethod
    async def discover_devices(self) -> List[Device]:
        """
        Discover devices.

        Returns:
            List of discovered devices
        """
        pass

    async def add_device(self, device: Device) -> None:
        """
        Add a device to the plugin.

        Args:
            device: Device to add
        """
        self.devices[device.info.id] = device

        # Publish device discovery
        await self.event_bus.publish(
            f"device.discovery.{device.info.id}",
            {
                "device": device.info.model_dump(),
                "plugin_id": self.plugin_id,
            },
        )

        # Set device as available
        await device.set_available(True)

        # Subscribe to device commands
        await self.event_bus.subscribe_device_commands(
            device.info.id,
            lambda topic, payload: self._handle_device_command(device.info.id, payload),
        )

        self._logger.info(f"Added device: {device.info.name} ({device.info.id})")

    async def remove_device(self, device_id: str) -> None:
        """
        Remove a device from the plugin.

        Args:
            device_id: Device ID to remove
        """
        device = self.devices.get(device_id)
        if not device:
            return

        # Set device as unavailable
        await device.set_available(False)

        # Publish removal
        await self.event_bus.publish(
            f"device.removed.{device_id}",
            {"plugin_id": self.plugin_id},
        )

        # Remove from devices
        del self.devices[device_id]

        self._logger.info(f"Removed device: {device_id}")

    def get_device(self, device_id: str) -> Optional[Device]:
        """Get a device by ID."""
        return self.devices.get(device_id)

    def get_devices(self) -> List[Device]:
        """Get all devices."""
        return list(self.devices.values())

    async def _handle_device_command(self, device_id: str, payload: Dict) -> None:
        """
        Handle device command from MQTT.

        Args:
            device_id: Device ID
            payload: Command payload
        """
        device = self.devices.get(device_id)
        if not device:
            self._logger.warning(f"Command for unknown device: {device_id}")
            return

        try:
            command = payload.get("command")
            params = payload.get("params", {})

            if not command:
                self._logger.warning(f"Command missing in payload: {payload}")
                return

            self._logger.info(f"Executing command '{command}' on device {device_id}")

            # Execute command
            await device.execute_command(command, params)

            # Refresh state after command
            await device.refresh_state()

        except Exception as e:
            self._logger.error(
                f"Error executing command on device {device_id}: {e}",
                exc_info=True,
            )

            # Publish error
            await self.event_bus.publish(
                f"device.{device_id}.error",
                {"error": str(e), "command": payload.get("command")},
            )

    async def start(self) -> None:
        """Start the device plugin."""
        # Discover devices
        self._logger.info("Discovering devices...")
        discovered_devices = await self.discover_devices()

        # Add discovered devices
        for device in discovered_devices:
            await self.add_device(device)

        self._logger.info(f"Discovered {len(discovered_devices)} devices")

    async def stop(self) -> None:
        """Stop the device plugin."""
        # Mark all devices as unavailable
        for device in self.devices.values():
            await device.set_available(False)

        # Clear devices
        self.devices.clear()
