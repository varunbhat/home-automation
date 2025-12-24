"""FastAPI application for ManeYantra device control."""

import logging
from datetime import datetime
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from maneyantra.api.models import HealthResponse
from maneyantra.api.routers import devices, plugins, events
from maneyantra.core.manager import PluginManager
from maneyantra.core.rabbitmq_bus import RabbitMQEventBus

logger = logging.getLogger(__name__)


def create_app(
    plugin_manager: Optional[PluginManager] = None,
    event_bus: Optional[RabbitMQEventBus] = None,
) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        plugin_manager: PluginManager instance to use for API operations

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="ManeYantra Device API",
        description="REST API for controlling and monitoring ManeYantra home automation devices",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure this properly in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Set plugin manager and event bus for routers
    if plugin_manager:
        devices.set_plugin_manager(plugin_manager)
        plugins.set_plugin_manager(plugin_manager)
        events.set_plugin_manager(plugin_manager)

    if event_bus:
        events.set_event_bus(event_bus)

    # Include routers
    app.include_router(devices.router, prefix="/api/v1")
    app.include_router(plugins.router, prefix="/api/v1")
    app.include_router(events.router, prefix="/api/v1")

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
    async def health_check():
        """Health check endpoint."""
        plugin_health = None

        if plugin_manager:
            try:
                plugin_health = await plugin_manager.health_check()
            except Exception as e:
                logger.error(f"Error checking plugin health: {e}")
                plugin_health = {"error": str(e)}

        return HealthResponse(
            status="healthy" if plugin_manager else "degraded",
            timestamp=datetime.utcnow().isoformat(),
            plugins=plugin_health,
        )

    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "ManeYantra Device API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app
