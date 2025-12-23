"""Plugin manager for loading and managing plugins."""

import asyncio
import importlib
import logging
from typing import Dict, List, Optional

from .config import ConfigManager
from .rabbitmq_bus import RabbitMQEventBus
from .plugin import PluginBase, PluginState


logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manages plugin lifecycle.

    Responsibilities:
    - Load plugins from configuration
    - Initialize plugins in dependency order
    - Start/stop plugins
    - Monitor plugin health
    """

    def __init__(self, config_manager: ConfigManager, event_bus: RabbitMQEventBus):
        self.config_manager = config_manager
        self.event_bus = event_bus

        self.plugins: Dict[str, PluginBase] = {}
        self._logger = logging.getLogger("plugin_manager")

    async def load_plugins(self) -> None:
        """Load all enabled plugins from configuration."""
        self._logger.info("Loading plugins...")

        enabled_plugins = self.config_manager.get_enabled_plugins()

        for plugin_id, plugin_config in enabled_plugins.items():
            try:
                plugin = await self._load_plugin(plugin_id, plugin_config)
                self.plugins[plugin_id] = plugin
                self._logger.info(f"Loaded plugin: {plugin_id}")

            except Exception as e:
                self._logger.error(f"Failed to load plugin {plugin_id}: {e}", exc_info=True)
                await self.event_bus.publish_plugin_status(
                    plugin_id,
                    "load_error",
                    {"error": str(e)},
                )

        self._logger.info(f"Loaded {len(self.plugins)} plugins")

    async def _load_plugin(self, plugin_id: str, config: Dict) -> PluginBase:
        """
        Load a single plugin.

        Args:
            plugin_id: Plugin identifier
            config: Plugin configuration

        Returns:
            Instantiated plugin

        Raises:
            ImportError: If plugin module cannot be imported
            AttributeError: If plugin class not found
        """
        module_path = config.get("module")
        class_name = config.get("class")
        plugin_config = config.get("config", {})

        if not module_path or not class_name:
            raise ValueError(f"Plugin {plugin_id} missing module or class in config")

        # Dynamically import plugin module
        module = importlib.import_module(module_path)

        # Get plugin class
        plugin_class = getattr(module, class_name)

        # Instantiate plugin
        plugin = plugin_class(
            plugin_id=plugin_id,
            config=plugin_config,
            event_bus=self.event_bus,
        )

        return plugin

    async def initialize_plugins(self) -> None:
        """Initialize all loaded plugins."""
        self._logger.info("Initializing plugins...")

        # Resolve initialization order based on dependencies
        init_order = self._resolve_dependency_order()

        for plugin_id in init_order:
            plugin = self.plugins.get(plugin_id)
            if not plugin:
                continue

            try:
                self._logger.info(f"Initializing plugin: {plugin_id}")
                await plugin.run_initialize()

            except Exception as e:
                self._logger.error(
                    f"Failed to initialize plugin {plugin_id}: {e}",
                    exc_info=True,
                )

        self._logger.info("Plugins initialized")

    async def start_plugins(self) -> None:
        """Start all initialized plugins."""
        self._logger.info("Starting plugins...")

        # Start in dependency order
        start_order = self._resolve_dependency_order()

        for plugin_id in start_order:
            plugin = self.plugins.get(plugin_id)
            if not plugin:
                continue

            if plugin.state != PluginState.INITIALIZED:
                self._logger.warning(
                    f"Skipping start for plugin {plugin_id} (state: {plugin.state.value})"
                )
                continue

            try:
                self._logger.info(f"Starting plugin: {plugin_id}")
                await plugin.run_start()

            except Exception as e:
                self._logger.error(
                    f"Failed to start plugin {plugin_id}: {e}",
                    exc_info=True,
                )

        self._logger.info("Plugins started")

    async def stop_plugins(self) -> None:
        """Stop all running plugins."""
        self._logger.info("Stopping plugins...")

        # Stop in reverse dependency order
        stop_order = list(reversed(self._resolve_dependency_order()))

        for plugin_id in stop_order:
            plugin = self.plugins.get(plugin_id)
            if not plugin:
                continue

            if plugin.state not in [PluginState.RUNNING, PluginState.ERROR]:
                continue

            try:
                self._logger.info(f"Stopping plugin: {plugin_id}")
                await plugin.run_stop()

            except Exception as e:
                self._logger.error(
                    f"Error stopping plugin {plugin_id}: {e}",
                    exc_info=True,
                )

        self._logger.info("Plugins stopped")

    async def destroy_plugins(self) -> None:
        """Destroy all plugins."""
        for plugin_id, plugin in self.plugins.items():
            try:
                await plugin.destroy()
            except Exception as e:
                self._logger.error(
                    f"Error destroying plugin {plugin_id}: {e}",
                    exc_info=True,
                )

        self.plugins.clear()

    def get_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """Get a plugin by ID."""
        return self.plugins.get(plugin_id)

    def get_plugins(self) -> List[PluginBase]:
        """Get all plugins."""
        return list(self.plugins.values())

    def get_plugins_by_type(self, plugin_type: str) -> List[PluginBase]:
        """Get plugins by type."""
        return [
            plugin
            for plugin in self.plugins.values()
            if plugin.metadata.plugin_type.value == plugin_type
        ]

    async def health_check(self) -> Dict[str, Dict]:
        """Run health check on all plugins."""
        health = {}

        for plugin_id, plugin in self.plugins.items():
            try:
                health[plugin_id] = await plugin.health_check()
            except Exception as e:
                health[plugin_id] = {
                    "healthy": False,
                    "error": str(e),
                }

        return health

    def _resolve_dependency_order(self) -> List[str]:
        """
        Resolve plugin load order based on dependencies.

        Uses topological sort.
        """
        # For now, simple implementation without dependency checking
        # TODO: Implement proper topological sort based on metadata.dependencies

        return list(self.plugins.keys())

    async def reload_plugin(self, plugin_id: str) -> None:
        """
        Reload a specific plugin.

        Stops, reloads, initializes, and starts the plugin.
        """
        self._logger.info(f"Reloading plugin: {plugin_id}")

        # Get current plugin
        plugin = self.plugins.get(plugin_id)
        if plugin:
            await plugin.run_stop()

        # Reload config
        self.config_manager.load()
        plugin_config = self.config_manager.get_plugin_config(plugin_id)

        if not plugin_config or not plugin_config.get("enabled"):
            # Plugin disabled or removed
            if plugin_id in self.plugins:
                del self.plugins[plugin_id]
            self._logger.info(f"Plugin {plugin_id} removed (disabled or not found)")
            return

        # Load new instance
        plugin = await self._load_plugin(plugin_id, plugin_config)
        self.plugins[plugin_id] = plugin

        # Initialize and start
        await plugin.run_initialize()
        await plugin.run_start()

        self._logger.info(f"Plugin {plugin_id} reloaded")
