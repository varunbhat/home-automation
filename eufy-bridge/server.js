#!/usr/bin/env node

/**
 * Eufy Security Bridge Server
 * Wraps eufy-security-client and exposes HTTP + WebSocket API for Python integration
 */

const express = require('express');
const WebSocket = require('ws');
const { EufySecurity } = require('eufy-security-client');
require('dotenv').config();

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3000;
const WS_PORT = process.env.WS_PORT || 3001;

// Eufy client instance
let eufyClient = null;
let devices = new Map();
let stations = new Map();

// WebSocket clients for event streaming
const wsClients = new Set();

/**
 * Initialize Eufy Security client
 */
async function initializeEufy() {
    const username = process.env.EUFY_USERNAME;
    const password = process.env.EUFY_PASSWORD;
    const country = process.env.EUFY_COUNTRY || 'US';

    if (!username || !password) {
        throw new Error('EUFY_USERNAME and EUFY_PASSWORD must be set');
    }

    console.log(`Initializing Eufy Security client for ${username}...`);

    eufyClient = await EufySecurity.initialize({
        username,
        password,
        country,
        trustedDeviceName: 'ManeYantra',
        p2pConnectionSetup: 2, // Quickest connection
        pollingIntervalMinutes: 10,
        eventDurationSeconds: 10,
    });

    // Set up event listeners
    setupEventListeners();

    // Connect to stations (devices will be discovered via events)
    await eufyClient.connect();

    console.log('Eufy Security client initialized successfully');
}

/**
 * Setup Eufy event listeners
 */
function setupEventListeners() {
    // Device added
    eufyClient.on('device added', (device) => {
        const serial = device.getSerial();
        const name = device.getName();
        console.log(`Device added: ${name} (${serial})`);
        devices.set(serial, device);
        console.log(`Devices Map now has ${devices.size} devices`);
        broadcastEvent({
            type: 'device_added',
            device: serializeDevice(device)
        });
    });

    // Station added
    eufyClient.on('station added', (station) => {
        console.log(`Station added: ${station.getName()} (${station.getSerial()})`);
        stations.set(station.getSerial(), station);
        broadcastEvent({
            type: 'station_added',
            station: serializeStation(station)
        });
    });

    // Motion detected
    eufyClient.on('device motion detected', (device, state) => {
        console.log(`Motion detected: ${device.getName()}`);
        broadcastEvent({
            type: 'motion_detected',
            serial: device.getSerial(),
            state
        });
    });

    // Person detected
    eufyClient.on('device person detected', (device, state, person) => {
        console.log(`Person detected: ${device.getName()}`);
        broadcastEvent({
            type: 'person_detected',
            serial: device.getSerial(),
            state,
            person
        });
    });

    // Connection events
    eufyClient.on('connect', () => {
        console.log('Connected to Eufy cloud');
        broadcastEvent({ type: 'connected' });
    });

    eufyClient.on('close', () => {
        console.log('Disconnected from Eufy cloud');
        broadcastEvent({ type: 'disconnected' });
    });
}

/**
 * Serialize device for API response
 */
function serializeDevice(device) {
    try {
        return {
            serial: device.getSerial?.() || 'unknown',
            name: device.getName?.() || 'Unknown Device',
            model: device.getModel?.() || 'unknown',
            type: device.getDeviceType?.() || 0,
            station_serial: device.getStationSerial?.() || 'unknown',
            battery: device.getBatteryValue?.() || 0,
            state: {
                enabled: device.isEnabled?.() || false,
                motion_detected: device.isMotionDetected?.() || false,
            }
        };
    } catch (error) {
        console.error('Error serializing device:', error);
        return {
            serial: 'error',
            name: 'Error',
            model: 'error',
            type: 0,
            station_serial: 'error',
            battery: 0,
            state: { enabled: false, motion_detected: false }
        };
    }
}

/**
 * Serialize station for API response
 */
function serializeStation(station) {
    return {
        serial: station.getSerial(),
        name: station.getName(),
        model: station.getModel(),
        guard_mode: station.getGuardMode(),
    };
}

/**
 * Broadcast event to all WebSocket clients
 */
function broadcastEvent(event) {
    const message = JSON.stringify(event);
    wsClients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(message);
        }
    });
}

