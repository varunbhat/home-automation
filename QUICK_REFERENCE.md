# ManeYantra Quick Reference

## Installation

```bash
./scripts/setup.sh
source venv/bin/activate
maneyantra
```

## MQTT Commands Cheat Sheet

### Device Control

```bash
# Turn device on
mosquitto_pub -t "maneyantra/device/{ID}/command" -m '{"command":"turn_on"}'

# Turn device off
mosquitto_pub -t "maneyantra/device/{ID}/command" -m '{"command":"turn_off"}'

# Set brightness (0-100)
mosquitto_pub -t "maneyantra/device/{ID}/command" -m '{"command":"set_brightness","params":{"brightness":75}}'

# Set color (HSV)
mosquitto_pub -t "maneyantra/device/{ID}/command" -m '{"command":"set_hsv","params":{"hue":120,"saturation":100,"value":100}}'

# Set color temperature (Kelvin)
mosquitto_pub -t "maneyantra/device/{ID}/command" -m '{"command":"set_color_temperature","params":{"temperature":4000}}'
```

### Monitoring

```bash
# Monitor all events
mosquitto_sub -v -t "maneyantra/#"

# Monitor device states
mosquitto_sub -t "maneyantra/device/+/state"

# Monitor specific device
mosquitto_sub -t "maneyantra/device/{ID}/#"

# Monitor system events
mosquitto_sub -t "maneyantra/system/#"

# Monitor plugin status
mosquitto_sub -t "maneyantra/plugin/+/status"
```

### Notifications

```bash
# Send notification
mosquitto_pub -t "maneyantra/service/notify" -m '{
  "title":"Alert",
  "message":"Something happened",
  "priority":"high"
}'
```

## Python Plugin Template

```python
from maneyantra.core.plugin import PluginBase, PluginMetadata, PluginType

class MyPlugin(PluginBase):
    def __init__(self, plugin_id, config, mqtt_bus):
        metadata = PluginMetadata(
            name="My Plugin",
            version="0.1.0",
            plugin_type=PluginType.SERVICE,
            description="Description",
        )
        super().__init__(plugin_id, metadata, config, mqtt_bus)

    async def initialize(self):
        pass  # Setup

    async def start(self):
        await self.mqtt.subscribe("topic", self._handler)

    async def stop(self):
        pass  # Cleanup

    async def _handler(self, topic, payload):
        pass  # Handle events
```

## Automation Rule Template

```yaml
rules:
  - id: my_rule
    name: "My automation rule"
    trigger:
      topic: "device/+/state"
      condition:
        field: "state.motion"
        operator: "eq"  # eq, ne, gt, gte, lt, lte, in, contains
        value: true
    actions:
      - command:
          topic: "device/light/command"
          payload:
            command: "turn_on"
      - delay: 300  # seconds
      - command:
          topic: "device/light/command"
          payload:
            command: "turn_off"
```

## Configuration Files

### system.yaml
```yaml
system:
  name: "Home"
  log_level: INFO

mqtt:
  broker: localhost
  port: 1883
```

### plugins.yaml
```yaml
my_plugin:
  enabled: true
  type: service  # device, automation, service
  module: path.to.module
  class: ClassName
  config:
    key: value
```

## Common Device IDs

TP-Link devices use MAC address without colons:
- Example: `800627ABCDEF123`

Eufy devices use serial number:
- Example: `T8410P1234567890`

Find device IDs:
```bash
mosquitto_sub -t "maneyantra/device/discovery/#"
```

## Operators for Rules

- `eq` - Equal to
- `ne` - Not equal to
- `gt` - Greater than
- `gte` - Greater than or equal
- `lt` - Less than
- `lte` - Less than or equal
- `in` - Value in list
- `contains` - Contains substring

## Log Levels

- `DEBUG` - Detailed information
- `INFO` - General information (default)
- `WARNING` - Warning messages
- `ERROR` - Error messages

## File Locations

- Config: `config/`
- Logs: `logs/maneyantra.log`
- Data: `data/`
- Rules: `config/rules/*.yaml`

## Useful Commands

```bash
# View logs
tail -f logs/maneyantra.log

# Check MQTT broker
mosquitto_sub -t test &
mosquitto_pub -t test -m "ping"

# Test configuration
python -c "from maneyantra.core.config import ConfigManager; c=ConfigManager(); c.load(); print('OK')"

# List Python packages
pip list | grep -i kasa

# Restart MQTT broker (macOS)
brew services restart mosquitto

# Restart MQTT broker (Linux)
sudo systemctl restart mosquitto
```

## Environment Variables

```bash
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=
EUFY_USERNAME=
EUFY_PASSWORD=
EUFY_COUNTRY=US
LOG_LEVEL=INFO
```

## Plugin Types

1. **Device** - Hardware integrations (lights, cameras, sensors)
2. **Automation** - Rules, schedules, scenes
3. **Service** - Cross-cutting concerns (logging, notifications)

## Message Format

All MQTT messages are JSON with timestamp:
```json
{
  "timestamp": "2025-01-15T10:30:00.000Z",
  "command": "turn_on",
  "params": {}
}
```

## Exit Codes

- `0` - Success
- `1` - Fatal error
- `Ctrl+C` - Graceful shutdown
