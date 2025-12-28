# ManeYantra 🏠

**Plugin-based home automation system with RabbitMQ and React UI**

ManeYantra is a custom, language-agnostic home automation system built with Python backend, React frontend, and RabbitMQ message broker. It uses RabbitMQ (AMQP) for inter-plugin communication, allowing you to write plugins in any language.

## Features

- 🎨 **Modern React UI** - Real-time dashboard with device control and guard mode management
- ⚡ **Server-Sent Events (SSE)** - Live device updates without polling
- 🔌 **RabbitMQ-based architecture** - Enterprise-grade message broker with guaranteed delivery
- 🧩 **Plugin system** - Extensible device, automation, and service plugins
- 🏡 **Device support** - TP-Link Kasa, Eufy Security (cameras, sensors, stations)
- 🛡️ **Guard Mode Control** - Arm/disarm Eufy HomeBase stations (Disarmed/Home/Away)
- 🤖 **Automation** - Rule-based automation engine
- 📊 **REST API** - FastAPI backend with OpenAPI documentation
- 🌍 **Distributed** - Plugins can run anywhere on your network
- 📈 **Management UI** - Built-in RabbitMQ management dashboard

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    React Frontend (Port 5173)                 │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │Device Cards│  │Guard Mode UI │  │SSE Event Connection  │ │
│  └────────────┘  └──────────────┘  └──────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                              │
                         REST API + SSE
                              │
┌──────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Port 8000)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  /api/v1/    │  │   /events    │  │  Plugin Manager  │  │
│  │   devices    │  │    (SSE)     │  │                  │  │
│  │   stations   │  │              │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                              │
                    RabbitMQ Broker (AMQP)
                   Management UI: Port 15672
                              │
                 ┌────────────┼────────────┐
                 ▼            ▼            ▼
         ┌───────────┐ ┌──────────┐ ┌──────────┐
         │  Device   │ │Automation│ │ Service  │
         │  Plugins  │ │ Plugins  │ │ Plugins  │
         │           │ │          │ │          │
         │ • TP-Link │ │ • Rules  │ │ • Logger │
         │ • Eufy    │ │          │ │ • Notify │
         └───────────┘ └──────────┘ └──────────┘
                 │
         ┌───────┴────────┐
         ▼                ▼
   ┌──────────┐    ┌────────────┐
   │ Devices  │    │Eufy Bridge │
   │(TP-Link) │    │(Node.js)   │
   └──────────┘    │Port 3000   │
                   └────────────┘
```

### RabbitMQ Routing Keys

- `maneyantra.device.{device_id}.state` - Device state updates
- `maneyantra.device.{device_id}.command` - Device commands
- `maneyantra.device.{device_id}.available` - Device online/offline
- `maneyantra.device.discovery.{device_id}` - Device discovery
- `maneyantra.plugin.{plugin_id}.status` - Plugin lifecycle
- `maneyantra.automation.{rule_id}.trigger` - Automation triggers
- `maneyantra.service.notify` - Notification requests
- `maneyantra.system.{event_type}` - System events

**Routing Wildcards:**
- `*` - Matches exactly one word
- `#` - Matches zero or more words

## Quick Start

### Prerequisites

1. **Python 3.11+**
2. **Node.js 18+** (for frontend)
3. **Docker & Docker Compose** (recommended for RabbitMQ and Eufy Bridge)

### Installation

```bash
# Clone the repository
git clone git@github.com:varunbhat/home-automation.git
cd home-automation

# Start infrastructure (RabbitMQ + Eufy Bridge)
docker-compose up -d

# Install backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install frontend
cd frontend
npm install
cd ..
```

### Running the Application

You need to run three components:

#### 1. Backend (from project root)
```bash
# Activate virtual environment
source venv/bin/activate

# Run from project root directory
python -m maneyantra.main

# Backend runs on http://localhost:8000
# API docs: http://localhost:8000/docs
```

#### 2. Frontend (from frontend/ directory)
```bash
# Navigate to frontend directory
cd frontend

# Start development server
npm run dev

# Frontend runs on http://localhost:5173
```

#### 3. Infrastructure (Docker containers)
```bash
# From project root
docker-compose up -d

# RabbitMQ Management UI: http://localhost:15672 (guest/guest)
# Eufy Bridge: http://localhost:3000
```

### Verify Setup

