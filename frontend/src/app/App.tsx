import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/lib/query-client'
import { Toaster } from '@/shared/components/ui/toast'
import { ErrorBoundary } from '@/shared/components/ErrorBoundary'
import { useDevices } from '@/features/devices/hooks/useDevices'
import { useEventStream } from '@/features/events/hooks/useEventStream'
import { useStations } from '@/features/stations/hooks/useStations'
import { DeviceCard } from '@/features/devices/components/DeviceCard/DeviceCard'
import { GuardModeControl } from '@/features/stations/components/GuardModeControl'
import { Skeleton } from '@/shared/components/ui/skeleton'
import { Card, CardContent, CardHeader } from '@/shared/components/ui/card'
import { AlertCircle, Wifi, WifiOff } from 'lucide-react'
import '@/features/stations/styles.css'

function DeviceGrid() {
  const { data, isLoading, error } = useDevices()
  const { data: stationsData } = useStations()
  const { state: sseState, isConnected } = useEventStream()

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
        {[...Array(6)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="space-y-2">
              <Skeleton className="h-10 w-10 rounded-full" />
              <Skeleton className="h-4 w-32" />
            </CardHeader>
            <CardContent className="space-y-3">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-6 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="flex flex-row items-center gap-3">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <div>
              <h2 className="text-lg font-semibold">Error Loading Devices</h2>
              <p className="text-sm text-muted-foreground">
                {error instanceof Error ? error.message : 'Failed to load devices'}
              </p>
            </div>
          </CardHeader>
        </Card>
      </div>
    )
  }

  if (!data || data.devices.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-md text-center">
          <CardContent className="pt-6">
            <p className="text-lg font-semibold">No Devices Found</p>
            <p className="text-sm text-muted-foreground mt-2">
              Connect your smart home devices to get started
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-10">
        <div className="container mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">ManeYantra</h1>
              <p className="text-sm text-muted-foreground mt-1">
                {data.total} device{data.total !== 1 ? 's' : ''} connected
              </p>
            </div>
            <div className="flex items-center gap-3">
              {isConnected ? (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 text-green-700 dark:text-green-400 border border-green-500/20">
                  <Wifi className="h-4 w-4" />
                  <span className="text-sm font-medium">Live</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted text-muted-foreground border">
                  <WifiOff className="h-4 w-4" />
                  <span className="text-sm font-medium">
                    {sseState === 'reconnecting' ? 'Reconnecting...' : 'Offline'}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Device Grid */}
      <main className="container mx-auto px-6 py-8">
        {/* Guard Mode Controls */}
        {stationsData && stationsData.stations.length > 0 && (
          <div className="mb-8">
            {stationsData.stations.map((station) => (
              <GuardModeControl key={station.serial} station={station} />
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6" data-testid="device-grid">
          {data.devices.map((device) => (
            <DeviceCard key={device.info.id} device={device} />
          ))}
        </div>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <DeviceGrid />
        <Toaster />
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
