import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { devicesApi } from '@/lib/api/devices'
import type { Device, DeviceCommand, CommandResult, DeviceState } from '@/lib/types'

// Apply optimistic update based on command
function applyOptimisticUpdate(
  state: DeviceState,
  command: string,
  params?: Record<string, unknown>
): DeviceState {
  const newState = { ...state }

  switch (command) {
    case 'turn_on':
      newState.on = true
      break
    case 'turn_off':
      newState.on = false
      break
    case 'toggle':
      newState.on = !state.on
      break
    case 'set_brightness':
      if (params?.brightness !== undefined) {
        newState.brightness = params.brightness as number
      }
      break
    case 'set_color_temperature':
      if (params?.temperature !== undefined) {
        newState.color_temperature = params.temperature as number
      }
      break
    case 'set_hsv':
      if (params?.hue !== undefined && params?.saturation !== undefined && params?.value !== undefined) {
        newState.color = {
          hue: params.hue as number,
          saturation: params.saturation as number,
          value: params.value as number,
        }
      }
      break
  }

  return newState
}

export function useDeviceCommand(deviceId: string) {
  const queryClient = useQueryClient()

  return useMutation<CommandResult, Error, DeviceCommand>({
    mutationFn: (command: DeviceCommand) => devicesApi.executeCommand(deviceId, command),

    // Optimistic update
    onMutate: async (command: DeviceCommand) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['devices', deviceId] })

      // Snapshot previous value
      const previous = queryClient.getQueryData<Device>(['devices', deviceId])

      // Optimistically update
      if (previous) {
        const optimisticState = applyOptimisticUpdate(
          previous.state,
          command.command,
          command.params
        )

        queryClient.setQueryData<Device>(['devices', deviceId], {
          ...previous,
          state: optimisticState,
        })
      }

      return { previous }
    },

    // Rollback on error
    onError: (error, variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['devices', deviceId], context.previous)
      }

      toast.error('Command failed', {
        description: error.message,
      })
    },

    // Reconcile with server state
    onSuccess: (data) => {
      // Server returns updated state
      queryClient.setQueryData<Device>(['devices', deviceId], (old) => {
        if (!old) return old
        return {
          ...old,
          state: data.state ?? old.state,
        }
      })

      // Also update in device list
      queryClient.setQueryData<{ devices: Device[]; total: number }>(['devices'], (old) => {
        if (!old) return old
        return {
          ...old,
          devices: old.devices.map((device) =>
            device.info.id === deviceId
              ? { ...device, state: data.state ?? device.state }
              : device
          ),
        }
      })

      toast.success('Command executed', {
        description: data.message || 'Device updated successfully',
      })
    },
  })
}

export default useDeviceCommand
