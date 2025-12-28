import { useState } from 'react'
import { Palette } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/shared/components/ui/dialog'
import { Slider } from '@/shared/components/ui/slider'
import { Label } from '@/shared/components/ui/label'
import type { ColorValue } from '@/lib/types'
import { hsvToHsl } from '@/shared/utils/formatters'

interface ColorControlProps {
  color?: ColorValue
  onChange: (color: ColorValue) => void
  disabled?: boolean
}

export function ColorControl({ color, onChange, disabled }: ColorControlProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [hue, setHue] = useState(color?.hue ?? 0)
  const [saturation, setSaturation] = useState(color?.saturation ?? 100)
  const [value, setValue] = useState(color?.value ?? 100)

  const handleApply = () => {
    onChange({ hue, saturation, value })
    setIsOpen(false)
  }

  const colorStyle = color
    ? { backgroundColor: hsvToHsl(color.hue, color.saturation, color.value) }
    : undefined

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          className="w-full justify-start"
          disabled={disabled}
        >
          <Palette className="h-4 w-4 mr-2" />
          <span>Color</span>
          {color && (
            <div
              className="ml-auto h-6 w-6 rounded-full border-2 border-border"
              style={colorStyle}
              aria-label={`Current color: Hue ${color.hue}, Saturation ${color.saturation}%, Value ${color.value}%`}
            />
          )}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Select Color</DialogTitle>
        </DialogHeader>
        <div className="space-y-6">
          {/* Color Preview */}
          <div
            className="h-24 w-full rounded-lg border-2 border-border"
            style={{ backgroundColor: hsvToHsl(hue, saturation, value) }}
          />

          {/* Hue Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Hue</Label>
              <span className="text-sm text-muted-foreground">{hue}°</span>
            </div>
            <Slider
              value={[hue]}
              onValueChange={(v) => setHue(v[0])}
              max={360}
              step={1}
              className="w-full"
            />
          </div>

          {/* Saturation Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Saturation</Label>
              <span className="text-sm text-muted-foreground">{saturation}%</span>
            </div>
            <Slider
              value={[saturation]}
              onValueChange={(v) => setSaturation(v[0])}
              max={100}
              step={1}
              className="w-full"
            />
          </div>

          {/* Brightness/Value Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Brightness</Label>
              <span className="text-sm text-muted-foreground">{value}%</span>
            </div>
            <Slider
              value={[value]}
              onValueChange={(v) => setValue(v[0])}
              max={100}
              step={1}
              className="w-full"
            />
          </div>

          <Button onClick={handleApply} className="w-full">
            Apply Color
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
