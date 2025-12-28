import { apiClient } from '../../lib/api/client'
import type { StationListResponse, GuardModeRequest, GuardModeResponse } from './types'

export const stationsApi = {
  getStations: async (): Promise<StationListResponse> => {
    const response = await apiClient.get<StationListResponse>('/api/v1/stations')
    return response.data
  },

  setGuardMode: async (serial: string, mode: number): Promise<GuardModeResponse> => {
    const response = await apiClient.post<GuardModeResponse>(
      `/api/v1/stations/${serial}/guard-mode`,
      { mode } as GuardModeRequest
    )
    return response.data
  },
}
