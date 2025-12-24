"""API server runner for ManeYantra."""

import asyncio
import logging
from typing import Optional
import uvicorn
from uvicorn import Config, Server

from maneyantra.api.app import create_app
from maneyantra.core.manager import PluginManager
from maneyantra.core.rabbitmq_bus import RabbitMQEventBus

logger = logging.getLogger(__name__)


class APIServer:
    """API server wrapper for running FastAPI with ManeYantra."""

    def __init__(
        self,
        plugin_manager: PluginManager,
        event_bus: RabbitMQEventBus,
        host: str = "0.0.0.0",
        port: int = 8000,
    ):
        self.plugin_manager = plugin_manager
        self.event_bus = event_bus
        self.host = host
        self.port = port
        self.server: Optional[Server] = None
        self._server_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the API server."""
        logger.info(f"Starting API server on {self.host}:{self.port}")

        # Create FastAPI app
        app = create_app(self.plugin_manager, self.event_bus)

        # Create uvicorn config
        config = Config(
            app=app,
            host=self.host,
            port=self.port,
            log_level="info",
            loop="asyncio",
        )

        # Create server
        self.server = Server(config)

        # Start server in background task
        self._server_task = asyncio.create_task(self.server.serve())

        logger.info(f"API server started at http://{self.host}:{self.port}")
        logger.info(f"API documentation at http://{self.host}:{self.port}/docs")

    async def stop(self) -> None:
        """Stop the API server."""
        if not self.server:
            return

        logger.info("Stopping API server...")

        # Shutdown server
        self.server.should_exit = True

        # Wait for server task to complete
        if self._server_task:
            try:
                await asyncio.wait_for(self._server_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("API server shutdown timed out")
                self._server_task.cancel()
                try:
                    await self._server_task
                except asyncio.CancelledError:
                    pass

        logger.info("API server stopped")
