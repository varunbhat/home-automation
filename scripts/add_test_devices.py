#!/usr/bin/env python3
"""Add test devices to ManeYantra for UI testing."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from maneyantra.core.rabbitmq_bus import RabbitMQEventBus
from maneyantra.types.devices import DeviceInfo, DeviceState, DeviceType, DeviceCapability


async def add_test_devices():
    """Add test devices via RabbitMQ event bus."""

    # Connect to RabbitMQ
    event_bus = RabbitMQEventBus(
        host="localhost",
        port=5672,
        username="maneyantra",
        password="XVHpJplmBHEsGGY84QGEdvbx1SxbEZrU",
        vhost="/",
    )

    print("Connecting to RabbitMQ...")
    await event_bus.connect()
    print("Connected!")

    # Test devices
    test_light_1 = {
        "info": DeviceInfo(
                id="test-light-1",
                name="Living Room Light",
                type=DeviceType.LIGHT,
                capabilities=[
                    DeviceCapability.ON_OFF,
                    DeviceCapability.BRIGHTNESS,
                    DeviceCapability.COLOR,
                ],
                manufacturer="Philips",
                model="Hue A19",
                plugin_id="test",
                room="Living Room",
                tags=["smart", "rgb"],
            ),
            state=DeviceState(
                online=True,
                on=True,
                brightness=75,
                color={"hue": 210, "saturation": 80, "value": 75},
            ),
        ),
        Device(
            info=DeviceInfo(
                id="test-light-2",
                name="Bedroom Light",
                type=DeviceType.LIGHT,
                capabilities=[
                    DeviceCapability.ON_OFF,
                    DeviceCapability.BRIGHTNESS,
                    DeviceCapability.COLOR_TEMPERATURE,
                ],
                manufacturer="IKEA",
                model="Tradfri E27",
                plugin_id="test",
                room="Bedroom",
                tags=["smart"],
            ),
            state=DeviceState(
                online=True,
                on=False,
                brightness=50,
                color_temperature=4000,
            ),
        ),
        Device(
            info=DeviceInfo(
                id="test-switch-1",
                name="Kitchen Switch",
                type=DeviceType.SWITCH,
                capabilities=[DeviceCapability.ON_OFF],
                manufacturer="TP-Link",
                model="HS200",
                plugin_id="test",
                room="Kitchen",
            ),
            state=DeviceState(
                online=True,
                on=True,
            ),
        ),
        Device(
            info=DeviceInfo(
                id="test-sensor-1",
                name="Living Room Sensor",
                type=DeviceType.SENSOR,
                capabilities=[
                    DeviceCapability.TEMPERATURE,
                    DeviceCapability.HUMIDITY,
                    DeviceCapability.BATTERY,
                ],
                manufacturer="Aqara",
                model="Temperature & Humidity Sensor",
                plugin_id="test",
                room="Living Room",
            ),
            state=DeviceState(
                online=True,
                temperature=22.5,
                humidity=45,
                battery=87,
            ),
        ),
        Device(
            info=DeviceInfo(
                id="test-camera-1",
                name="Front Door Camera",
                type=DeviceType.CAMERA,
                capabilities=[
                    DeviceCapability.VIDEO_STREAM,
                    DeviceCapability.MOTION_DETECTION,
                    DeviceCapability.PERSON_DETECTION,
                ],
                manufacturer="Eufy",
                model="2C Pro",
                plugin_id="test",
                room="Entrance",
                tags=["security"],
            ),
            state=DeviceState(
                online=True,
                motion=False,
                battery=65,
            ),
        ),
        Device(
            info=DeviceInfo(
                id="test-plug-1",
                name="Coffee Maker Plug",
                type=DeviceType.PLUG,
                capabilities=[
                    DeviceCapability.ON_OFF,
                    DeviceCapability.POWER_MONITORING,
                    DeviceCapability.ENERGY_MONITORING,
                ],
                manufacturer="TP-Link",
                model="HS110",
                plugin_id="test",
                room="Kitchen",
            ),
            state=DeviceState(
                online=True,
                on=False,
                power=0.0,
                energy=12.5,
                voltage=120.2,
                current=0.0,
            ),
        ),
    ]

    # Publish discovery events for each device
    for device in devices:
        print(f"Adding device: {device.info.name} ({device.info.id})")
        await event_bus.publish_device_discovery(device)

    print(f"\n✅ Added {len(devices)} test devices!")
    print("Check the frontend at http://localhost:5173/")

    await event_bus.disconnect()


if __name__ == "__main__":
    asyncio.run(add_test_devices())
