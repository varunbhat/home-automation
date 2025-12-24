# ManeYantra REST API Documentation

## Overview

ManeYantra now includes a comprehensive REST API with real-time Server-Sent Events (SSE) for device control and monitoring.

## Features

- ✅ **REST API** - Full CRUD operations for devices and plugins
- ✅ **Real-time SSE** - Live device state updates
- ✅ **TypeSpec Specification** - Type-safe API definitions
- ✅ **Auto-generated OpenAPI** - Interactive API documentation
- ✅ **CORS Enabled** - Ready for frontend integration

## Starting the API Server

### Start with API (default)
```bash
python3 -m maneyantra.main
# API will be available at http://localhost:8000
```

### Custom port
```bash
python3 -m maneyantra.main --api-port 3000
```

### Disable API
```bash
python3 -m maneyantra.main --no-api
```

## API Endpoints

### Base URL
```
http://localhost:8000
```

### Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## REST Endpoints

### Health Check
```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00",
  "plugins": {
    "tplink": { "healthy": true, "device_count": 11 },
    "eufy": { "healthy": true, "device_count": 14 }
  }
}
```

---

### Devices

#### List All Devices
```http
GET /api/v1/devices
```

**Query Parameters:**
- `type` (optional): Filter by device type (light, plug, camera, etc.)
- `plugin_id` (optional): Filter by plugin ID
- `room` (optional): Filter by room
- `online` (optional): Filter by online status (true/false)

**Example:**
```http
GET /api/v1/devices?type=light&online=true
```

**Response:**
```json
{
  "devices": [
    {
      "info": {
        "id": "192_168_86_45",
        "name": "Living Room Light",
        "type": "light",
        "capabilities": ["on_off", "brightness", "color"],
        "manufacturer": "TP-Link",
        "model": "KL130",
        "plugin_id": "tplink"
      },
      "state": {
        "online": true,
        "on": true,
        "brightness": 75,
        "color": {
          "hue": 120,
          "saturation": 80,
          "value": 100
        }
      }
    }
  ],
  "total": 25
}
```

#### Get Single Device
```http
GET /api/v1/devices/{device_id}
```

**Response:** Same as single device object above

#### Execute Device Command
```http
POST /api/v1/devices/{device_id}/command
```

**Request Body:**
```json
{
  "command": "turn_on",
  "params": {
    "brightness": 80
  }
}
```

**Common Commands:**
- `turn_on` - Turn device on
- `turn_off` - Turn device off
- `toggle` - Toggle device state
- `set_brightness` - Set brightness (params: `{"brightness": 0-100}`)
- `set_color_temperature` - Set color temp (params: `{"temperature": 2000-9000}`)
- `set_hsv` - Set color (params: `{"hue": 0-360, "saturation": 0-100, "value": 0-100}`)

**Response:**
```json
{
  "success": true,
  "message": "Command 'turn_on' executed successfully",
  "state": {
    "online": true,
    "on": true,
    "brightness": 80
  }
}
```

#### Get Device State
```http
GET /api/v1/devices/{device_id}/state
```

**Response:**
```json
{
  "online": true,
  "on": true,
  "brightness": 75,
  "color": {
    "hue": 120,
    "saturation": 80,
    "value": 100
  }
}
```

#### Refresh Device State
```http
POST /api/v1/devices/{device_id}/refresh
```

Forces a refresh from the physical device.

**Response:** Updated device state

---

### Plugins

#### List All Plugins
```http
GET /api/v1/plugins
```

**Response:**
```json
{
  "plugins": [
    {
      "id": "tplink",
      "name": "TP-Link Kasa",
      "version": "0.1.0",
      "type": "device",
      "description": "TP-Link Kasa smart home devices integration",
      "state": "running",
      "device_count": 11
    }
  ],
  "total": 2
}
```

#### Get Single Plugin
```http
GET /api/v1/plugins/{plugin_id}
```

#### Trigger Device Discovery
```http
POST /api/v1/plugins/{plugin_id}/discover
```

Triggers device discovery for a specific plugin.

**Response:**
```json
{
  "message": "Discovery completed for TP-Link Kasa",
  "discovered_count": 3
}
```

---

## Real-time Events (SSE)

### Event Stream
```http
GET /api/v1/events/stream
```

**Query Parameters:**
- `device_id` (optional): Filter events for specific device
- `event_type` (optional): Filter by event type (state, discovery, error, etc.)

**Event Types:**
- `connected` - Initial connection confirmation
- `state` - Device state changed
- `discovery` - New device discovered
- `available` - Device availability changed
- `error` - Device error occurred
- `system` - System event
- `heartbeat` - Keepalive message (every 30s)

### Device-Specific Stream
```http
GET /api/v1/events/devices/{device_id}/stream
```

Convenience endpoint for subscribing to a single device.

---

## SSE Client Examples

### JavaScript (Browser)

