# Getting Started with ManeYantra

This guide will help you get ManeYantra up and running in minutes.

## Quick Start

### 1. Install MQTT Broker

**macOS:**
```bash
brew install mosquitto
brew services start mosquitto
```

**Ubuntu/Debian:**
```bash
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

**Verify MQTT is running:**
```bash
mosquitto_sub -t test
# Keep this terminal open, open another terminal:
mosquitto_pub -t test -m "Hello MQTT"
# You should see "Hello MQTT" in the first terminal
```

### 2. Setup ManeYantra

```bash
cd /Users/varunbhat/workspace/maneyantra

# Run the setup script
./scripts/setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 3. Configure

```bash
# Copy example configs
cp config/system.yaml.example config/system.yaml
cp config/plugins.yaml.example config/plugins.yaml
cp .env.example .env

# Edit credentials
nano .env
# Add your Eufy credentials if using Eufy devices
```

### 4. Run

```bash
source venv/bin/activate
maneyantra
```

You should see:
```
🏠 ManeYantra - Home Automation System
================================================
📋 Loading configuration...
🔌 Connecting to MQTT broker...
🔧 Loading plugins...
⚙️  Initializing plugins...
🚀 Starting plugins...

✅ ManeYantra is running!
📊 Loaded 5 plugins
   Press Ctrl+C to stop
```

## Testing Device Control

### Monitor all events:
```bash
# In a new terminal
mosquitto_sub -v -t "maneyantra/#"
```

### Control a TP-Link light:
```bash
# Turn on
mosquitto_pub -t "maneyantra/device/YOUR_LIGHT_ID/command" \
  -m '{"command": "turn_on"}'

# Set brightness to 50%
mosquitto_pub -t "maneyantra/device/YOUR_LIGHT_ID/command" \
  -m '{"command": "set_brightness", "params": {"brightness": 50}}'

# Turn off
mosquitto_pub -t "maneyantra/device/YOUR_LIGHT_ID/command" \
  -m '{"command": "turn_off"}'
```

### View device states:
```bash
mosquitto_sub -t "maneyantra/device/+/state"
```

## Creating Your First Automation

Create `config/rules/my_rules.yaml`:

```yaml
rules:
  # Turn on bedroom light at sunset
  - id: bedroom_light_sunset
    name: "Bedroom light at sunset"
    trigger:
      topic: "system/time"
      condition:
        field: "event"
        operator: "eq"
        value: "sunset"
    actions:
      - command:
          topic: "device/bedroom_light/command"
          payload:
            command: "turn_on"
            params:
              brightness: 30

  # Notify when front door opens
  - id: door_open_notify
    name: "Front door opened"
    trigger:
      topic: "device/front_door_sensor/state"
      condition:
        field: "state.contact"
        operator: "eq"
        value: true
    actions:
      - command:
          topic: "service/notify"
          payload:
            title: "Front Door"
            message: "Front door opened"
            priority: "normal"
```

Restart ManeYantra to load the new rules.

## Creating a Custom Plugin

### Python Plugin

1. Create `maneyantra/plugins/services/my_plugin.py`:

```python
from maneyantra.core.plugin import PluginBase, PluginMetadata, PluginType

class MyPlugin(PluginBase):
    def __init__(self, plugin_id, config, mqtt_bus):
        metadata = PluginMetadata(
            name="My Plugin",
            version="0.1.0",
            plugin_type=PluginType.SERVICE,
            description="My custom plugin",
        )
        super().__init__(plugin_id, metadata, config, mqtt_bus)

    async def initialize(self):
        self._logger.info("Initializing...")

    async def start(self):
        # Subscribe to events
        await self.mqtt.subscribe("device/+/state", self._handle_event)

    async def stop(self):
        self._logger.info("Stopping...")

    async def _handle_event(self, topic, payload):
        self._logger.info(f"Got event: {topic}")
```

2. Add to `config/plugins.yaml`:

```yaml
my_plugin:
  enabled: true
  type: service
  module: maneyantra.plugins.services.my_plugin
  class: MyPlugin
  config:
    my_setting: "value"
```

### External Plugin (Any Language)

See `examples/external_plugin.js` for a complete Node.js example.

Key points:
1. Connect to MQTT broker
2. Subscribe to topics you care about
3. Publish to `maneyantra/` topics
4. Follow the message format (JSON with timestamp)

## Common Tasks

### List all devices:
```bash
mosquitto_sub -t "maneyantra/device/discovery/#" -C 10
```

### Check plugin health:
```bash
# Request health check from all plugins
mosquitto_pub -t "maneyantra/system/health_check" -m '{}'

# Watch for responses
mosquitto_sub -t "maneyantra/plugin/+/status"
```

### Debug issues:
```bash
# Check logs
tail -f logs/maneyantra.log

# Verbose MQTT monitoring
mosquitto_sub -v -t "maneyantra/#"

# Test MQTT connection
mosquitto_pub -t "maneyantra/test" -m '{"test": true}'
```

### Reload a plugin:
```bash
# Edit config/plugins.yaml, then:
mosquitto_pub -t "maneyantra/system/reload_plugin" \
  -m '{"plugin_id": "tplink"}'
```

## Architecture Overview

```
Your Network
    │
    ├── MQTT Broker (mosquitto)
    │       ↕
    ├── ManeYantra Core (Python)
    │       ├── Plugin Manager
    │       ├── Event Bus
    │       └── Config Manager
    │
    ├── Python Plugins
    │   ├── TP-Link (device)
    │   ├── Eufy (device)
    │   ├── Rule Engine (automation)
    │   ├── Logger (service)
    │   └── Notifications (service)
    │
    ├── External Plugins (optional)
    │   ├── Node.js plugins
    │   ├── Go plugins
    │   └── Any language!
    │
    └── Your Devices
        ├── TP-Link lights/plugs
        ├── Eufy cameras/sensors
        └── Future integrations
```

## MQTT Topic Reference

### Device Topics
- `device/{id}/state` - Device state updates
- `device/{id}/command` - Send commands to device
- `device/{id}/available` - Device online/offline
- `device/discovery/{id}` - New device discovered
- `device/{id}/error` - Device errors

### Plugin Topics
- `plugin/{id}/status` - Plugin status/health
- `plugin/{id}/heartbeat` - Plugin heartbeat

### Automation Topics
- `automation/{rule_id}/trigger` - Rule triggered

### Service Topics
- `service/notify` - Send notification
- `service/log` - Log message

### System Topics
- `system/start` - System started
- `system/stop` - System stopping
- `system/health_check` - Request health check

## Next Steps

1. **Add more devices**: Configure TP-Link, Eufy, or create custom integrations
2. **Create automations**: Write rules in `config/rules/`
3. **Build plugins**: Extend ManeYantra with custom functionality
4. **Web UI**: Build a dashboard that subscribes to MQTT topics
5. **Mobile app**: Use MQTT client libraries for iOS/Android

## Troubleshooting

**Plugin not loading?**
- Check `config/plugins.yaml` syntax
- Verify module path is correct
- Look at `logs/maneyantra.log`

**Devices not discovered?**
- Ensure devices are on same network
- Check firewall settings
- TP-Link: Enable local control in Kasa app

**MQTT not working?**
- Verify broker is running: `brew services list`
- Test connection: `mosquitto_sub -t test`
- Check broker logs: `tail -f /opt/homebrew/var/log/mosquitto/mosquitto.log`

## Resources

- [MQTT Documentation](https://mqtt.org/)
- [python-kasa Documentation](https://python-kasa.readthedocs.io/)
- [ManeYantra Examples](./examples/)

Happy Automating! 🏠✨
