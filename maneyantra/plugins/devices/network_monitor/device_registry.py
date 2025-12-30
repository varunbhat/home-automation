"""Device registry for storing and managing discovered devices."""

import json
import logging
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


class DeviceRegistry:
    """Stores discovered devices and their metadata."""

    def __init__(self, storage_path: str = "data/devices.json"):
        """
        Initialize device registry.

        Args:
            storage_path: Path to JSON file for persistent storage
        """
        self.storage_path = Path(storage_path)
        self.devices: Dict[str, Dict] = {}  # mac -> device_info
        self.load()

    def load(self) -> None:
        """Load devices from storage."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path) as f:
                    self.devices = json.load(f)
                logger.info(f"Loaded {len(self.devices)} devices from registry")
            else:
                logger.info("No existing device registry found, starting fresh")
                self.devices = {}
        except Exception as e:
            logger.error(f"Failed to load device registry: {e}")
            self.devices = {}

    def save(self) -> None:
        """Save devices to storage."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w") as f:
                json.dump(self.devices, f, indent=2)
            logger.debug(f"Saved {len(self.devices)} devices to registry")
        except Exception as e:
            logger.error(f"Failed to save device registry: {e}")

    def register_discovered_device(self, device: Dict) -> Optional[str]:
        """
        Register newly discovered device.

        Args:
            device: Device info dict with optional 'mac', 'ip', 'hostname' keys

        Returns:
            MAC address if successfully registered, None otherwise
        """
        try:
            mac = device.get("mac")

            # If MAC not provided, try to resolve from IP
            if not mac and device.get("ip"):
                mac = self._get_mac_from_ip(device["ip"])

            if not mac:
                logger.debug(
                    f"Cannot register device without MAC address: "
                    f"{device.get('hostname', 'unknown')}"
                )
                return None

            # Normalize MAC address (uppercase, colon-separated)
            mac = self._normalize_mac(mac)

            # Check if device already exists
            if mac in self.devices:
                # Update existing device info
                existing = self.devices[mac]
                existing.update({
                    "ip": device.get("ip", existing.get("ip")),
                    "hostname": device.get("hostname", existing.get("hostname")),
                    "last_seen": datetime.now().isoformat(),
                })

                # Add service type if from mDNS
                if device.get("service_type"):
                    if "service_types" not in existing:
                        existing["service_types"] = []
                    if device["service_type"] not in existing["service_types"]:
                        existing["service_types"].append(device["service_type"])

                logger.debug(f"Updated device {mac} in registry")

            else:
                # Register new device
                self.devices[mac] = {
                    "mac": mac,
                    "ip": device.get("ip", "unknown"),
                    "hostname": device.get("hostname", "unknown"),
                    "name": device.get("name", device.get("hostname", "Unknown Device")),
                    "discovered_via": device.get("method", "unknown"),
                    "first_seen": datetime.now().isoformat(),
                    "last_seen": datetime.now().isoformat(),
                    "track": device.get("track", True),
                }

                # Add service type if from mDNS
                if device.get("service_type"):
                    self.devices[mac]["service_types"] = [device["service_type"]]

                logger.info(
                    f"Registered new device: {device.get('name', 'unknown')} "
                    f"({mac}) at {device.get('ip', 'unknown')}"
                )

            self.save()
            return mac

        except Exception as e:
            logger.error(f"Failed to register device: {e}")
            return None

    def get_device(self, mac: str) -> Optional[Dict]:
        """
        Get device info by MAC address.

        Args:
            mac: Device MAC address

        Returns:
            Device info dict or None
        """
        mac = self._normalize_mac(mac)
        return self.devices.get(mac)

    def get_all_tracked_devices(self) -> List[Dict]:
        """
        Get all devices that should be tracked for presence.

        Returns:
            List of device info dicts
        """
        return [
            device
            for device in self.devices.values()
            if device.get("track", True)
        ]

    def set_device_name(self, mac: str, name: str):
        """
        Set friendly name for a device.

        Args:
            mac: Device MAC address
            name: Friendly name
        """
        mac = self._normalize_mac(mac)
        if mac in self.devices:
            self.devices[mac]["name"] = name
            self.save()
            logger.info(f"Updated device name for {mac} to {name}")

    def set_device_tracking(self, mac: str, track: bool):
        """
        Enable or disable presence tracking for a device.

        Args:
            mac: Device MAC address
            track: Whether to track this device
        """
        mac = self._normalize_mac(mac)
        if mac in self.devices:
            self.devices[mac]["track"] = track
            self.save()
            logger.info(f"Set tracking for {mac} to {track}")

    def update_device_ip(self, mac: str, ip: str):
        """
        Update device IP address (for DHCP scenarios).

        Args:
            mac: Device MAC address
            ip: New IP address
        """
        mac = self._normalize_mac(mac)
        if mac in self.devices:
            old_ip = self.devices[mac].get("ip")
            if old_ip != ip:
                self.devices[mac]["ip"] = ip
                self.devices[mac]["last_ip_change"] = datetime.now().isoformat()
                self.save()
                logger.info(f"Updated IP for {mac} from {old_ip} to {ip}")

    def _get_mac_from_ip(self, ip: str) -> Optional[str]:
        """
        Resolve MAC address from IP using ARP table.

        Args:
            ip: IP address

        Returns:
            MAC address or None
        """
        try:
            # Use system ARP command
            result = subprocess.run(
                ["arp", "-n", ip],
                capture_output=True,
                text=True,
                timeout=2
            )

            # Parse ARP output
            # macOS format: hostname (192.168.1.100) at aa:bb:cc:dd:ee:ff
            # Linux format: Address HWtype HWaddress Flags Mask Iface
            for line in result.stdout.split("\n"):
                # Try macOS format
                match = re.search(r"at ([0-9a-f:]{17})", line, re.IGNORECASE)
                if match:
                    return match.group(1)

                # Try Linux format
                match = re.search(r"([0-9a-f:]{17})", line, re.IGNORECASE)
                if match:
                    return match.group(1)

            return None

        except Exception as e:
            logger.debug(f"Failed to resolve MAC from IP {ip}: {e}")
            return None

    def _normalize_mac(self, mac: str) -> str:
        """
        Normalize MAC address to uppercase colon-separated format.

        Args:
            mac: MAC address in any format

        Returns:
            Normalized MAC address (e.g., AA:BB:CC:DD:EE:FF)

        Raises:
            ValueError: If MAC address is invalid
        """
        # Remove any separators
        mac_clean = re.sub(r"[:-]", "", mac)

        # Validate: must be exactly 12 hex characters
        if len(mac_clean) != 12:
            raise ValueError(
                f"Invalid MAC address length: {mac} (expected 12 hex digits, got {len(mac_clean)})"
            )

        if not re.match(r'^[0-9a-fA-F]{12}$', mac_clean):
            raise ValueError(
                f"Invalid MAC address format: {mac} (must contain only hex digits)"
            )

        # Add colons every 2 characters
        mac_formatted = ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))
        return mac_formatted.upper()

    def get_device_count(self) -> int:
        """Get total number of registered devices."""
        return len(self.devices)

    def get_tracked_device_count(self) -> int:
        """Get number of devices being tracked."""
        return len(self.get_all_tracked_devices())
