"""Server-Sent Events (SSE) endpoints for real-time updates."""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Query, Request
from sse_starlette.sse import EventSourceResponse

from maneyantra.core.manager import PluginManager
from maneyantra.core.rabbitmq_bus import RabbitMQEventBus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

# Global references (set by app.py)
plugin_manager: Optional[PluginManager] = None
event_bus: Optional[RabbitMQEventBus] = None


def set_plugin_manager(manager: PluginManager):
    """Set the plugin manager reference."""
    global plugin_manager
    plugin_manager = manager


def set_event_bus(bus: RabbitMQEventBus):
    """Set the event bus reference."""
    global event_bus
    event_bus = bus


@router.get("/stream")
async def event_stream(
    request: Request,
    device_id: Optional[str] = Query(None, description="Filter by specific device ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type (state, discovery, error)"),
):
    """
    Server-Sent Events stream for real-time device updates.

    Subscribe to receive live updates when device states change.

    Event types:
    - state: Device state updates
    - discovery: New device discoveries
    - available: Device availability changes
    - error: Device errors
    - system: System events

    Example usage (JavaScript):
    ```javascript
    const eventSource = new EventSource('/api/v1/events/stream');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Device update:', data);
    };
    ```
    """
    if not event_bus:
        async def error_generator():
            yield {
                "event": "error",
                "data": json.dumps({"error": "Event bus not initialized"}),
            }
        return EventSourceResponse(error_generator())

    async def event_generator():
        """Generate SSE events from RabbitMQ messages."""
        # Create a queue to receive events
        event_queue = asyncio.Queue()

        # Define message handler
        async def message_handler(topic: str, payload: Dict[str, Any]):
            """Handle incoming RabbitMQ messages and queue them for SSE."""
            try:
                # Parse the topic to determine event type
                parts = topic.split(".")

                # Determine event category
                if "device" in parts:
                    if "state" in parts:
                        msg_event_type = "state"
                        msg_device_id = parts[2] if len(parts) > 2 else None
                    elif "discovery" in parts:
                        msg_event_type = "discovery"
                        msg_device_id = parts[2] if len(parts) > 2 else None
                    elif "available" in parts:
                        msg_event_type = "available"
                        msg_device_id = parts[1] if len(parts) > 1 else None
                    elif "error" in parts:
                        msg_event_type = "error"
                        msg_device_id = parts[1] if len(parts) > 1 else None
                    else:
                        msg_event_type = "device"
                        msg_device_id = parts[1] if len(parts) > 1 else None
                elif "system" in parts:
                    msg_event_type = "system"
                    msg_device_id = None
                else:
                    msg_event_type = "unknown"
                    msg_device_id = None

                # Apply filters
                if device_id and msg_device_id != device_id:
                    return

                if event_type and msg_event_type != event_type:
                    return

                # Queue the event
                event_data = {
                    "topic": topic,
                    "type": msg_event_type,
                    "device_id": msg_device_id,
                    "data": payload,
                    "timestamp": payload.get("timestamp") if isinstance(payload, dict) else None,
                }

                await event_queue.put(event_data)

            except Exception as e:
                logger.error(f"Error processing message for SSE: {e}", exc_info=True)

        try:
            # Subscribe to all device events
            await event_bus.subscribe("device.#", message_handler)
            await event_bus.subscribe("system.#", message_handler)

            # Send initial connection event
            yield {
                "event": "connected",
                "data": json.dumps({
                    "message": "Connected to ManeYantra event stream",
                    "filters": {
                        "device_id": device_id,
                        "event_type": event_type,
                    }
                }),
            }

            # Stream events
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info("SSE client disconnected")
                    break

                try:
                    # Wait for event with timeout
                    event_data = await asyncio.wait_for(
                        event_queue.get(),
                        timeout=30.0  # Send heartbeat every 30s if no events
                    )

                    yield {
                        "event": event_data["type"],
                        "data": json.dumps(event_data),
                    }

                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"timestamp": asyncio.get_event_loop().time()}),
                    }

        except asyncio.CancelledError:
            logger.info("SSE stream cancelled")
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_generator())


@router.get("/devices/{device_id}/stream")
async def device_event_stream(
    request: Request,
    device_id: str,
):
    """
    SSE stream for a specific device.

    Convenience endpoint for subscribing to a single device's updates.
    """
    # Reuse the main stream with device_id filter
    return await event_stream(request, device_id=device_id)
