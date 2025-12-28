import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { stationsApi } from '../api'
import { GUARD_MODES, GUARD_MODE_LABELS, GUARD_MODE_ICONS } from '../types'
import type { Station } from '../types'

interface GuardModeControlProps {
  station: Station
}

export function GuardModeControl({ station }: GuardModeControlProps) {
  const [isChanging, setIsChanging] = useState(false)
  const queryClient = useQueryClient()

  const setGuardModeMutation = useMutation({
    mutationFn: ({ serial, mode }: { serial: string; mode: number }) =>
      stationsApi.setGuardMode(serial, mode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stations'] })
      queryClient.invalidateQueries({ queryKey: ['devices'] })
    },
  })

  const handleModeChange = async (mode: number) => {
    if (mode === station.guard_mode) return

    setIsChanging(true)
    try {
      await setGuardModeMutation.mutateAsync({
        serial: station.serial,
        mode,
      })
    } finally {
      setIsChanging(false)
    }
  }

  const modes = [
    { value: GUARD_MODES.DISARMED, label: GUARD_MODE_LABELS[0], icon: GUARD_MODE_ICONS[0] },
    { value: GUARD_MODES.HOME, label: GUARD_MODE_LABELS[1], icon: GUARD_MODE_ICONS[1] },
    { value: GUARD_MODES.AWAY, label: GUARD_MODE_LABELS[2], icon: GUARD_MODE_ICONS[2] },
  ]

  return (
    <div className="guard-mode-control">
      <div className="guard-mode-header">
        <h3>{station.name}</h3>
        <span className="station-model">{station.model}</span>
      </div>

      <div className="guard-mode-buttons">
        {modes.map((mode) => (
          <button
            key={mode.value}
            onClick={() => handleModeChange(mode.value)}
            disabled={isChanging || station.guard_mode === mode.value}
            className={`mode-button ${station.guard_mode === mode.value ? 'active' : ''} ${
              isChanging ? 'changing' : ''
            }`}
          >
            <span className="mode-icon">{mode.icon}</span>
            <span className="mode-label">{mode.label}</span>
          </button>
        ))}
      </div>

      {setGuardModeMutation.isError && (
        <div className="error-message">
          Failed to change guard mode. Please try again.
        </div>
      )}
    </div>
  )
}