1. **Backend health**: http://localhost:8000/health
2. **Frontend**: http://localhost:5173
3. **RabbitMQ**: http://localhost:15672
4. **API docs**: http://localhost:8000/docs

### Directory Reference

**CRITICAL**: Always run commands from the correct directory:

| Component | Working Directory | Command |
|-----------|------------------|---------|
| **Backend** | `/path/to/home-automation` (project root) | `python -m maneyantra.main` |
| **Frontend** | `/path/to/home-automation/frontend` | `npm run dev` |
| **Docker** | `/path/to/home-automation` (project root) | `docker-compose up -d` |
| **Scripts** | `/path/to/home-automation` (project root) | `python scripts/add_test_devices.py` |

⚠️ **Common Error**: Running backend from wrong directory causes "config/system.yaml not found" error

## Configuration

### 1. Copy example configurations

```bash
cp config/system.yaml.example config/system.yaml
cp config/plugins.yaml.example config/plugins.yaml
cp .env.example .env
```

### 2. Edit configuration files

**config/system.yaml** - System configuration
```yaml
system:
  name: "ManeYantra Home Automation"
  log_level: INFO

rabbitmq:
  host: localhost
  port: 5672
  username: guest
  password: guest
  vhost: /
  exchange_name: maneyantra
```

**config/plugins.yaml** - Plugin configuration
```yaml
plugins:
  tplink:
    enabled: true
    type: device
    module: maneyantra.plugins.devices.tplink.plugin
    class: TpLinkPlugin
    config:
      discovery_interval: 300
```

**/.env** - Environment variables (credentials)
```bash
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=guest
RABBITMQ_PASSWORD=guest
EUFY_USERNAME=your_email@example.com
EUFY_PASSWORD=your_password
```

## Usage

### Control Devices

The easiest way to control devices is through the **Web UI** at http://localhost:5173

#### Via Web UI (Recommended)
1. Open http://localhost:5173
2. View all connected devices in the grid
3. Click device controls to turn on/off, adjust brightness, etc.
4. Use guard mode control to arm/disarm Eufy stations

#### Via REST API
```bash
# Turn on a light
curl -X POST http://localhost:8000/api/v1/devices/living_room_light/command \
  -H "Content-Type: application/json" \
  -d '{"command": "turn_on"}'

# Set brightness to 75%
curl -X POST http://localhost:8000/api/v1/devices/living_room_light/command \
  -H "Content-Type: application/json" \
  -d '{"command": "set_brightness", "params": {"brightness": 75}}'

# Set guard mode to Away (mode 2)
curl -X POST http://localhost:8000/api/v1/stations/T8010XXXXX/guard-mode \
  -H "Content-Type: application/json" \
  -d '{"mode": 2}'
```

#### Via RabbitMQ (Advanced)

You can also publish messages directly to RabbitMQ:

**Using RabbitMQ Management UI:**
1. Open http://localhost:15672 (guest/guest)
2. Go to "Queues" tab
3. Publish messages to the exchange "maneyantra"

**Using Python with pika:**
```python
import pika
import json

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

message = {"command": "turn_on", "params": {}}
channel.basic_publish(
    exchange='maneyantra',
    routing_key='maneyantra.device.living_room_light.command',
    body=json.dumps(message)
)
```

## Creating Plugins

### Python Device Plugin

```python
from maneyantra.core.plugin import PluginMetadata, PluginType
from maneyantra.plugins.devices.base import BaseDevicePlugin, Device

class MyDevicePlugin(BaseDevicePlugin):
    def __init__(self, plugin_id, config, mqtt_bus):
        metadata = PluginMetadata(
            name="My Device",
            version="0.1.0",
            plugin_type=PluginType.DEVICE,
            description="My custom device integration",
        )
        super().__init__(plugin_id, metadata, config, mqtt_bus)

    async def discover_devices(self):
        # Discover and return devices
        devices = []
        # ... discovery logic
        return devices
```

### External Plugin (Any Language)

Plugins in other languages just need to:
1. Connect to the RabbitMQ broker (AMQP)
2. Publish/subscribe to the topic exchange
3. Follow the message format

