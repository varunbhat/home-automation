import { useQuery } from '@tanstack/react-query'
import { devicesApi } from '@/lib/api/devices'
import type { Device } from '@/lib/types'

export function useDevice(deviceId: string, enabled = true) {
  return useQuery<Device>({
    queryKey: ['devices', deviceId],
    queryFn: () => devicesApi.get(deviceId),
    enabled,
  })
}

export default useDevice
