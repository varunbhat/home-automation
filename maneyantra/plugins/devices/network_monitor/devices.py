"""Network device for presence detection."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from icmplib import async_ping

from maneyantra.core.rabbitmq_bus import RabbitMQEventBus
from maneyantra.plugins.devices.base import Device
from maneyantra.types.devices import (
    DeviceInfo,
    DeviceType,
    DeviceCapability,
    DeviceState,
)


class NetworkDevice(Device):
    """
    A network-connected device tracked by presence detection.

    Uses ICMP ping to detect device presence on the network.
    """

    def __init__(
        self,
        device_config: Dict[str, Any],
        plugin_id: str,
        event_bus: RabbitMQEventBus,
        ping_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize network device.

        Args:
            device_config: Device configuration with mac, ip, name
            plugin_id: Plugin identifier
            event_bus: RabbitMQ event bus
            ping_config: Ping configuration (timeout, count)
        """
        # Extract device info
        mac = device_config["mac"]
        ip = device_config["ip"]
        name = device_config.get("name", f"Device {ip}")

        # Create device info
        device_info = DeviceInfo(
            id=f"network_{mac.replace(':', '_').lower()}",
            name=name,
            type=DeviceType.SENSOR,  # Network devices are sensors
            capabilities=[DeviceCapability.PRESENCE_DETECTION],
            manufacturer="Network",
            model="IP Device",
            plugin_id=plugin_id,
        )

        super().__init__(device_info, event_bus)

        # Store network info
        self.mac = mac
        self.ip = ip
        self.ping_config = ping_config or {"timeout": 2, "count": 1}
        self._last_seen: Optional[str] = None

    async def execute_command(self, command: str, params: Optional[Dict] = None) -> None:
        """
        Execute device command.

        Network devices don't support commands.

        Raises:
            NotImplementedError: Always raised as network devices don't support commands
        """
        raise NotImplementedError(
            f"Network devices don't support commands (attempted: {command})"
        )

    async def refresh_state(self) -> DeviceState:
        """
        Refresh device state by pinging it.

        Returns:
            Updated device state
        """
        try:
            # Ping device
            is_present = await self._ping_device()

            # Update last seen if present
            if is_present:
                self._last_seen = datetime.now().isoformat()

            # Update state
            new_state = {
                "online": is_present,
                "custom": {
                    "ip": self.ip,
                    "mac": self.mac,
                    "last_seen": self._last_seen,
                    "checked_at": datetime.now().isoformat(),
                },
            }

            await self.update_state(new_state)
            return self.state

        except Exception as e:
            self._logger.error(f"Failed to refresh state for {self.info.name}: {e}")
            await self.set_available(False)
            return self.state

    async def _ping_device(self) -> bool:
        """
        Ping device to check presence.

        Returns:
            True if device responds, False otherwise
        """
        try:
            host = await async_ping(
                self.ip,
                count=self.ping_config.get("count", 1),
                timeout=self.ping_config.get("timeout", 2),
                privileged=False,
            )
            return host.is_alive
        except Exception as e:
            self._logger.debug(f"Ping failed for {self.ip}: {e}")
            return False
