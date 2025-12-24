"""TP-Link Smart Home plugin."""

import asyncio
from typing import Dict, List

from kasa import Discover, Device as KasaDevice

from maneyantra.core.plugin import PluginMetadata, PluginType
from maneyantra.core.rabbitmq_bus import RabbitMQEventBus
from maneyantra.plugins.devices.base import BaseDevicePlugin, Device
from maneyantra.types.devices import DeviceInfo, DeviceType, DeviceCapability, DeviceState

from .devices import TpLinkLight, TpLinkPlug


class TpLinkPlugin(BaseDevicePlugin):
    """
    TP-Link Kasa smart home device plugin.

    Supports:
    - Smart bulbs (with brightness and color)
    - Smart plugs and switches
    - Auto-discovery on local network
    """

    def __init__(
        self,
        plugin_id: str,
        config: Dict,
        event_bus: RabbitMQEventBus,
    ):
        metadata = PluginMetadata(
            name="TP-Link Kasa",
            version="0.1.0",
            plugin_type=PluginType.DEVICE,
            description="TP-Link Kasa smart home devices integration",
            capabilities=["discovery", "lights", "switches", "plugs"],
        )

        super().__init__(plugin_id, metadata, config, event_bus)

        self._discovery_interval = self.get_config("discovery_interval", 300)
        self._discovery_task: asyncio.Task = None

    async def initialize(self) -> None:
        """Initialize the TP-Link plugin."""
        self._logger.info("TP-Link plugin initialized")

    async def discover_devices(self) -> List[Device]:
        """Discover TP-Link devices on the network."""
        self._logger.info("Discovering TP-Link devices...")

        discovered_devices = []

        try:
            # Get broadcast address from config, fallback to network-specific address for macOS
            broadcast_address = self.get_config("broadcast_address", "192.168.86.255")
            timeout = self.get_config("discovery_timeout", 10)

            # Discover devices on local network
            self._logger.debug(f"Using broadcast address: {broadcast_address}, timeout: {timeout}s")
            found_devices = await Discover.discover(target=broadcast_address, timeout=timeout)

            for host, kasa_device in found_devices.items():
                try:
                    # Try to update device info, but continue even if it fails
                    # Some TP-Link devices respond to discovery but block TCP connections
                    try:
                        await kasa_device.update()
                    except Exception as update_error:
                        self._logger.warning(
                            f"Could not update device at {host}, using discovery data only: {update_error}"
                        )

                    # Create wrapper device
                    device = self._create_device(kasa_device)

                    if device:
                        discovered_devices.append(device)
                        device_type = type(kasa_device).__name__
                        self._logger.info(
                            f"Discovered: {device_type} at {host}"
                        )

                except Exception as e:
                    self._logger.error(f"Error processing device at {host}: {e}")

        except Exception as e:
            self._logger.error(f"Discovery error: {e}", exc_info=True)

        return discovered_devices

    def _create_device(self, kasa_device: KasaDevice) -> Device:
        """Create appropriate device wrapper based on device type."""
        # Determine device type
        if kasa_device.is_bulb:
            return TpLinkLight(kasa_device, self.plugin_id, self.event_bus)
        elif kasa_device.is_plug or kasa_device.is_strip:
            # is_plug includes wall switches, plugs, and power strips
            return TpLinkPlug(kasa_device, self.plugin_id, self.event_bus)
        else:
            # For unknown types or devices without update data, try creating as plug
            self._logger.warning(
                f"Unknown or uninitialized device type: {kasa_device.device_type}, treating as switch/plug"
            )
            return TpLinkPlug(kasa_device, self.plugin_id, self.event_bus)

    async def start(self) -> None:
        """Start the TP-Link plugin."""
        await super().start()

        # Start periodic discovery if configured
        if self._discovery_interval > 0:
            self._discovery_task = asyncio.create_task(self._periodic_discovery())

    async def stop(self) -> None:
        """Stop the TP-Link plugin."""
        # Stop discovery task
        if self._discovery_task:
            self._discovery_task.cancel()
            try:
                await self._discovery_task
            except asyncio.CancelledError:
                pass

        await super().stop()

    async def _periodic_discovery(self) -> None:
        """Periodically discover new devices."""
        while True:
            try:
                await asyncio.sleep(self._discovery_interval)

                self._logger.debug("Running periodic discovery...")
                new_devices = await self.discover_devices()

                # Add only new devices
                for device in new_devices:
                    if device.info.id not in self.devices:
                        await self.add_device(device)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in periodic discovery: {e}", exc_info=True)
