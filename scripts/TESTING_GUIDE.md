# ManeYantra Integration Testing Guide

## Architecture Overview

### Correct Connection Pattern

```
┌─────────────────────────────────────────────────────────────┐
│ Frontend (Browser/React)                                    │
│  - REST API calls (commands, queries)                       │
│  - SSE connection (real-time events)                        │
│  - NEVER connects to RabbitMQ directly                      │
└────────────────┬──────────────┬─────────────────────────────┘
                 │              │
                 │ HTTP/REST    │ SSE Stream
                 │              │
┌────────────────▼──────────────▼─────────────────────────────┐
│ Backend (FastAPI)                                           │
│  - REST API endpoints (/api/v1/devices, /health, etc.)     │
│  - SSE endpoint (/api/v1/events/stream)                    │
│  - RabbitMQ client (internal connection pool)              │
└────────────────────────────┬────────────────────────────────┘
                             │
                             │ AMQP Protocol
                             │ (Internal Only)
                             │
┌────────────────────────────▼────────────────────────────────┐
│ RabbitMQ Broker                                             │
│  - Topic exchange (maneyantra)                              │
│  - Message routing                                          │
│  - NOT exposed to frontend                                  │
└────────────────────────────┬────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
┌─────────────▼────┐ ┌──────▼──────┐ ┌────▼──────────┐
│ Plugin: TP-Link  │ │ Plugin:Eufy │ │ Plugin:Logger │
│  - Devices       │ │  - Cameras  │ │  - Events     │
└──────────────────┘ └─────────────┘ └───────────────┘
```

### Key Principles

1. **Frontend Isolation**: Frontend NEVER connects directly to RabbitMQ
2. **API Gateway**: All frontend communication goes through FastAPI
3. **Internal Messaging**: RabbitMQ is internal backend infrastructure
4. **Real-time via SSE**: Server-Sent Events for push notifications to frontend

## Test Scripts

### 1. SSE Connection Test (`test_sse_connection.py`)

Tests the frontend's SSE connection to the backend.

**Install dependencies:**
```bash
pip install httpx httpx-sse
```

**Basic usage:**
```bash
# Test SSE connection for 15 seconds
python scripts/test_sse_connection.py --duration 15

# Test with custom API URL
python scripts/test_sse_connection.py --url http://192.168.1.100:8000

# Test device-specific stream
python scripts/test_sse_connection.py --device-id device123

# Test filtered events
python scripts/test_sse_connection.py --event-type state
```

**What it tests:**
- SSE endpoint connectivity
- Event stream parsing
- Connected, heartbeat, state, error events
- Connection stability
- Event filtering

**Expected output:**
```
[HH:MM:SS] Testing SSE connection to http://localhost:8000
[HH:MM:SS] ✓ SSE connection established
[HH:MM:SS] ✓ Connected event received
[HH:MM:SS] ♥ Heartbeat received
[HH:MM:SS] 📊 State event received
```

### 2. RabbitMQ Connection Test (`test_rabbitmq_connection.py`)

Tests the backend's RabbitMQ connection (INTERNAL ONLY - not for frontend use).

**Install dependencies:**
```bash
pip install aio-pika
```

**Usage:**
```bash
# Test RabbitMQ connection
python scripts/test_rabbitmq_connection.py

# Custom connection
python scripts/test_rabbitmq_connection.py \
  --host localhost \
  --port 5672 \
  --username maneyantra \
  --password YOUR_PASSWORD
```

**What it tests:**
- RabbitMQ broker connectivity
- Channel creation and state
- Exchange declaration
- Queue binding with patterns
- Publish/subscribe operations
- Concurrent operations

**⚠️ Important:** This is for **backend testing only**. Frontend should NEVER use this.

### 3. End-to-End Integration Test (`test_e2e_integration.py`)

Tests the complete architecture from frontend perspective.

**Install dependencies:**
```bash
pip install httpx httpx-sse
```

**Usage:**
```bash
# Run full E2E test
python scripts/test_e2e_integration.py --duration 20

# Test against remote server
python scripts/test_e2e_integration.py \
  --api-url http://192.168.1.100:8000 \
  --duration 30
```

**What it tests:**
- Architecture isolation (frontend → API only)
- REST API endpoints (health, devices)
- SSE event stream
- Command flow (REST → RabbitMQ → Device)
- Event propagation (Device → RabbitMQ → SSE → Frontend)

**Expected output:**
```
Correct Architecture:
  Frontend (Browser)
      ↓ REST API
  Backend (FastAPI)
      ↓ RabbitMQ (INTERNAL)
  Plugins/Devices
      ↓ SSE Stream
  Frontend (Events)

✓ Architecture follows correct pattern
✓ Health endpoint working
✓ Devices endpoint working
✓ SSE stream working
✓ Event propagation working
```

## Common Integration Patterns

### Frontend: Subscribe to Events

