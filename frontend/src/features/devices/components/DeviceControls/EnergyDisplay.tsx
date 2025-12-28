import { Zap, Activity, TrendingUp } from 'lucide-react'
import { formatPower, formatVoltage, formatCurrent, formatEnergy } from '@/shared/utils/formatters'

interface EnergyDisplayProps {
  power?: number
  voltage?: number
  current?: number
  energy?: number
}

export function EnergyDisplay({ power, voltage, current, energy }: EnergyDisplayProps) {
  const hasData = power !== undefined || voltage !== undefined || current !== undefined || energy !== undefined

  if (!hasData) return null

  return (
    <div className="space-y-2.5">
      {/* Real-time Power */}
      {power !== undefined && (
        <div className="flex items-center justify-between rounded-lg bg-gradient-to-r from-yellow-500/10 to-yellow-500/5 border border-yellow-500/20 p-3">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-yellow-500/10">
              <Zap className="h-4 w-4 text-yellow-600 dark:text-yellow-500" />
            </div>
            <span className="text-sm font-semibold">Power</span>
          </div>
          <span className="text-sm font-bold">{formatPower(power)}</span>
        </div>
      )}

      {/* Voltage */}
      {voltage !== undefined && (
        <div className="flex items-center justify-between rounded-lg bg-gradient-to-r from-blue-500/10 to-blue-500/5 border border-blue-500/20 p-3">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-blue-500/10">
              <Activity className="h-4 w-4 text-blue-600 dark:text-blue-500" />
            </div>
            <span className="text-sm font-semibold">Voltage</span>
          </div>
          <span className="text-sm font-bold">{formatVoltage(voltage)}</span>
        </div>
      )}

      {/* Current */}
      {current !== undefined && (
        <div className="flex items-center justify-between rounded-lg bg-gradient-to-r from-purple-500/10 to-purple-500/5 border border-purple-500/20 p-3">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-purple-500/10">
              <Activity className="h-4 w-4 text-purple-600 dark:text-purple-500" />
            </div>
            <span className="text-sm font-semibold">Current</span>
          </div>
          <span className="text-sm font-bold">{formatCurrent(current)}</span>
        </div>
      )}

      {/* Energy Consumption */}
      {energy !== undefined && (
        <div className="flex items-center justify-between rounded-lg bg-gradient-to-r from-green-500/10 to-green-500/5 border border-green-500/20 p-3">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-green-500/10">
              <TrendingUp className="h-4 w-4 text-green-600 dark:text-green-500" />
            </div>
            <span className="text-sm font-semibold">Energy (This Month)</span>
          </div>
          <span className="text-sm font-bold">{formatEnergy(energy)}</span>
        </div>
      )}
    </div>
  )
}
