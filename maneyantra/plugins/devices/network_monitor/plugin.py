"""Network monitoring plugin for device presence detection."""

import asyncio
from typing import Any, Dict, List, Optional

from maneyantra.core.plugin import PluginMetadata, PluginType
from maneyantra.core.rabbitmq_bus import RabbitMQEventBus
from maneyantra.plugins.devices.base import BaseDevicePlugin, Device

from .devices import NetworkDevice
from .device_registry import DeviceRegistry
from .mdns_discovery import MDNSDiscovery


class NetworkMonitorPlugin(BaseDevicePlugin):
    """
    Network monitoring plugin for device presence detection.

    Discovers network devices from configuration and mDNS broadcasts,
    then monitors their presence using ICMP ping.
    """

    def __init__(self, plugin_id: str, config: Dict[str, Any], event_bus: RabbitMQEventBus):
        """
        Initialize network monitoring plugin.

        Args:
            plugin_id: Plugin identifier
            config: Plugin configuration
            event_bus: RabbitMQ event bus
        """
        metadata = PluginMetadata(
            name="Network Monitor",
            version="1.0.0",
            plugin_type=PluginType.DEVICE,
            description="Network device presence detection via ping and mDNS",
        )
        super().__init__(plugin_id, metadata, config, event_bus)

        # Configuration
        self.poll_interval = config.get("poll_interval", 30)
        self.ping_config = config.get("methods", {}).get("ping", {})

        # Device registry for persistence
        storage_path = config.get("storage_path", "data/devices.json")
        self.registry = DeviceRegistry(storage_path)

        # mDNS discovery (optional)
        mdns_config = config.get("methods", {}).get("mdns", {})
        self.mdns_enabled = mdns_config.get("enabled", True)
        self.mdns_discovery: Optional[MDNSDiscovery] = None
        if self.mdns_enabled:
            self.mdns_discovery = MDNSDiscovery(self.registry, event_bus)

        # Refresh task
        self._refresh_task: Optional[asyncio.Task] = None

    async def discover_devices(self) -> List[Device]:
        """
        Discover network devices from config.

        Returns:
            List of NetworkDevice instances
        """
        self._logger.info("Discovering network devices...")

        devices = []

        # Load manually configured devices from config
        known_devices = self.config.get("known_devices", [])
        if known_devices:
            self._logger.info(f"Loading {len(known_devices)} configured devices")
            for device_config in known_devices:
                # Create NetworkDevice instance
                device = NetworkDevice(
                    device_config,
                    self.plugin_id,
                    self.event_bus,
                    self.ping_config,
                )
                devices.append(device)

        self._logger.info(f"Discovered {len(devices)} network devices")
        return devices

    async def initialize(self) -> None:
        """Initialize the plugin (required by PluginBase)."""
        # Start mDNS discovery if enabled
        if self.mdns_enabled and self.mdns_discovery:
            await self.mdns_discovery.start()
            self._logger.info("mDNS discovery started")

    async def start(self) -> None:
        """Start the plugin."""
        # Initialize plugin resources first
        await self.initialize()

        # Call parent start() which will:
        # 1. Call discover_devices()
        # 2. Add each device via add_device()
        # 3. Set up command subscriptions
        await super().start()

        # Start periodic state refresh
        self._refresh_task = asyncio.create_task(self._refresh_loop())
        self._logger.info(f"Started periodic refresh every {self.poll_interval}s")

    async def stop(self) -> None:
        """Stop the plugin and clean up resources."""
        # Stop refresh task
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self._logger.error(f"Error stopping refresh task: {e}", exc_info=True)

        # Stop mDNS discovery
        if self.mdns_discovery:
            try:
                await self.mdns_discovery.stop()
            except Exception as e:
                self._logger.error(f"Error stopping mDNS discovery: {e}", exc_info=True)

        # Call parent stop to mark devices unavailable
        try:
            await super().stop()
        except Exception as e:
            self._logger.error(f"Error in parent stop: {e}", exc_info=True)

        # Save registry after all cleanup (to capture final states)
        try:
            self.registry.save()
        except Exception as e:
            self._logger.error(f"Error saving device registry: {e}", exc_info=True)

    async def _refresh_loop(self) -> None:
        """
        Periodically refresh all device states.

        Refreshes immediately on start, then every poll_interval seconds.
        Uses semaphore to limit concurrent pings to avoid network overload.
        """
        # Semaphore to limit concurrent pings (max 20 at once)
        semaphore = asyncio.Semaphore(20)

        async def bounded_refresh(device: Device) -> None:
            """Refresh a single device with concurrency limiting."""
            async with semaphore:
                try:
                    await device.refresh_state()
                except Exception as e:
                    self._logger.error(
                        f"Failed to refresh device {device.info.name}: {e}",
                        exc_info=True
                    )

        while True:
            try:
                # Create snapshot to avoid race condition during iteration
                devices_snapshot = list(self.devices.values())

                # Refresh all devices with bounded concurrency
                tasks = [
                    bounded_refresh(device)
                    for device in devices_snapshot
                ]

                # Gather with return_exceptions=True to prevent loop crash
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Log any exceptions that occurred
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        device_name = devices_snapshot[i].info.name if i < len(devices_snapshot) else "unknown"
                        self._logger.error(
                            f"Device refresh failed for {device_name}: {result}",
                            exc_info=result
                        )

                # Wait before next refresh cycle
                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                self._logger.debug("Refresh loop cancelled")
                break
            except Exception as e:
                self._logger.error(f"Unexpected error in refresh loop: {e}", exc_info=True)

