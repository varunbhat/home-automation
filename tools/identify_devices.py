#!/usr/bin/env python3
"""Identify devices on the network by MAC address vendor lookup and mDNS."""

import asyncio
import logging
import subprocess
import re
import sys
import os
from typing import Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
import socket

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


# Common MAC address OUI (Organizationally Unique Identifier) to manufacturer mapping
MAC_OUI_DATABASE = {
    "60:83:E7": "TP-Link",
    "24:2F:D0": "Anker (Eufy)",
    "E4:FA:C4": "Anker (Eufy)",
    "48:E1:5C": "Unknown",
    "A8:42:A1": "Unknown",
    "90:09:D0": "Unknown",
    "10:2C:B1": "Unknown",
    "04:17:B6": "Unknown",
    "C0:F5:35": "Unknown",
    "02:56:D7": "Locally Administered (Virtual)",
    "2E:71:60": "Locally Administered (Virtual)",
}


class DeviceIdentifier(ServiceListener):
    """Identify devices using mDNS and other methods."""

    def __init__(self):
        self.mdns_devices = {}
        self.hostname_to_ip = {}

    def add_service(self, zc: Zeroconf, type_: str, name: str):
        """New mDNS service discovered."""
        try:
            info = zc.get_service_info(type_, name)
            if info and info.addresses:
                hostname = info.server.rstrip('.')
                ip = socket.inet_ntoa(info.addresses[0])

                # Store hostname to IP mapping
                self.hostname_to_ip[ip] = hostname

                # Store service info
                if ip not in self.mdns_devices:
                    self.mdns_devices[ip] = {
                        'hostname': hostname,
                        'services': [],
                        'properties': {}
                    }

                # Add service type
                if type_ not in self.mdns_devices[ip]['services']:
                    self.mdns_devices[ip]['services'].append(type_)

                # Parse properties
                for key, value in info.properties.items():
                    try:
                        k = key.decode('utf-8')
                        v = value.decode('utf-8')
                        self.mdns_devices[ip]['properties'][k] = v
                    except:
                        pass

        except Exception as e:
            pass

    def update_service(self, zc: Zeroconf, type_: str, name: str):
        """Service updated."""
        self.add_service(zc, type_, name)

    def remove_service(self, zc: Zeroconf, type_: str, name: str):
        """Service removed."""
        pass


def get_arp_table() -> Dict[str, Dict[str, str]]:
    """Get ARP table with IP and MAC addresses."""
    devices = {}

    try:
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True)

        for line in result.stdout.split('\n'):
            # Parse: ? (192.168.86.1) at 60:83:e7:43:44:0 on en1 ifscope [ethernet]
            match = re.search(r'\(([\d.]+)\) at ([0-9a-f:]+)', line, re.IGNORECASE)
            if match:
                ip, mac = match.groups()
                # Skip incomplete entries and broadcast
                if 'incomplete' not in line and mac != 'ff:ff:ff:ff:ff:ff':
                    devices[ip] = {
                        'mac': mac.upper(),
                        'ip': ip
                    }
    except Exception as e:
        logger.error(f"Failed to get ARP table: {e}")

    return devices


def identify_vendor(mac: str) -> str:
    """Identify device vendor from MAC address OUI."""
    # Get first 3 octets (OUI)
    oui = ':'.join(mac.split(':')[:3])
    return MAC_OUI_DATABASE.get(oui, "Unknown Vendor")


def identify_device_type(services: List[str], properties: Dict[str, str]) -> str:
    """Identify device type from mDNS services."""
    device_types = []

    for service in services:
        if '_airplay._tcp' in service:
            device_types.append("AirPlay Device")
        elif '_googlecast._tcp' in service:
            device_types.append("Chromecast")
        elif '_homekit._tcp' in service or '_hap._tcp' in service:
            device_types.append("HomeKit Device")
        elif '_printer._tcp' in service:
            device_types.append("Printer")
        elif '_http._tcp' in service:
            device_types.append("Web Server")
        elif '_ssh._tcp' in service:
            device_types.append("SSH Server")
        elif '_companion-link._tcp' in service:
            device_types.append("Apple Device")
        elif '_raop._tcp' in service:
            device_types.append("AirPlay Audio")

    if not device_types:
        return "Unknown Device"

    return ", ".join(set(device_types))


