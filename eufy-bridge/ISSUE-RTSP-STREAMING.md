# Issue: Eufy Camera RTSP Streaming Fails with FFmpeg

## Summary
FFmpeg cannot connect to Eufy Indoor Cam S350 (T8416) RTSP stream at `rtsp://192.168.86.205/live0`, despite successfully enabling RTSP via eufy-security-client and receiving the stream URL. Error: "No route to host" when FFmpeg attempts connection.

## Environment
- **Camera Model**: Eufy Indoor Cam S350 (T8416P1024190F98)
- **Camera IP**: 192.168.86.205
- **RTSP Port**: 554
- **eufy-security-client**: v3.6.0
- **FFmpeg**: v8.0.1
- **Node.js**: v23.4.0
- **Platform**: macOS (Darwin 25.1.0)
- **Network**: Local LAN (192.168.86.x/24)

## Current Implementation

### What Works
1. ✅ Eufy cloud connection successful
2. ✅ Device discovery and enumeration
3. ✅ RTSP enablement via `eufyClient.setDeviceProperty(serial, PropertyName.DeviceRTSPStream, true)`
4. ✅ RTSP URL received via `station rtsp url` event: `rtsp://192.168.86.205/live0`
5. ✅ Basic TCP connectivity to camera port 554 (verified with `nc -zv 192.168.86.205 554`)
6. ✅ Camera is pingable with 0% packet loss

### What Fails
❌ FFmpeg cannot establish RTSP connection to the camera

## Error Details

### FFmpeg Error Output
```
[tcp @ 0x9a0c4c000] Connection to tcp://192.168.86.205:554?timeout=0 failed: No route to host
[in#0 @ 0x9a1038000] Error opening input: No route to host
Error opening input file rtsp://192.168.86.205/live0.
Error opening input files: No route to host
```

### FFmpeg Command Tested
```bash
# TCP transport
ffmpeg -rtsp_transport tcp -i rtsp://192.168.86.205/live0 -t 5 -f null -

# UDP transport
ffmpeg -rtsp_transport udp -i rtsp://192.168.86.205/live0 -t 5 -f null -
```

Both fail with identical "No route to host" error.

### Network Connectivity Tests
```bash
# Ping test - SUCCESS
$ ping -c 3 192.168.86.205
3 packets transmitted, 3 packets received, 0.0% packet loss

# Port 554 connectivity - SUCCESS
$ nc -zv 192.168.86.205 554
Connection to 192.168.86.205 port 554 [tcp/rtsp] succeeded!

# FFmpeg connection - FAIL
$ ffmpeg -rtsp_transport tcp -i rtsp://192.168.86.205/live0 -f null -
Error: No route to host
```

## Investigation Results

### 1. Docker Networking
**Initial Issue**: Docker container on bridge network couldn't reach LAN camera
**Resolution**: Moved eufy-bridge to host networking (`network_mode: host`)
**Result**: Still fails even on macOS host

### 2. Firewall Rules
**Checked**: macOS packet filter (PF) and application firewall
**Result**: No blocking rules found for camera IP or FFmpeg

### 3. RTSP Server Accessibility
**Observation**: While `nc` can establish TCP connection to port 554, FFmpeg's RTSP client cannot
**Hypothesis**: Camera's RTSP server may have client authentication or restrictions

### 4. eufy-security-client Events
Successfully captured these events:
- ✅ `station rtsp url` - Fires with RTSP URL
- ✅ `station command result` - RTSP enable command successful
- ❌ No errors or warnings from eufy-security-client

## Code Implementation

