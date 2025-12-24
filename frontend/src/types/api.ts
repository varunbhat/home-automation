// API Types generated from TypeSpec

export type DeviceType =
  | "light"
  | "switch"
  | "camera"
  | "sensor"
  | "motion_sensor"
  | "door_sensor"
  | "thermostat"
  | "lock"
  | "plug"
  | "unknown";

export type DeviceCapability =
  | "on_off"
  | "brightness"
  | "color"
  | "color_temperature"
  | "motion_detection"
  | "temperature"
  | "humidity"
  | "battery"
  | "contact"
  | "video_stream"
  | "audio"
  | "energy_monitoring"
  | "power_monitoring"
  | "person_detection"
  | "face_detection"
  | "crying_detection";

export interface ColorValue {
  hue: number; // 0-360
  saturation: number; // 0-100
  value: number; // 0-100
}

export interface DeviceState {
  online: boolean;
  last_seen?: number;
  on?: boolean;
  brightness?: number; // 0-100
  color?: ColorValue;
  color_temperature?: number; // 2000-9000
  temperature?: number;
  humidity?: number; // 0-100
  battery?: number; // 0-100
  motion?: boolean;
  contact?: boolean;
  power?: number;
  energy?: number;
  voltage?: number;
  current?: number;
  custom?: Record<string, unknown>;
}

export interface DeviceInfo {
  id: string;
  name: string;
  type: DeviceType;
  capabilities: DeviceCapability[];
  manufacturer?: string;
  model?: string;
  sw_version?: string;
  hw_version?: string;
  plugin_id: string;
  room?: string;
  tags?: string[];
}

export interface Device {
  info: DeviceInfo;
  state: DeviceState;
}

export interface DeviceListResponse {
  devices: Device[];
  total: number;
}

export interface DeviceCommand {
  command: string;
  params?: Record<string, unknown>;
}

export interface CommandResult {
  success: boolean;
  message?: string;
  state?: DeviceState;
}

export interface PluginInfo {
  id: string;
  name: string;
  version: string;
  type: string;
  description?: string;
  state: string;
  device_count: number;
}

export interface PluginListResponse {
  plugins: PluginInfo[];
  total: number;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  plugins?: Record<string, unknown>;
}

export interface ErrorResponse {
  error: string;
  details?: Record<string, unknown>;
}

// SSE Event types
export type SSEEventType =
  | "connected"
  | "state"
  | "discovery"
  | "available"
  | "error"
  | "system"
  | "heartbeat";

export interface SSEEvent {
  type: SSEEventType;
  timestamp: string;
  device_id?: string;
  data?: unknown;
}
