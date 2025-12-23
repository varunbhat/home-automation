"""Main application entry point."""

import asyncio
import logging
import signal
from pathlib import Path
from typing import Optional

from maneyantra.core.config import ConfigManager
from maneyantra.core.rabbitmq_bus import RabbitMQEventBus
from maneyantra.core.manager import PluginManager


class ManeYantra:
    """Main application class."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.config_manager: Optional[ConfigManager] = None
        self.event_bus: Optional[RabbitMQEventBus] = None
        self.plugin_manager: Optional[PluginManager] = None
        self._running = False
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the application."""
        print("=" * 60)
        print("🏠 ManeYantra - Home Automation System")
        print("=" * 60)

        try:
            # Load configuration
            print("\n📋 Loading configuration...")
            self.config_manager = ConfigManager(self.config_dir)
            self.config_manager.load()

            # Setup logging
            self._setup_logging()

            logger = logging.getLogger(__name__)
            logger.info("Starting ManeYantra...")

            # Initialize RabbitMQ
            print("🔌 Connecting to RabbitMQ broker...")
            rabbitmq_config = self.config_manager.get_rabbitmq_config()
            self.event_bus = RabbitMQEventBus(**rabbitmq_config)
            await self.event_bus.connect()

            # Publish system start event
            await self.event_bus.publish_system_event("start")

            # Initialize plugin manager
            print("🔧 Loading plugins...")
            self.plugin_manager = PluginManager(self.config_manager, self.event_bus)
            await self.plugin_manager.load_plugins()

            # Initialize plugins
            print("⚙️  Initializing plugins...")
            await self.plugin_manager.initialize_plugins()

            # Start plugins
            print("🚀 Starting plugins...")
            await self.plugin_manager.start_plugins()

            self._running = True

            print("\n✅ ManeYantra is running!")
            print(f"📊 Loaded {len(self.plugin_manager.plugins)} plugins")
            print("   Press Ctrl+C to stop\n")

            logger.info("ManeYantra started successfully")

            # Wait for shutdown signal
            await self._shutdown_event.wait()

        except Exception as e:
            logging.error(f"Failed to start ManeYantra: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop the application."""
        if not self._running:
            return

        logger = logging.getLogger(__name__)
        logger.info("Stopping ManeYantra...")

        print("\n⏸️  Stopping ManeYantra...")

        try:
            # Publish system stop event
            if self.event_bus:
                await self.event_bus.publish_system_event("stop")

            # Stop plugins
            if self.plugin_manager:
                print("🛑 Stopping plugins...")
                await self.plugin_manager.stop_plugins()
                await self.plugin_manager.destroy_plugins()

            # Disconnect RabbitMQ
            if self.event_bus:
                print("🔌 Disconnecting from RabbitMQ...")
                await self.event_bus.disconnect()

            self._running = False

            print("✅ ManeYantra stopped gracefully\n")
            logger.info("ManeYantra stopped")

        except Exception as e:
            logging.error(f"Error during shutdown: {e}", exc_info=True)

    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        log_level = self.config_manager.get_log_level()

        # Create logs directory
        paths = self.config_manager.get_paths()
        logs_dir = paths["logs"]
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(logs_dir / "maneyantra.log"),
            ],
        )

        # Reduce noise from libraries
        logging.getLogger("aio_pika").setLevel(logging.WARNING)
        logging.getLogger("aiormq").setLevel(logging.WARNING)

    def trigger_shutdown(self) -> None:
        """Trigger graceful shutdown."""
        self._shutdown_event.set()


async def async_main(config_dir: str = "config") -> None:
    """Async main function."""
    app = ManeYantra(config_dir)

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    def signal_handler():
        print("\n\n⚠️  Shutdown signal received...")
        app.trigger_shutdown()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await app.start()
    finally:
        await app.stop()


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="ManeYantra - Home Automation System")
    parser.add_argument(
        "--config",
        default="config",
        help="Configuration directory (default: config)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="ManeYantra 0.1.0",
    )

    args = parser.parse_args()

    # Run the application
    try:
        asyncio.run(async_main(args.config))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logging.error(f"Fatal error: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    main()
