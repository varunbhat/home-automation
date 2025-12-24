"""Plugin API endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Path

from maneyantra.api.models import (
    PluginInfo,
    PluginListResponse,
    DiscoveryResult,
)
from maneyantra.core.manager import PluginManager
from maneyantra.plugins.devices.base import BaseDevicePlugin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plugins", tags=["plugins"])

# Global reference to plugin manager (set by app.py)
plugin_manager: Optional[PluginManager] = None


def set_plugin_manager(manager: PluginManager):
    """Set the plugin manager reference."""
    global plugin_manager
    plugin_manager = manager


@router.get("", response_model=PluginListResponse)
async def list_plugins():
    """List all plugins."""
    if not plugin_manager:
        raise HTTPException(status_code=503, detail="Plugin manager not initialized")

    plugins = []

    for plugin in plugin_manager.get_plugins():
        # Count devices for device plugins
        device_count = 0
        if isinstance(plugin, BaseDevicePlugin):
            device_count = len(plugin.get_devices())

        plugins.append(
            PluginInfo(
                id=plugin.plugin_id,
                name=plugin.metadata.name,
                version=plugin.metadata.version,
                type=plugin.metadata.plugin_type.value,
                description=plugin.metadata.description,
                state=plugin.state.value,
                device_count=device_count,
            )
        )

    return PluginListResponse(plugins=plugins, total=len(plugins))


@router.get("/{plugin_id}", response_model=PluginInfo)
async def get_plugin(
    plugin_id: str = Path(..., description="Plugin ID"),
):
    """Get plugin by ID."""
    if not plugin_manager:
        raise HTTPException(status_code=503, detail="Plugin manager not initialized")

    plugin = plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    # Count devices for device plugins
    device_count = 0
    if isinstance(plugin, BaseDevicePlugin):
        device_count = len(plugin.get_devices())

    return PluginInfo(
        id=plugin.plugin_id,
        name=plugin.metadata.name,
        version=plugin.metadata.version,
        type=plugin.metadata.plugin_type.value,
        description=plugin.metadata.description,
        state=plugin.state.value,
        device_count=device_count,
    )


@router.post("/{plugin_id}/discover", response_model=DiscoveryResult)
async def discover_devices(
    plugin_id: str = Path(..., description="Plugin ID"),
):
    """Trigger device discovery for a plugin."""
    if not plugin_manager:
        raise HTTPException(status_code=503, detail="Plugin manager not initialized")

    plugin = plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    if not isinstance(plugin, BaseDevicePlugin):
        raise HTTPException(
            status_code=400,
            detail=f"Plugin {plugin_id} is not a device plugin",
        )

    try:
        # Discover new devices
        logger.info(f"Triggering discovery for plugin: {plugin_id}")
        new_devices = await plugin.discover_devices()

        # Add only new devices
        added_count = 0
        for device in new_devices:
            if device.info.id not in plugin.devices:
                await plugin.add_device(device)
                added_count += 1

        return DiscoveryResult(
            message=f"Discovery completed for {plugin.metadata.name}",
            discovered_count=added_count,
        )

    except Exception as e:
        logger.error(f"Error during discovery: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Discovery failed: {str(e)}",
        )
