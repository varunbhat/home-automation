import { DeviceCapability, type Device } from '@/lib/types'
import { hasCapability, isSensor, hasPowerMonitoring } from '@/shared/utils/device-helpers'
import { PowerControl } from '../DeviceControls/PowerControl'
import { BrightnessControl } from '../DeviceControls/BrightnessControl'
import { ColorControl } from '../DeviceControls/ColorControl'
import { ColorTempControl } from '../DeviceControls/ColorTempControl'
import { SensorDisplay } from '../DeviceControls/SensorDisplay'
import { EnergyDisplay } from '../DeviceControls/EnergyDisplay'
import { CameraControls } from '../DeviceControls/CameraControls'

interface DeviceCardControlsProps {
  device: Device
  onCommand: (command: string, params?: Record<string, unknown>) => void
  disabled?: boolean
}

export function DeviceCardControls({ device, onCommand, disabled }: DeviceCardControlsProps) {
  const controls: React.ReactNode[] = []

  // Video streaming (cameras)
  if (hasCapability(device, DeviceCapability.VIDEO_STREAM)) {
    controls.push(
      <CameraControls
        key="camera"
        device={device}
        onCommand={(command, success) => {
          if (success) {
            onCommand(command)
          }
        }}
        disabled={disabled}
      />
    )
  }

  // Power control (most devices)
  if (hasCapability(device, DeviceCapability.ON_OFF)) {
    controls.push(
      <PowerControl
        key="power"
        on={device.state.on ?? false}
        onToggle={() => onCommand(device.state.on ? 'turn_off' : 'turn_on')}
        disabled={disabled}
      />
    )
  }

  // Brightness (dimmable lights)
  if (hasCapability(device, DeviceCapability.BRIGHTNESS)) {
    controls.push(
      <BrightnessControl
        key="brightness"
        value={device.state.brightness ?? 0}
        onChange={(brightness) => onCommand('set_brightness', { brightness })}
        disabled={disabled}
      />
    )
  }

  // Color (RGB lights)
  if (hasCapability(device, DeviceCapability.COLOR)) {
    controls.push(
      <ColorControl
        key="color"
        color={device.state.color}
        onChange={(color) =>
          onCommand('set_hsv', {
            hue: color.hue,
            saturation: color.saturation,
            value: color.value,
          })
        }
        disabled={disabled}
      />
    )
  }

  // Color temperature (white ambiance lights)
  if (hasCapability(device, DeviceCapability.COLOR_TEMPERATURE)) {
    controls.push(
      <ColorTempControl
        key="color-temp"
        value={device.state.color_temperature ?? 4000}
        onChange={(temperature) => onCommand('set_color_temperature', { temperature })}
        disabled={disabled}
      />
    )
  }

  // Sensor displays (read-only)
  if (isSensor(device)) {
    controls.push(<SensorDisplay key="sensor" device={device} />)
  }

  // Energy monitoring
  if (hasPowerMonitoring(device)) {
    controls.push(
      <EnergyDisplay
        key="energy"
        power={device.state.power}
        voltage={device.state.voltage}
        current={device.state.current}
        energy={device.state.energy}
      />
    )
  }

  if (controls.length === 0) {
    return (
      <div className="text-sm text-muted-foreground text-center py-4">
        No controls available
      </div>
    )
  }

  return <div className="space-y-3">{controls}</div>
}
