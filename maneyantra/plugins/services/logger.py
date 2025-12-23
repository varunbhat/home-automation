"""Logger service plugin."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict

from maneyantra.core.plugin import PluginBase, PluginMetadata, PluginType
from maneyantra.core.rabbitmq_bus import RabbitMQEventBus


class LoggerPlugin(PluginBase):
    """
    Logging service plugin.

    Subscribes to all RabbitMQ routing keys and logs events to console and/or file.
    """

    def __init__(
        self,
        plugin_id: str,
        config: Dict,
        event_bus: RabbitMQEventBus,
    ):
        metadata = PluginMetadata(
            name="Logger",
            version="0.1.0",
            plugin_type=PluginType.SERVICE,
            description="System-wide logging service",
            capabilities=["logging", "console", "file"],
        )

        super().__init__(plugin_id, metadata, config, event_bus)

        self.event_logger = None

    async def initialize(self) -> None:
        """Initialize the logger."""
        # Create dedicated logger for events
        self.event_logger = logging.getLogger("maneyantra.events")
        self.event_logger.setLevel(self.get_config("level", "INFO"))
        self.event_logger.propagate = False

        # Clear existing handlers
        self.event_logger.handlers.clear()

        outputs = self.get_config("outputs", ["console"])

        # Console handler
        if "console" in outputs:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            self.event_logger.addHandler(console_handler)

        # File handler
        if "file" in outputs:
            file_path = Path(self.get_config("file_path", "./logs/maneyantra.log"))
            file_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=self.get_config("max_size", 10 * 1024 * 1024),  # 10MB default
                backupCount=self.get_config("backup_count", 5),
            )
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            self.event_logger.addHandler(file_handler)

        self._logger.info("Logger plugin initialized")

    async def start(self) -> None:
        """Start the logger."""
        # Subscribe to all events
        await self.event_bus.subscribe("#", self._log_event)

        self._logger.info("Logger plugin started - listening to all events")

    async def stop(self) -> None:
        """Stop the logger."""
        self._logger.info("Logger plugin stopped")

    async def _log_event(self, topic: str, payload: Dict) -> None:
        """Log an event."""
        try:
            # Format log message
            timestamp = payload.get("timestamp", "")
            log_msg = f"[{topic}] {payload}"

            # Log at appropriate level based on topic
            if "error" in topic.lower():
                self.event_logger.error(log_msg)
            elif "warning" in topic.lower():
                self.event_logger.warning(log_msg)
            else:
                self.event_logger.info(log_msg)

        except Exception as e:
            self._logger.error(f"Error logging event: {e}")