### Current server.js Implementation
```javascript
// Enable RTSP
await eufyClient.setDeviceProperty(deviceSerial, PropertyName.DeviceRTSPStream, true);
await new Promise(resolve => setTimeout(resolve, 3000));

// RTSP URL is captured via event listener
eufyClient.on('station rtsp url', (station, channel, rtspUrl) => {
    const deviceSerial = findDeviceByChannel(station, channel);
    if (deviceSerial) {
        streamUrls.set(deviceSerial, rtspUrl);
        console.log(`RTSP URL: ${rtspUrl}`);
    }
});

// Attempt FFmpeg transcoding
const ffmpeg = spawn('ffmpeg', [
    '-rtsp_transport', 'tcp',
    '-i', rtspUrl,  // rtsp://192.168.86.205/live0
    '-c:v', 'libx264',
    '-preset', 'ultrafast',
    '-tune', 'zerolatency',
    '-b:v', '2M',
    '-f', 'hls',
    '-hls_time', '2',
    '-hls_list_size', '3',
    '-hls_flags', 'delete_segments+append_list',
    '-hls_segment_filename', path.join(deviceDir, 'segment%03d.ts'),
    playlistPath
]);
```

### Log Output
```
Attempting to enable RTSP for T8416P1024190F98
Event emitted: station rtsp url
[MANUAL HANDLER] RTSP URL: rtsp://192.168.86.205/live0
Found camera device: T8416P1024190F98 (type 104) for station T8030P13233230A6
[MANUAL] Stored URL for T8416P1024190F98
RTSP URL from property: rtsp://192.168.86.205/live0
Starting FFmpeg transcoding for T8416P1024190F98: rtsp://192.168.86.205/live0 -> /tmp/hls/T8416P1024190F98/stream.m3u8
[FFmpeg T8416P1024190F98] [tcp @ 0x9a0c4c000] Connection to tcp://192.168.86.205:554?timeout=0 failed: No route to host
FFmpeg process exited with code 191
```

## Root Cause Analysis

### Likely Causes (in order of probability)

1. **RTSP Authentication Required**
   - Camera's RTSP server may require username/password
   - eufy-security-client doesn't provide credentials in RTSP URL
   - FFmpeg needs authentication parameters

2. **Client Whitelist/Restrictions**
   - Eufy camera RTSP server may only accept connections from:
     - Eufy app clients
     - Specific user agents
     - Authenticated sessions
   - FFmpeg's RTSP client might be rejected

3. **RTSP Server Not Fully Enabled**
   - `PropertyName.DeviceRTSPStream` may not fully enable the server
   - Additional configuration needed through Eufy app
   - Feature may be partially implemented in firmware

4. **Network Security Policy**
   - macOS may have undocumented network security features
   - Camera may have firewall rules for RTSP connections
   - Some network-level restriction blocking RTSP protocol

### Less Likely Causes
- ❌ Docker networking issues (tested on host)
- ❌ Firewall blocking (PF rules checked)
- ❌ Camera unreachable (ping/nc work)
- ❌ Port blocked (nc connects successfully)

## Attempted Solutions

1. ✅ Moved from Docker bridge to host networking
2. ✅ Ran eufy-bridge natively on macOS (outside Docker)
3. ✅ Installed FFmpeg v8.0.1 with full codec support
4. ✅ Tried both TCP and UDP RTSP transport
5. ✅ Checked firewall and packet filter rules
6. ✅ Verified camera reachability and port accessibility
7. ❌ None successful

## Recommended Solutions

### Option 1: P2P Streaming (Recommended)
Use eufy-security-client's native P2P streaming instead of RTSP.

**Advantages:**
- Officially supported by eufy-security-client
- No network/firewall issues
- Works for all Eufy camera models
- Provides video/audio as Node.js Readable streams

**Implementation:**
```javascript
// Listen for P2P livestream event
eufyClient.on('station livestream start', (station, device, metadata, videostream, audiostream) => {
    // Pipe streams to FFmpeg stdin
    const ffmpeg = spawn('ffmpeg', [
        '-f', 'h264',           // Input format from videostream
        '-i', 'pipe:0',         // Video from stdin
        '-c:v', 'copy',         // Copy video codec
        '-f', 'hls',
        '-hls_time', '2',
        '-hls_list_size', '3',
        playlistPath
    ]);

    videostream.pipe(ffmpeg.stdin);
});

// Start P2P livestream
await eufyClient.startStationLivestream(deviceSerial);
```

