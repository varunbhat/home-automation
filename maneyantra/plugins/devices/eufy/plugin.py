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
        device_type = str(device_data.get('type', '')).lower()

        if "camera" in device_type or "doorbell" in device_type:
            return EufyCamera(device_data, self.plugin_id, self.event_bus, self.session, self.bridge_url)

        elif "sensor" in device_type or "motion" in device_type:
            return EufySensor(device_data, self.plugin_id, self.event_bus, self.session, self.bridge_url)

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
                self._logger.debug(f"Motion detected: {serial}")

        elif event_type == 'person_detected':
            serial = event.get('serial')
            device = self.devices.get(serial)
            if device:
                await device.update_state({"motion": True, "custom": {"person": True}})
                self._logger.debug(f"Person detected: {serial}")

        elif event_type == 'device_added':
            device_data = event.get('device')
            if device_data:
                self._logger.info(f"New device added: {device_data.get('name')}")

        elif event_type == 'station_added':
            station_data = event.get('station')
            if station_data:
                self._logger.info(f"New station added: {station_data.get('name')}")

        else:
            self._logger.debug(f"Unhandled event type: {event_type}")
