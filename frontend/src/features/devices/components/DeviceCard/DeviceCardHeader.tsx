import * as LucideIcons from 'lucide-react'
import type { Device } from '@/lib/types'
import { getDeviceIcon } from '@/shared/utils/device-helpers'
import { cn } from '@/shared/utils/cn'

interface DeviceCardHeaderProps {
  device: Device
}

export function DeviceCardHeader({ device }: DeviceCardHeaderProps) {
  const iconName = getDeviceIcon(device.info.type)

  // Dynamically get the icon component
  const IconComponent = (LucideIcons as any)[
    iconName.split('-').map((word, i) =>
      i === 0 ? word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
      : word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
    ).join('')
  ] || LucideIcons.HelpCircle

  return (
    <div className="flex items-start gap-4 p-6 pb-0">
      <div className={cn(
        "flex h-14 w-14 items-center justify-center rounded-2xl shadow-sm transition-colors",
        device.state.online
          ? "bg-gradient-to-br from-primary/20 to-primary/10 text-primary border-2 border-primary/20"
          : "bg-muted text-muted-foreground border-2 border-muted"
      )}>
        <IconComponent className="h-7 w-7" />
      </div>
      <div className="flex-1 min-w-0 pt-1">
        <div className="flex items-center gap-2 mb-1">
          <h3 className="font-bold text-lg truncate">{device.info.name}</h3>
          <div className={cn(
            "h-2.5 w-2.5 rounded-full ring-2 ring-background shadow-sm transition-colors",
            device.state.online
              ? "bg-green-500 ring-green-500/20 shadow-green-500/50"
              : "bg-red-500 ring-red-500/20"
          )}
          aria-label={device.state.online ? "Online" : "Offline"}
          title={device.state.online ? "Online" : "Offline"}
          />
        </div>
        <p className="text-sm text-muted-foreground truncate font-medium">
          {device.info.manufacturer} {device.info.model}
        </p>
      </div>
    </div>
  )
}
