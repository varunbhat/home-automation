"""Station API endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from maneyantra.core.manager import PluginManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stations", tags=["stations"])

# Global reference to plugin manager (set by app.py)
plugin_manager: Optional[PluginManager] = None


def set_plugin_manager(manager: PluginManager):
    """Set the plugin manager reference."""
    global plugin_manager
    plugin_manager = manager


class StationInfo(BaseModel):
    """Station information."""
    serial: str
    name: str
    model: str
    guard_mode: int
    plugin_id: str


class StationListResponse(BaseModel):
    """List of stations response."""
    stations: list[StationInfo]
    total: int


class GuardModeRequest(BaseModel):
    """Guard mode change request."""
    mode: int


class GuardModeResponse(BaseModel):
    """Guard mode change response."""
    success: bool
    mode: int


@router.get("", response_model=StationListResponse)
async def list_stations():
    """List all stations."""
    if not plugin_manager:
        raise HTTPException(status_code=503, detail="Plugin manager not initialized")

    stations = []

    # Get Eufy plugin
    eufy_plugin = plugin_manager.get_plugin("eufy")
    if eufy_plugin and hasattr(eufy_plugin, 'get_stations'):
        try:
            eufy_stations = await eufy_plugin.get_stations()
            for station in eufy_stations:
                stations.append(StationInfo(
                    serial=station['serial'],
                    name=station['name'],
                    model=station['model'],
                    guard_mode=station['guard_mode'],
                    plugin_id='eufy'
                ))
        except Exception as e:
            logger.error(f"Error getting Eufy stations: {e}", exc_info=True)

    return StationListResponse(stations=stations, total=len(stations))


@router.post("/{serial}/guard-mode", response_model=GuardModeResponse)
async def set_guard_mode(
    serial: str = Path(..., description="Station serial number"),
    request: GuardModeRequest = ...,
):
    """Set station guard mode."""
    if not plugin_manager:
        raise HTTPException(status_code=503, detail="Plugin manager not initialized")

    # Get Eufy plugin
    eufy_plugin = plugin_manager.get_plugin("eufy")
    if not eufy_plugin:
        raise HTTPException(status_code=404, detail="Eufy plugin not found")

    if not hasattr(eufy_plugin, 'set_guard_mode'):
        raise HTTPException(status_code=501, detail="Guard mode control not supported")

    try:
        success = await eufy_plugin.set_guard_mode(serial, request.mode)
        if success:
            return GuardModeResponse(success=True, mode=request.mode)
        else:
            raise HTTPException(status_code=500, detail="Failed to set guard mode")
    except Exception as e:
        logger.error(f"Error setting guard mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set guard mode: {str(e)}")
