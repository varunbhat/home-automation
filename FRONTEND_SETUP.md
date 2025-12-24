# ManeYantra React Frontend - Setup Complete ✅

A modern React + TypeScript frontend has been created for ManeYantra with real-time device control and monitoring.

## 📁 What Was Created

```
maneyantra/
├── frontend/                          # New React application
│   ├── src/
│   │   ├── components/
│   │   │   ├── DeviceCard.tsx        # Individual device control card
│   │   │   ├── DeviceList.tsx        # Device grid with filtering
│   │   │   └── EventLog.tsx          # Live event viewer
│   │   ├── hooks/
│   │   │   └── useDeviceEvents.ts    # SSE hook for real-time updates
│   │   ├── lib/
│   │   │   └── api.ts                # TypeScript API client
│   │   ├── types/
│   │   │   └── api.ts                # Type definitions from TypeSpec
│   │   ├── App.tsx                   # Main app component
│   │   ├── main.tsx                  # Entry point
│   │   └── index.css                 # Tailwind CSS
│   ├── .env                          # Environment configuration
│   ├── .env.example                  # Environment template
│   ├── package.json                  # Dependencies
│   ├── vite.config.ts                # Vite configuration with proxy
│   ├── tailwind.config.js            # Tailwind CSS config
│   ├── postcss.config.js             # PostCSS config
│   ├── start.sh                      # Quick start script
│   └── README.md                     # Frontend documentation
└── api-spec/                         # Already exists
    └── main.tsp                      # TypeSpec API specification
```

## 🚀 Quick Start

### 1. Start the ManeYantra API (Terminal 1)

```bash
# From project root
cd /Users/varunbhat/workspace/maneyantra

# Make sure Docker is running (for RabbitMQ)
docker-compose up -d

# Start ManeYantra with API
python3 -m maneyantra.main
```

API will be available at http://localhost:8000

### 2. Start the React Frontend (Terminal 2)

```bash
# From project root
cd /Users/varunbhat/workspace/maneyantra/frontend

# Quick start (installs deps if needed)
./start.sh

# Or manually
npm install
npm run dev
```

Frontend will be available at http://localhost:5173

## ✨ Features

### Device Control
- **View all devices** in a responsive grid layout
- **Control power** - Turn devices on/off with a single click
- **Adjust brightness** - Slider control for dimmable lights
- **Real-time status** - See online/offline status instantly
- **Device info** - View manufacturer, model, battery, temperature

### Real-time Updates
- **Server-Sent Events (SSE)** - Live updates from the API
- **Auto-reconnect** - Automatically reconnects if connection is lost
- **Event log** - View all system events in real-time
- **State sync** - Device states update instantly when changed

### Filtering & Search
- Filter by **device type** (light, plug, camera, sensor, etc.)
- Filter by **room** (Living Room, Bedroom, etc.)
- Filter by **status** (Online/Offline)
- Clear all filters with one click

### Modern UI/UX
- **Responsive design** - Works on desktop, tablet, and mobile
- **Dark mode** - Automatically adapts to system preference
- **Tailwind CSS** - Beautiful, consistent styling
- **Loading states** - Visual feedback for all actions
- **Error handling** - Graceful error messages

## 🛠️ Technology Stack

| Technology | Purpose |
|------------|---------|
| **React 19** | UI framework |
| **TypeScript** | Type safety |
| **Vite** | Build tool (fast HMR) |
| **Tailwind CSS** | Styling |
| **TanStack Query** | Data fetching & caching |
| **Axios** | HTTP client |
| **Lucide React** | Icon library |
| **EventSource API** | SSE implementation |

## 📡 API Integration

The frontend connects to the ManeYantra REST API using:

### REST Endpoints
- `GET /api/v1/devices` - List all devices
- `GET /api/v1/devices/{id}` - Get single device
- `POST /api/v1/devices/{id}/command` - Execute command
- `GET /api/v1/devices/{id}/state` - Get device state
- `POST /api/v1/devices/{id}/refresh` - Refresh state

### Real-time Events (SSE)
- `GET /api/v1/events/stream` - All events
- `GET /api/v1/events/devices/{id}/stream` - Device-specific events

