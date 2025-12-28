import { useState, useEffect } from 'react'
import { Sun } from 'lucide-react'
import { Slider } from '@/shared/components/ui/slider'
import { Label } from '@/shared/components/ui/label'
import { useDebounce } from '@/shared/hooks/useDebounce'

interface BrightnessControlProps {
  value: number
  onChange: (value: number) => void
  disabled?: boolean
}

export function BrightnessControl({ value, onChange, disabled }: BrightnessControlProps) {
  const [localValue, setLocalValue] = useState(value)
  const debouncedValue = useDebounce(localValue, 300)

  // Update local value when prop changes (from SSE or API)
  useEffect(() => {
    setLocalValue(value)
  }, [value])

  // Call onChange when debounced value changes
  useEffect(() => {
    if (debouncedValue !== value) {
      onChange(debouncedValue)
    }
  }, [debouncedValue, onChange, value])

  const handleChange = (newValue: number[]) => {
    setLocalValue(newValue[0])
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label className="flex items-center gap-2 font-semibold text-sm">
          <div className="p-1.5 rounded-lg bg-amber-500/10">
            <Sun className="h-4 w-4 text-amber-600 dark:text-amber-500" />
          </div>
          <span>Brightness</span>
        </Label>
        <span className="text-sm font-bold text-foreground bg-muted px-2.5 py-1 rounded-md">
          {localValue}%
        </span>
      </div>
      <Slider
        value={[localValue]}
        onValueChange={handleChange}
        max={100}
        step={1}
        disabled={disabled}
        className="w-full"
        aria-label="Brightness"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={localValue}
        aria-valuetext={`${localValue} percent`}
      />
    </div>
  )
}
