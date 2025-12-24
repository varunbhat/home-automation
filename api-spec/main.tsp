import "@typespec/http";
import "@typespec/rest";
import "@typespec/openapi3";

using TypeSpec.Http;
using TypeSpec.Rest;

@service({
  title: "ManeYantra Device API",
})
@server("http://localhost:8000", "Development server")
namespace ManeYantra;

// ==================== Enums ====================

enum DeviceType {
  light: "light",
  switch: "switch",
  camera: "camera",
  sensor: "sensor",
  motion_sensor: "motion_sensor",
  door_sensor: "door_sensor",
  thermostat: "thermostat",
  lock: "lock",
  plug: "plug",
  unknown: "unknown",
}

enum DeviceCapability {
  // Power
  on_off: "on_off",

  // Lighting
  brightness: "brightness",
  color: "color",
  color_temperature: "color_temperature",

  // Sensors
  motion_detection: "motion_detection",
  temperature: "temperature",
  humidity: "humidity",
  battery: "battery",
  contact: "contact",

  // Media
  video_stream: "video_stream",
  audio: "audio",

  // Energy
  energy_monitoring: "energy_monitoring",
  power_monitoring: "power_monitoring",

  // Security
  person_detection: "person_detection",
  face_detection: "face_detection",
  crying_detection: "crying_detection",
}

// ==================== Models ====================

@doc("Color value in HSV format")
model ColorValue {
  @doc("Hue (0-360 degrees)")
  @minValue(0)
  @maxValue(360)
  hue: int32;

  @doc("Saturation (0-100%)")
  @minValue(0)
  @maxValue(100)
  saturation: int32;

  @doc("Value/Brightness (0-100%)")
  @minValue(0)
  @maxValue(100)
  value: int32;
}

@doc("Device state information")
model DeviceState {
  @doc("Device online status")
  online: boolean;

  @doc("Last seen timestamp (Unix epoch)")
  last_seen?: float64;

  @doc("Power state")
  on?: boolean;

  @doc("Brightness level (0-100%)")
  @minValue(0)
  @maxValue(100)
  brightness?: int32;

  @doc("Color in HSV format")
  color?: ColorValue;

  @doc("Color temperature in Kelvin")
  @minValue(2000)
  @maxValue(9000)
  color_temperature?: int32;

  @doc("Temperature in Celsius")
  temperature?: float64;

  @doc("Humidity percentage")
  @minValue(0)
  @maxValue(100)
  humidity?: int32;

  @doc("Battery percentage")
  @minValue(0)
  @maxValue(100)
  battery?: int32;

  @doc("Motion detected")
  motion?: boolean;

  @doc("Contact state (true = open, false = closed)")
  contact?: boolean;

  @doc("Power consumption in Watts")
  power?: float64;

  @doc("Energy consumption in kWh")
  energy?: float64;

  @doc("Voltage in Volts")
  voltage?: float64;

  @doc("Current in Amps")
  current?: float64;

  @doc("Custom attributes")
  custom?: Record<string>;
}

@doc("Device information")
model DeviceInfo {
  @doc("Unique device identifier")
  id: string;

  @doc("Device display name")
  name: string;

  @doc("Device type")
  type: DeviceType;

  @doc("Device capabilities")
  capabilities: DeviceCapability[];

  @doc("Manufacturer name")
  manufacturer?: string;

  @doc("Device model")
  model?: string;

  @doc("Software version")
  sw_version?: string;

  @doc("Hardware version")
  hw_version?: string;

  @doc("Plugin ID managing this device")
  plugin_id: string;

  @doc("Room assignment")
  room?: string;

  @doc("Device tags")
  tags?: string[];
}

@doc("Complete device with info and state")
model Device {
  @doc("Device information")
  info: DeviceInfo;

  @doc("Current device state")
  state: DeviceState;
}

@doc("Device command request")
model DeviceCommand {
  @doc("Command name (e.g., turn_on, turn_off, set_brightness)")
  command: string;

  @doc("Command parameters")
  params?: Record<unknown>;
}

@doc("Command execution result")
model CommandResult {
  @doc("Execution success status")
  success: boolean;

  @doc("Result message")
  message?: string;

  @doc("Updated device state")
  state?: DeviceState;
}

@doc("API error response")
@error
model ErrorResponse {
  @doc("Error message")
  error: string;

  @doc("Error details")
  details?: Record<unknown>;
}

@doc("List of devices response")
model DeviceListResponse {
  @doc("List of devices")
  devices: Device[];

  @doc("Total count of devices")
  total: int32;
}

@doc("Plugin information")
model PluginInfo {
  @doc("Plugin identifier")
  id: string;

  @doc("Plugin name")
  name: string;

  @doc("Plugin version")
  version: string;

  @doc("Plugin type")
  type: string;

  @doc("Plugin description")
  description?: string;

  @doc("Plugin state")
  state: string;

  @doc("Number of devices managed by this plugin")
  device_count: int32;
}

@doc("Health check response")
model HealthResponse {
  @doc("Service status")
  status: string;

  @doc("Timestamp of health check")
  timestamp: string;

  @doc("Plugin health information")
  plugins?: Record<unknown>;
}

// ==================== Routes ====================

@route("/api/v1")
namespace API {

  @route("/health")
  @get
  @doc("Health check endpoint")
  op healthCheck(): HealthResponse;

  @route("/events")
  namespace Events {

    @get
    @route("/stream")
    @doc("Server-Sent Events stream for real-time device updates")
    op eventStream(
      @query device_id?: string,
      @query event_type?: string,
    ): {
      @header("Content-Type") contentType: "text/event-stream";
      @header("Cache-Control") cacheControl: "no-cache";
      @header("Connection") connection: "keep-alive";
      @body body: string;
    };

    @get
    @route("/devices/{device_id}/stream")
    @doc("SSE stream for a specific device")
    op deviceEventStream(
      @path device_id: string,
    ): {
      @header("Content-Type") contentType: "text/event-stream";
      @header("Cache-Control") cacheControl: "no-cache";
      @header("Connection") connection: "keep-alive";
      @body body: string;
    };
  }

  @route("/devices")
  namespace Devices {

    @get
    @doc("List all devices")
    op listDevices(
      @query type?: DeviceType,
      @query plugin_id?: string,
      @query room?: string,
      @query online?: boolean,
    ): DeviceListResponse | ErrorResponse;

    @get
    @doc("Get device by ID")
    op getDevice(
      @path device_id: string,
    ): Device | ErrorResponse;

    @post
    @route("/{device_id}/command")
    @doc("Execute command on device")
    op executeCommand(
      @path device_id: string,
      @body command: DeviceCommand,
    ): CommandResult | ErrorResponse;

    @get
    @route("/{device_id}/state")
    @doc("Get device state")
    op getDeviceState(
      @path device_id: string,
    ): DeviceState | ErrorResponse;

    @post
    @route("/{device_id}/refresh")
    @doc("Refresh device state from physical device")
    op refreshDeviceState(
      @path device_id: string,
    ): DeviceState | ErrorResponse;
  }

  @route("/plugins")
  namespace Plugins {

    @get
    @doc("List all plugins")
    op listPlugins(): {
      plugins: PluginInfo[];
      total: int32;
    } | ErrorResponse;

    @get
    @doc("Get plugin by ID")
    op getPlugin(
      @path plugin_id: string,
    ): PluginInfo | ErrorResponse;

    @post
    @route("/{plugin_id}/discover")
    @doc("Trigger device discovery for a plugin")
    op discoverDevices(
      @path plugin_id: string,
    ): {
      message: string;
      discovered_count: int32;
    } | ErrorResponse;
  }
}
