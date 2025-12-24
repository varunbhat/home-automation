# ManeYantra 🏠

**Plugin-based home automation system with RabbitMQ**

ManeYantra is a custom, language-agnostic home automation system built with Python. It uses RabbitMQ (AMQP) for inter-plugin communication, allowing you to write plugins in any language.

## Features

- 🔌 **RabbitMQ-based architecture** - Enterprise-grade message broker with guaranteed delivery
- 🧩 **Plugin system** - Extensible device, automation, and service plugins
- 🏡 **Device support** - TP-Link Kasa, Eufy Security (cameras, sensors)
- 🤖 **Automation** - Rule-based automation engine
- 📊 **Services** - Logging, notifications, and more
- 🌍 **Distributed** - Plugins can run anywhere on your network
- 📈 **Management UI** - Built-in RabbitMQ management dashboard

## Architecture

```
┌─────────────────────────────────────────┐
│          ManeYantra Core (Python)        │
│  ┌──────────────┐  ┌──────────────┐    │
│  │Plugin Manager│  │RabbitMQ Bus  │    │
│  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────┘
              │
      RabbitMQ Broker (AMQP)
     with Management UI :15672
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
┌─────────┐┌──────────┐┌──────────┐
│ Device  ││Automation││ Service  │
│Plugins  ││ Plugins  ││ Plugins  │
│(Python) ││(Python)  ││(Python)  │
│         ││          ││          │
│• TP-Link││• Rules   ││• Logger  │
│• Eufy   ││          ││• Notify  │
└─────────┘└──────────┘└──────────┘
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

## Installation

### Prerequisites

1. **Python 3.11+**
2. **RabbitMQ** (Message broker)

```bash
# Install RabbitMQ on macOS
brew install rabbitmq
brew services start rabbitmq

# Install RabbitMQ on Ubuntu/Debian
sudo apt install rabbitmq-server
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server

# Enable RabbitMQ Management UI (optional but recommended)
sudo rabbitmq-plugins enable rabbitmq_management
# Access at http://localhost:15672 (guest/guest)
```

### Install ManeYantra

```bash
# Clone the repository
cd /path/to/maneyantra

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

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

### Start the system

```bash
# Using the installed command
maneyantra

# Or run directly
python -m maneyantra.main

# With custom config directory
maneyantra --config /path/to/config
```

### Control devices via RabbitMQ

You can use the RabbitMQ Management UI or command-line tools:

**Using RabbitMQ Management UI:**
1. Open http://localhost:15672 (guest/guest)
2. Go to "Queues" tab
3. Publish messages to the exchange "maneyantra"

**Using rabbitmqadmin CLI:**
```bash
# Install rabbitmqadmin
sudo rabbitmq-plugins enable rabbitmq_management
wget http://localhost:15672/cli/rabbitmqadmin
chmod +x rabbitmqadmin

# Turn on a light
./rabbitmqadmin publish exchange=maneyantra \
  routing_key="maneyantra.device.living_room_light.command" \
  payload='{"command":"turn_on","params":{}}'

# Set brightness
./rabbitmqadmin publish exchange=maneyantra \
  routing_key="maneyantra.device.living_room_light.command" \
  payload='{"command":"set_brightness","params":{"brightness":75}}'
```

**Or use Python with pika:**
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
maneyantra/
├── maneyantra/
│   ├── core/                   # Core system
│   │   ├── mqtt_bus.py        # MQTT event bus
│   │   ├── plugin.py          # Plugin base classes
│   │   ├── manager.py         # Plugin manager
│   │   └── config.py          # Configuration
│   ├── plugins/
│   │   ├── devices/           # Device plugins
│   │   │   ├── base.py
│   │   │   ├── tplink/
│   │   │   └── eufy/
│   │   ├── automations/       # Automation plugins
│   │   │   └── rules.py
│   │   └── services/          # Service plugins
│   │       ├── logger.py
│   │       └── notifications.py
│   ├── types/                 # Type definitions
│   │   └── devices.py
│   └── main.py               # Entry point
├── config/                    # Configuration
│   ├── system.yaml
│   ├── plugins.yaml
│   └── rules/
├── requirements.txt
├── pyproject.toml
└── README.md
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

ManeYantra includes a modern React frontend with real-time updates:

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173 to access the dashboard.

**Features:**
- 🎨 Modern, responsive UI with Tailwind CSS
- ⚡ Real-time device updates via Server-Sent Events (SSE)
- 🎛️ Device control (on/off, brightness, etc.)
- 🔍 Filter devices by type, room, and status
- 📊 Live event log
- 🌙 Dark mode support

See [frontend/README.md](frontend/README.md) for more details.

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
