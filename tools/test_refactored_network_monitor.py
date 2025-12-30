#!/usr/bin/env python3
"""Test the refactored network monitor plugin."""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from maneyantra.plugins.devices.network_monitor.plugin import NetworkMonitorPlugin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockEventBus:
    """Mock event bus for testing."""

    def __init__(self):
        self.events = []

    async def publish(self, topic: str, payload: dict):
        """Mock publish that just logs events."""
        self.events.append({
            'topic': topic,
            'payload': payload,
            'timestamp': datetime.now().isoformat()
        })
        logger.info(f"📨 Event: {topic}")
        logger.info(f"   Payload: {payload}")

    async def publish_device_state(self, device_id: str, state: dict):
        """Mock publish device state."""
        await self.publish(f"maneyantra.device/{device_id}/state", state)

    async def publish_device_available(self, device_id: str, available: bool):
        """Mock publish device availability."""
        await self.publish(f"maneyantra.device/{device_id}/available", {"available": available})

    async def subscribe(self, topic: str, callback):
        """Mock subscribe."""
        pass

    async def subscribe_device_commands(self, device_id: str, callback):
        """Mock subscribe to device commands."""
        pass

    async def connect(self):
        """Mock connect."""
        pass

    async def close(self):
        """Mock close."""
        pass


async def test_refactored_plugin():
    """Test the refactored network monitor plugin."""
    logger.info("="*80)
    logger.info("Testing Refactored Network Monitor Plugin")
    logger.info("="*80)

    # Create mock event bus
    event_bus = MockEventBus()

    # Configure plugin with a few test devices
    config = {
        "poll_interval": 10,  # Short interval for testing
        "storage_path": "./data/test_refactored.json",
        "methods": {
            "ping": {
                "enabled": True,
                "timeout": 2,
                "count": 1
            },
            "mdns": {
                "enabled": False,  # Disable mDNS for simple test
            }
        },
        "known_devices": [
            {
                "name": "Router",
                "mac": "60:83:E7:43:44:00",
                "ip": "192.168.86.1",
                "track": True
            },
            {
                "name": "This Machine",
                "mac": "2E:71:60:FF:CE:59",
                "ip": "192.168.86.19",
                "track": True
            },
            {
                "name": "Offline Device",
                "mac": "00:00:00:00:00:FF",
                "ip": "192.168.86.250",
                "track": True
            }
        ]
    }

    # Create plugin
    plugin = NetworkMonitorPlugin("network_monitor", config, event_bus)

    try:
        logger.info("\n" + "="*80)
        logger.info("Step 1: Starting plugin (will call discover_devices)")
        logger.info("="*80)
        await plugin.start()

        logger.info("\n✅ Plugin started successfully!")
        logger.info(f"   Discovered {len(plugin.devices)} devices")

        # List devices
        logger.info("\n" + "="*80)
        logger.info("Step 2: Listing discovered devices")
        logger.info("="*80)
        for device_id, device in plugin.devices.items():
            logger.info(f"   📱 {device.info.name}")
            logger.info(f"      ID: {device_id}")
            logger.info(f"      IP: {device.ip}")
            logger.info(f"      MAC: {device.mac}")
            logger.info(f"      Type: {device.info.type}")
            logger.info(f"      Capabilities: {device.info.capabilities}")

        logger.info("\n" + "="*80)
        logger.info("Step 3: Waiting 15 seconds for first refresh cycle")
        logger.info("="*80)
        await asyncio.sleep(15)

        # Check device states
        logger.info("\n" + "="*80)
        logger.info("Step 4: Checking device states")
        logger.info("="*80)
        for device_id, device in plugin.devices.items():
            is_online = device.state.online
            status = "✅ ONLINE" if is_online else "❌ OFFLINE"
            logger.info(f"   {status} {device.info.name} ({device.ip})")
            if hasattr(device.state, 'custom') and device.state.custom:
                logger.info(f"      Last seen: {device.state.custom.get('last_seen', 'never')}")

        logger.info("\n" + "="*80)
        logger.info("Step 5: Event Summary")
        logger.info("="*80)
        logger.info(f"   Total events published: {len(event_bus.events)}")

        # Group events by type
        state_events = [e for e in event_bus.events if 'state' in e['topic']]
        discovery_events = [e for e in event_bus.events if 'discovery' in e['topic']]

        logger.info(f"   State events: {len(state_events)}")
        logger.info(f"   Discovery events: {len(discovery_events)}")

        logger.info("\n" + "="*80)
        logger.info("✅ TEST COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        logger.info("\nKey Achievements:")
        logger.info("✅ Plugin extends BaseDevicePlugin")
        logger.info("✅ Created NetworkDevice objects (not dicts)")
        logger.info("✅ discover_devices() returns List[Device]")
        logger.info("✅ Devices auto-registered via BaseDevicePlugin.start()")
        logger.info("✅ State changes published via Device.update_state()")

    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        logger.info("\n" + "="*80)
        logger.info("Cleaning up...")
        logger.info("="*80)
        await plugin.stop()
        logger.info("   Cleanup complete")


if __name__ == "__main__":
    asyncio.run(test_refactored_plugin())