**Required Changes:**
- Add `station livestream start` event handler
- Pipe video/audio streams to FFmpeg stdin
- Update FFmpeg arguments for piped input
- Handle stream cleanup on stop

### Option 2: Investigate RTSP Authentication
Try adding authentication to FFmpeg RTSP URL.

**Test Commands:**
```bash
# Try default Eufy credentials
ffmpeg -i rtsp://admin:admin@192.168.86.205/live0 -f null -

# Try with RTSP-specific options
ffmpeg -rtsp_flags prefer_tcp -i rtsp://192.168.86.205/live0 -f null -

# Try with longer timeout
ffmpeg -timeout 30000000 -i rtsp://192.168.86.205/live0 -f null -
```

### Option 3: Use Snapshot Fallback
If live streaming isn't critical, use snapshot functionality.

**Implementation:**
```javascript
// Get snapshot via eufy-security-client
const snapshotBuffer = await device.getPictureBuffer();

// Serve as image endpoint
app.get('/devices/:serial/snapshot', async (req, res) => {
    const device = devices.get(req.params.serial);
    const buffer = await device.getPictureBuffer();
    res.setHeader('Content-Type', 'image/jpeg');
    res.send(buffer);
});
```

### Option 4: Enable RTSP via Eufy App
Check if RTSP needs additional enablement through official Eufy Security app.

**Steps to Test:**
1. Open Eufy Security app
2. Navigate to T8416 camera settings
3. Look for RTSP server or streaming settings
4. Enable any RTSP-related options
5. Note any credentials displayed
6. Test FFmpeg with credentials

## Additional Information

### Camera Type Details
- **Device Type**: 104 (Camera, not sensor)
- **Model**: T8416 (Indoor Cam S350)
- **Capabilities**: Motion detection, person detection, video streaming
- **RTSP Support**: Added in eufy-security-client v3.1.1

### eufy-security-client Events Available
```javascript
// P2P streaming events
'station livestream start'  // (station, device, metadata, videostream, audiostream)
'station livestream stop'   // (station, device)

// RTSP events
'station rtsp url'          // (station, channel, rtspUrl)
'station rtsp livestream start'   // (station, device)
'station rtsp livestream stop'    // (station, device)

// Other useful events
'station command result'    // (station, result)
```

### Network Topology
```
Internet
    |
Eufy Cloud
    |
[eufy-bridge (macOS host)]
    |
Local Network (192.168.86.x/24)
    |
[Camera: 192.168.86.205:554]
```

## Questions for Further Investigation

1. Does the Eufy app show RTSP settings for T8416?
2. Are RTSP credentials required? If so, where are they stored?
3. Does the camera's RTSP server require specific RTSP client headers?
4. Is RTSP fully supported on T8416, or is it a limited implementation?
5. Can VLC or another RTSP client connect to `rtsp://192.168.86.205/live0`?

## References

- eufy-security-client: https://github.com/bropat/eufy-security-client
- RTSP support added in v3.1.1: https://github.com/bropat/eufy-security-client/blob/master/CHANGELOG.md
- T8416 Indoor Cam S350: https://us.eufy.com/products/t8416123

## Next Steps

1. **Immediate**: Test RTSP connection with VLC or other RTSP client
2. **Short-term**: Implement P2P streaming as primary solution
3. **Long-term**: Contact Eufy or eufy-security-client maintainers about RTSP accessibility

## Timeline

- **2026-01-01**: Discovered RTSP URL is provided but FFmpeg cannot connect
- **2026-01-01**: Tested on Docker bridge network → failed
- **2026-01-01**: Changed to host networking → still failed
- **2026-01-01**: Moved to native macOS execution → still failed
- **2026-01-01**: Verified network connectivity, firewall rules → no issues found
- **2026-01-01**: Identified P2P streaming as recommended alternative

## Labels
`bug`, `eufy-bridge`, `video-streaming`, `rtsp`, `network`, `help-wanted`

## Priority
High - Blocking video streaming feature implementation
