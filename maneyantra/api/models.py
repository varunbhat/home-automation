"""API models for FastAPI endpoints."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from maneyantra.types.devices import (
    DeviceInfo,
    DeviceState,
    DeviceType,
    DeviceCapability,
)


class Device(BaseModel):
    """Complete device with info and state."""

    info: DeviceInfo
    state: DeviceState

    model_config = {'exclude_none': True}


class DeviceListResponse(BaseModel):
    """List of devices response."""

    devices: List[Device]
    total: int


class DeviceCommand(BaseModel):
    """Device command request."""

    command: str = Field(..., description="Command name (e.g., turn_on, turn_off)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")


class CommandResult(BaseModel):
    """Command execution result."""

    success: bool
    message: Optional[str] = None
    state: Optional[DeviceState] = None
    data: Optional[Dict[str, Any]] = None  # Command-specific data (e.g., stream_url)


class ErrorResponse(BaseModel):
    """API error response."""

    error: str
    details: Optional[Dict[str, Any]] = None


class PluginInfo(BaseModel):
    """Plugin information."""

    id: str
    name: str
    version: str
    type: str
    description: Optional[str] = None
    state: str
    device_count: int


class PluginListResponse(BaseModel):
    """List of plugins response."""

    plugins: List[PluginInfo]
    total: int


class DiscoveryResult(BaseModel):
    """Device discovery result."""

    message: str
    discovered_count: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    plugins: Optional[Dict[str, Any]] = None
