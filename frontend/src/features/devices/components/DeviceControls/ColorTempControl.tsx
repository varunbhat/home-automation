import { useState, useEffect } from 'react'
import { Thermometer } from 'lucide-react'
import { Slider } from '@/shared/components/ui/slider'
import { Label } from '@/shared/components/ui/label'
import { useDebounce } from '@/shared/hooks/useDebounce'
import { formatColorTemperature, getColorTemperatureLabel } from '@/shared/utils/formatters'

interface ColorTempControlProps {
  value: number
  onChange: (value: number) => void
  disabled?: boolean
  min?: number
  max?: number
}

export function ColorTempControl({
  value,
  onChange,
  disabled,
  min = 2000,
  max = 9000,
}: ColorTempControlProps) {
  const [localValue, setLocalValue] = useState(value)
  const debouncedValue = useDebounce(localValue, 300)

  useEffect(() => {
    setLocalValue(value)
  }, [value])

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
          <div className="p-1.5 rounded-lg bg-orange-500/10">
            <Thermometer className="h-4 w-4 text-orange-600 dark:text-orange-500" />
          </div>
          <span>Color Temperature</span>
        </Label>
        <div className="text-right">
          <div className="text-sm font-bold text-foreground">{formatColorTemperature(localValue)}</div>
          <div className="text-xs text-muted-foreground">({getColorTemperatureLabel(localValue)})</div>
        </div>
      </div>
      <Slider
        value={[localValue]}
        onValueChange={handleChange}
        min={min}
        max={max}
        step={100}
        disabled={disabled}
        className="w-full"
        aria-label="Color Temperature"
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={localValue}
        aria-valuetext={`${localValue} Kelvin`}
      />
    </div>
  )
}
