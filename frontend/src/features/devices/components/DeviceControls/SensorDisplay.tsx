import { Thermometer, Droplets, Battery, DoorOpen, Waves } from 'lucide-react'
import type { Device } from '@/lib/types'
import { formatTemperature, formatPercentage } from '@/shared/utils/formatters'
import { getBatteryStatus } from '@/shared/utils/device-helpers'
import { cn } from '@/shared/utils/cn'

interface SensorDisplayProps {
  device: Device
}

export function SensorDisplay({ device }: SensorDisplayProps) {
  const { state } = device

  return (
    <div className="space-y-2.5">
      {/* Temperature */}
      {state.temperature !== undefined && (
        <div className="flex items-center justify-between rounded-lg bg-gradient-to-r from-blue-500/10 to-blue-500/5 border border-blue-500/20 p-3">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-blue-500/10">
              <Thermometer className="h-4 w-4 text-blue-600 dark:text-blue-500" />
            </div>
            <span className="text-sm font-semibold">Temperature</span>
          </div>
          <span className="text-sm font-bold">{formatTemperature(state.temperature)}</span>
        </div>
      )}

      {/* Humidity */}
      {state.humidity !== undefined && (
        <div className="flex items-center justify-between rounded-lg bg-gradient-to-r from-cyan-500/10 to-cyan-500/5 border border-cyan-500/20 p-3">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-cyan-500/10">
              <Droplets className="h-4 w-4 text-cyan-600 dark:text-cyan-500" />
            </div>
            <span className="text-sm font-semibold">Humidity</span>
          </div>
          <span className="text-sm font-bold">{formatPercentage(state.humidity)}</span>
        </div>
      )}

      {/* Battery */}
      {state.battery !== undefined && (
        <div className={cn(
          "flex items-center justify-between rounded-lg p-3 border",
          getBatteryStatus(state.battery) === 'critical' && 'bg-gradient-to-r from-red-500/10 to-red-500/5 border-red-500/20',
          getBatteryStatus(state.battery) === 'low' && 'bg-gradient-to-r from-yellow-500/10 to-yellow-500/5 border-yellow-500/20',
          getBatteryStatus(state.battery) === 'medium' && 'bg-gradient-to-r from-blue-500/10 to-blue-500/5 border-blue-500/20',
          getBatteryStatus(state.battery) === 'good' && 'bg-gradient-to-r from-green-500/10 to-green-500/5 border-green-500/20'
        )}>
          <div className="flex items-center gap-2.5">
            <div className={cn(
              "p-1.5 rounded-lg",
              getBatteryStatus(state.battery) === 'critical' && 'bg-red-500/10',
              getBatteryStatus(state.battery) === 'low' && 'bg-yellow-500/10',
              getBatteryStatus(state.battery) === 'medium' && 'bg-blue-500/10',
              getBatteryStatus(state.battery) === 'good' && 'bg-green-500/10'
            )}>
              <Battery
                className={cn(
                  'h-4 w-4',
                  getBatteryStatus(state.battery) === 'critical' && 'text-red-600 dark:text-red-500',
                  getBatteryStatus(state.battery) === 'low' && 'text-yellow-600 dark:text-yellow-500',
                  getBatteryStatus(state.battery) === 'medium' && 'text-blue-600 dark:text-blue-500',
                  getBatteryStatus(state.battery) === 'good' && 'text-green-600 dark:text-green-500'
                )}
              />
            </div>
            <span className="text-sm font-semibold">Battery</span>
          </div>
          <span className="text-sm font-bold">{formatPercentage(state.battery)}</span>
        </div>
      )}

      {/* Motion */}
      {state.motion !== undefined && (
        <div className={cn(
          "flex items-center justify-between rounded-lg p-3 border",
          state.motion
            ? 'bg-gradient-to-r from-amber-500/10 to-amber-500/5 border-amber-500/20'
            : 'bg-muted/50 border-border'
        )}>
          <div className="flex items-center gap-2.5">
            <div className={cn(
              "p-1.5 rounded-lg",
              state.motion ? 'bg-amber-500/10' : 'bg-muted'
            )}>
              <Waves className={cn(
                "h-4 w-4",
                state.motion ? 'text-amber-600 dark:text-amber-500' : 'text-muted-foreground'
              )} />
            </div>
            <span className="text-sm font-semibold">Motion</span>
          </div>
          <span className="text-sm font-bold">
            {state.motion ? 'Detected' : 'Clear'}
          </span>
        </div>
      )}

      {/* Contact */}
      {state.contact !== undefined && (
        <div className={cn(
          "flex items-center justify-between rounded-lg p-3 border",
          state.contact
            ? 'bg-gradient-to-r from-amber-500/10 to-amber-500/5 border-amber-500/20'
            : 'bg-muted/50 border-border'
        )}>
          <div className="flex items-center gap-2.5">
            <div className={cn(
              "p-1.5 rounded-lg",
              state.contact ? 'bg-amber-500/10' : 'bg-muted'
            )}>
              <DoorOpen className={cn(
                "h-4 w-4",
                state.contact ? 'text-amber-600 dark:text-amber-500' : 'text-muted-foreground'
              )} />
            </div>
            <span className="text-sm font-semibold">Door/Window</span>
          </div>
          <span className="text-sm font-bold">
            {state.contact ? 'Open' : 'Closed'}
          </span>
        </div>
      )}
    </div>
  )
}
