"""mDNS/Bonjour-based device discovery."""

import asyncio
import logging
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
from zeroconf.asyncio import AsyncZeroconf


logger = logging.getLogger(__name__)


class MDNSDiscovery(ServiceListener):
    """Discover devices on the network using mDNS/Bonjour."""

    def __init__(self, device_registry, event_bus):
        """
        Initialize mDNS discovery.

        Args:
            device_registry: DeviceRegistry instance for storing discovered devices
            event_bus: RabbitMQ event bus for publishing discovery events
        """
        self.registry = device_registry
        self.event_bus = event_bus
        self.aiozc: Optional[AsyncZeroconf] = None
        self.zeroconf: Optional[Zeroconf] = None
        self.browser: Optional[ServiceBrowser] = None
        self._discovered_services: Dict[str, Dict[str, Any]] = {}
        self._event_tasks: List[asyncio.Task] = []  # Track background tasks

    async def start(self) -> None:
        """Start mDNS listener."""
        try:
            logger.info("Starting mDNS discovery service")

            # Create AsyncZeroconf instance
            self.aiozc = AsyncZeroconf()
            self.zeroconf = self.aiozc.zeroconf

            # Browse for all mDNS services
            # Common service types to discover
            service_types = [
                "_services._dns-sd._udp.local.",  # Service discovery meta-query
                "_http._tcp.local.",              # HTTP services
                "_https._tcp.local.",             # HTTPS services
                "_device-info._tcp.local.",       # Device info
                "_airplay._tcp.local.",           # AirPlay devices
                "_raop._tcp.local.",              # AirPlay audio
                "_googlecast._tcp.local.",        # Chromecast
                "_homekit._tcp.local.",           # HomeKit devices
                "_hap._tcp.local.",               # HomeKit Accessory Protocol
                "_companion-link._tcp.local.",    # Apple devices
            ]

            # Start browsing for each service type
            for service_type in service_types:
                try:
                    ServiceBrowser(self.zeroconf, service_type, self)
                    logger.debug(f"Browsing for {service_type}")
                except Exception as e:
                    logger.warning(f"Failed to browse for {service_type}: {e}")

            logger.info("mDNS discovery started successfully")

        except Exception as e:
            logger.error(f"Failed to start mDNS discovery: {e}")
            raise

    async def stop(self) -> None:
        """Stop mDNS listener and cancel pending tasks."""
        try:
            logger.info("Stopping mDNS discovery")

            # Cancel all pending event tasks
            for task in self._event_tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete cancellation
            if self._event_tasks:
                await asyncio.gather(*self._event_tasks, return_exceptions=True)
                self._event_tasks.clear()

            if self.aiozc:
                await self.aiozc.async_close()
                self.aiozc = None
                self.zeroconf = None

            logger.info("mDNS discovery stopped")

        except Exception as e:
            logger.error(f"Error stopping mDNS discovery: {e}")

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """
        Called when a new mDNS service is discovered.

        Args:
            zc: Zeroconf instance
            type_: Service type
            name: Service name
        """
        try:
            info = zc.get_service_info(type_, name)

            if info and info.addresses:
                # Extract device information
                device = {
                    "hostname": info.server.rstrip("."),
                    "ip": socket.inet_ntoa(info.addresses[0]),
                    "port": info.port,
                    "service_type": type_,
                    "service_name": name,
                    "properties": self._parse_properties(info.properties),
                    "discovered_at": datetime.now().isoformat(),
                }

                # Log discovery
                logger.info(
                    f"Discovered mDNS device: {device['hostname']} "
                    f"({device['ip']}) - {type_}"
                )

                # Store in discovered services
                service_key = f"{name}_{type_}"
                self._discovered_services[service_key] = device

                # Register in device database
                self.registry.register_discovered_device(device)

                # Publish discovery event (async) and track task
                try:
                    task = asyncio.create_task(self._publish_discovery_event(device))
                    self._event_tasks.append(task)
                    # Clean completed tasks to avoid memory leak
                    self._event_tasks = [t for t in self._event_tasks if not t.done()]
                except RuntimeError:
                    # If no event loop is running, log and skip
                    logger.debug(f"Cannot publish discovery event (no event loop)")

        except Exception as e:
            logger.debug(f"Error processing mDNS service {name}: {e}")

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """
        Called when an mDNS service is updated.

        Args:
            zc: Zeroconf instance
            type_: Service type
            name: Service name
        """
        logger.debug(f"mDNS service updated: {name} ({type_})")
        # Treat update as a new discovery
        self.add_service(zc, type_, name)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """
        Called when an mDNS service disappears.

        Args:
            zc: Zeroconf instance
            type_: Service type
            name: Service name
        """
        service_key = f"{name}_{type_}"

        if service_key in self._discovered_services:
            device = self._discovered_services[service_key]
            logger.info(
                f"mDNS device disappeared: {device.get('hostname', 'unknown')} "
                f"({device.get('ip', 'unknown')}) - {type_}"
            )
            del self._discovered_services[service_key]

        # Note: We don't mark devices as absent based on mDNS disappearance
        # because devices may stop broadcasting while still present.
        # Ping monitor will handle actual presence detection.

    def _parse_properties(self, properties: Dict[bytes, bytes]) -> Dict[str, str]:
        """
        Parse mDNS service properties.

        Args:
            properties: Raw properties dict

        Returns:
            Decoded properties dict
        """
        parsed = {}
        for key, value in properties.items():
            try:
                parsed[key.decode("utf-8")] = value.decode("utf-8")
            except Exception:
                # Skip properties that can't be decoded
                pass
        return parsed

    async def _publish_discovery_event(self, device: Dict[str, Any]) -> None:
        """
        Publish device discovery event to RabbitMQ.

        Args:
            device: Device information dict
        """
        topic = "network_monitor.discovery.device_discovered"

        payload = {
            "device_hostname": device.get("hostname", "unknown"),
            "device_ip": device.get("ip", "unknown"),
            "service_type": device.get("service_type", "unknown"),
            "service_name": device.get("service_name", "unknown"),
            "properties": device.get("properties", {}),
            "method": "mdns",
            "timestamp": datetime.now().isoformat(),
        }

        try:
            await self.event_bus.publish(topic, payload)
            logger.debug(f"Published discovery event for {device.get('hostname', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to publish discovery event: {e}")

    def get_discovered_devices(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all currently discovered devices.

        Returns:
            Dict of service_key -> device_info
        """
        return self._discovered_services.copy()