async def scan_network():
    """Scan network and identify devices."""
    logger.info("="*80)
    logger.info("Device Identification Tool")
    logger.info("="*80)
    logger.info("")

    # Step 1: Get ARP table
    logger.info("Step 1: Reading ARP table...")
    arp_devices = get_arp_table()
    logger.info(f"   Found {len(arp_devices)} devices in ARP table")
    logger.info("")

    # Step 2: Start mDNS discovery
    logger.info("Step 2: Starting mDNS discovery (15 seconds)...")
    identifier = DeviceIdentifier()
    zeroconf = Zeroconf()

    # Browse for various service types
    service_types = [
        "_services._dns-sd._udp.local.",
        "_http._tcp.local.",
        "_airplay._tcp.local.",
        "_googlecast._tcp.local.",
        "_homekit._tcp.local.",
        "_hap._tcp.local.",
        "_companion-link._tcp.local.",
        "_raop._tcp.local.",
        "_ssh._tcp.local.",
    ]

    for service_type in service_types:
        try:
            ServiceBrowser(zeroconf, service_type, identifier)
        except:
            pass

    # Wait for discoveries
    await asyncio.sleep(15)

    logger.info(f"   Found {len(identifier.mdns_devices)} devices via mDNS")
    logger.info("")

    # Step 3: Try to ping devices to check if they're online
    logger.info("Step 3: Checking device availability (ping)...")

    from icmplib import ping

    online_devices = set()
    for ip in arp_devices.keys():
        try:
            # Skip special addresses
            if ip.startswith('169.254') or ip.startswith('224.') or ip.startswith('239.'):
                continue

            host = ping(ip, count=1, timeout=1, privileged=False)
            if host.is_alive:
                online_devices.add(ip)
        except:
            pass

    logger.info(f"   {len(online_devices)} devices are currently online")
    logger.info("")

    # Step 4: Compile and display results
    logger.info("="*80)
    logger.info("Device Identification Results")
    logger.info("="*80)
    logger.info("")

    # Combine all information
    all_devices = []

    for ip, arp_info in sorted(arp_devices.items()):
        # Skip special addresses
        if ip.startswith('224.') or ip.startswith('239.'):
            continue

        mac = arp_info['mac']
        vendor = identify_vendor(mac)
        is_online = ip in online_devices

        # Get mDNS info
        mdns_info = identifier.mdns_devices.get(ip, {})
        hostname = mdns_info.get('hostname', identifier.hostname_to_ip.get(ip, '-'))
        services = mdns_info.get('services', [])
        properties = mdns_info.get('properties', {})

        device_type = identify_device_type(services, properties)

        device = {
            'ip': ip,
            'mac': mac,
            'vendor': vendor,
            'hostname': hostname,
            'type': device_type,
            'online': is_online,
            'services': services,
            'properties': properties
        }

        all_devices.append(device)

    # Display organized by vendor/type
    logger.info(f"{'Status':<8} {'IP Address':<16} {'MAC Address':<18} {'Vendor':<20} {'Hostname':<25} {'Type'}")
    logger.info("-" * 140)

    for device in all_devices:
        status = "✅ ONLINE" if device['online'] else "❌ Offline"

        # Truncate long hostnames
        hostname = device['hostname'][:24] if len(device['hostname']) > 24 else device['hostname']

        logger.info(
            f"{status:<8} {device['ip']:<16} {device['mac']:<18} "
            f"{device['vendor']:<20} {hostname:<25} {device['type']}"
        )

    logger.info("")
    logger.info("="*80)
    logger.info("Device Details")
    logger.info("="*80)
    logger.info("")

    # Show detailed info for devices with mDNS
    for device in all_devices:
        if device['services'] or device['properties']:
            logger.info(f"🔍 {device['ip']} - {device['hostname']}")
            logger.info(f"   MAC: {device['mac']} ({device['vendor']})")
            logger.info(f"   Status: {'✅ Online' if device['online'] else '❌ Offline'}")

            if device['services']:
                logger.info(f"   Services:")
                for service in device['services']:
                    logger.info(f"      - {service}")

            if device['properties']:
                logger.info(f"   Properties:")
                for key, value in device['properties'].items():
                    logger.info(f"      - {key}: {value}")

            logger.info("")

    # Cleanup
    zeroconf.close()

    logger.info("="*80)
    logger.info("Summary by Vendor")
    logger.info("="*80)
    logger.info("")

    # Group by vendor
    vendor_counts = {}
    for device in all_devices:
        vendor = device['vendor']
        if vendor not in vendor_counts:
            vendor_counts[vendor] = {'total': 0, 'online': 0}
        vendor_counts[vendor]['total'] += 1
        if device['online']:
            vendor_counts[vendor]['online'] += 1

    for vendor, counts in sorted(vendor_counts.items()):
        logger.info(f"   {vendor:<30} {counts['online']}/{counts['total']} online")

    logger.info("")
    logger.info("="*80)
    logger.info(f"Total: {len(all_devices)} devices found ({len(online_devices)} online)")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(scan_network())
