"""Plugin base classes and types."""

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

from .rabbitmq_bus import RabbitMQEventBus


logger = logging.getLogger(__name__)


class PluginType(str, Enum):
    """Plugin type enumeration."""

    DEVICE = "device"
    AUTOMATION = "automation"
    SERVICE = "service"


class PluginState(str, Enum):
    """Plugin state enumeration."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class PluginMetadata:
    """Plugin metadata."""

    def __init__(
        self,
        name: str,
        version: str,
        plugin_type: PluginType,
        description: str,
        author: Optional[str] = None,
        dependencies: Optional[list[str]] = None,
        capabilities: Optional[list[str]] = None,
    ):
        self.name = name
        self.version = version
        self.plugin_type = plugin_type
        self.description = description
        self.author = author
        self.dependencies = dependencies or []
        self.capabilities = capabilities or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "type": self.plugin_type.value,
            "description": self.description,
            "author": self.author,
            "dependencies": self.dependencies,
            "capabilities": self.capabilities,
        }


class PluginBase(ABC):
    """
    Base class for all plugins.

    Plugins communicate exclusively through RabbitMQ.
    Each plugin must implement the lifecycle methods.
    """

    def __init__(
        self,
        plugin_id: str,
        metadata: PluginMetadata,
        config: Dict[str, Any],
        event_bus: RabbitMQEventBus,
    ):
        self.plugin_id = plugin_id
        self.metadata = metadata
        self.config = config
        self.event_bus = event_bus

        self._state = PluginState.UNINITIALIZED
        self._logger = logging.getLogger(f"plugin.{plugin_id}")

    @property
    def state(self) -> PluginState:
        """Get plugin state."""
        return self._state

    async def _set_state(self, new_state: PluginState) -> None:
        """Set plugin state and publish to RabbitMQ."""
        old_state = self._state
        self._state = new_state

        self._logger.info(f"State changed: {old_state.value} -> {new_state.value}")

        await self.event_bus.publish_plugin_status(
            self.plugin_id,
            new_state.value,
            {"previous_state": old_state.value},
        )

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the plugin.

        Load configuration, setup internal state, but don't connect to devices yet.
        """
        pass

    @abstractmethod
    async def start(self) -> None:
        """
        Start the plugin.

        Connect to devices, start background tasks, subscribe to MQTT topics.
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the plugin.

        Disconnect from devices, stop background tasks, cleanup resources.
        """
        pass

    async def destroy(self) -> None:
        """
        Destroy the plugin.

        Final cleanup before plugin removal. Override if needed.
        """
        pass

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check.

        Returns health status and metrics.
        Override to provide custom health info.
        """
        return {
            "healthy": self._state == PluginState.RUNNING,
            "state": self._state.value,
        }

    async def _lifecycle_wrapper(self, method: str) -> None:
        """Wrap lifecycle methods with state management and error handling."""
        state_map = {
            "initialize": (PluginState.INITIALIZING, PluginState.INITIALIZED),
            "start": (PluginState.STARTING, PluginState.RUNNING),
            "stop": (PluginState.STOPPING, PluginState.STOPPED),
        }

        if method not in state_map:
            return

        starting_state, success_state = state_map[method]

        try:
            await self._set_state(starting_state)

            if method == "initialize":
                await self.initialize()
            elif method == "start":
                await self.start()
            elif method == "stop":
                await self.stop()

            await self._set_state(success_state)

        except Exception as e:
            self._logger.error(f"Error during {method}: {e}", exc_info=True)
            await self._set_state(PluginState.ERROR)
            await self.event_bus.publish_plugin_status(
                self.plugin_id,
                PluginState.ERROR.value,
                {"error": str(e), "method": method},
            )
            raise

    async def run_initialize(self) -> None:
        """Run initialize with lifecycle wrapper."""
        await self._lifecycle_wrapper("initialize")

    async def run_start(self) -> None:
        """Run start with lifecycle wrapper."""
        await self._lifecycle_wrapper("start")

    async def run_stop(self) -> None:
        """Run stop with lifecycle wrapper."""
        await self._lifecycle_wrapper("stop")

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
