"""Notification service plugin."""

from typing import Dict, List

from maneyantra.core.plugin import PluginBase, PluginMetadata, PluginType
from maneyantra.core.rabbitmq_bus import RabbitMQEventBus


class NotificationPlugin(PluginBase):
    """
    Notification service plugin.

    Sends notifications via various channels:
    - RabbitMQ (for UI consumption)
    - Email (future)
    - Webhooks (future)
    - Push notifications (future)
    """

    def __init__(
        self,
        plugin_id: str,
        config: Dict,
        event_bus: RabbitMQEventBus,
    ):
        metadata = PluginMetadata(
            name="Notifications",
            version="0.1.0",
            plugin_type=PluginType.SERVICE,
            description="Multi-channel notification service",
            capabilities=["notifications", "rabbitmq", "email", "webhooks"],
        )

        super().__init__(plugin_id, metadata, config, event_bus)

        self.channels = []

    async def initialize(self) -> None:
        """Initialize the notification service."""
        # Load configured channels
        channels_config = self.get_config("channels", [])

        for channel_config in channels_config:
            channel_type = channel_config.get("type")

            if channel_type == "rabbitmq" or channel_type == "mqtt":  # Support both names
                self.channels.append({"type": "rabbitmq", "config": channel_config})
            elif channel_type == "email":
                self._logger.warning("Email notifications not yet implemented")
            elif channel_type == "webhook":
                self._logger.warning("Webhook notifications not yet implemented")

        self._logger.info(f"Notification plugin initialized with {len(self.channels)} channels")

    async def start(self) -> None:
        """Start the notification service."""
        # Subscribe to notification requests
        await self.event_bus.subscribe("service.notify", self._handle_notification_request)

        # Subscribe to important events for automatic notifications
        await self.event_bus.subscribe("device.*.error", self._handle_device_error)
        await self.event_bus.subscribe("plugin.*.status", self._handle_plugin_status)

        self._logger.info("Notification plugin started")

    async def stop(self) -> None:
        """Stop the notification service."""
        self._logger.info("Notification plugin stopped")

    async def _handle_notification_request(self, topic: str, payload: Dict) -> None:
        """Handle notification request from other plugins."""
        try:
            title = payload.get("title", "Notification")
            message = payload.get("message", "")
            priority = payload.get("priority", "normal")

            await self._send_notification(title, message, priority)

        except Exception as e:
            self._logger.error(f"Error handling notification request: {e}", exc_info=True)

    async def _handle_device_error(self, topic: str, payload: Dict) -> None:
        """Handle device errors and send notification."""
        parts = topic.split(".")
        device_id = parts[1] if len(parts) > 1 else "unknown"
        error = payload.get("error", "Unknown error")

        await self._send_notification(
            f"Device Error: {device_id}",
            f"Error: {error}",
            "high",
        )

    async def _handle_plugin_status(self, topic: str, payload: Dict) -> None:
        """Handle plugin status changes."""
        parts = topic.split(".")
        plugin_id = parts[1] if len(parts) > 1 else "unknown"
        status = payload.get("status")

        # Only notify on errors
        if status == "error":
            details = payload.get("details", {})
            error_msg = details.get("error", "Unknown error")

            await self._send_notification(
                f"Plugin Error: {plugin_id}",
                f"Error: {error_msg}",
                "high",
            )

    async def _send_notification(self, title: str, message: str, priority: str = "normal") -> None:
        """Send notification through all configured channels."""
        notification = {
            "title": title,
            "message": message,
            "priority": priority,
        }

        for channel in self.channels:
            try:
                if channel["type"] == "rabbitmq":
                    await self._send_rabbitmq_notification(notification, channel["config"])
                # Add other channel types here

            except Exception as e:
                self._logger.error(f"Error sending notification via {channel['type']}: {e}")

    async def _send_rabbitmq_notification(self, notification: Dict, config: Dict) -> None:
        """Send notification via RabbitMQ."""
        topic = config.get("topic", "notifications")

        await self.event_bus.publish(
            topic,
            notification,
        )

        self._logger.debug(f"Sent notification: {notification['title']}")
