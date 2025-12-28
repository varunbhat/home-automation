import { Power } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { cn } from '@/shared/utils/cn'

interface PowerControlProps {
  on: boolean
  onToggle: () => void
  disabled?: boolean
}

export function PowerControl({ on, onToggle, disabled }: PowerControlProps) {
  return (
    <Button
      onClick={onToggle}
      disabled={disabled}
      variant={on ? 'default' : 'outline'}
      size="lg"
      className={cn(
        'w-full font-semibold gap-2.5 h-12 transition-all',
        on && 'bg-primary text-primary-foreground shadow-lg shadow-primary/30'
      )}
      aria-label={`Turn ${on ? 'off' : 'on'}`}
      aria-pressed={on}
    >
      <Power className="h-5 w-5" />
      <span className="text-base">{on ? 'On' : 'Off'}</span>
    </Button>
  )
}
