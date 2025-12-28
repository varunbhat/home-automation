"""Eufy Security plugin using Node.js bridge."""

import asyncio
import os
from typing import Dict, List, Optional
import aiohttp
import websockets
import json

from maneyantra.core.plugin import PluginMetadata, PluginType
from maneyantra.core.rabbitmq_bus import RabbitMQEventBus
from maneyantra.plugins.devices.base import BaseDevicePlugin, Device
from maneyantra.types.devices import DeviceInfo, DeviceType, DeviceCapability

from .devices import EufyCamera, EufySensor


class EufyPlugin(BaseDevicePlugin):
    """
    Eufy Security device plugin using Node.js bridge.

    Supports:
    - Eufy security cameras
    - Eufy sensors (motion, door/window)
    - Event notifications (motion, person detection)
    """

    def __init__(
        self,
        plugin_id: str,
        config: Dict,
        event_bus: RabbitMQEventBus,
    ):
        metadata = PluginMetadata(
            name="Eufy Security (Bridge)",
            version="0.2.0",
            plugin_type=PluginType.DEVICE,
            description="Eufy Security cameras and sensors via Node.js bridge",
            capabilities=["cameras", "sensors", "motion_detection", "person_detection"],
        )

        super().__init__(plugin_id, metadata, config, event_bus)

        # Bridge connection details
        self.bridge_url = os.getenv("EUFY_BRIDGE_URL", "http://eufy-bridge:3000")
        self.bridge_ws_url = os.getenv("EUFY_BRIDGE_WS_URL", "ws://eufy-bridge:3001")

        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._ws_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize the Eufy plugin."""
        self._logger.info(f"Initializing Eufy Bridge plugin")
        self._logger.info(f"Bridge URL: {self.bridge_url}")

        # Create aiohttp session
        self.session = aiohttp.ClientSession()

        # Check bridge health
        try:
            async with self.session.get(f"{self.bridge_url}/health") as resp:
                health = await resp.json()
                self._logger.info(f"Bridge health: {health}")
                if health['status'] != 'ok':
                    raise RuntimeError("Eufy bridge not healthy")
        except Exception as e:
            self._logger.error(f"Failed to connect to Eufy bridge: {e}")
            raise

        self._logger.info("Eufy Bridge plugin initialized")

    async def discover_devices(self) -> List[Device]:
        """Discover Eufy devices via bridge."""
        if not self.session:
            raise RuntimeError("Session not initialized")

        self._logger.info("Discovering Eufy devices via bridge...")

        discovered_devices = []

        try:
            # Get devices from bridge
            async with self.session.get(f"{self.bridge_url}/devices") as resp:
                data = await resp.json()
                devices = data.get('devices', [])

                self._logger.info(f"Found {len(devices)} Eufy devices")

                for device_data in devices:
                    try:
                        # Create wrapper device
                        device = self._create_device(device_data)

                        if device:
                            # Refresh state to populate initial data
                            await device.refresh_state()

                            discovered_devices.append(device)
                            self._logger.info(
                                f"Discovered: {device_data['name']} ({device_data['serial']})"
                            )

                    except Exception as e:
                        self._logger.error(f"Error processing device {device_data.get('name')}: {e}")

            # Get stations
            async with self.session.get(f"{self.bridge_url}/stations") as resp:
                data = await resp.json()
                stations = data.get('stations', [])
                self._logger.info(f"Found {len(stations)} Eufy stations")

        except Exception as e:
            self._logger.error(f"Discovery error: {e}", exc_info=True)

        self._logger.info(f"Discovered {len(discovered_devices)} Eufy devices total")
        return discovered_devices

    def _create_device(self, device_data: Dict) -> Optional[Device]:
        """Create appropriate device wrapper based on device type."""
        device_type = device_data.get('type', 0)

        # Eufy device type codes:
        # 1 = Station
        # 2 = Entry/Door Sensor (T8900)
        # 7, 8, 9 = Cameras (various models)
        # 10 = Motion Sensor (T8910)
        # 30-39 = Doorbells (various models)
        # 90+ = Cameras (advanced models, e.g., 104 = SoloCam S40)

        # Cameras and Doorbells
        if device_type in [7, 8, 9, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39] or device_type >= 90:
            return EufyCamera(device_data, self.plugin_id, self.event_bus)

        # Sensors (Entry/Door sensors and Motion sensors)
        elif device_type in [2, 10]:
            return EufySensor(device_data, self.plugin_id, self.event_bus)

        else:
            self._logger.warning(f"Unknown Eufy device type: {device_type}")
            return None

    async def start(self) -> None:
        """Start the Eufy plugin."""
        await super().start()

        # Start WebSocket event monitoring
        self._ws_task = asyncio.create_task(self._monitor_events())

    async def stop(self) -> None:
        """Stop the Eufy plugin."""
        # Stop WebSocket monitoring
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket
        if self.ws:
            await self.ws.close()
            self.ws = None

        # Close aiohttp session
        if self.session:
            await self.session.close()
            self.session = None

        await super().stop()

    async def _monitor_events(self) -> None:
        """Monitor Eufy events via WebSocket."""
        retry_delay = 5

        while True:
            try:
                self._logger.info(f"Connecting to Eufy bridge WebSocket: {self.bridge_ws_url}")

                async with websockets.connect(self.bridge_ws_url) as ws:
                    self.ws = ws
                    self._logger.info("Connected to Eufy bridge WebSocket")

                    async for message in ws:
                        try:
                            event = json.loads(message)
                            self._logger.info(f"WebSocket event received: {event}")
                            await self._handle_event(event)
                        except Exception as e:
                            self._logger.error(f"Error processing event: {e}", exc_info=True)

            except asyncio.CancelledError:
                self._logger.debug("Event monitoring cancelled")
                raise
            except Exception as e:
                self._logger.error(f"WebSocket error: {e}")
                self._logger.info(f"Reconnecting in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)  # Exponential backoff up to 60s

    async def _handle_event(self, event: Dict) -> None:
        """Handle events from Eufy bridge."""
        event_type = event.get('type')

        if event_type == 'connected':
            self._logger.info("Eufy bridge connected event")

        elif event_type == 'disconnected':
            self._logger.warning("Eufy bridge disconnected event")

        elif event_type == 'motion_detected':
            serial = event.get('serial')
            device = self.devices.get(serial)
            if device:
                await device.update_state({"motion": True})
                self._logger.info(f"Motion detected: {device.info.name} ({serial})")
                # Publish system event for UI notification
                await self.event_bus.publish_system_event({
                    'type': 'sensor.motion_detected',
                    'device_id': serial,
                    'device_name': device.info.name,
                    'timestamp': event.get('timestamp')
                })

        elif event_type == 'person_detected':
            serial = event.get('serial')
            device = self.devices.get(serial)
            if device:
                await device.update_state({"motion": True, "custom": {"person": True}})
                self._logger.info(f"Person detected: {device.info.name} ({serial})")
                await self.event_bus.publish_system_event({
                    'type': 'sensor.person_detected',
                    'device_id': serial,
                    'device_name': device.info.name,
                    'timestamp': event.get('timestamp')
                })

        elif event_type == 'device_added':
            device_data = event.get('device')
            if device_data:
                self._logger.info(f"New device added: {device_data.get('name')}")

        elif event_type == 'station_added':
            station_data = event.get('station')
            if station_data:
                self._logger.info(f"New station added: {station_data.get('name')}")

        elif event_type == 'station_guard_mode':
            # Guard mode changed event
            serial = event.get('serialNumber') or event.get('serial')
            current_mode = event.get('currentMode') or event.get('mode')
            if serial and current_mode is not None:
                self._logger.info(f"Guard mode changed for station {serial}: {current_mode}")
                # Publish system event for guard mode change
                await self.event_bus.publish_system_event({
                    'type': 'station.guard_mode_changed',
                    'station_serial': serial,
                    'guard_mode': current_mode,
                    'timestamp': event.get('timestamp')
                })

        elif event_type == 'station_current_mode':
            # Alternative event name for mode changes
            serial = event.get('serialNumber') or event.get('serial')
            current_mode = event.get('currentMode') or event.get('mode')
            if serial and current_mode is not None:
                self._logger.info(f"Station current mode for {serial}: {current_mode}")
                await self.event_bus.publish_system_event({
                    'type': 'station.guard_mode_changed',
                    'station_serial': serial,
                    'guard_mode': current_mode,
                    'timestamp': event.get('timestamp')
                })

        elif event_type == 'property_changed':
            # Handle device property changes (battery, contact, etc.)
            serial = event.get('serialNumber')
            name = event.get('name')
            value = event.get('value')

            device = self.devices.get(serial)
            if device:
                self._logger.debug(f"Property changed for {serial}: {name} = {value}")

                # Map property names to state fields
                if name == 'batteryLevel':
                    await device.update_state({"battery": value})
                    self._logger.info(f"Battery level changed: {device.info.name} = {value}%")
                elif name == 'motionDetected':
                    await device.update_state({"motion": value})
                    if value:  # Motion detected
                        self._logger.info(f"Motion detected (property): {device.info.name}")
                        await self.event_bus.publish_system_event({
                            'type': 'sensor.motion_detected',
                            'device_id': serial,
                            'device_name': device.info.name,
                            'timestamp': event.get('timestamp')
                        })
                elif name == 'sensorOpen':
                    await device.update_state({"contact": value})
                    status = "opened" if value else "closed"
                    self._logger.info(f"Door sensor {status}: {device.info.name}")
                    await self.event_bus.publish_system_event({
                        'type': f'sensor.door_{status}',
                        'device_id': serial,
                        'device_name': device.info.name,
                        'is_open': value,
                        'timestamp': event.get('timestamp')
                    })
                elif name == 'enabled':
                    await device.update_state({"online": value})

        else:
            self._logger.info(f"Unhandled event type: {event_type}, event: {event}")

    async def get_stations(self) -> List[Dict]:
        """Get list of stations from bridge."""
        try:
            async with self.session.get(f"{self.bridge_url}/stations") as resp:
                data = await resp.json()
                return data.get('stations', [])
        except Exception as e:
            self._logger.error(f"Error getting stations: {e}", exc_info=True)
            return []

    async def set_guard_mode(self, serial: str, mode: int) -> bool:
        """Set station guard mode."""
        try:
            async with self.session.post(
                f"{self.bridge_url}/stations/{serial}/guard-mode",
                json={"mode": mode}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._logger.info(f"Guard mode changed to {mode} for station {serial}")
                    return data.get('success', False)
                else:
                    self._logger.error(f"Failed to set guard mode: HTTP {resp.status}")
                    return False
        except Exception as e:
            self._logger.error(f"Error setting guard mode: {e}", exc_info=True)
            return False
