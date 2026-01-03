import React, { useState, useEffect, useCallback } from 'react'
import type { Device } from '@/lib/types/api'
import { devicesApi } from '@/lib/api/devices'
import { VideoPlayer } from './VideoPlayer'
import { Play, Square, Camera } from 'lucide-react'

interface CameraControlsProps {
  device: Device
  onCommand?: (command: string, success: boolean) => void
  disabled?: boolean
}

export const CameraControls: React.FC<CameraControlsProps> = ({
  device,
  onCommand,
  disabled = false,
}) => {
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamUrl, setStreamUrl] = useState<string | null>(null)
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null)
  const [snapshotAvailable, setSnapshotAvailable] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Generate snapshot URL with cache-busting timestamp
  const refreshSnapshotUrl = useCallback(() => {
    // Only set snapshot URL if it's available (don't show broken images)
    // For now, snapshots are not implemented so we don't set it
    // setSnapshotUrl(`/api/v1/devices/${device.info.id}/snapshot?t=${Date.now()}`)
    setSnapshotAvailable(false)
  }, [device.info.id])

  // Refresh snapshot every 10 seconds
  useEffect(() => {
    refreshSnapshotUrl()
    const interval = setInterval(refreshSnapshotUrl, 10000)
    return () => clearInterval(interval)
  }, [refreshSnapshotUrl])

  // Cleanup stream on unmount
  useEffect(() => {
    return () => {
      if (isStreaming) {
        devicesApi.stopVideoStream(device.info.id).catch(console.error)
      }
    }
  }, [isStreaming, device.info.id])

  const startStream = async () => {
    setLoading(true)
    setError(null)

    try {
      const result = await devicesApi.startVideoStream(device.info.id)

      if (result.success && result.data?.stream_url) {
        setStreamUrl(result.data.stream_url)
        setIsStreaming(true)
        onCommand?.('start_stream', true)
      } else {
        throw new Error('No stream URL returned')
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to start stream'
      setError(errorMsg)
      onCommand?.('start_stream', false)
      console.error('Failed to start stream:', err)
    } finally {
      setLoading(false)
    }
  }

  const stopStream = async () => {
    setLoading(true)
    setError(null)

    try {
      const result = await devicesApi.stopVideoStream(device.info.id)

      if (result.success) {
        setStreamUrl(null)
        setIsStreaming(false)
        refreshSnapshotUrl()
        onCommand?.('stop_stream', true)
      } else {
        throw new Error('Failed to stop stream')
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to stop stream'
      setError(errorMsg)
      onCommand?.('stop_stream', false)
      console.error('Failed to stop stream:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleVideoError = (videoError: Error) => {
    setError(`Video playback error: ${videoError.message}`)
    setIsStreaming(false)
    setStreamUrl(null)
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {isStreaming && streamUrl ? (
        <div className="space-y-2">
          <VideoPlayer streamUrl={streamUrl} onError={handleVideoError} />
          <button
            onClick={stopStream}
            disabled={loading || disabled}
            className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
          >
            <Square className="w-5 h-5" />
            {loading ? 'Stopping...' : 'Stop Stream'}
          </button>
        </div>
      ) : (
        <div className="relative group">
          {snapshotAvailable && snapshotUrl ? (
            <img
              src={snapshotUrl}
              alt={`${device.info.name} snapshot`}
              className="w-full aspect-video object-cover rounded-lg bg-gray-900"
              onError={(e) => {
                // Hide broken image icon
                e.currentTarget.style.display = 'none'
                setSnapshotAvailable(false)
              }}
            />
          ) : (
            <div className="w-full aspect-video bg-gray-900 rounded-lg flex items-center justify-center">
              <Camera className="w-16 h-16 text-gray-600" />
            </div>
          )}
          <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-opacity">
            <button
              onClick={startStream}
              disabled={loading || disabled}
              className="opacity-0 group-hover:opacity-100 transition-opacity px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg flex items-center gap-2"
            >
              <Play className="w-6 h-6" />
              {loading ? 'Starting...' : 'Watch Live'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
