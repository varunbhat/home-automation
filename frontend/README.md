# ManeYantra Frontend

Modern React dashboard for ManeYantra home automation system.

## Features

- ✅ **Real-time Updates** - Live device state changes via Server-Sent Events (SSE)
- ✅ **Device Control** - Turn devices on/off, adjust brightness, and more
- ✅ **TypeScript** - Full type safety with auto-generated types from TypeSpec API
- ✅ **Modern UI** - Beautiful, responsive design with Tailwind CSS
- ✅ **Dark Mode** - Support for light and dark themes
- ✅ **Filtering** - Filter devices by type, room, and online status
- ✅ **Event Log** - View live events from all devices

## Tech Stack

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Fast build tool
- **Tailwind CSS** - Styling
- **TanStack Query** - Data fetching and caching
- **Axios** - HTTP client
- **Lucide React** - Icon library

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- ManeYantra API server running (default: http://localhost:8000)

### Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Start development server
npm run dev
```

The app will be available at http://localhost:5173

### Build for Production

```bash
npm run build
npm run preview
```

## Configuration

Edit `.env` to configure the API URL:

```bash
VITE_API_URL=http://localhost:8000
```

## Project Structure

```
frontend/
├── src/
│   ├── components/       # React components
│   │   ├── DeviceCard.tsx    # Individual device card
│   │   ├── DeviceList.tsx    # Device grid with filters
│   │   └── EventLog.tsx      # Real-time event viewer
│   ├── hooks/            # Custom React hooks
│   │   └── useDeviceEvents.ts # SSE hook for real-time updates
│   ├── lib/              # Utilities
│   │   └── api.ts            # API client
│   ├── types/            # TypeScript types
│   │   └── api.ts            # API types from TypeSpec
│   ├── App.tsx           # Main app component
│   ├── main.tsx          # Entry point
│   └── index.css         # Global styles
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Features in Detail

### Device Control

- View all devices in a responsive grid
- Control device power state (on/off)
- Adjust brightness for lights
- See device status (online/offline)
- View device information (manufacturer, model, battery, temperature, etc.)

### Real-time Updates

The app uses Server-Sent Events (SSE) to receive live updates from the API:

- Device state changes are reflected immediately
- Event log shows all system events
- Auto-reconnect on connection loss

### Filtering

Filter devices by:
- **Type**: light, plug, camera, sensor, etc.
- **Room**: Living Room, Bedroom, etc.
- **Status**: Online or Offline

## API Integration

The frontend connects to the ManeYantra REST API:

- **Base URL**: `http://localhost:8000/api/v1`
- **SSE Stream**: `http://localhost:8000/api/v1/events/stream`

See `src/lib/api.ts` for all available API methods.

## Development

### Hot Module Replacement

Vite provides instant HMR - changes are reflected immediately in the browser.

### Type Safety

All API types are defined in `src/types/api.ts` and match the TypeSpec specification.

### Code Style

```bash
npm run lint
```

## Troubleshooting

### API Connection Issues

If the frontend can't connect to the API:

1. Ensure the ManeYantra API server is running:
   ```bash
   python3 -m maneyantra.main
   ```

2. Check the API URL in `.env` matches your API server

3. Check browser console for CORS errors

### SSE Not Working

If real-time updates aren't working:

1. Check the SSE connection status in the Event Log component
2. Open browser DevTools > Network tab and filter for "stream"
3. Verify RabbitMQ is running (required for events)

### Build Errors

If you encounter build errors:

```bash
# Clean install
rm -rf node_modules package-lock.json
npm install

# Clear cache
npm run build -- --force
```

## Contributing

When adding new features:

1. Add types to `src/types/api.ts` if needed
2. Update API client in `src/lib/api.ts`
3. Create/update components in `src/components/`
4. Use TypeScript strictly - no `any` types
5. Follow existing code style

## License

Part of the ManeYantra project.
