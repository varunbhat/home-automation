#!/usr/bin/env node

/**
 * Eufy Security Bridge Server
 * Wraps eufy-security-client and exposes HTTP + WebSocket API for Python integration
 */

const express = require('express');
const WebSocket = require('ws');
const { EufySecurity, PropertyName } = require('eufy-security-client');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
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
let streamUrls = new Map(); // Map of device serial -> stream URL
let ffmpegProcesses = new Map(); // Map of device serial -> ffmpeg process
let activeP2PStreams = new Map(); // Map of device serial -> {ffmpeg, videostream, audiostream, metadata}

// WebSocket clients for event streaming
const wsClients = new Set();

// CAPTCHA handling
let pendingCaptcha = null;

// HLS stream directory
const HLS_DIR = '/tmp/hls';
if (!fs.existsSync(HLS_DIR)) {
    fs.mkdirSync(HLS_DIR, { recursive: true });
}

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

    // RTSP Livestream events - eufyClient emits "station <event>" format
    eufyClient.on('station rtsp url', (station, channel, rtspUrl) => {
        console.log(`[EVENT: station rtsp url] Station: ${station.getSerial()}, Channel: ${JSON.stringify(channel)}, URL: ${rtspUrl}`);
        // Find device by channel (channel typically maps to device)
        const deviceSerial = findDeviceByChannel(station, channel);
        console.log(`Mapped to device serial: ${deviceSerial}`);
        if (deviceSerial) {
            streamUrls.set(deviceSerial, rtspUrl);
            console.log(`Stream URL stored for ${deviceSerial}: ${rtspUrl}`);
            console.log(`streamUrls Map now has ${streamUrls.size} entries`);
            broadcastEvent({
                type: 'stream_started',
                serial: deviceSerial,
                stream_url: rtspUrl
            });
        } else {
            console.log(`WARNING: Could not find device for station ${station.getSerial()}, channel ${JSON.stringify(channel)}`);
        }
    });

    eufyClient.on('station rtsp livestream started', (station, channel) => {
        console.log(`[EVENT: station rtsp livestream started] Station: ${station.getSerial()}, Channel: ${channel}`);
    });

    eufyClient.on('station rtsp livestream stopped', (station, channel) => {
        console.log(`[EVENT: station rtsp livestream stopped] Station: ${station.getSerial()}, Channel: ${channel}`);
        const deviceSerial = findDeviceByChannel(station, channel);
        if (deviceSerial) {
            streamUrls.delete(deviceSerial);
            broadcastEvent({
                type: 'stream_stopped',
                serial: deviceSerial
            });
        }
    });

    // P2P Livestream event handlers
    eufyClient.on('station livestream start', (station, device, metadata, videostream, audiostream) => {
        const deviceSerial = device.getSerial();
        console.log(`[P2P] Livestream started for ${deviceSerial}:`, metadata);
        console.log(`[P2P] Video: ${metadata.videoWidth}x${metadata.videoHeight} @ ${metadata.videoFPS}fps, codec ${metadata.videoCodec}`);
        console.log(`[P2P] Audio: codec ${metadata.audioCodec}`);

        // Start FFmpeg transcoding from P2P streams
        try {
            startP2PTranscoding(deviceSerial, metadata, videostream, audiostream);

            broadcastEvent({
                type: 'p2p_stream_started',
                serial: deviceSerial,
                metadata
            });
        } catch (err) {
            console.error(`[P2P] Failed to start transcoding for ${deviceSerial}:`, err);
        }
    });

    eufyClient.on('station livestream stop', (station, device) => {
        const deviceSerial = device.getSerial();
        console.log(`[P2P] Livestream stopped for ${deviceSerial}`);

        stopP2PTranscoding(deviceSerial);

        broadcastEvent({
            type: 'p2p_stream_stopped',
            serial: deviceSerial
        });
    });

    // Add listener for ALL events to debug AND manually handle events if needed
    const originalEmit = eufyClient.emit;
    eufyClient.emit = function(eventName, ...args) {
        console.log(`Event emitted: ${eventName}`);

        // Manually handle station rtsp url event if the normal listener doesn't work
        if (eventName === 'station rtsp url' && args.length >= 3) {
            const station = args[0];
            const channel = args[1];
            const rtspUrl = args[2];
            console.log(`[MANUAL HANDLER] RTSP URL: ${rtspUrl}`);
            const deviceSerial = findDeviceByChannel(station, channel);
            if (deviceSerial) {
                streamUrls.set(deviceSerial, rtspUrl);
                console.log(`[MANUAL] Stored URL for ${deviceSerial}`);
            }
        }

        // Manually handle P2P livestream start event if normal listener doesn't work
        if (eventName === 'station livestream start' && args.length >= 5) {
            const station = args[0];
            const device = args[1];
            const metadata = args[2];
            const videostream = args[3];
            const audiostream = args[4];

            const deviceSerial = device.getSerial();
            console.log(`[MANUAL P2P] Livestream started for ${deviceSerial}:`, metadata);

            try {
                startP2PTranscoding(deviceSerial, metadata, videostream, audiostream);
                broadcastEvent({
                    type: 'p2p_stream_started',
                    serial: deviceSerial,
                    metadata
                });
            } catch (err) {
                console.error(`[MANUAL P2P] Failed to start transcoding for ${deviceSerial}:`, err);
            }
        }

        return originalEmit.apply(this, [eventName, ...args]);
    };
}

