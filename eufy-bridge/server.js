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
app.use(express.urlencoded({ extended: true })); // Parse form data

const PORT = process.env.PORT || 3000;
const WS_PORT = process.env.WS_PORT || 3001;

// Eufy client instance
let eufyClient = null;
let devices = new Map();
let stations = new Map();

// WebSocket clients for event streaming
const wsClients = new Set();

// CAPTCHA handling
let pendingCaptcha = null;

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

    console.log(`Initializing Eufy Security client for ${username} (country: ${country})...`);

    eufyClient = await EufySecurity.initialize({
        username,
        password,
        country,
        trustedDeviceName: 'ManeYantra',
        persistentDir: './data',  // Store trusted device token to avoid CAPTCHA
        p2pConnectionSetup: 2, // Quickest connection
        pollingIntervalMinutes: 10,
        eventDurationSeconds: 10,
    });

    console.log('EufySecurity object created');

    // Set up event listeners
    setupEventListeners();

    // Connect to stations - don't wait for it to complete
    console.log('Starting eufy client connection...');
    eufyClient.connect().then(() => {
        console.log('Eufy client connect() completed');
    }).catch((error) => {
        console.error('Error during connect():', error);
    });

    console.log('Eufy Security client initialized successfully');
}

/**
 * Setup Eufy event listeners
 */
