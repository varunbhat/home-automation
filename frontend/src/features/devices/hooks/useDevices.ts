import { useQuery } from '@tanstack/react-query'
import { devicesApi, type ListDevicesParams } from '@/lib/api/devices'
import type { DeviceListResponse } from '@/lib/types'

export function useDevices(params?: ListDevicesParams) {
  return useQuery<DeviceListResponse>({
    queryKey: ['devices', params],
    queryFn: () => devicesApi.list(params),
  })
}

export default useDevices