// ============================================================================
// HTTP API Routes
// ============================================================================

/**
 * Health check
 */
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        connected: eufyClient ? eufyClient.isConnected() : false,
        devices: devices.size,
        stations: stations.size
    });
});

/**
 * Get all devices
 */
app.get('/devices', (req, res) => {
    try {
        const deviceList = Array.from(devices.values()).map(serializeDevice);
        console.log(`/devices endpoint called - returning ${deviceList.length} devices`);
        res.json({ devices: deviceList });
    } catch (error) {
        console.error('Error in /devices endpoint:', error);
        res.status(500).json({ error: error.message });
    }
});

/**
 * Get specific device
 */
app.get('/devices/:serial', (req, res) => {
    const device = devices.get(req.params.serial);
    if (!device) {
        return res.status(404).json({ error: 'Device not found' });
    }
    res.json(serializeDevice(device));
});

/**
 * Get all stations
 */
app.get('/stations', (req, res) => {
    try {
        const stationList = Array.from(stations.values()).map(serializeStation);
        console.log(`/stations endpoint called - returning ${stationList.length} stations`);
        res.json({ stations: stationList });
    } catch (error) {
        console.error('Error in /stations endpoint:', error);
        res.status(500).json({ error: error.message });
    }
});

/**
 * Control device
 */
app.post('/devices/:serial/command', async (req, res) => {
    const device = devices.get(req.params.serial);
    if (!device) {
        return res.status(404).json({ error: 'Device not found' });
    }

    const { command, params = {} } = req.body;

    try {
        switch (command) {
            case 'enable':
                await device.setEnabled(true);
                break;
            case 'disable':
                await device.setEnabled(false);
                break;
            case 'start_stream':
                const streamUrl = await device.startStream();
                return res.json({ stream_url: streamUrl });
            case 'stop_stream':
                await device.stopStream();
                break;
            default:
                return res.status(400).json({ error: `Unknown command: ${command}` });
        }
        res.json({ success: true });
    } catch (error) {
        console.error(`Command error:`, error);
        res.status(500).json({ error: error.message });
    }
});

/**
 * Set station guard mode
 */
app.post('/stations/:serial/guard-mode', async (req, res) => {
    const station = stations.get(req.params.serial);
    if (!station) {
        return res.status(404).json({ error: 'Station not found' });
    }

    const { mode } = req.body;

    try {
        await station.setGuardMode(mode);
        res.json({ success: true, mode });
    } catch (error) {
        console.error(`Guard mode error:`, error);
        res.status(500).json({ error: error.message });
    }
});

// ============================================================================
// WebSocket Server for Events
// ============================================================================

const wss = new WebSocket.Server({ port: WS_PORT });

wss.on('connection', (ws) => {
    console.log('WebSocket client connected');
    wsClients.add(ws);

    // Send current state on connection
    ws.send(JSON.stringify({
        type: 'connected',
        devices: Array.from(devices.values()).map(serializeDevice),
        stations: Array.from(stations.values()).map(serializeStation)
    }));

    ws.on('close', () => {
        console.log('WebSocket client disconnected');
        wsClients.delete(ws);
    });

    ws.on('error', (error) => {
        console.error('WebSocket error:', error);
        wsClients.delete(ws);
    });
});

// ============================================================================
// Startup
// ============================================================================

async function start() {
    try {
        // Initialize Eufy client
        await initializeEufy();

        // Start HTTP server
        app.listen(PORT, () => {
            console.log(`Eufy Bridge HTTP API listening on port ${PORT}`);
        });

        console.log(`Eufy Bridge WebSocket server listening on port ${WS_PORT}`);
        console.log('Eufy Bridge ready!');

    } catch (error) {
        console.error('Failed to start Eufy Bridge:', error);
        process.exit(1);
    }
}

// Handle shutdown gracefully
process.on('SIGTERM', async () => {
    console.log('Shutting down...');
    if (eufyClient) {
        await eufyClient.close();
    }
    process.exit(0);
});

process.on('SIGINT', async () => {
    console.log('Shutting down...');
    if (eufyClient) {
        await eufyClient.close();
    }
    process.exit(0);
});

// Start the server
start();
