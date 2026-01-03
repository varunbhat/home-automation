import React, { useEffect, useRef, useState } from 'react'

interface VideoPlayerProps {
  streamUrl: string
  onError?: (error: Error) => void
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({ streamUrl, onError }) => {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const hlsRef = useRef<any>(null)

  useEffect(() => {
    const video = videoRef.current
    if (!video || !streamUrl) return

    setLoading(true)
    setError(null)

    // Check if HLS stream
    const isHLS = streamUrl.includes('.m3u8')

    if (isHLS) {
      // Check if browser supports native HLS (Safari)
      if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = streamUrl
        video.addEventListener('loadeddata', () => setLoading(false))
        video.play().catch((err) => {
          const errorMsg = `Playback failed: ${err.message}`
          setError(errorMsg)
          onError?.(new Error(errorMsg))
        })
      } else {
        // Use HLS.js for other browsers
        import('hls.js')
          .then(({ default: Hls }) => {
            if (Hls.isSupported()) {
              const hls = new Hls({
                enableWorker: true,
                lowLatencyMode: true,
              })

              hlsRef.current = hls

              hls.loadSource(streamUrl)
              hls.attachMedia(video)

              hls.on(Hls.Events.MANIFEST_PARSED, () => {
                setLoading(false)
                video.play().catch((err) => {
                  const errorMsg = `Playback failed: ${err.message}`
                  setError(errorMsg)
                  onError?.(new Error(errorMsg))
                })
              })

              hls.on(Hls.Events.ERROR, (event, data) => {
                if (data.fatal) {
                  const errorMsg = `HLS error: ${data.type} - ${data.details}`
                  setError(errorMsg)
                  onError?.(new Error(errorMsg))

                  switch (data.type) {
                    case Hls.ErrorTypes.NETWORK_ERROR:
                      hls.startLoad()
                      break
                    case Hls.ErrorTypes.MEDIA_ERROR:
                      hls.recoverMediaError()
                      break
                    default:
                      hls.destroy()
                      break
                  }
                }
              })
            } else {
              const errorMsg = 'HLS not supported in this browser'
              setError(errorMsg)
              onError?.(new Error(errorMsg))
            }
          })
          .catch((err) => {
            const errorMsg = `Failed to load HLS.js: ${err.message}`
            setError(errorMsg)
            onError?.(new Error(errorMsg))
          })
      }
    } else {
      // Direct stream (RTSP will be converted by browser or backend)
      video.src = streamUrl
      video.addEventListener('loadeddata', () => setLoading(false))
      video.play().catch((err) => {
        const errorMsg = `Playback failed: ${err.message}`
        setError(errorMsg)
        onError?.(new Error(errorMsg))
      })
    }

    // Cleanup
    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }
      if (video) {
        video.pause()
        video.src = ''
      }
    }
  }, [streamUrl, onError])

  return (
    <div className="relative w-full aspect-video bg-gray-900 rounded-lg overflow-hidden">
      <video
        ref={videoRef}
        className="w-full h-full object-contain"
        controls
        playsInline
        muted
        autoPlay
      />

      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-75">
          <div className="flex flex-col items-center gap-2">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-white text-sm">Loading stream...</p>
          </div>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-90">
          <div className="text-center p-4">
            <p className="text-red-400 mb-2">{error}</p>
            <button
              onClick={() => {
                setError(null)
                setLoading(true)
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
            >
              Retry
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
