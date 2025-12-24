#!/usr/bin/env python3
"""
Test SSE (Server-Sent Events) connection to ManeYantra API.

This script validates:
1. SSE endpoint connectivity
2. Event stream parsing
3. Different event types (connected, heartbeat, state, etc.)
4. Connection stability over time
5. Error handling

Usage:
    python scripts/test_sse_connection.py [--duration SECONDS] [--url URL]
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from typing import Dict, Any

try:
    import httpx
    from httpx_sse import aconnect_sse
except ImportError:
    print("ERROR: Required packages not installed")
    print("Install with: pip install httpx httpx-sse")
    sys.exit(1)


class SSEConnectionTester:
    """Test SSE connection to ManeYantra API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.events_received = []
        self.event_counts = {}
        self.errors = []

    async def test_basic_connection(self, duration: int = 10):
        """Test basic SSE connection."""
        print(f"[{self._timestamp()}] Testing SSE connection to {self.base_url}")
        print(f"[{self._timestamp()}] Will run for {duration} seconds")
        print("-" * 60)

        url = f"{self.base_url}/api/v1/events/stream"

        try:
            async with httpx.AsyncClient(timeout=duration + 5) as client:
                async with aconnect_sse(client, "GET", url) as event_source:
                    print(f"[{self._timestamp()}] ✓ SSE connection established")

                    start_time = asyncio.get_event_loop().time()

                    async for event in event_source.aiter_sse():
                        # Check duration
                        if asyncio.get_event_loop().time() - start_time > duration:
                            print(f"\n[{self._timestamp()}] Test duration reached")
                            break

                        # Process event
                        self._process_event(event)

        except httpx.ConnectError as e:
            error = f"Connection failed: {e}"
            self.errors.append(error)
            print(f"[{self._timestamp()}] ✗ {error}")
            return False

        except Exception as e:
            error = f"Unexpected error: {e}"
            self.errors.append(error)
            print(f"[{self._timestamp()}] ✗ {error}")
            return False

        # Print summary
        self._print_summary()
        return len(self.errors) == 0

    def _process_event(self, event):
        """Process a single SSE event."""
        event_type = event.event or "message"

        # Count event types
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1

        # Parse data
        try:
            if event.data:
                data = json.loads(event.data)
            else:
                data = None
        except json.JSONDecodeError:
            data = event.data
            self.errors.append(f"Invalid JSON in {event_type} event: {event.data}")

        # Store event
        event_info = {
            "timestamp": self._timestamp(),
            "type": event_type,
            "data": data,
            "id": event.id,
            "retry": event.retry,
        }
        self.events_received.append(event_info)

        # Print event
        if event_type == "connected":
            print(f"[{self._timestamp()}] ✓ Connected event received")
            if data:
                print(f"  Message: {data.get('message', 'N/A')}")
                print(f"  Filters: {data.get('filters', {})}")

        elif event_type == "heartbeat":
            print(f"[{self._timestamp()}] ♥ Heartbeat received")
            if data and 'timestamp' in data:
                print(f"  Server time: {data['timestamp']}")

        elif event_type == "state":
            print(f"[{self._timestamp()}] 📊 State event received")
            if data:
                device_id = data.get('device_id', 'unknown')
                print(f"  Device: {device_id}")

        elif event_type == "error":
            print(f"[{self._timestamp()}] ✗ Error event received")
            if data:
                print(f"  Error: {data.get('error', 'Unknown')}")
            self.errors.append(f"Server error: {data}")

        else:
            print(f"[{self._timestamp()}] 📨 {event_type} event received")
            if data:
                print(f"  Data: {json.dumps(data, indent=2)}")

    def _print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total events received: {len(self.events_received)}")
        print(f"\nEvent breakdown:")
        for event_type, count in sorted(self.event_counts.items()):
            print(f"  {event_type}: {count}")

        if self.errors:
            print(f"\n⚠ Errors encountered: {len(self.errors)}")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print(f"\n✓ No errors encountered")

        print("=" * 60)

    @staticmethod
    def _timestamp():
        """Get formatted timestamp."""
        return datetime.now().strftime("%H:%M:%S")


async def test_device_specific_stream(base_url: str, device_id: str, duration: int = 10):
    """Test device-specific SSE stream."""
    print(f"\n[Testing device-specific stream for {device_id}]")

    url = f"{base_url}/api/v1/events/devices/{device_id}/stream"

    try:
        async with httpx.AsyncClient(timeout=duration + 5) as client:
            async with aconnect_sse(client, "GET", url) as event_source:
                print(f"✓ Connected to device stream: {device_id}")

                start_time = asyncio.get_event_loop().time()
                event_count = 0

                async for event in event_source.aiter_sse():
                    if asyncio.get_event_loop().time() - start_time > duration:
                        break

                    event_count += 1
                    print(f"  [{event.event or 'message'}] {event.data[:100] if event.data else 'No data'}")

                print(f"✓ Received {event_count} events for device {device_id}")
                return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


async def test_filtered_stream(base_url: str, event_type: str, duration: int = 10):
    """Test filtered event stream."""
    print(f"\n[Testing filtered stream for event_type={event_type}]")

    url = f"{base_url}/api/v1/events/stream?event_type={event_type}"

    try:
        async with httpx.AsyncClient(timeout=duration + 5) as client:
            async with aconnect_sse(client, "GET", url) as event_source:
                print(f"✓ Connected with filter: event_type={event_type}")

                start_time = asyncio.get_event_loop().time()
                event_count = 0

                async for event in event_source.aiter_sse():
                    if asyncio.get_event_loop().time() - start_time > duration:
                        break

                    event_count += 1
                    if event.event != event_type and event.event not in ["connected", "heartbeat"]:
                        print(f"  ⚠ Unexpected event type: {event.event} (expected {event_type})")
                    else:
                        print(f"  ✓ [{event.event or 'message'}]")

                print(f"✓ Received {event_count} events (filtered by {event_type})")
                return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


async def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Test ManeYantra SSE connection")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--duration", type=int, default=15, help="Test duration in seconds")
    parser.add_argument("--device-id", help="Test device-specific stream")
    parser.add_argument("--event-type", help="Test filtered stream (state, error, etc.)")
    args = parser.parse_args()

    print("=" * 60)
    print("ManeYantra SSE Connection Test")
    print("=" * 60)

    # Test basic connection
    tester = SSEConnectionTester(args.url)
    success = await tester.test_basic_connection(args.duration)

    # Test device-specific stream if requested
    if args.device_id:
        await test_device_specific_stream(args.url, args.device_id, args.duration)

    # Test filtered stream if requested
    if args.event_type:
        await test_filtered_stream(args.url, args.event_type, args.duration)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
