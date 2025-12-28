import { useQuery } from '@tanstack/react-query'
import { stationsApi } from '../api'

export function useStations() {
  return useQuery({
    queryKey: ['stations'],
    queryFn: stationsApi.getStations,
    refetchInterval: 10000, // Refetch every 10 seconds
  })
}
