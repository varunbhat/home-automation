#!/usr/bin/env python3
"""
Interactive tool to rename devices in the device registry.
Helps identify Eufy cameras and other devices by pinging them and checking status.
"""

import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from icmplib import ping

# Device registry path
REGISTRY_PATH = "data/real_devices.json"

# Common vendor identifications
VENDORS = {
    "60:83:E7": "TP-Link",
    "24:2F:D0": "Anker (Eufy)",
    "E4:FA:C4": "Anker (Eufy)",
}


def get_vendor(mac: str) -> str:
    """Get vendor from MAC OUI."""
    oui = ':'.join(mac.split(':')[:3])
    return VENDORS.get(oui, "Unknown")


def is_online(ip: str) -> bool:
    """Check if device is online."""
    try:
        host = ping(ip, count=1, timeout=2, privileged=False)
        return host.is_alive
    except:
        return False


def load_registry():
    """Load device registry."""
    try:
        with open(REGISTRY_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Registry file not found: {REGISTRY_PATH}")
        return {}


def save_registry(devices):
    """Save device registry."""
    with open(REGISTRY_PATH, 'w') as f:
        json.dump(devices, f, indent=2)
    print(f"\n✅ Device registry saved to {REGISTRY_PATH}")


def main():
    print("="*80)
    print("Device Naming Tool")
    print("="*80)
    print()

    devices = load_registry()

    if not devices:
        print("No devices in registry!")
        return

    # Sort by IP for easier reading
    sorted_devices = sorted(devices.items(), key=lambda x: x[1].get('ip', ''))

    # Display current devices
    print(f"Found {len(sorted_devices)} devices in registry:")
    print()
    print(f"{'#':<4} {'Status':<8} {'IP':<16} {'Current Name':<30} {'Vendor'}")
    print("-" * 100)

    device_list = []
    for idx, (mac, info) in enumerate(sorted_devices, 1):
        ip = info.get('ip', 'unknown')
        name = info.get('name', 'unknown')
        vendor = get_vendor(mac)

        # Check if online
        status = "⏳"
        if ip != 'unknown' and not ip.startswith('192.168.86.250'):  # Skip test device
            online = is_online(ip)
            status = "✅" if online else "❌"

        print(f"{idx:<4} {status:<8} {ip:<16} {name:<30} {vendor}")
        device_list.append((mac, info))

    print()
    print("="*80)
    print()

    # Interactive renaming
    print("You can rename devices by typing their number, or 'q' to quit.")
    print("Suggested names for Eufy cameras: 'Front Door Camera', 'Backyard Camera', etc.")
    print()

    # Auto-suggest Eufy cameras
    eufy_devices = [(idx, mac, info) for idx, (mac, info) in enumerate(device_list, 1)
                    if get_vendor(mac) == "Anker (Eufy)"]

    if eufy_devices:
        print(f"💡 Found {len(eufy_devices)} Eufy devices that could be renamed:")
        for idx, mac, info in eufy_devices:
            print(f"   #{idx}: {info['ip']}")
        print()

    while True:
        try:
            choice = input("Enter device number to rename (or 'q' to quit, 's' to save): ").strip()

            if choice.lower() == 'q':
                print("\nQuitting without saving...")
                break

            if choice.lower() == 's':
                save_registry(devices)
                break

            if not choice.isdigit():
                print("Invalid input. Please enter a number.")
                continue

            idx = int(choice)
            if idx < 1 or idx > len(device_list):
                print(f"Invalid number. Please enter 1-{len(device_list)}")
                continue

            mac, info = device_list[idx - 1]
            current_name = info.get('name', 'unknown')
            ip = info.get('ip', 'unknown')
            vendor = get_vendor(mac)

            print()
            print(f"Device #{idx}:")
            print(f"   IP: {ip}")
            print(f"   MAC: {mac}")
            print(f"   Vendor: {vendor}")
            print(f"   Current name: {current_name}")
            print()

            new_name = input("Enter new name (or press Enter to skip): ").strip()

            if new_name:
                devices[mac]['name'] = new_name
                print(f"✅ Renamed to: {new_name}")
                print()
            else:
                print("Skipped.")
                print()

        except KeyboardInterrupt:
            print("\n\nQuitting without saving...")
            break
        except Exception as e:
            print(f"Error: {e}")

    print()
    print("Done!")


if __name__ == "__main__":
    main()
