# Frontend Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Browser (React App)                    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │              App Component                      │    │
│  │         (QueryClientProvider)                   │    │
│  │                                                  │    │
│  │  ┌──────────────┐    ┌─────────────────────┐  │    │
│  │  │ DeviceList   │    │    EventLog          │  │    │
│  │  │              │    │                      │  │    │
│  │  │ ┌──────────┐│    │ useDeviceEvents()   │  │    │
│  │  │ │DeviceCard││    │      ↓               │  │    │
│  │  │ │DeviceCard││    │ EventSource (SSE)   │  │    │
│  │  │ │DeviceCard││    │      ↓               │  │    │
│  │  │ └──────────┘│    │ Event Display       │  │    │
│  │  │              │    │                      │  │    │
│  │  └──────────────┘    └─────────────────────┘  │    │
│  │         ↓                      ↑               │    │
│  │    API Client              SSE Stream          │    │
│  └────────┼──────────────────────┼────────────────┘    │
└───────────┼──────────────────────┼─────────────────────┘
            │                      │
            │ HTTP REST            │ Server-Sent Events
            │ (axios)              │ (EventSource)
            ↓                      ↑
┌─────────────────────────────────────────────────────────┐
│              Vite Dev Server (Port 5173)                 │
│                                                          │
│  Proxy: /api/* → http://localhost:8000/api/*           │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────┐
│           FastAPI Server (Port 8000)                     │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐ │
│  │   Devices   │  │   Plugins   │  │    Events      │ │
│  │   Router    │  │   Router    │  │    Router      │ │
│  │             │  │             │  │                │ │
│  │ GET /devices│  │ GET /plugins│  │ GET /events/   │ │
│  │ POST /cmd   │  │ POST /disc. │  │     stream     │ │
│  └─────────────┘  └─────────────┘  └────────────────┘ │
│         ↓                ↓                  ↑          │
│  ┌─────────────────────────────────────────────────┐  │
│  │          Plugin Manager + Event Bus             │  │
│  └─────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────┐
│              RabbitMQ Message Broker                     │
│                                                          │
│  Topics:                                                │
│  • device.state.{id}                                   │
│  • device.discovery.{id}                               │
│  • device.available.{id}                               │
│  • system.*                                            │
└─────────────────────────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────┐
│                  Device Plugins                          │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ TP-Link  │  │   Eufy   │  │  Custom  │            │
│  │  Plugin  │  │  Plugin  │  │  Plugin  │            │
│  └──────────┘  └──────────┘  └──────────┘            │
│       ↓              ↓              ↓                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  Lights  │  │  Cameras │  │ Sensors  │            │
│  │  Plugs   │  │  Sensors │  │  Locks   │            │
│  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Device List Load

```
User opens app
    ↓
DeviceList component mounts
    ↓
useEffect() triggers
    ↓
api.listDevices()
    ↓
axios.get('/api/v1/devices')
    ↓
Vite proxy → http://localhost:8000/api/v1/devices
    ↓
FastAPI devices router
    ↓
Plugin Manager queries all device plugins
    ↓
Returns devices array
    ↓
React state updates
    ↓
DeviceCard components render
```

### 2. Device Command Execution

```
User clicks "Turn On" button
    ↓
DeviceCard.togglePower()
    ↓
api.executeCommand(deviceId, { command: 'turn_on' })
    ↓
POST /api/v1/devices/{id}/command
    ↓
FastAPI devices router
    ↓
Plugin Manager routes to correct plugin
    ↓
Plugin executes command on physical device
    ↓
Plugin publishes state change to RabbitMQ
    ↓
API returns new state
    ↓
DeviceCard updates local state
    ↓
Button and UI reflect new state
```

### 3. Real-time Updates (SSE)

```
DeviceList component mounts
    ↓
useDeviceEvents() hook initializes
    ↓
new EventSource('/api/v1/events/stream')
    ↓
FastAPI events router
    ↓
Subscribe to RabbitMQ topics (device.*, system.*)
    ↓
Create asyncio.Queue for event buffering
    ↓
SSE connection established
    ↓
[Meanwhile, device state changes...]
    ↓
Plugin publishes to RabbitMQ: device.state.{id}
    ↓
Event router receives message
    ↓
Filters by device_id/event_type (if specified)
    ↓
Formats as SSE event
    ↓
Sends to EventSource connection
    ↓
Browser receives event
    ↓
useDeviceEvents processes event
    ↓
Calls onEvent callback
    ↓
DeviceList updates device in state
    ↓
UI updates automatically (React re-render)
```

## Component Hierarchy

```
App
├── QueryClientProvider (TanStack Query)
│   └── div.min-h-screen
│       ├── header
│       │   └── div.container
│       │       ├── div.logo (Home icon)
│       │       └── div.title
│       │           ├── h1 "ManeYantra"
│       │           └── p "Home Automation Dashboard"
│       ├── main
│       │   └── div.container
│       │       ├── DeviceList
│       │       │   ├── div.header-card
│       │       │   │   ├── div.title
│       │       │   │   │   ├── h2 "Devices"
│       │       │   │   │   └── p "{count} devices • {status}"
│       │       │   │   └── button.refresh
│       │       │   ├── div.filters
│       │       │   │   ├── Filter icon
│       │       │   │   ├── select (type)
│       │       │   │   ├── select (room)
│       │       │   │   ├── select (online)
│       │       │   │   └── button "Clear filters"
│       │       │   └── div.grid
│       │       │       └── DeviceCard[] (for each device)
│       │       │           ├── div.header
│       │       │           │   ├── div.icon
│       │       │           │   ├── div.info
│       │       │           │   │   ├── h3 {device.name}
│       │       │           │   │   └── p {device.room}
│       │       │           │   └── div.status
│       │       │           │       ├── Loader (if loading)
│       │       │           │       └── div.dot (online/offline)
│       │       │           ├── div.controls
│       │       │           │   ├── button "Turn On/Off"
│       │       │           │   └── input[range] (brightness)
│       │       │           └── div.device-info
│       │       │               └── div.grid (brand, model, etc.)
│       │       └── EventLog
│       │           ├── div.header
│       │           │   ├── Activity icon + "Live Events"
│       │           │   ├── button (clear)
│       │           │   └── button (connect/disconnect)
│       │           └── div.events-list
│       │               └── div.event[] (for each event)
│       │                   ├── div.event-type
│       │                   ├── div.timestamp
│       │                   └── pre.event-data
│       └── footer
│           └── p "ManeYantra v0.1.0 • ..."
```

## State Management

### Component State (useState)

**DeviceList:**
- `devices: Device[]` - List of all devices
- `loading: boolean` - Loading indicator
- `filter: FilterOptions` - Current filter settings

**DeviceCard:**
- `loading: boolean` - Command execution state
- `localState: DeviceState` - Local copy of device state

**EventLog:**
- None (uses hook)

### Custom Hook State (useDeviceEvents)

- `events: SSEEvent[]` - Last 100 events
- `connected: boolean` - SSE connection status
- `error: string | null` - Connection error
- `eventSourceRef` - EventSource instance

### Server State (TanStack Query)

Currently minimal - could be expanded for:
- Device list caching
- Plugin list caching
- Optimistic updates
- Background refetching

## Type System

### Core Types (src/types/api.ts)

```typescript
// Enums
DeviceType = "light" | "plug" | "camera" | ...
DeviceCapability = "on_off" | "brightness" | ...
SSEEventType = "state" | "discovery" | ...

// Device Models
DeviceInfo { id, name, type, capabilities, ... }
DeviceState { online, on?, brightness?, ... }
Device { info: DeviceInfo, state: DeviceState }

// API Requests/Responses
DeviceListResponse { devices: Device[], total: number }
DeviceCommand { command: string, params?: ... }
CommandResult { success: boolean, state?: ... }

// SSE Events
SSEEvent { type, timestamp, device_id?, data? }
```

All types are derived from the TypeSpec specification in `api-spec/main.tsp`.

## API Client (src/lib/api.ts)

Singleton instance with methods:

```typescript
class ManeYantraAPI {
  // Health
  health(): Promise<HealthResponse>

  // Devices
  listDevices(params?): Promise<DeviceListResponse>
  getDevice(id): Promise<Device>
  executeCommand(id, cmd): Promise<CommandResult>
  getDeviceState(id): Promise<DeviceState>
  refreshDeviceState(id): Promise<DeviceState>

  // Plugins
  listPlugins(): Promise<PluginListResponse>
  getPlugin(id): Promise<PluginInfo>
  discoverDevices(id): Promise<{...}>

  // SSE URLs
  getEventStreamURL(params?): string
  getDeviceEventStreamURL(id): string
}

export const api = new ManeYantraAPI();
```

## Styling System

### Tailwind CSS Classes

**Colors:**
- Primary: `blue-600`, `blue-700`
- Success: `green-500`
- Error: `red-500`
- Gray scale: `gray-50` to `gray-900`

**Spacing:**
- Container: `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`
- Gaps: `gap-2`, `gap-3`, `gap-4`, `gap-6`
- Padding: `p-2`, `p-3`, `p-4`

**Dark Mode:**
- All components support dark mode via `dark:` prefix
- Automatically uses system preference

**Responsive:**
- Mobile-first approach
- Breakpoints: `sm:`, `md:`, `lg:`, `xl:`
- Grid: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`

## Performance Considerations

### Optimizations

1. **Event Buffering**
   - useDeviceEvents keeps only last 100 events
   - Prevents memory leaks from long-running sessions

2. **SSE Auto-reconnect**
   - 5-second delay before reconnect
   - Prevents rapid reconnection loops

3. **Component Memoization**
   - DeviceCard could use React.memo
   - Consider useMemo for expensive filters

4. **Virtual Scrolling**
   - EventLog could use react-window for many events
   - DeviceList could virtualize with large device counts

5. **Code Splitting**
   - Could lazy-load routes with React.lazy
   - Currently single bundle (small enough)

### Bundle Size

Current production build is small:
- React 19: ~6 KB (gzipped)
- Tailwind CSS: ~10 KB (purged)
- Dependencies: ~50 KB total
- **Total: ~70 KB gzipped**

## Security Considerations

### Current State (Development)

- No authentication
- CORS allows all origins
- No rate limiting
- No input sanitization

### Production Recommendations

1. **Authentication**
   - JWT tokens
   - Secure cookie storage
   - Token refresh

2. **CORS**
   - Restrict to specific origins
   - Remove wildcard (`*`)

3. **Input Validation**
   - Validate all user inputs
   - Sanitize command parameters
   - Type checking with Zod

4. **Rate Limiting**
   - Limit API requests per user
   - Prevent SSE connection spam

5. **HTTPS**
   - Use TLS in production
   - Secure WebSocket/SSE connections

## Testing Strategy

### Unit Tests (Not Yet Implemented)

- Test custom hooks with @testing-library/react-hooks
- Test components with @testing-library/react
- Test API client with mock axios

### Integration Tests

- Test SSE connection with mock EventSource
- Test device command flow end-to-end

### E2E Tests

- Cypress or Playwright
- Test full user flows
- Test real-time updates

## Build & Deployment

### Development

```bash
npm run dev
# Vite dev server with HMR
# Port 5173
# Proxy to API
```

### Production Build

```bash
npm run build
# TypeScript check
# Vite build
# Output: dist/
```

### Preview Production

```bash
npm run preview
# Test production build locally
```

### Deploy

Static hosting (Netlify, Vercel, etc.):
- Build: `npm run build`
- Publish: `dist/`
- Redirect `/api/*` to API server
- Set `VITE_API_URL` environment variable

## Future Architecture Considerations

### Potential Improvements

1. **State Management Library**
   - Zustand or Jotai for global state
   - Would simplify prop drilling

2. **Router**
   - React Router for multi-page app
   - Routes: /devices, /automations, /settings

3. **GraphQL**
   - Replace REST with GraphQL
   - Better real-time with subscriptions

4. **Progressive Web App (PWA)**
   - Service worker for offline support
   - Install as native app
   - Push notifications

5. **Micro-frontends**
   - Split plugins into separate apps
   - Independent deployment
   - Module federation

6. **WebSockets**
   - Bidirectional communication
   - More efficient than SSE for high-frequency updates

---

This architecture provides a solid foundation for a modern, real-time home automation dashboard while remaining simple and maintainable.