Example in Node.js using amqplib:
```javascript
const amqp = require('amqplib');

async function start() {
  const connection = await amqp.connect('amqp://guest:guest@localhost:5672');
  const channel = await connection.createChannel();

  const exchange = 'maneyantra';
  await channel.assertExchange(exchange, 'topic', {durable: true});

  // Subscribe to commands
  const {queue} = await channel.assertQueue('', {exclusive: true});
  await channel.bindQueue(queue, exchange, 'maneyantra.device.my_device.command');

  channel.consume(queue, (msg) => {
    const payload = JSON.parse(msg.content.toString());
    console.log('Command received:', payload);
  }, {noAck: true});

  // Publish state updates
  const message = {
    timestamp: new Date().toISOString(),
    state: {on: true, brightness: 100}
  };
  channel.publish(exchange, 'maneyantra.device.my_device.state',
    Buffer.from(JSON.dumps(message)));
}

start();
```

## Automation Rules

Create rule files in `config/rules/`:

**config/rules/motion_lights.yaml**
```yaml
rules:
  - id: turn_on_lights_on_motion
    name: Turn on lights when motion detected
    trigger:
      topic: device/+/state
      condition:
        field: state.motion
        operator: eq
        value: true
    actions:
      - command:
          topic: device/living_room_light/command
          payload:
            command: turn_on
      - delay: 300  # Wait 5 minutes
      - command:
          topic: device/living_room_light/command
          payload:
            command: turn_off
```

## Supported Devices

### TP-Link Kasa
- ✅ Smart bulbs (color, brightness, color temperature)
- ✅ Smart plugs
- ✅ Smart switches
- ✅ Energy monitoring

### Eufy Security
- ✅ Cameras (streaming, motion detection)
- ✅ Doorbells
- ✅ Motion sensors
- ✅ Door/window sensors

## Project Structure

```
home-automation/
├── frontend/                   # React frontend (Port 5173)
│   ├── src/
│   │   ├── app/               # Main app component
│   │   ├── features/          # Feature modules
│   │   │   ├── devices/       # Device management
│   │   │   ├── stations/      # Guard mode control
│   │   │   └── events/        # SSE event stream
│   │   ├── shared/            # Shared components & utils
│   │   └── lib/               # API client, React Query
│   ├── package.json
│   └── vite.config.ts
│
├── maneyantra/                 # Python backend (Port 8000)
│   ├── api/                   # FastAPI routes
│   │   ├── app.py             # FastAPI app setup
│   │   ├── models.py          # Pydantic models
│   │   └── routers/           # API endpoints
│   │       ├── devices.py     # /api/v1/devices
│   │       ├── stations.py    # /api/v1/stations
│   │       ├── events.py      # /events (SSE)
│   │       └── plugins.py     # /api/v1/plugins
│   ├── core/                  # Core system
│   │   ├── rabbitmq_bus.py    # RabbitMQ event bus
│   │   ├── plugin.py          # Plugin base classes
│   │   ├── manager.py         # Plugin manager
│   │   └── config.py          # Configuration
│   ├── plugins/
│   │   ├── devices/           # Device plugins
│   │   │   ├── base.py
│   │   │   ├── tplink/        # TP-Link integration
│   │   │   ├── eufy/          # Eufy integration
│   │   │   └── mock/          # Mock devices for testing
│   │   ├── automations/       # Automation plugins
│   │   │   └── rules.py
│   │   └── services/          # Service plugins
│   │       ├── logger.py
│   │       └── notifications.py
│   ├── types/                 # Type definitions
│   │   └── devices.py
│   └── main.py                # Entry point
│
├── eufy-bridge/                # Node.js Eufy Security bridge
│   ├── server.js              # HTTP API + WebSocket server
│   └── package.json
│
├── config/                     # Configuration files
│   ├── system.yaml            # System settings
│   ├── plugins.yaml           # Plugin configuration
│   └── rules/                 # Automation rules
│
├── scripts/                    # Utility scripts
│   └── add_test_devices.py    # Add mock devices
│
├── docker-compose.yml          # Infrastructure (RabbitMQ, Eufy Bridge)
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Python project config
├── RULES.md                    # Branch protection rules
└── README.md                   # This file

IMPORTANT DIRECTORIES TO RUN COMMANDS:
- Backend: Run from PROJECT ROOT (/path/to/home-automation)
- Frontend: Run from frontend/ directory (/path/to/home-automation/frontend)
```

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Format code
black maneyantra/

# Lint code
ruff check maneyantra/

# Run tests
pytest
```

## Troubleshooting

### MQTT Connection Issues

```bash
# Check if MQTT broker is running
mosquitto_sub -t test