/**
 * Find device serial by station channel
 */
function findDeviceByChannel(station, channel) {
    // Iterate through devices to find CAMERA belonging to this station
    // Cameras typically have type 104, 106, etc. (not sensors which are type 11, 12, etc.)
    for (const [serial, device] of devices) {
        if (device.getStationSerial() === station.getSerial()) {
            const deviceType = device.getDeviceType();
            // Camera types are typically >= 100
            if (deviceType >= 100) {
                console.log(`Found camera device: ${serial} (type ${deviceType}) for station ${station.getSerial()}`);
                return serial;
            }
        }
    }
    // Fallback to first device if no camera found
    for (const [serial, device] of devices) {
        if (device.getStationSerial() === station.getSerial()) {
            console.log(`Fallback: Using first device ${serial} for station ${station.getSerial()}`);
            return serial;
        }
    }
    return null;
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
            case 'enable_rtsp':
                // Enable RTSP stream on the device
                console.log(`Enabling RTSP for device ${req.params.serial}`);
                await eufyClient.setDeviceProperty(req.params.serial, PropertyName.DeviceRTSPStream, true);
                // Wait a bit for the property to be applied
                await new Promise(resolve => setTimeout(resolve, 2000));
                break;
            case 'start_stream':
                // Use P2P livestreaming instead of RTSP
                console.log(`[P2P] Starting livestream for ${req.params.serial}`);

                try {
                    // Start P2P livestream - the event handler will start FFmpeg transcoding
                    await eufyClient.startStationLivestream(req.params.serial);

                    // Wait for P2P stream to start and HLS segments to be created
                    console.log(`[P2P] Waiting for stream to start...`);
                    for (let i = 0; i < 30; i++) {
                        if (activeP2PStreams.has(req.params.serial)) {
                            console.log(`[P2P] Stream active, checking for HLS playlist...`);

                            // Check if HLS playlist exists
                            const playlistPath = path.join(HLS_DIR, req.params.serial, 'stream.m3u8');
                            if (fs.existsSync(playlistPath)) {
                                const hlsUrl = `http://localhost:${PORT}/hls/${req.params.serial}/stream.m3u8`;
                                console.log(`[P2P] HLS playlist ready: ${hlsUrl}`);
                                return res.json({ stream_url: hlsUrl });
                            }
                        }
                        await new Promise(resolve => setTimeout(resolve, 200));
                    }

                    // Stream started but HLS not ready yet - return URL anyway
                    const hlsUrl = `http://localhost:${PORT}/hls/${req.params.serial}/stream.m3u8`;
                    console.log(`[P2P] Returning HLS URL (may take a moment to be ready): ${hlsUrl}`);
                    return res.json({ stream_url: hlsUrl });

                } catch (err) {
                    console.error(`[P2P] Failed to start livestream:`, err);
                    throw new Error(`Failed to start P2P livestream: ${err.message}`);
                }
            case 'stop_stream':
                // Stop P2P livestream (this will trigger the event handler to cleanup)
                console.log(`[P2P] Stopping livestream for ${req.params.serial}`);
                try {
                    await eufyClient.stopStationLivestream(req.params.serial);
                    // Also manually cleanup in case event doesn't fire
                    stopP2PTranscoding(req.params.serial);
                } catch (err) {
                    console.error(`[P2P] Error stopping stream:`, err.message);
                    // Force cleanup even if stop fails
                    stopP2PTranscoding(req.params.serial);
                }
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
 * Get device snapshot
 */
app.get('/devices/:serial/snapshot', async (req, res) => {
    try {
        if (!eufyClient) {
            return res.status(503).json({ error: 'Eufy client not initialized' });
        }

        const device = devices.get(req.params.serial);

        if (!device) {
            return res.status(404).json({ error: 'Device not found' });
        }

        const snapshotBuffer = await device.getPictureBuffer();

        res.setHeader('Content-Type', 'image/jpeg');
        res.setHeader('Cache-Control', 'no-cache');
        res.send(snapshotBuffer);
    } catch (error) {
        console.error(`Snapshot error:`, error);
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
// HLS Transcoding Functions
// ============================================================================

/**
 * Start FFmpeg transcoding from RTSP to HLS
 */
async function startHLSTranscoding(deviceSerial, rtspUrl) {
    // Stop existing process if any
    stopHLSTranscoding(deviceSerial);

    const deviceDir = path.join(HLS_DIR, deviceSerial);
    if (!fs.existsSync(deviceDir)) {
        fs.mkdirSync(deviceDir, { recursive: true });
    }

    const playlistPath = path.join(deviceDir, 'stream.m3u8');

    console.log(`Starting FFmpeg transcoding for ${deviceSerial}: ${rtspUrl} -> ${playlistPath}`);

    const ffmpeg = spawn('ffmpeg', [
        '-rtsp_transport', 'tcp',
        '-i', rtspUrl,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-tune', 'zerolatency',
        '-b:v', '2M',
        '-maxrate', '2M',
        '-bufsize', '4M',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-f', 'hls',
        '-hls_time', '2',
        '-hls_list_size', '3',
        '-hls_flags', 'delete_segments+append_list',
        '-hls_segment_filename', path.join(deviceDir, 'segment%03d.ts'),
        playlistPath
    ]);

    ffmpegProcesses.set(deviceSerial, ffmpeg);

    ffmpeg.stdout.on('data', (data) => {
        console.log(`[FFmpeg ${deviceSerial}] ${data}`);
    });

    ffmpeg.stderr.on('data', (data) => {
        console.log(`[FFmpeg ${deviceSerial}] ${data}`);
    });

    ffmpeg.on('close', (code) => {
        console.log(`FFmpeg process for ${deviceSerial} exited with code ${code}`);
        ffmpegProcesses.delete(deviceSerial);
    });

    // Wait a bit for FFmpeg to start generating segments
    await new Promise(resolve => setTimeout(resolve, 3000));
}

/**
 * Stop FFmpeg transcoding
 */
function stopHLSTranscoding(deviceSerial) {
    const ffmpeg = ffmpegProcesses.get(deviceSerial);
    if (ffmpeg) {
        console.log(`Stopping FFmpeg transcoding for ${deviceSerial}`);
        ffmpeg.kill('SIGTERM');
        ffmpegProcesses.delete(deviceSerial);

        // Clean up HLS files
        const deviceDir = path.join(HLS_DIR, deviceSerial);
        if (fs.existsSync(deviceDir)) {
            fs.rmSync(deviceDir, { recursive: true, force: true });
        }
    }
}

/**
 * Start FFmpeg transcoding from P2P video/audio streams to HLS
 */
function startP2PTranscoding(deviceSerial, metadata, videostream, audiostream) {
    // Stop existing transcoding if any
    stopP2PTranscoding(deviceSerial);

    const deviceDir = path.join(HLS_DIR, deviceSerial);
    if (!fs.existsSync(deviceDir)) {
        fs.mkdirSync(deviceDir, { recursive: true });
    }

    const playlistPath = path.join(deviceDir, 'stream.m3u8');

    console.log(`[P2P] Starting FFmpeg transcoding for ${deviceSerial} -> ${playlistPath}`);

    // Video codec mapping: 0 = H.264, 1 = H.265
    const videoFormat = metadata.videoCodec === 0 ? 'h264' : 'h264';

    // Build FFmpeg arguments for piped input
    const ffmpegArgs = [
        // Input format and settings
        '-f', videoFormat,
        '-r', String(metadata.videoFPS || 15),
        '-s', `${metadata.videoWidth}x${metadata.videoHeight}`,
        '-i', 'pipe:0',         // Video from stdin

        // Video encoding - copy to avoid re-encoding (faster, less CPU)
        '-c:v', 'copy',

        // HLS output settings
        '-f', 'hls',
        '-hls_time', '2',                                    // 2 second segments
        '-hls_list_size', '3',                               // Keep last 3 segments
        '-hls_flags', 'delete_segments+append_list',         // Auto-cleanup old segments
        '-hls_segment_filename', path.join(deviceDir, 'segment%03d.ts'),
        playlistPath
    ];

    console.log(`[P2P] FFmpeg command: ffmpeg ${ffmpegArgs.join(' ')}`);

    const ffmpeg = spawn('ffmpeg', ffmpegArgs);

    // Pipe video stream to FFmpeg stdin
    videostream.pipe(ffmpeg.stdin);

    // Handle video stream errors
    videostream.on('error', (err) => {
        console.error(`[P2P] Video stream error for ${deviceSerial}:`, err.message);
    });

    // Handle FFmpeg stdout
    ffmpeg.stdout.on('data', (data) => {
        console.log(`[P2P FFmpeg ${deviceSerial}] ${data}`);
    });

    // Handle FFmpeg stderr (progress info)
    ffmpeg.stderr.on('data', (data) => {
        const output = data.toString();
        // Only log errors and important messages, not every frame
        if (output.includes('error') || output.includes('Error') || output.includes('failed')) {
            console.error(`[P2P FFmpeg ${deviceSerial}] ${output}`);
        }
    });

    // Handle FFmpeg exit
    ffmpeg.on('close', (code) => {
        console.log(`[P2P] FFmpeg process for ${deviceSerial} exited with code ${code}`);
        ffmpegProcesses.delete(deviceSerial);
        activeP2PStreams.delete(deviceSerial);
    });

    ffmpeg.on('error', (err) => {
        console.error(`[P2P] FFmpeg error for ${deviceSerial}:`, err.message);
        ffmpegProcesses.delete(deviceSerial);
        activeP2PStreams.delete(deviceSerial);
    });

    // Store process and stream info
    ffmpegProcesses.set(deviceSerial, ffmpeg);
    activeP2PStreams.set(deviceSerial, {
        ffmpeg,
        videostream,
        audiostream,
        metadata
    });

    console.log(`[P2P] Transcoding started for ${deviceSerial}`);
}

/**
 * Stop P2P transcoding and cleanup
 */
function stopP2PTranscoding(deviceSerial) {
    const streamInfo = activeP2PStreams.get(deviceSerial);
    if (streamInfo) {
        console.log(`[P2P] Stopping transcoding for ${deviceSerial}`);

        // Kill FFmpeg process
        if (streamInfo.ffmpeg) {
            streamInfo.ffmpeg.kill('SIGTERM');
        }

        // Unpipe and destroy streams
        if (streamInfo.videostream) {
            streamInfo.videostream.unpipe();
            streamInfo.videostream.destroy();
        }
        if (streamInfo.audiostream) {
            streamInfo.audiostream.unpipe();
            streamInfo.audiostream.destroy();
        }

        activeP2PStreams.delete(deviceSerial);
    }

    // Also remove from ffmpegProcesses map
    const ffmpeg = ffmpegProcesses.get(deviceSerial);
    if (ffmpeg && !streamInfo) {
        ffmpeg.kill('SIGTERM');
        ffmpegProcesses.delete(deviceSerial);
    }

    // Clean up HLS files
    const deviceDir = path.join(HLS_DIR, deviceSerial);
    if (fs.existsSync(deviceDir)) {
        fs.rmSync(deviceDir, { recursive: true, force: true });
    }

    console.log(`[P2P] Transcoding stopped and cleaned up for ${deviceSerial}`);
}

/**
 * Serve HLS streams
 */
app.use('/hls', express.static(HLS_DIR));

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
