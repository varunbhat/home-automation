import { Loader2 } from 'lucide-react'
import { Card, CardContent } from '@/shared/components/ui/card'
import type { Device } from '@/lib/types'
import { useDeviceCommand } from '../../hooks/useDeviceCommand'
import { DeviceCardHeader } from './DeviceCardHeader'
import { DeviceCardControls } from './DeviceCardControls'
import { DeviceCardFooter } from './DeviceCardFooter'
import { cn } from '@/shared/utils/cn'

interface DeviceCardProps {
  device: Device
  compact?: boolean
}

export function DeviceCard({ device, compact = false }: DeviceCardProps) {
  const { mutate: executeCommand, isPending } = useDeviceCommand(device.info.id)

  const handleCommand = (command: string, params?: Record<string, unknown>) => {
    executeCommand({ command, params })
  }

  return (
    <Card
      className={cn(
        'relative transition-all duration-200 hover:shadow-lg hover:scale-[1.02] border-2',
        !device.state.online && 'opacity-60 grayscale',
        isPending && 'opacity-70'
      )}
      data-device-id={device.info.id}
      data-device-type={device.info.type}
      data-testid="device-card"
    >
      <DeviceCardHeader device={device} />

      <CardContent className="pt-6 pb-4 px-6">
        <DeviceCardControls
          device={device}
          onCommand={handleCommand}
          disabled={!device.state.online || isPending}
        />

        {!compact && <DeviceCardFooter device={device} />}
      </CardContent>

      {/* Loading overlay */}
      {isPending && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/50 backdrop-blur-sm rounded-lg">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}
    </Card>
  )
}