# Test with verbose logging
maneyantra --config config
```

### Device Discovery Issues

- Ensure devices are on the same network
- Check firewall settings
- TP-Link: Devices must be in local control mode
- Eufy: Verify credentials in .env

### Plugin Not Loading

- Check `config/plugins.yaml` syntax
- Verify module path is correct
- Check logs in `logs/maneyantra.log`

## Web Dashboard

ManeYantra includes a modern React 19 frontend with real-time updates via Server-Sent Events.

### Features

- 🎨 **Modern UI** - Responsive design with Tailwind CSS and shadcn/ui components
- ⚡ **Real-time Updates** - Server-Sent Events (SSE) for live device state changes
- 🎛️ **Device Control** - Control lights, plugs, switches (on/off, brightness, color, temperature)
- 🛡️ **Guard Mode** - Arm/disarm Eufy HomeBase stations (Disarmed/Home/Away)
- 📊 **Sensor Display** - Motion sensors, door/window sensors, battery levels
- 🔍 **Device Organization** - Grid view with device cards showing capabilities
- 🌐 **Network Status** - Live connection indicator for SSE stream
- 📱 **Responsive** - Works on desktop, tablet, and mobile

### Technology Stack

- **Frontend Framework**: React 19 with TypeScript
- **Build Tool**: Vite 7
- **State Management**: TanStack Query (React Query)
- **UI Components**: shadcn/ui + Tailwind CSS
- **API Client**: Axios
- **Real-time**: Server-Sent Events (SSE)

### Running Frontend

```bash
# From frontend/ directory
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev

# Production build
npm run build
npm run preview
```

**URLs:**
- Development: http://localhost:5173
- Backend API: http://localhost:8000
- SSE Events: http://localhost:8000/events

See [frontend/README.md](frontend/README.md) and [frontend/ARCHITECTURE.md](frontend/ARCHITECTURE.md) for more details.

## REST API

ManeYantra provides a FastAPI-based REST API with automatic OpenAPI documentation.

### API Endpoints

#### Devices
- `GET /api/v1/devices` - List all devices
- `GET /api/v1/devices/{device_id}` - Get device details
- `GET /api/v1/devices/{device_id}/state` - Get device state
- `POST /api/v1/devices/{device_id}/command` - Send device command
- `POST /api/v1/devices/{device_id}/refresh` - Refresh device state

#### Stations (Eufy HomeBase)
- `GET /api/v1/stations` - List all stations
- `POST /api/v1/stations/{serial}/guard-mode` - Set guard mode (0=Disarmed, 1=Home, 2=Away)

#### Plugins
- `GET /api/v1/plugins` - List all plugins
- `GET /api/v1/plugins/{plugin_id}` - Get plugin details

#### Events
- `GET /events` - Server-Sent Events stream for real-time updates

### API Documentation

- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc (Alternative documentation)
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Example API Usage

```bash
# List all devices
curl http://localhost:8000/api/v1/devices

# Turn on a light
curl -X POST http://localhost:8000/api/v1/devices/living_room_light/command \
  -H "Content-Type: application/json" \
  -d '{"command": "turn_on"}'

# Set brightness
curl -X POST http://localhost:8000/api/v1/devices/living_room_light/command \
  -H "Content-Type: application/json" \
  -d '{"command": "set_brightness", "params": {"brightness": 75}}'

# Set guard mode to Away
curl -X POST http://localhost:8000/api/v1/stations/T8010XXXXX/guard-mode \
  -H "Content-Type: application/json" \
  -d '{"mode": 2}'

# Subscribe to real-time events
curl -N http://localhost:8000/events
```

## Future Enhancements

- [x] Web UI dashboard
- [x] REST API with SSE
- [ ] More device integrations (Zigbee, Z-Wave via bridges)
- [ ] Advanced scheduling
- [ ] Scenes support
- [ ] Email/SMS notifications
- [ ] Database persistence
- [ ] Multi-user support

## Contributing

Contributions welcome! This is a custom system built for flexibility and extensibility.

## License

MIT License - See LICENSE file

## Credits

Built with:
- [aio-pika](https://github.com/mosquito/aio-pika) - Async RabbitMQ (AMQP) client
- [python-kasa](https://github.com/python-kasa/python-kasa) - TP-Link integration
- [lakeside](https://github.com/fuatakgun/eufy_security) - Eufy Security integration

---

**ManeYantra** - *Your home, your rules, your code* 🏠✨
