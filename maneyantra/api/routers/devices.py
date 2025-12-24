"""Device API endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Path

from maneyantra.api.models import (
    Device,
    DeviceListResponse,
    DeviceCommand,
    CommandResult,
    ErrorResponse,
)
from maneyantra.types.devices import DeviceType, DeviceState
from maneyantra.core.manager import PluginManager
from maneyantra.plugins.devices.base import BaseDevicePlugin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/devices", tags=["devices"])

# Global reference to plugin manager (set by app.py)
plugin_manager: Optional[PluginManager] = None


def set_plugin_manager(manager: PluginManager):
    """Set the plugin manager reference."""
    global plugin_manager
    plugin_manager = manager


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    type: Optional[DeviceType] = Query(None, description="Filter by device type"),
    plugin_id: Optional[str] = Query(None, description="Filter by plugin ID"),
    room: Optional[str] = Query(None, description="Filter by room"),
    online: Optional[bool] = Query(None, description="Filter by online status"),
):
    """List all devices with optional filters."""
    if not plugin_manager:
        raise HTTPException(status_code=503, detail="Plugin manager not initialized")

    devices = []

    # Get all device plugins
    device_plugins = plugin_manager.get_plugins_by_type("device")

    for plugin in device_plugins:
        if not isinstance(plugin, BaseDevicePlugin):
            continue

        # Filter by plugin_id
        if plugin_id and plugin.plugin_id != plugin_id:
            continue

        # Get devices from plugin
        for device in plugin.get_devices():
            # Apply filters
            if type and device.info.type != type:
                continue

            if room and device.info.room != room:
                continue

            if online is not None and device.state.online != online:
                continue

            devices.append(
                Device(
                    info=device.info,
                    state=device.state,
                )
            )

    return DeviceListResponse(devices=devices, total=len(devices))


@router.get("/{device_id}", response_model=Device)
async def get_device(
    device_id: str = Path(..., description="Device ID"),
):
    """Get device by ID."""
    if not plugin_manager:
        raise HTTPException(status_code=503, detail="Plugin manager not initialized")

    # Search for device across all plugins
    device_plugins = plugin_manager.get_plugins_by_type("device")

    for plugin in device_plugins:
        if not isinstance(plugin, BaseDevicePlugin):
            continue

        device = plugin.get_device(device_id)
        if device:
            return Device(
                info=device.info,
                state=device.state,
            )

    raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")


@router.post("/{device_id}/command", response_model=CommandResult)
async def execute_command(
    device_id: str = Path(..., description="Device ID"),
    command: DeviceCommand = ...,
):
    """Execute a command on a device."""
    if not plugin_manager:
        raise HTTPException(status_code=503, detail="Plugin manager not initialized")

    # Find device
    device_plugins = plugin_manager.get_plugins_by_type("device")

    for plugin in device_plugins:
        if not isinstance(plugin, BaseDevicePlugin):
            continue

        device = plugin.get_device(device_id)
        if device:
            try:
                # Execute command
                await device.execute_command(command.command, command.params)

                # Refresh state
                await device.refresh_state()

                return CommandResult(
                    success=True,
                    message=f"Command '{command.command}' executed successfully",
                    state=device.state,
                )

            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

            except Exception as e:
                logger.error(f"Error executing command: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to execute command: {str(e)}",
                )

    raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")


@router.get("/{device_id}/state", response_model=DeviceState)
async def get_device_state(
    device_id: str = Path(..., description="Device ID"),
):
    """Get device state."""
    if not plugin_manager:
        raise HTTPException(status_code=503, detail="Plugin manager not initialized")

    # Find device
    device_plugins = plugin_manager.get_plugins_by_type("device")

    for plugin in device_plugins:
        if not isinstance(plugin, BaseDevicePlugin):
            continue

        device = plugin.get_device(device_id)
        if device:
            return device.state

    raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")


@router.post("/{device_id}/refresh", response_model=DeviceState)
async def refresh_device_state(
    device_id: str = Path(..., description="Device ID"),
):
    """Refresh device state from physical device."""
    if not plugin_manager:
        raise HTTPException(status_code=503, detail="Plugin manager not initialized")

    # Find device
    device_plugins = plugin_manager.get_plugins_by_type("device")

    for plugin in device_plugins:
        if not isinstance(plugin, BaseDevicePlugin):
            continue

        device = plugin.get_device(device_id)
        if device:
            try:
                # Refresh state from device
                state = await device.refresh_state()
                return state

            except Exception as e:
                logger.error(f"Error refreshing device state: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to refresh device state: {str(e)}",
                )

    raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
