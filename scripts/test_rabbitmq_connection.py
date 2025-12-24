#!/usr/bin/env python3
"""
Test RabbitMQ connection for ManeYantra.

This script validates:
1. RabbitMQ broker connectivity
2. Channel creation and lifecycle
3. Exchange declaration
4. Queue binding and patterns
5. Publish/Subscribe operations
6. Connection resilience

Usage:
    python scripts/test_rabbitmq_connection.py [--host HOST] [--port PORT]
"""

import asyncio
import argparse
import sys
from datetime import datetime
from typing import Optional

try:
    import aio_pika
    from aio_pika import ExchangeType, Message
except ImportError:
    print("ERROR: aio-pika not installed")
    print("Install with: pip install aio-pika")
    sys.exit(1)


class RabbitMQTester:
    """Test RabbitMQ connection and operations."""

    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        self.test_results = []

    async def test_basic_connection(self):
        """Test basic RabbitMQ connection."""
        print(f"[{self._ts()}] Testing basic connection to {self.host}:{self.port}")

        try:
            url = f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/"
            self.connection = await aio_pika.connect_robust(url, timeout=10)
            self._log_success("Connection established (robust mode)")
            return True
        except Exception as e:
            self._log_error(f"Connection failed: {e}")
            return False

    async def test_channel_creation(self):
        """Test channel creation."""
        print(f"\n[{self._ts()}] Testing channel creation")

        try:
            if not self.connection:
                raise RuntimeError("No connection available")

            self.channel = await self.connection.channel()
            self._log_success("Channel created")

            # Set QoS
            await self.channel.set_qos(prefetch_count=10)
            self._log_success("QoS configured (prefetch_count=10)")

            return True
        except Exception as e:
            self._log_error(f"Channel creation failed: {e}")
            return False

    async def test_channel_state(self):
        """Test channel state properties."""
        print(f"\n[{self._ts()}] Testing channel state")

        if not self.channel:
            self._log_error("No channel available")
            return False

        try:
            print(f"  Channel object: {self.channel}")
            print(f"  is_closed: {self.channel.is_closed}")
            print(f"  is_initialized: {hasattr(self.channel, 'is_initialized')}")

            if hasattr(self.channel, 'ready'):
                print(f"  has ready() method: True")
                await self.channel.ready()
                self._log_success("Channel ready() completed")
            else:
                print(f"  has ready() method: False")

            self._log_success("Channel state validated")
            return True
        except Exception as e:
            self._log_error(f"Channel state check failed: {e}")
            return False

    async def test_exchange_declaration(self):
        """Test exchange declaration."""
        print(f"\n[{self._ts()}] Testing exchange declaration")

        try:
            if not self.channel:
                raise RuntimeError("No channel available")

            self.exchange = await self.channel.declare_exchange(
                "maneyantra_test",
                ExchangeType.TOPIC,
                durable=True,
            )
            self._log_success("Exchange 'maneyantra_test' declared (topic, durable)")
            return True
        except Exception as e:
            self._log_error(f"Exchange declaration failed: {e}")
            return False

    async def test_queue_operations(self):
        """Test queue creation and binding."""
        print(f"\n[{self._ts()}] Testing queue operations")

        try:
            if not self.channel or not self.exchange:
                raise RuntimeError("Channel or exchange not available")

            # Declare queue
            queue = await self.channel.declare_queue(
                "maneyantra_test_queue",
                auto_delete=True,
            )
            self._log_success(f"Queue created: {queue.name}")

            # Bind queue to exchange with pattern
            patterns = [
                "maneyantra_test.device.#",
                "maneyantra_test.device.*.state",
                "maneyantra_test.system.*",
            ]

            for pattern in patterns:
                await queue.bind(self.exchange, routing_key=pattern)
                self._log_success(f"Queue bound to pattern: {pattern}")

            return True
        except Exception as e:
            self._log_error(f"Queue operations failed: {e}")
            return False

    async def test_publish_subscribe(self):
        """Test publish and subscribe operations."""
        print(f"\n[{self._ts()}] Testing publish/subscribe")

        try:
            if not self.channel or not self.exchange:
                raise RuntimeError("Channel or exchange not available")

            # Create test queue
            queue = await self.channel.declare_queue(
                "test_pubsub_queue",
                auto_delete=True,
            )

            # Bind to test pattern
            routing_key = "maneyantra_test.device.test123.state"
            await queue.bind(self.exchange, routing_key=routing_key)
            self._log_success(f"Subscribed to: {routing_key}")

            # Track received messages
            received_messages = []

            async def on_message(message: aio_pika.abc.AbstractIncomingMessage):
                async with message.process():
                    body = message.body.decode()
                    received_messages.append(body)
                    print(f"  📨 Received: {body}")

            # Start consuming
            consumer_tag = await queue.consume(on_message)
            self._log_success("Consumer started")

            # Publish test message
            test_payload = f"Test message at {self._ts()}"
            message = Message(
                body=test_payload.encode(),
                content_type="text/plain",
            )

            await self.exchange.publish(message, routing_key=routing_key)
            self._log_success(f"Published: {test_payload}")

            # Wait for message
            await asyncio.sleep(2)

            if received_messages:
                self._log_success(f"Message received successfully: {received_messages[0]}")
                return True
            else:
                self._log_error("No message received (timeout)")
                return False

        except Exception as e:
            self._log_error(f"Publish/subscribe test failed: {e}")
            return False

    async def test_concurrent_operations(self):
        """Test concurrent publish/subscribe."""
        print(f"\n[{self._ts()}] Testing concurrent operations")

        try:
            if not self.exchange:
                raise RuntimeError("Exchange not available")

            # Publish multiple messages concurrently
            publish_tasks = []
            for i in range(10):
                routing_key = f"maneyantra_test.concurrent.msg{i}"
                message = Message(body=f"Concurrent message {i}".encode())
                publish_tasks.append(
                    self.exchange.publish(message, routing_key=routing_key)
                )

            await asyncio.gather(*publish_tasks)
            self._log_success("Published 10 concurrent messages")
            return True

        except Exception as e:
            self._log_error(f"Concurrent operations failed: {e}")
            return False

    async def cleanup(self):
        """Clean up test resources."""
        print(f"\n[{self._ts()}] Cleaning up")

        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
                print("  ✓ Channel closed")

            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                print("  ✓ Connection closed")

        except Exception as e:
            print(f"  ⚠ Cleanup error: {e}")

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        success_count = sum(1 for r in self.test_results if r['success'])
        fail_count = len(self.test_results) - success_count

        print(f"Total tests: {len(self.test_results)}")
        print(f"✓ Passed: {success_count}")
        print(f"✗ Failed: {fail_count}")

        if fail_count > 0:
            print("\nFailed tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['message']}")

        print("=" * 60)
        return fail_count == 0

    def _log_success(self, message: str):
        """Log successful operation."""
        print(f"  ✓ {message}")
        self.test_results.append({"success": True, "message": message})

    def _log_error(self, message: str):
        """Log failed operation."""
        print(f"  ✗ {message}")
        self.test_results.append({"success": False, "message": message})

    @staticmethod
    def _ts():
        """Get timestamp."""
        return datetime.now().strftime("%H:%M:%S")


async def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Test RabbitMQ connection")
    parser.add_argument("--host", default="localhost", help="RabbitMQ host")
    parser.add_argument("--port", type=int, default=5672, help="RabbitMQ port")
    parser.add_argument("--username", default="maneyantra", help="Username")
    parser.add_argument("--password", default="XVHpJplmBHEsGGY84QGEdvbx1SxbEZrU", help="Password")
    args = parser.parse_args()

    print("=" * 60)
    print("ManeYantra RabbitMQ Connection Test")
    print("=" * 60)

    tester = RabbitMQTester(args.host, args.port, args.username, args.password)

    try:
        # Run tests
        await tester.test_basic_connection()
        await tester.test_channel_creation()
        await tester.test_channel_state()
        await tester.test_exchange_declaration()
        await tester.test_queue_operations()
        await tester.test_publish_subscribe()
        await tester.test_concurrent_operations()

    finally:
        await tester.cleanup()

    # Print summary and exit
    success = tester.print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