function setupEventListeners() {
    // Devices loaded - triggered when all devices are initially loaded
    eufyClient.on('devices loaded', () => {
        console.log('Devices loaded event received');
        eufyClient.getDevices().then((deviceList) => {
            console.log(`Loaded ${deviceList.length} devices`);
            deviceList.forEach(device => {
                const serial = device.getSerial();
                devices.set(serial, device);
                console.log(`  - ${device.getName()} (${serial})`);
            });
        }).catch(err => console.error('Error in devices loaded handler:', err));
    });

    // Stations loaded - triggered when all stations are initially loaded
    eufyClient.on('stations loaded', () => {
        console.log('Stations loaded event received');
        eufyClient.getStations().then((stationList) => {
            console.log(`Loaded ${stationList.length} stations`);
            stationList.forEach(station => {
                stations.set(station.getSerial(), station);
                console.log(`  - ${station.getName()} (${station.getSerial()})`);
            });
        }).catch(err => console.error('Error in stations loaded handler:', err));
    });

    // Device added
    eufyClient.on('device added', (device) => {
        const serial = device.getSerial();
        const name = device.getName();
        console.log(`Device added event: ${name} (${serial})`);
        devices.set(serial, device);
        broadcastEvent({
            type: 'device_added',
            device: serializeDevice(device)
        });
    });

    // Station added
    eufyClient.on('station added', (station) => {
        console.log(`Station added event: ${station.getName()} (${station.getSerial()})`);
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

    // Error events
    eufyClient.on('error', (error) => {
        console.error('Eufy client error:', error);
    });

    // CAPTCHA request handler
    eufyClient.on('captcha request', (id, captcha) => {
        console.log('CAPTCHA required for Eufy login!');
        console.log('CAPTCHA ID:', id);

        // Store pending captcha for web interface
        pendingCaptcha = {
            id: id,
            image: captcha,  // Base64 encoded image
            timestamp: Date.now()
        };

        console.log('CAPTCHA available at: http://localhost:3000/captcha');
        console.log('Submit solution to: POST http://localhost:3000/captcha/solve');
    });

    // 2FA request handler
    eufyClient.on('tfa request', () => {
        console.log('Two-factor authentication required');
        console.log('Please check your Eufy app for verification code');
    });

    // Add listener for ALL events to debug
    const originalEmit = eufyClient.emit;
    eufyClient.emit = function(eventName, ...args) {
        console.log(`Event emitted: ${eventName}`);
        return originalEmit.apply(this, [eventName, ...args]);
    };
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
app.get('/devices', async (req, res) => {
    try {
        if (!eufyClient) {
            console.log('/devices endpoint called - client not initialized');
            return res.json({ devices: [] });
        }

        // Use the devices Map populated by events (more reliable than getDevices())
        const deviceList = Array.from(devices.values()).map(device => serializeDevice(device));

        console.log(`/devices endpoint called - returning ${deviceList.length} devices from Map`);
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
    try {
        if (!eufyClient) {
            return res.status(503).json({ error: 'Eufy client not initialized' });
        }

        const device = devices.get(req.params.serial);

        if (!device) {
            return res.status(404).json({ error: 'Device not found' });
        }
        res.json(serializeDevice(device));
    } catch (error) {
        console.error('Error in /devices/:serial endpoint:', error);
        res.status(500).json({ error: error.message });
    }
});

/**
 * Get all stations
 */
app.get('/stations', async (req, res) => {
    try {
        if (!eufyClient) {
            console.log('/stations endpoint called - client not initialized');
            return res.json({ stations: [] });
        }

        // Use the stations Map populated by events (more reliable than getStations())
        const stationList = Array.from(stations.values()).map(station => serializeStation(station));

        console.log(`/stations endpoint called - returning ${stationList.length} stations from Map`);
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
    try {
        if (!eufyClient) {
            return res.status(503).json({ error: 'Eufy client not initialized' });
        }

        const device = devices.get(req.params.serial);

        if (!device) {
            return res.status(404).json({ error: 'Device not found' });
        }

        const { command, params = {} } = req.body;

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
    try {
        if (!eufyClient) {
            return res.status(503).json({ error: 'Eufy client not initialized' });
        }

        const station = stations.get(req.params.serial);

        if (!station) {
            return res.status(404).json({ error: 'Station not found' });
        }

        const { mode } = req.body;

        await station.setGuardMode(mode);
        res.json({ success: true, mode });
    } catch (error) {
        console.error(`Guard mode error:`, error);
        res.status(500).json({ error: error.message });
    }
});

/**
 * Get CAPTCHA challenge (if pending)
 */
app.get('/captcha', (req, res) => {
    if (!pendingCaptcha) {
        return res.send(`
            <html>
            <head><title>Eufy CAPTCHA</title></head>
            <body>
                <h1>No CAPTCHA pending</h1>
                <p>The bridge will request CAPTCHA if needed during login.</p>
                <p><a href="/health">Check bridge status</a></p>
            </body>
            </html>
        `);
    }

    // Check if the image already has the data URI prefix
    const imageData = pendingCaptcha.image.startsWith('data:')
        ? pendingCaptcha.image
        : `data:image/png;base64,${pendingCaptcha.image}`;

    res.send(`
        <html>
        <head>
            <title>Eufy CAPTCHA - Solve Challenge</title>
            <style>
                body { font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px; }
                img { border: 2px solid #ccc; margin: 20px 0; max-width: 100%; }
                input { font-size: 18px; padding: 10px; width: 200px; }
                button { font-size: 18px; padding: 10px 30px; background: #4CAF50; color: white; border: none; cursor: pointer; }
                button:hover { background: #45a049; }
            </style>
        </head>
        <body>
            <h1>Eufy CAPTCHA Challenge</h1>
            <p>Please enter the characters shown in the image below:</p>
            <img src="${imageData}" alt="CAPTCHA" />
            <form action="/captcha/solve" method="POST">
                <input type="text" name="code" placeholder="Enter CAPTCHA" required autofocus />
                <button type="submit">Submit</button>
            </form>
            <p><small>CAPTCHA ID: ${pendingCaptcha.id}</small></p>
        </body>
        </html>
    `);
});

/**
 * Submit CAPTCHA solution
 */
app.post('/captcha/solve', async (req, res) => {
    const { code } = req.body;

    if (!pendingCaptcha) {
        return res.status(400).json({ error: 'No pending CAPTCHA' });
    }

    if (!code) {
        return res.status(400).json({ error: 'CAPTCHA code is required' });
    }

    try {
        console.log(`Attempting to solve CAPTCHA ${pendingCaptcha.id} with code: ${code}`);

        // Re-login with CAPTCHA solution
        await eufyClient.connect({
            captcha: {
                captchaId: pendingCaptcha.id,
                captchaCode: code
            }
        });

        pendingCaptcha = null;

        res.send(`
            <html>
            <head>
                <title>CAPTCHA Submitted</title>
                <meta http-equiv="refresh" content="3;url=/health" />
            </head>
            <body>
                <h1>CAPTCHA Solution Submitted!</h1>
                <p>Reconnecting to Eufy...</p>
                <p>Redirecting to status page in 3 seconds...</p>
                <p><a href="/health">Check status now</a></p>
            </body>
            </html>
        `);
    } catch (error) {
        console.error('CAPTCHA solution error:', error);
        res.status(500).send(`
            <html>
            <head><title>CAPTCHA Error</title></head>
            <body>
                <h1>Error Solving CAPTCHA</h1>
                <p>${error.message}</p>
                <p><a href="/captcha">Try again</a></p>
            </body>
            </html>
        `);
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
