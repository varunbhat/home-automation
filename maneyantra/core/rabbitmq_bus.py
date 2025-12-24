"""RabbitMQ Event Bus for inter-plugin communication."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict

import aio_pika
from aio_pika import ExchangeType, Message
from aio_pika.abc import AbstractIncomingMessage


logger = logging.getLogger(__name__)


class RabbitMQEventBus:
    """
    RabbitMQ-based event bus for plugin communication.

    Uses RabbitMQ topic exchange for routing, which provides:
    - Pattern-based routing (similar to MQTT)
    - Guaranteed delivery
    - Message persistence
    - Management UI
    - Better scalability

    Routing Key Structure:
        maneyantra.device.{device_id}.state
        maneyantra.device.{device_id}.command
        maneyantra.device.{device_id}.available
        maneyantra.device.discovery
        maneyantra.plugin.{plugin_id}.status
        maneyantra.automation.{rule_id}.trigger
        maneyantra.service.log
        maneyantra.system.{event_type}
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        username: Optional[str] = "guest",
        password: Optional[str] = "guest",
        vhost: str = "/",
        exchange_name: str = "maneyantra",
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.vhost = vhost
        self.exchange_name = exchange_name

        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        self.queue: Optional[aio_pika.Queue] = None

        self._subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        self._running = False
        self._consumer_tags: List[str] = []

    async def connect(self) -> None:
        """Connect to RabbitMQ broker."""
        logger.info(f"Connecting to RabbitMQ at {self.host}:{self.port}")

        # Build connection URL
        connection_url = f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/{self.vhost}"

        # Connect
        self.connection = await aio_pika.connect_robust(
            connection_url,
            timeout=10,
        )

        # Create channel
        self.channel = await self.connection.channel()

        # Set QoS for the channel (prefetch count)
        await self.channel.set_qos(prefetch_count=10)

        # Declare topic exchange
        self.exchange = await self.channel.declare_exchange(
            self.exchange_name,
            ExchangeType.TOPIC,
            durable=True,
        )

        # Create queue for this instance
        queue_name = f"{self.exchange_name}_consumer_{id(self)}"
        self.queue = await self.channel.declare_queue(
            queue_name,
            auto_delete=True,  # Delete when consumer disconnects
        )

        self._running = True

        logger.info("Connected to RabbitMQ broker")

    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ broker."""
        logger.info("Disconnecting from RabbitMQ broker")

        self._running = False

        # Close channel and connection
        if self.channel and not self.channel.is_closed:
            await self.channel.close()

        if self.connection and not self.connection.is_closed:
            await self.connection.close()

        logger.info("Disconnected from RabbitMQ broker")

    async def publish(
        self,
        routing_key: str,
        payload: Dict[str, Any],
        persistent: bool = True,
    ) -> None:
        """
        Publish a message.

        Args:
            routing_key: Routing key (will be prefixed automatically)
            payload: Message payload (will be JSON encoded)
            persistent: Make message persistent (survive broker restart)
        """
        if not self.exchange:
            raise RuntimeError("Not connected to RabbitMQ broker")

        full_routing_key = f"{self.exchange_name}.{routing_key}"

        # Add timestamp to payload
        message_data = {
            "timestamp": datetime.utcnow().isoformat(),
            **payload,
        }

        payload_json = json.dumps(message_data)

        # Create message
        message = Message(
            body=payload_json.encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT if persistent else aio_pika.DeliveryMode.NOT_PERSISTENT,
        )

        # Publish to exchange
        await self.exchange.publish(
            message,
            routing_key=full_routing_key,
        )

        logger.debug(f"Published to {full_routing_key}: {payload_json[:100]}...")

    async def subscribe(self, routing_pattern: str, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        Subscribe to a routing pattern.

        Args:
            routing_pattern: Routing key pattern (supports wildcards: *, #)
                * matches exactly one word
                # matches zero or more words
            callback: Async callback function(routing_key, payload)
        """
        if not self.queue:
            raise RuntimeError("Not connected to RabbitMQ broker")

        if not self.channel:
            raise RuntimeError("RabbitMQ channel not initialized")

        # Wait for channel to be ready (robust channels may temporarily close during reconnection)
        if hasattr(self.channel, 'ready') and callable(self.channel.ready):
            await self.channel.ready()

        full_pattern = f"{self.exchange_name}.{routing_pattern}"

        # Bind queue to exchange with pattern
        await self.queue.bind(
            self.exchange,
            routing_key=full_pattern,
        )

        # Add to subscriptions
        self._subscriptions[full_pattern].append(callback)

        # Start consuming if not already started
        if not self._consumer_tags:
            await self._start_consuming()

        logger.info(f"Subscribed to {full_pattern}")

    async def unsubscribe(self, routing_pattern: str) -> None:
        """Unsubscribe from a routing pattern."""
        if not self.queue:
            return

        full_pattern = f"{self.exchange_name}.{routing_pattern}"

        # Remove from subscriptions
        if full_pattern in self._subscriptions:
            del self._subscriptions[full_pattern]

        # Unbind from exchange
        await self.queue.unbind(
            self.exchange,
            routing_key=full_pattern,
        )

        logger.info(f"Unsubscribed from {full_pattern}")

    async def _start_consuming(self) -> None:
        """Start consuming messages from the queue."""
        if not self.queue:
            return

        # Set up consumer
        async def on_message(message: AbstractIncomingMessage) -> None:
            async with message.process():
                try:
                    # Decode payload
                    payload_str = message.body.decode()
                    payload = json.loads(payload_str)

                    routing_key = message.routing_key

                    logger.debug(f"Received message on {routing_key}: {payload_str[:100]}...")

                    # Dispatch to callbacks
                    await self._dispatch_message(routing_key, payload)

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON payload: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}", exc_info=True)

        # Start consuming
        consumer_tag = await self.queue.consume(on_message)
        self._consumer_tags.append(consumer_tag)

    async def _dispatch_message(self, routing_key: str, payload: Dict[str, Any]) -> None:
        """Dispatch message to matching subscribers."""
        for pattern, callbacks in self._subscriptions.items():
            if self._pattern_matches(routing_key, pattern):
                for callback in callbacks:
                    try:
                        # Extract routing key without exchange prefix for callback
                        routing_key_without_exchange = routing_key.replace(f"{self.exchange_name}.", "", 1)

                        if asyncio.iscoroutinefunction(callback):
                            await callback(routing_key_without_exchange, payload)
                        else:
                            callback(routing_key_without_exchange, payload)

                    except Exception as e:
                        logger.error(f"Error in callback for {routing_key}: {e}", exc_info=True)

    @staticmethod
    def _pattern_matches(routing_key: str, pattern: str) -> bool:
        """
        Check if routing key matches pattern.

        RabbitMQ wildcard rules:
        * matches exactly one word
        # matches zero or more words
        """
        routing_parts = routing_key.split('.')
        pattern_parts = pattern.split('.')

        i, j = 0, 0

        while i < len(routing_parts) and j < len(pattern_parts):
            if pattern_parts[j] == '#':
                # # matches rest of routing key
                if j == len(pattern_parts) - 1:
                    return True
                # Try to match remaining pattern
                j += 1
                while i < len(routing_parts):
                    if RabbitMQEventBus._pattern_matches(
                        '.'.join(routing_parts[i:]),
                        '.'.join(pattern_parts[j:])
                    ):
                        return True
                    i += 1
                return False

            elif pattern_parts[j] == '*' or pattern_parts[j] == routing_parts[i]:
                i += 1
                j += 1

            else:
                return False

        # Check if we consumed all parts
        return i == len(routing_parts) and j == len(pattern_parts)

    # Convenience methods for common topics (same as MQTT version)

    async def publish_device_state(self, device_id: str, state: Dict[str, Any]) -> None:
        """Publish device state update."""
        await self.publish(f"device.{device_id}.state", {"state": state})

    async def publish_device_command(self, device_id: str, command: str, params: Optional[Dict] = None) -> None:
        """Publish device command."""
        await self.publish(
            f"device.{device_id}.command",
            {"command": command, "params": params or {}},
        )

    async def publish_device_available(self, device_id: str, available: bool) -> None:
        """Publish device availability."""
        await self.publish(f"device.{device_id}.available", {"available": available}, persistent=True)

    async def publish_plugin_status(self, plugin_id: str, status: str, details: Optional[Dict] = None) -> None:
        """Publish plugin status."""
        await self.publish(
            f"plugin.{plugin_id}.status",
            {"status": status, "details": details or {}},
        )

    async def publish_system_event(self, event_type: str, data: Optional[Dict] = None) -> None:
        """Publish system event."""
        await self.publish(f"system.{event_type}", data or {})

    async def subscribe_device_commands(self, device_id: str, callback: Callable) -> None:
        """Subscribe to device commands."""
        await self.subscribe(f"device.{device_id}.command", callback)

    async def subscribe_device_states(self, callback: Callable) -> None:
        """Subscribe to all device state updates."""
        await self.subscribe("device.*.state", callback)

    async def subscribe_system_events(self, callback: Callable) -> None:
        """Subscribe to system events."""
        await self.subscribe("system.#", callback)
