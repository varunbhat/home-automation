import { format, formatDistanceToNow } from 'date-fns'

// Format timestamp to readable string
export function formatTimestamp(timestamp: number | string | Date): string {
  const date = typeof timestamp === 'number' ? new Date(timestamp * 1000) : new Date(timestamp)
  return format(date, 'MMM d, yyyy HH:mm:ss')
}

// Format relative time (e.g., "2 hours ago")
export function formatRelativeTime(timestamp: number | string | Date): string {
  const date = typeof timestamp === 'number' ? new Date(timestamp * 1000) : new Date(timestamp)
  return formatDistanceToNow(date, { addSuffix: true })
}

// Format percentage
export function formatPercentage(value: number): string {
  return `${Math.round(value)}%`
}

// Format temperature
export function formatTemperature(celsius: number | null | undefined): string {
  if (celsius == null) return 'N/A'
  return `${celsius.toFixed(1)}°C`
}

// Format power (Watts)
export function formatPower(watts: number | null | undefined): string {
  if (watts == null) return 'N/A'
  if (watts >= 1000) {
    return `${(watts / 1000).toFixed(2)} kW`
  }
  return `${watts.toFixed(1)} W`
}

// Format energy (kWh)
export function formatEnergy(kwh: number | null | undefined): string {
  if (kwh == null) return 'N/A'
  return `${kwh.toFixed(2)} kWh`
}

// Format voltage
export function formatVoltage(volts: number | null | undefined): string {
  if (volts == null) return 'N/A'
  return `${volts.toFixed(1)} V`
}

// Format current (Amps)
export function formatCurrent(amps: number | null | undefined): string {
  if (amps == null) return 'N/A'
  return `${amps.toFixed(2)} A`
}

// Format color temperature (Kelvin)
export function formatColorTemperature(kelvin: number): string {
  return `${kelvin}K`
}

// Get color temperature label
export function getColorTemperatureLabel(kelvin: number): string {
  if (kelvin < 3000) return 'Warm'
  if (kelvin < 4000) return 'Soft White'
  if (kelvin < 5000) return 'Neutral'
  if (kelvin < 6000) return 'Cool White'
  return 'Daylight'
}

// Format HSV color to CSS hsl
export function hsvToHsl(hue: number, saturation: number, value: number): string {
  const s = saturation / 100
  const v = value / 100

  const l = (2 - s) * v / 2

  let sHsl: number
  if (l !== 0) {
    if (l === 1) {
      sHsl = 0
    } else if (l < 0.5) {
      sHsl = s * v / (l * 2)
    } else {
      sHsl = s * v / (2 - l * 2)
    }
  } else {
    sHsl = s
  }

  return `hsl(${hue}, ${Math.round(sHsl * 100)}%, ${Math.round(l * 100)}%)`
}
