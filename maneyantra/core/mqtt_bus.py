"""MQTT Event Bus for inter-plugin communication."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict

import aiomqtt


logger = logging.getLogger(__name__)


class MQTTEventBus:
    """
    MQTT-based event bus for plugin communication.

    Topic Structure:
        maneyantra/device/{device_id}/state
        maneyantra/device/{device_id}/command
        maneyantra/device/{device_id}/available
        maneyantra/device/discovery
        maneyantra/plugin/{plugin_id}/status
        maneyantra/automation/{rule_id}/trigger
        maneyantra/service/log
        maneyantra/system/{event_type}
    """

    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: str = "maneyantra",
        topic_prefix: str = "maneyantra",
        qos: int = 1,
    ):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id
        self.topic_prefix = topic_prefix
        self.qos = qos

        self.client: Optional[aiomqtt.Client] = None
        self._subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        self._running = False
        self._message_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Connect to MQTT broker."""
        logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")

        self.client = aiomqtt.Client(
            hostname=self.broker,
            port=self.port,
            username=self.username,
            password=self.password,
            identifier=self.client_id,
        )

        await self.client.__aenter__()
        self._running = True

        # Start message handling task
        self._message_task = asyncio.create_task(self._handle_messages())

        logger.info("Connected to MQTT broker")

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        logger.info("Disconnecting from MQTT broker")

        self._running = False

        if self._message_task:
            self._message_task.cancel()
            try:
                await self._message_task
            except asyncio.CancelledError:
                pass

        if self.client:
            await self.client.__aexit__(None, None, None)

        logger.info("Disconnected from MQTT broker")

    async def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        qos: Optional[int] = None,
        retain: bool = False,
    ) -> None:
        """
        Publish a message to a topic.

        Args:
            topic: Topic to publish to (will be prefixed automatically)
            payload: Message payload (will be JSON encoded)
            qos: Quality of Service (0, 1, or 2)
            retain: Retain message on broker
        """
        if not self.client:
            raise RuntimeError("Not connected to MQTT broker")

        full_topic = f"{self.topic_prefix}/{topic}"

        # Add timestamp to payload
        message = {
            "timestamp": datetime.utcnow().isoformat(),
            **payload,
        }

        payload_json = json.dumps(message)

        await self.client.publish(
            full_topic,
            payload=payload_json,
            qos=qos or self.qos,
            retain=retain,
        )

        logger.debug(f"Published to {full_topic}: {payload_json[:100]}...")

    async def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        Subscribe to a topic.

        Args:
            topic: Topic pattern to subscribe to (supports MQTT wildcards: +, #)
            callback: Async callback function(topic, payload)
        """
        if not self.client:
            raise RuntimeError("Not connected to MQTT broker")

        full_topic = f"{self.topic_prefix}/{topic}"

        # Add to subscriptions
        self._subscriptions[full_topic].append(callback)

        # Subscribe on MQTT broker
        await self.client.subscribe(full_topic, qos=self.qos)

        logger.info(f"Subscribed to {full_topic}")

    async def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic."""
        if not self.client:
            return

        full_topic = f"{self.topic_prefix}/{topic}"

        # Remove from subscriptions
        if full_topic in self._subscriptions:
            del self._subscriptions[full_topic]

        # Unsubscribe from MQTT broker
        await self.client.unsubscribe(full_topic)

        logger.info(f"Unsubscribed from {full_topic}")

    async def _handle_messages(self) -> None:
        """Handle incoming MQTT messages."""
        if not self.client:
            return

        try:
            async for message in self.client.messages:
                try:
                    # Decode payload
                    payload_str = message.payload.decode()
                    payload = json.loads(payload_str)

                    topic = message.topic.value

                    logger.debug(f"Received message on {topic}: {payload_str[:100]}...")

                    # Call matching callbacks
                    await self._dispatch_message(topic, payload)

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON payload: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}", exc_info=True)

        except asyncio.CancelledError:
            logger.debug("Message handler cancelled")
            raise
        except Exception as e:
            logger.error(f"Message handler error: {e}", exc_info=True)

    async def _dispatch_message(self, topic: str, payload: Dict[str, Any]) -> None:
        """Dispatch message to matching subscribers."""
        for pattern, callbacks in self._subscriptions.items():
            if self._topic_matches(topic, pattern):
                for callback in callbacks:
                    try:
                        # Extract topic without prefix for callback
                        topic_without_prefix = topic.replace(f"{self.topic_prefix}/", "", 1)

                        if asyncio.iscoroutinefunction(callback):
                            await callback(topic_without_prefix, payload)
                        else:
                            callback(topic_without_prefix, payload)

                    except Exception as e:
                        logger.error(f"Error in callback for {topic}: {e}", exc_info=True)

    @staticmethod
    def _topic_matches(topic: str, pattern: str) -> bool:
        """
        Check if topic matches pattern (with MQTT wildcards).

        + matches single level
        # matches multiple levels
        """
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')

        # Multi-level wildcard
        if '#' in pattern_parts:
            hash_index = pattern_parts.index('#')
            if hash_index != len(pattern_parts) - 1:
                return False  # # must be last
            pattern_parts = pattern_parts[:hash_index]
            topic_parts = topic_parts[:hash_index]

        if len(topic_parts) != len(pattern_parts):
            return False

        for t, p in zip(topic_parts, pattern_parts):
            if p != '+' and p != t:
                return False

        return True

    # Convenience methods for common topics

    async def publish_device_state(self, device_id: str, state: Dict[str, Any]) -> None:
        """Publish device state update."""
        await self.publish(f"device/{device_id}/state", {"state": state})

    async def publish_device_command(self, device_id: str, command: str, params: Optional[Dict] = None) -> None:
        """Publish device command."""
        await self.publish(
            f"device/{device_id}/command",
            {"command": command, "params": params or {}},
        )

    async def publish_device_available(self, device_id: str, available: bool) -> None:
        """Publish device availability."""
        await self.publish(f"device/{device_id}/available", {"available": available}, retain=True)

    async def publish_plugin_status(self, plugin_id: str, status: str, details: Optional[Dict] = None) -> None:
        """Publish plugin status."""
        await self.publish(
            f"plugin/{plugin_id}/status",
            {"status": status, "details": details or {}},
        )

    async def publish_system_event(self, event_type: str, data: Optional[Dict] = None) -> None:
        """Publish system event."""
        await self.publish(f"system/{event_type}", data or {})

    async def subscribe_device_commands(self, device_id: str, callback: Callable) -> None:
        """Subscribe to device commands."""
        await self.subscribe(f"device/{device_id}/command", callback)

    async def subscribe_device_states(self, callback: Callable) -> None:
        """Subscribe to all device state updates."""
        await self.subscribe("device/+/state", callback)

    async def subscribe_system_events(self, callback: Callable) -> None:
        """Subscribe to system events."""
        await self.subscribe("system/#", callback)
