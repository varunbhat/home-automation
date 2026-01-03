"""Device types and enumerations."""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class DeviceType(str, Enum):
    """Device type enumeration."""

    LIGHT = "light"
    SWITCH = "switch"
    CAMERA = "camera"
    SENSOR = "sensor"
    MOTION_SENSOR = "motion_sensor"
    DOOR_SENSOR = "door_sensor"
    THERMOSTAT = "thermostat"
    LOCK = "lock"
    PLUG = "plug"
    UNKNOWN = "unknown"


class DeviceCapability(str, Enum):
    """Device capability enumeration."""

    # Power
    ON_OFF = "on_off"

    # Lighting
    BRIGHTNESS = "brightness"
    COLOR = "color"
    COLOR_TEMPERATURE = "color_temperature"

    # Sensors
    MOTION_DETECTION = "motion_detection"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    BATTERY = "battery"
    CONTACT = "contact"  # Door/window sensor

    # Media
    VIDEO_STREAM = "video_stream"
    AUDIO = "audio"

    # Energy
    ENERGY_MONITORING = "energy_monitoring"
    POWER_MONITORING = "power_monitoring"

    # Security
    PERSON_DETECTION = "person_detection"
    FACE_DETECTION = "face_detection"
    CRYING_DETECTION = "crying_detection"


class ColorValue(BaseModel):
    """Color value in HSV."""

    hue: int = Field(ge=0, le=360, description="Hue (0-360)")
    saturation: int = Field(ge=0, le=100, description="Saturation (0-100)")
    value: int = Field(ge=0, le=100, description="Value/Brightness (0-100)")


class DeviceState(BaseModel):
    """Device state model."""

    # Common
    online: bool = True
    last_seen: Optional[float] = None

    # Power
    on: Optional[bool] = None

    # Lighting
    brightness: Optional[int] = Field(None, ge=0, le=100)
    color: Optional[ColorValue] = None
    color_temperature: Optional[int] = Field(None, ge=2000, le=9000)  # Kelvin

    # Sensors
    temperature: Optional[float] = None  # Celsius
    humidity: Optional[int] = Field(None, ge=0, le=100)  # Percentage
    battery: Optional[int] = Field(None, ge=0, le=100)  # Percentage
    motion: Optional[bool] = None
    contact: Optional[bool] = None  # True = open, False = closed

    # Energy
    power: Optional[float] = None  # Watts
    energy: Optional[float] = None  # kWh
    voltage: Optional[float] = None  # Volts
    current: Optional[float] = None  # Amps

    # Video streaming
    stream_url: Optional[str] = None  # Current active stream URL
    snapshot_url: Optional[str] = None  # Last snapshot URL

    # Custom attributes
    custom: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"  # Allow additional fields

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values by default."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)


class DeviceInfo(BaseModel):
    """Device information model."""

    id: str
    name: str
    type: DeviceType
    capabilities: list[DeviceCapability]
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    sw_version: Optional[str] = None
    hw_version: Optional[str] = None
    plugin_id: str
    room: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class DeviceCommand(BaseModel):
    """Device command model."""

    command: str
    params: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"
