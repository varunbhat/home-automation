import { type Device, DeviceCapability, DeviceType, type ColorValue } from '@/lib/types'

// Capability checks
export function hasCapability(
  device: Device,
  capability: DeviceCapability
): boolean {
  return device.info.capabilities.includes(capability)
}

// Type guards for devices with specific capabilities
export function hasBrightness(
  device: Device
): device is Device & { state: { brightness: number } } {
  return (
    hasCapability(device, DeviceCapability.BRIGHTNESS) &&
    typeof device.state.brightness === 'number'
  )
}

export function hasColor(
  device: Device
): device is Device & { state: { color: ColorValue } } {
  return (
    hasCapability(device, DeviceCapability.COLOR) &&
    device.state.color !== undefined
  )
}

export function hasColorTemperature(
  device: Device
): device is Device & { state: { color_temperature: number } } {
  return (
    hasCapability(device, DeviceCapability.COLOR_TEMPERATURE) &&
    typeof device.state.color_temperature === 'number'
  )
}

export function hasPowerMonitoring(
  device: Device
): device is Device & { state: { power: number } } {
  return (
    hasCapability(device, DeviceCapability.POWER_MONITORING) &&
    typeof device.state.power === 'number'
  )
}

export function hasBattery(
  device: Device
): device is Device & { state: { battery: number } } {
  return (
    hasCapability(device, DeviceCapability.BATTERY) &&
    typeof device.state.battery === 'number'
  )
}

// Device type checks
export function isLight(device: Device): boolean {
  return device.info.type === DeviceType.LIGHT
}

export function isSwitch(device: Device): boolean {
  return device.info.type === DeviceType.SWITCH
}

export function isCamera(device: Device): boolean {
  return device.info.type === DeviceType.CAMERA
}

export function isSensor(device: Device): boolean {
  return [
    DeviceType.SENSOR,
    DeviceType.MOTION_SENSOR,
    DeviceType.DOOR_SENSOR,
  ].includes(device.info.type)
}

export function isPlug(device: Device): boolean {
  return device.info.type === DeviceType.PLUG
}

// Get device icon name based on type
export function getDeviceIcon(type: DeviceType): string {
  const iconMap: Record<DeviceType, string> = {
    [DeviceType.LIGHT]: 'lightbulb',
    [DeviceType.SWITCH]: 'toggle-left',
    [DeviceType.CAMERA]: 'camera',
    [DeviceType.SENSOR]: 'activity',
    [DeviceType.MOTION_SENSOR]: 'waves',
    [DeviceType.DOOR_SENSOR]: 'door-open',
    [DeviceType.THERMOSTAT]: 'thermometer',
    [DeviceType.LOCK]: 'lock',
    [DeviceType.PLUG]: 'plug',
    [DeviceType.UNKNOWN]: 'help-circle',
  }

  return iconMap[type] || 'help-circle'
}

// Get device type display name
export function getDeviceTypeName(type: DeviceType): string {
  const nameMap: Record<DeviceType, string> = {
    [DeviceType.LIGHT]: 'Light',
    [DeviceType.SWITCH]: 'Switch',
    [DeviceType.CAMERA]: 'Camera',
    [DeviceType.SENSOR]: 'Sensor',
    [DeviceType.MOTION_SENSOR]: 'Motion Sensor',
    [DeviceType.DOOR_SENSOR]: 'Door Sensor',
    [DeviceType.THERMOSTAT]: 'Thermostat',
    [DeviceType.LOCK]: 'Lock',
    [DeviceType.PLUG]: 'Plug',
    [DeviceType.UNKNOWN]: 'Unknown',
  }

  return nameMap[type] || 'Unknown Device'
}

// Check if device is controllable (has ON_OFF capability)
export function isControllable(device: Device): boolean {
  return hasCapability(device, DeviceCapability.ON_OFF)
}

// Check if device is read-only (sensors typically)
export function isReadOnly(device: Device): boolean {
  return isSensor(device) && !isControllable(device)
}

// Get battery level status
export function getBatteryStatus(battery?: number): 'critical' | 'low' | 'medium' | 'good' {
  if (!battery) return 'good'
  if (battery <= 10) return 'critical'
  if (battery <= 25) return 'low'
  if (battery <= 50) return 'medium'
  return 'good'
}

// Format last seen time
export function formatLastSeen(lastSeen?: number): string {
  if (!lastSeen) return 'Never'

  const now = Date.now() / 1000
  const diff = now - lastSeen

  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}
