#!/usr/bin/env python3
"""
Verify TP-Link device discovery on host network.
This script runs on the host machine to test if TP-Link devices can be discovered.
"""

import asyncio
import sys


async def discover_devices():
    """Discover TP-Link devices on the network."""
    try:
        from kasa import Discover

        print("=" * 60)
        print("TP-Link Device Discovery Test")
        print("=" * 60)
        print("\nSearching for TP-Link devices on local network...")
        print("Timeout: 10 seconds\n")

        # Discover devices using correct broadcast address for network
        # Default 255.255.255.255 may be blocked by macOS firewall
        devices = await Discover.discover(
            timeout=10,
            target="192.168.86.255"  # Use network-specific broadcast address
        )

        print(f"Found {len(devices)} TP-Link device(s):\n")

        if len(devices) == 0:
            print("❌ No TP-Link devices found!")
            print("\nPossible reasons:")
            print("  1. No TP-Link devices on the network")
            print("  2. Devices are powered off")
            print("  3. Devices are on a different network/VLAN")
            print("  4. Firewall blocking discovery (UDP port 9999)")
            return False

        # Display device details
        for idx, (host, device) in enumerate(devices.items(), 1):
            await device.update()

            print(f"{idx}. {device.alias}")
            print(f"   IP Address: {host}")
            print(f"   Model: {device.model}")
            print(f"   Device Type: {device.device_type}")

            # Check if it's a bulb, plug, or other
            if device.is_bulb:
                print(f"   Type: Smart Bulb")
            elif device.is_plug:
                print(f"   Type: Smart Plug/Switch")
            elif device.is_strip:
                print(f"   Type: Power Strip")
            else:
                print(f"   Type: Other")

            print(f"   Is On: {device.is_on}")
            print()

        print("=" * 60)
        print(f"✅ Successfully discovered {len(devices)} TP-Link device(s)!")
        print("=" * 60)
        return True

    except ImportError:
        print("❌ Error: 'python-kasa' library not installed")
        print("\nTo install, run:")
        print("  pip3 install python-kasa")
        return False
    except Exception as e:
        print(f"❌ Error during discovery: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🔍 Starting TP-Link device discovery...\n")

    success = asyncio.run(discover_devices())

    if success:
        print("\n✅ Verification successful!")
        print("Your host can discover TP-Link devices.")
        sys.exit(0)
    else:
        print("\n❌ Verification failed!")
        print("Please check the errors above.")
        sys.exit(1)
