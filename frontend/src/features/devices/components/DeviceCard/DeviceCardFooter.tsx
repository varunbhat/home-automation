import { MapPin, Tag } from 'lucide-react'
import type { Device } from '@/lib/types'
import { formatLastSeen } from '@/shared/utils/device-helpers'

interface DeviceCardFooterProps {
  device: Device
}

export function DeviceCardFooter({ device }: DeviceCardFooterProps) {
  const hasFooterContent = device.info.room || device.info.tags?.length || device.state.last_seen

  if (!hasFooterContent) return null

  return (
    <div className="border-t border-dashed pt-4 mt-4 space-y-3">
      {/* Room */}
      {device.info.room && (
        <div className="flex items-center gap-2 text-sm">
          <div className="p-1.5 rounded-lg bg-muted/50">
            <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          <span className="font-medium text-muted-foreground">{device.info.room}</span>
        </div>
      )}

      {/* Tags */}
      {device.info.tags && device.info.tags.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <div className="p-1.5 rounded-lg bg-muted/50">
            <Tag className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          {device.info.tags.map((tag) => (
            <span
              key={tag}
              className="text-xs font-medium bg-primary/10 text-primary px-2.5 py-1 rounded-md border border-primary/20"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Last Seen */}
      {device.state.last_seen && (
        <div className="text-xs text-muted-foreground font-medium">
          Last seen: {formatLastSeen(device.state.last_seen)}
        </div>
      )}
    </div>
  )
}
