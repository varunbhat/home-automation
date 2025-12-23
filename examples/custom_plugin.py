"""
Example custom plugin for ManeYantra.

This demonstrates how to create a simple plugin that:
1. Publishes custom events
2. Responds to MQTT messages
3. Runs periodic tasks
"""

import asyncio
from typing import Dict

from maneyantra.core.plugin import PluginBase, PluginMetadata, PluginType
from maneyantra.core.rabbitmq_bus import RabbitMQEventBus


class CustomPlugin(PluginBase):
    """
    Example custom plugin.

    This plugin demonstrates:
    - Publishing to MQTT
    - Subscribing to MQTT topics
    - Running background tasks
    - Health checks
    """

    def __init__(
        self,
        plugin_id: str,
        config: Dict,
        event_bus: RabbitMQEventBus,
    ):
        metadata = PluginMetadata(
            name="Custom Plugin",
            version="0.1.0",
            plugin_type=PluginType.SERVICE,
            description="Example custom plugin demonstrating ManeYantra plugin API",
            capabilities=["example", "demo"],
        )

        super().__init__(plugin_id, metadata, config, event_bus)

        self._task: asyncio.Task = None
        self._counter = 0

    async def initialize(self) -> None:
        """Initialize the plugin."""
        self._logger.info("Custom plugin initializing...")

        # Load configuration
        interval = self.get_config("interval", 30)
        self._logger.info(f"Configured interval: {interval}s")

    async def start(self) -> None:
        """Start the plugin."""
        self._logger.info("Custom plugin starting...")

        # Subscribe to system events
        await self.event_bus.subscribe_system_events(self._handle_system_event)

        # Subscribe to custom topic
        await self.event_bus.subscribe(
            "custom.command",
            self._handle_custom_command,
        )

        # Start background task
        self._task = asyncio.create_task(self._periodic_task())

        self._logger.info("Custom plugin started")

    async def stop(self) -> None:
        """Stop the plugin."""
        self._logger.info("Custom plugin stopping...")

        # Stop background task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._logger.info("Custom plugin stopped")

    async def _periodic_task(self) -> None:
        """Background task that runs periodically."""
        interval = self.get_config("interval", 30)

        try:
            while True:
                await asyncio.sleep(interval)

                self._counter += 1

                # Publish custom event
                await self.event_bus.publish(
                    f"plugin.{self.plugin_id}.heartbeat",
                    {
                        "counter": self._counter,
                        "status": "healthy",
                    },
                )

                self._logger.debug(f"Heartbeat #{self._counter}")

        except asyncio.CancelledError:
            self._logger.debug("Periodic task cancelled")
            raise

    async def _handle_system_event(self, topic: str, payload: Dict) -> None:
        """Handle system events."""
        event_type = topic.split(".")[-1]
        self._logger.info(f"System event: {event_type}")

        if event_type == "start":
            self._logger.info("System started, custom plugin is ready!")

    async def _handle_custom_command(self, topic: str, payload: Dict) -> None:
        """Handle custom commands."""
        command = payload.get("command")

        self._logger.info(f"Received custom command: {command}")

        if command == "reset":
            self._counter = 0
            await self.event_bus.publish(
                f"plugin.{self.plugin_id}.response",
                {"status": "counter reset"},
            )

        elif command == "status":
            await self.event_bus.publish(
                f"plugin.{self.plugin_id}.response",
                {
                    "counter": self._counter,
                    "status": "running",
                },
            )

    async def health_check(self) -> Dict:
        """Health check."""
        return {
            "healthy": True,
            "state": self.state.value,
            "counter": self._counter,
        }


# To use this plugin:
# 1. Add to config/plugins.yaml:
#
# custom_example:
#   enabled: true
#   type: service
#   module: examples.custom_plugin
#   class: CustomPlugin
#   config:
#     interval: 30
#
# 2. Make sure the examples directory is in the Python path
# 3. Test with RabbitMQ management UI or publish directly to exchange
