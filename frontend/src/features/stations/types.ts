export interface Station {
  serial: string
  name: string
  model: string
  guard_mode: number
  plugin_id: string
}

export interface StationListResponse {
  stations: Station[]
  total: number
}

export interface GuardModeRequest {
  mode: number
}

export interface GuardModeResponse {
  success: boolean
  mode: number
}

export const GUARD_MODES = {
  DISARMED: 0,
  HOME: 1,
  AWAY: 2,
  CUSTOM: 3,
} as const

export const GUARD_MODE_LABELS: Record<number, string> = {
  0: 'Disarmed',
  1: 'Home',
  2: 'Away',
  3: 'Custom',
}

export const GUARD_MODE_ICONS: Record<number, string> = {
  0: '🔓',
  1: '🏠',
  2: '🚪',
  3: '⚙️',
}