**JavaScript/TypeScript:**
```typescript
const eventSource = new EventSource('http://localhost:8000/api/v1/events/stream');

eventSource.addEventListener('connected', (event) => {
  const data = JSON.parse(event.data);
  console.log('Connected:', data.message);
});

eventSource.addEventListener('state', (event) => {
  const data = JSON.parse(event.data);
  console.log('Device state:', data.device_id, data.data);
});

eventSource.addEventListener('heartbeat', (event) => {
  console.log('Heartbeat received');
});

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  // Implement reconnection with exponential backoff
};
```

### Frontend: Send Commands

**JavaScript/TypeScript:**
```typescript
async function controlDevice(deviceId: string, command: string) {
  const response = await fetch(
    `http://localhost:8000/api/v1/devices/${deviceId}/command`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command, params: {} })
    }
  );

  return await response.json();
}

// Turn on a device
await controlDevice('device123', 'turn_on');
```

### Backend: Publish to RabbitMQ (Internal)

**Python:**
```python
# In a plugin or backend service
await event_bus.publish_device_state(
    device_id="device123",
    state={"on": True, "brightness": 80}
)

# This will automatically propagate to SSE clients
```

## Troubleshooting

### Issue: "Connection refused" on SSE

**Check:**
1. Is ManeYantra backend running? (`ps aux | grep maneyantra`)
2. Is API accessible? (`curl http://localhost:8000/api/v1/health`)
3. Is firewall blocking connection?

**Fix:**
```bash
# Check backend status
curl http://localhost:8000/api/v1/health

# Start backend
python -m maneyantra.main
```

### Issue: "RabbitMQ channel not open"

**Check:**
1. Is RabbitMQ running? (`docker ps | grep rabbitmq`)
2. Are credentials correct in `.env`?
3. Is backend connected to RabbitMQ?

**Fix:**
```bash
# Start RabbitMQ
docker-compose up -d rabbitmq

# Check RabbitMQ management UI
open http://localhost:15672

# Run RabbitMQ connection test
python scripts/test_rabbitmq_connection.py
```

### Issue: "No events received" on SSE

**Possible causes:**
1. No devices active (normal - will only get heartbeats)
2. Plugins not loaded
3. RabbitMQ not bridging to SSE

**Debug:**
```bash
# Check devices
curl http://localhost:8000/api/v1/devices

# Check plugins
curl http://localhost:8000/api/v1/plugins

# Run E2E test
python scripts/test_e2e_integration.py --duration 30
```

### Issue: Frontend trying to connect to RabbitMQ directly

**This is WRONG!** Frontend should NEVER connect to RabbitMQ.

**Correct pattern:**
- Frontend → REST API (port 8000)
- Frontend → SSE Stream (port 8000)
- Backend → RabbitMQ (port 5672, internal only)

**If you see:**
- `amqp://` URLs in frontend code → ❌ WRONG
- `ws://localhost:5672` → ❌ WRONG
- Frontend importing `aio-pika` → ❌ WRONG

**Should be:**
- `http://localhost:8000/api/v1/*` → ✅ CORRECT
- `EventSource('/api/v1/events/stream')` → ✅ CORRECT

## Performance Testing

### Load Test SSE Connections

```bash
# Test with multiple concurrent SSE connections
for i in {1..10}; do
  python scripts/test_sse_connection.py --duration 60 &
done
wait

# Check backend can handle load
curl http://localhost:8000/api/v1/health
```

### Measure Event Latency

```python
# Add to test scripts
import time

start = time.time()
# Publish event via API
# Receive via SSE
latency = time.time() - start
print(f"Latency: {latency*1000:.2f}ms")
```

## Best Practices

1. **Always test E2E first** - Validates entire architecture
2. **Use SSE for real-time** - Don't poll REST API
3. **Frontend never touches RabbitMQ** - Use API gateway pattern
4. **Implement reconnection backoff** - Exponential delays (5s → 10s → 20s)
5. **Handle SSE errors gracefully** - Show user connection status
6. **Monitor connection count** - Backend should limit concurrent SSE clients
7. **Use heartbeats** - Keep connections alive, detect failures

## Debugging Tips

### Enable verbose logging

**Backend:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Frontend:**
```typescript
// Add detailed console logging
eventSource.addEventListener('message', (e) => {
  console.log('[SSE]', e.type, e.data);
});
```

### Monitor RabbitMQ

```bash
# Access management UI
open http://localhost:15672

# Check queue bindings
docker exec rabbitmq rabbitmqctl list_bindings

# Check active connections
docker exec rabbitmq rabbitmqctl list_connections
```

### Check network traffic

```bash
# Monitor HTTP requests
tcpdump -i any -A 'port 8000'

# Monitor RabbitMQ traffic (backend only)
tcpdump -i any -A 'port 5672'
```

## Summary

- ✅ Frontend → REST API + SSE
- ✅ Backend → RabbitMQ (internal)
- ❌ Frontend → RabbitMQ (NEVER!)

Use these test scripts to validate your integration and ensure proper architecture!
