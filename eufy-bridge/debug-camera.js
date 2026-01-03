#!/usr/bin/env node

/**
 * Eufy Camera Debug & Verification Script
 * Tests all camera capabilities and documents what works
 */

const { EufySecurity, PropertyName } = require('eufy-security-client');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

const DEBUG_DIR = '/tmp/eufy-debug';
if (!fs.existsSync(DEBUG_DIR)) {
    fs.mkdirSync(DEBUG_DIR, { recursive: true });
}

const results = {
    timestamp: new Date().toISOString(),
    environment: {
        node_version: process.version,
        platform: process.platform,
        arch: process.arch
    },
    tests: []
};

function log(message) {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] ${message}`);
}

function addResult(test, success, details) {
    results.tests.push({
        test,
        success,
        details,
        timestamp: new Date().toISOString()
    });
    log(`${success ? '✅' : '❌'} ${test}: ${JSON.stringify(details)}`);
}

async function main() {
    log('Starting Eufy Camera Debug & Verification');

    const username = process.env.EUFY_USERNAME;
    const password = process.env.EUFY_PASSWORD;
    const country = process.env.EUFY_COUNTRY || 'US';

    if (!username || !password) {
        console.error('❌ Missing EUFY_USERNAME or EUFY_PASSWORD');
        process.exit(1);
    }

    log(`Initializing Eufy Security client for ${username}`);

    const eufyClient = await EufySecurity.initialize({
        username,
        password,
        country,
        trustedDeviceName: 'eufy-debug',
        persistentDir: path.join(DEBUG_DIR, 'data'),
        pollingIntervalMinutes: 0, // Disable polling for debug
    });

    addResult('Eufy Client Initialization', true, { username, country });

    // Test 1: Connect to Eufy cloud
    log('Test 1: Connecting to Eufy cloud...');
    try {
        await eufyClient.connect();
        addResult('Eufy Cloud Connection', true, { connected: true });
    } catch (err) {
        addResult('Eufy Cloud Connection', false, { error: err.message });
        process.exit(1);
    }

    // Wait for devices to load
    await new Promise(resolve => setTimeout(resolve, 5000));

    // Test 2: Enumerate devices
    log('Test 2: Enumerating devices...');
    const stationsMap = await eufyClient.getStations();
    const devicesMap = await eufyClient.getDevices();
    const stations = Array.from(stationsMap.values());
    const devices = Array.from(devicesMap.values());

    addResult('Device Enumeration', true, {
        station_count: stations.length,
        device_count: devices.length
    });

    // Find camera device (type >= 100)
    let camera = null;
    for (const device of devices) {
        const deviceType = device.getDeviceType();
        if (deviceType >= 100) {
            camera = device;
            log(`Found camera: ${device.getName()} (${device.getSerial()}), type: ${deviceType}`);
            break;
        }
    }

    if (!camera) {
        addResult('Find Camera Device', false, { error: 'No camera found' });
        await eufyClient.close();
        saveResults();
        process.exit(1);
    }

    const cameraSerial = camera.getSerial();
    const cameraName = camera.getName();
    const cameraType = camera.getDeviceType();
    const cameraModel = camera.getModel();

    addResult('Find Camera Device', true, {
        serial: cameraSerial,
        name: cameraName,
        type: cameraType,
        model: cameraModel
    });

    // Test 3: Get camera properties
    log('Test 3: Reading camera properties...');
    const properties = camera.getProperties();
    const propertyList = {};
    for (const [key, value] of Object.entries(properties)) {
        propertyList[key] = {
            value: value.value,
            timestamp: value.timestamp
        };
    }

    addResult('Camera Properties', true, {
        property_count: Object.keys(properties).length,
        has_rtsp_property: properties.hasOwnProperty(PropertyName.DeviceRTSPStream),
        rtsp_enabled: properties[PropertyName.DeviceRTSPStream]?.value
    });

    // Save all properties to file
    fs.writeFileSync(
        path.join(DEBUG_DIR, 'camera-properties.json'),
        JSON.stringify(propertyList, null, 2)
    );
    log(`Saved camera properties to ${DEBUG_DIR}/camera-properties.json`);

    // Test 4: Get snapshot
    log('Test 4: Capturing snapshot...');
    try {
        const snapshotBuffer = await camera.getPictureBuffer();
        const snapshotPath = path.join(DEBUG_DIR, 'snapshot.jpg');
        fs.writeFileSync(snapshotPath, snapshotBuffer);

        addResult('Snapshot Capture', true, {
            size_bytes: snapshotBuffer.length,
            path: snapshotPath
        });
    } catch (err) {
        addResult('Snapshot Capture', false, { error: err.message });
    }

    // Test 5: Enable RTSP
    log('Test 5: Enabling RTSP stream...');
    let rtspUrl = null;
    let rtspUrlReceived = false;

    // Listen for RTSP URL event
    const rtspUrlPromise = new Promise((resolve) => {
        const timeout = setTimeout(() => resolve(null), 10000);

        eufyClient.on('station rtsp url', (station, channel, url) => {
            log(`Received RTSP URL event: ${url}`);
            clearTimeout(timeout);
            rtspUrl = url;
            rtspUrlReceived = true;
            resolve(url);
        });
    });

    try {
        await eufyClient.setDeviceProperty(cameraSerial, PropertyName.DeviceRTSPStream, true);
        await new Promise(resolve => setTimeout(resolve, 3000));

        // Wait for RTSP URL event
        await rtspUrlPromise;

        if (rtspUrlReceived && rtspUrl) {
            addResult('RTSP Enable', true, { rtsp_url: rtspUrl });
        } else {
            addResult('RTSP Enable', false, { error: 'No RTSP URL received' });
        }
    } catch (err) {
        addResult('RTSP Enable', false, { error: err.message });
    }

    // Test 6: Test RTSP connectivity (if URL received)
    if (rtspUrl) {
        log('Test 6: Testing RTSP connectivity...');

        // Extract IP and port from RTSP URL
        const rtspMatch = rtspUrl.match(/rtsp:\/\/([^:\/]+):?(\d+)?/);
        if (rtspMatch) {
            const rtspHost = rtspMatch[1];
            const rtspPort = rtspMatch[2] || '554';

            // Test with netcat
            const ncTest = await new Promise((resolve) => {
                const nc = spawn('nc', ['-zv', rtspHost, rtspPort]);
                let output = '';

                nc.stderr.on('data', (data) => {
                    output += data.toString();
                });

                nc.on('close', (code) => {
                    resolve({
                        success: code === 0,
                        output: output.trim()
                    });
                });

                setTimeout(() => {
                    nc.kill();
                    resolve({ success: false, output: 'Timeout' });
                }, 5000);
            });

            addResult('RTSP Port Connectivity (netcat)', ncTest.success, {
                host: rtspHost,
                port: rtspPort,
                output: ncTest.output
            });

            // Test with FFmpeg
            const ffmpegTest = await new Promise((resolve) => {
                const ffmpeg = spawn('ffmpeg', [
                    '-rtsp_transport', 'tcp',
                    '-i', rtspUrl,
                    '-t', '3',
                    '-f', 'null',
                    '-'
                ]);

                let output = '';
                let errorOutput = '';

                ffmpeg.stdout.on('data', (data) => {
                    output += data.toString();
                });

                ffmpeg.stderr.on('data', (data) => {
                    errorOutput += data.toString();
                });

                ffmpeg.on('close', (code) => {
                    resolve({
                        success: code === 0,
                        exit_code: code,
                        output: errorOutput.slice(-500) // Last 500 chars
                    });
                });

                setTimeout(() => {
                    ffmpeg.kill('SIGKILL');
                    resolve({
                        success: false,
                        exit_code: -1,
                        output: 'Timeout after 10s'
                    });
                }, 10000);
            });

            addResult('RTSP Stream (FFmpeg)', ffmpegTest.success, {
                rtsp_url: rtspUrl,
                exit_code: ffmpegTest.exit_code,
                error_output: ffmpegTest.output
            });
        }
    }

    // Test 7: Start P2P livestream
    log('Test 7: Testing P2P livestream...');
    let p2pStreamStarted = false;
    let p2pStreamData = null;

    const p2pPromise = new Promise((resolve) => {
        const timeout = setTimeout(() => resolve(null), 15000);

        eufyClient.on('station livestream start', (station, device, metadata, videostream, audiostream) => {
            log(`P2P livestream started! Metadata: ${JSON.stringify(metadata)}`);
            clearTimeout(timeout);
            p2pStreamStarted = true;

            let videoChunks = 0;
            let audioChunks = 0;
            let videoBytes = 0;
            let audioBytes = 0;

            videostream.on('data', (chunk) => {
                videoChunks++;
                videoBytes += chunk.length;
                if (videoChunks === 1) {
                    log(`Received first video chunk: ${chunk.length} bytes`);
                }
            });

            audiostream.on('data', (chunk) => {
                audioChunks++;
                audioBytes += chunk.length;
                if (audioChunks === 1) {
                    log(`Received first audio chunk: ${chunk.length} bytes`);
                }
            });

            // Collect data for 5 seconds
            setTimeout(() => {
                p2pStreamData = {
                    metadata,
                    video_chunks: videoChunks,
                    audio_chunks: audioChunks,
                    video_bytes: videoBytes,
                    audio_bytes: audioBytes
                };

                // Stop stream
                eufyClient.stopStationLivestream(device.getSerial()).catch(err => {
                    log(`Error stopping stream: ${err.message}`);
                });

                resolve(p2pStreamData);
            }, 5000);
        });

        eufyClient.on('station livestream stop', (station, device) => {
            log('P2P livestream stopped');
        });
    });

    try {
        await eufyClient.startStationLivestream(cameraSerial);
        const streamData = await p2pPromise;

        if (streamData) {
            addResult('P2P Livestream', true, streamData);
        } else {
            addResult('P2P Livestream', false, { error: 'Timeout - no stream data received' });
        }
    } catch (err) {
        addResult('P2P Livestream', false, { error: err.message });
    }

    // Test 8: List available commands/methods
    log('Test 8: Checking available camera commands...');
    const commands = camera.getCommands();
    addResult('Available Commands', true, {
        command_count: commands.length,
        commands: commands.map(c => c.name || c)
    });

    // Test 9: Check station info
    log('Test 9: Getting station information...');
    try {
        const station = stations.find(s => s.getSerial() === camera.getStationSerial());
        if (station) {
            addResult('Station Info', true, {
                serial: station.getSerial(),
                name: station.getName(),
                model: station.getModel(),
                ip_address: station.getIPAddress(),
                lan_ip: station.getLANIPAddress()
            });
        } else {
            addResult('Station Info', false, { error: 'Station not found' });
        }
    } catch (err) {
        addResult('Station Info', false, { error: err.message });
    }

    // Cleanup
    log('Cleaning up...');
    try {
        await eufyClient.stopStationLivestream(cameraSerial);
    } catch (err) {
        // Ignore
    }

    await eufyClient.close();

    // Save results
    saveResults();

    log('Debug complete!');
    printSummary();
}

function saveResults() {
    const resultsPath = path.join(DEBUG_DIR, 'debug-results.json');
    fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2));
    log(`Results saved to: ${resultsPath}`);
}

function printSummary() {
    console.log('\n' + '='.repeat(80));
    console.log('DEBUG SUMMARY');
    console.log('='.repeat(80));

    const passed = results.tests.filter(t => t.success).length;
    const failed = results.tests.filter(t => !t.success).length;

    console.log(`Total Tests: ${results.tests.length}`);
    console.log(`✅ Passed: ${passed}`);
    console.log(`❌ Failed: ${failed}`);
    console.log('='.repeat(80));

    console.log('\nTest Results:');
    results.tests.forEach((test, idx) => {
        const icon = test.success ? '✅' : '❌';
        console.log(`${idx + 1}. ${icon} ${test.test}`);
        if (!test.success && test.details.error) {
            console.log(`   Error: ${test.details.error}`);
        }
    });

    console.log('\n' + '='.repeat(80));
    console.log(`Full results: ${DEBUG_DIR}/debug-results.json`);
    console.log(`Camera properties: ${DEBUG_DIR}/camera-properties.json`);
    console.log(`Snapshot: ${DEBUG_DIR}/snapshot.jpg`);
    console.log('='.repeat(80) + '\n');
}

// Run
main().catch(err => {
    console.error('Fatal error:', err);
    saveResults();
    process.exit(1);
});