Event types:
- `state` - Device state changed
- `discovery` - New device discovered
- `available` - Device online/offline
- `error` - Error occurred
- `heartbeat` - Connection keepalive

## 🎨 Component Architecture

```
App (QueryClientProvider)
├── Header
│   └── Logo + Title
├── Main
│   ├── DeviceList
│   │   ├── Filters (Type, Room, Status)
│   │   └── DeviceCard[] (Grid)
│   │       ├── Icon + Info
│   │       ├── Power Button
│   │       ├── Brightness Slider (if capable)
│   │       └── Device Details
│   └── EventLog
│       ├── Connection Status
│       └── Event Items[]
└── Footer
```

### Custom Hooks

**`useDeviceEvents(options)`** - SSE hook
- Manages EventSource connection
- Auto-reconnect on disconnect
- Event filtering by device_id and type
- Event buffering (keeps last 100)
- Connection status tracking

## 🔧 Configuration

### Environment Variables (.env)

```bash
VITE_API_URL=http://localhost:8000
```

### Vite Proxy (vite.config.ts)

The frontend proxies `/api` requests to the backend:

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
}
```

This allows using relative URLs like `/api/v1/devices` instead of full URLs.

## 📦 Dependencies

```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.90.12",
    "axios": "^1.13.2",
    "lucide-react": "^0.562.0",
    "react": "^19.2.0",
    "react-dom": "^19.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^5.1.1",
    "autoprefixer": "^10.4.23",
    "tailwindcss": "^4.1.18",
    "typescript": "~5.9.3",
    "vite": "^7.2.4"
  }
}
```

## 🧪 Testing the Setup

1. **Start both servers** (API + Frontend)
2. **Open browser** to http://localhost:5173
3. **Verify connection**:
   - Event log should show "Connected - Receiving live updates"
   - Devices should load in the grid
4. **Test device control**:
   - Click a device's power button
   - Watch state change in real-time
   - Check event log for state update event
5. **Test filtering**:
   - Select a device type filter
   - Select a room filter
   - Toggle online/offline filter

## 🐛 Troubleshooting

### Frontend won't start
```bash
# Clean install
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Can't connect to API
1. Verify API is running: http://localhost:8000/docs
2. Check `.env` file has correct URL
3. Check browser console for errors

### SSE not working
1. Check Event Log shows "Connected"
2. Open DevTools > Network > filter "stream"
3. Verify RabbitMQ is running: `docker ps`
4. Check API logs: `logs/maneyantra.log`

### CORS errors
The API has CORS enabled for all origins in development. If you get CORS errors:
1. Check API is running on port 8000
2. Verify Vite proxy is configured correctly
3. Clear browser cache

## 🎯 Next Steps

### Enhancements to Consider

1. **Authentication**
   - Add login/logout
   - User management
   - Protected routes

2. **More Device Types**
   - Camera video streams
   - Thermostat controls
   - Lock controls
   - Sensor graphs

3. **Automation UI**
   - Create/edit rules
   - Trigger automation
   - Schedule viewer

4. **Scenes**
   - Create device groups
   - One-click scene activation
   - Scene scheduling

5. **Notifications**
   - Browser notifications
   - Toast messages
   - Error alerts

6. **Data Persistence**
   - Device state history
   - Event history
   - Energy usage graphs

7. **Mobile App**
   - React Native version
   - Native push notifications
   - Offline support

## 📚 Documentation

- [Frontend README](frontend/README.md) - Detailed frontend docs
- [API README](API_README.md) - API documentation
- [TypeSpec](api-spec/main.tsp) - API specification
- [Main README](README.md) - Project overview

## 🎉 Summary

You now have a complete, modern web interface for ManeYantra with:

✅ Real-time device monitoring via SSE
✅ Device control (power, brightness)
✅ Filtering and search
✅ Beautiful, responsive UI
✅ Type-safe TypeScript codebase
✅ Fast development with Vite HMR
✅ Production-ready build system

**Enjoy your new ManeYantra dashboard!** 🏠✨