```javascript
const eventSource = new EventSource('http://localhost:8000/api/v1/events/stream');

// Handle all events
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Event received:', data);
};

// Handle specific event types
eventSource.addEventListener('state', (event) => {
    const data = JSON.parse(event.data);
    console.log('Device state changed:', data);
});

eventSource.addEventListener('error', (event) => {
    console.error('SSE error:', event);
});

// Close connection
eventSource.close();
```

### Python

```python
import requests
import json

url = "http://localhost:8000/api/v1/events/stream"
response = requests.get(url, stream=True)

for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith('data: '):
            data = json.loads(line[6:])
            print('Event:', data)
```

### cURL

```bash
curl -N http://localhost:8000/api/v1/events/stream
```

---

## Testing the API

### 1. Interactive Documentation
Open http://localhost:8000/docs in your browser to use the interactive Swagger UI.

### 2. SSE Test Page
Open `test_sse.html` in your browser to see real-time events.

### 3. Command Line Examples

**List all devices:**
```bash
curl http://localhost:8000/api/v1/devices
```

**Turn on a light:**
```bash
curl -X POST http://localhost:8000/api/v1/devices/192_168_86_45/command \
  -H "Content-Type: application/json" \
  -d '{"command": "turn_on", "params": {"brightness": 100}}'
```

**Watch live events:**
```bash
curl -N http://localhost:8000/api/v1/events/stream
```

---

## TypeSpec Specification

The API is fully specified using TypeSpec in `api-spec/main.tsp`.

### Generate OpenAPI spec:
```bash
cd api-spec
npm install
npm run build
```

This generates `openapi.yaml` which can be used for:
- Client SDK generation
- API documentation
- Contract testing

---

## Integration Examples

### React Hook for Real-time Updates

```javascript
import { useEffect, useState } from 'react';

function useDeviceEvents(deviceId = null) {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const url = deviceId
      ? `http://localhost:8000/api/v1/events/devices/${deviceId}/stream`
      : 'http://localhost:8000/api/v1/events/stream';

    const eventSource = new EventSource(url);

    eventSource.onopen = () => setConnected(true);
    eventSource.onerror = () => setConnected(false);

    eventSource.addEventListener('state', (event) => {
      const data = JSON.parse(event.data);
      setEvents(prev => [data, ...prev]);
    });

    return () => eventSource.close();
  }, [deviceId]);

  return { events, connected };
}
```

### Vue.js Composable

```javascript
import { ref, onMounted, onUnmounted } from 'vue';

export function useDeviceStream(deviceId = null) {
  const events = ref([]);
  const connected = ref(false);
  let eventSource = null;

  onMounted(() => {
    const url = deviceId
      ? `http://localhost:8000/api/v1/events/devices/${deviceId}/stream`
      : 'http://localhost:8000/api/v1/events/stream';

    eventSource = new EventSource(url);

    eventSource.onopen = () => connected.value = true;
    eventSource.onerror = () => connected.value = false;

    eventSource.addEventListener('state', (event) => {
      const data = JSON.parse(event.data);
      events.value.unshift(data);
    });
  });

  onUnmounted(() => {
    if (eventSource) eventSource.close();
  });

  return { events, connected };
}
```

---

## Architecture

```
┌─────────────┐
│   Frontend  │
│  (Browser)  │
└──────┬──────┘
       │ HTTP/SSE
       ▼
┌─────────────────────┐
│   FastAPI Server    │
│   (port 8000)       │
├─────────────────────┤
│ • REST endpoints    │
│ • SSE event stream  │
│ • CORS middleware   │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Plugin Manager     │
│  • Device plugins   │
│  • Plugin lifecycle │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   RabbitMQ Bus      │
│  • Event publish    │
│  • Event subscribe  │
│  • Device commands  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Device Plugins    │
│  • TP-Link          │
│  • Eufy             │
└─────────────────────┘
```

---

## Configuration

API server configuration is part of the main ManeYantra config.

### Command-line options:
```bash
python3 -m maneyantra.main --help

Options:
  --config CONFIG        Configuration directory (default: config)
  --api-port PORT        API server port (default: 8000)
  --no-api               Disable API server
  --version              Show version
```

---

## CORS Configuration

CORS is currently configured to allow all origins for development. For production, update `maneyantra/api/app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

## Next Steps

1. **Build a Frontend**: Use the SSE stream to create a real-time dashboard
2. **Mobile App**: Connect via REST API for device control
3. **Automation**: Use webhooks or API calls to trigger device actions
4. **Analytics**: Subscribe to events and store device data

---

## Troubleshooting

### API not starting
- Check if port 8000 is already in use
- Try different port: `--api-port 3000`
- Check logs in `logs/maneyantra.log`

### SSE not receiving events
- Verify RabbitMQ is running: `docker ps`
- Check device plugins are running: `GET /api/v1/plugins`
- Monitor RabbitMQ messages in management UI

### CORS errors
- Update CORS configuration in `api/app.py`
- Use proxy during development
- Check browser console for details
