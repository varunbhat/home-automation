import { useState, useEffect, useCallback, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { SSEConnectionManager } from '@/lib/api/sse'
import type { SSEEvent, ConnectionState, Device } from '@/lib/types'

interface UseEventStreamOptions {
  deviceId?: string
  eventType?: string
  enabled?: boolean
}

export function useEventStream(options: UseEventStreamOptions = {}) {
  const [state, setState] = useState<ConnectionState>('disconnected')
  const [events, setEvents] = useState<SSEEvent[]>([])
  const managerRef = useRef<SSEConnectionManager | null>(null)
  const queryClient = useQueryClient()

  const { enabled = true, deviceId, eventType } = options

  useEffect(() => {
    if (!enabled) return

    const manager = new SSEConnectionManager({
      deviceId,
      eventType,
      onEvent: (event) => {
        // Add to event buffer (circular buffer: keep last 1000)
        setEvents((prev) => {
          const newEvents = [event, ...prev].slice(0, 1000)
          return newEvents
        })

        // Sync state changes with TanStack Query cache
        if (event.type === 'state' && event.data.device_id) {
          // Update specific device
          queryClient.setQueryData<Device>(
            ['devices', event.data.device_id],
            (old) => {
              if (!old) return old
              return {
                ...old,
                state: { ...old.state, ...event.data.data },
              }
            }
          )

          // Update device list
          queryClient.setQueryData<{ devices: Device[]; total: number }>(
            ['devices'],
            (old) => {
              if (!old) return old
              return {
                ...old,
                devices: old.devices.map((device) =>
                  device.info.id === event.data.device_id
                    ? { ...device, state: { ...device.state, ...event.data.data } }
                    : device
                ),
              }
            }
          )
        }

        // Handle discovery events
        if (event.type === 'discovery') {
          // Invalidate device list to refetch
          queryClient.invalidateQueries({ queryKey: ['devices'] })
        }
      },
      onStateChange: setState,
    })

    managerRef.current = manager
    manager.connect()

    return () => {
      manager.disconnect()
    }
  }, [enabled, deviceId, eventType, queryClient])

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  const reconnect = useCallback(() => {
    managerRef.current?.disconnect()
    managerRef.current?.connect()
  }, [])

  return {
    state,
    events,
    clearEvents,
    reconnect,
    isConnected: state === 'connected',
    isReconnecting: state === 'reconnecting',
    isFailed: state === 'failed',
  }
}

export default useEventStream
