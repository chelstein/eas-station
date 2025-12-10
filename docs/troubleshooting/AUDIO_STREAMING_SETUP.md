# Audio Streaming Troubleshooting Guide

## Quick Diagnostic Checklist

If you're seeing "Buffer Utilization 0.0% ⚠️ No data flowing" and audio won't play, follow these steps:

### 1. Check if Audio Sources are Configured

```sql
-- Connect to database

-- Check for configured sources
SELECT name, source_type, enabled, auto_start, priority 
FROM audio_source_configs;
```

**Expected Result**: At least one row with `enabled=true` and `auto_start=true`

**If empty**: You need to configure audio sources through the web UI at Settings → Audio Sources, or manually insert into database.

### 2. Check if Audio Service is Running

```bash
# Check container status

# Check logs
```

**Expected Logs**:
```
✅ Loaded environment from: /app-config/.env
Initializing audio controller...
Loading N audio source configurations from database
Auto-starting source: 'your-source-name'
✅ Successfully started 'your-source-name'
```

**If not running**: Start the audio-service container:
### 3. Check if SDR Service is Running (for SDR sources only)

```bash
# Check container status

# Check logs
```

**Expected Logs for SDR sources**:
```
🔗 Auto-discovering Redis SDR sources from sdr-service...
✅ Created Redis SDR source: redis-rtlsdr-noaa
Connected to Redis for receiver rtlsdr-00000001
Subscribed to Redis channel: sdr:samples:rtlsdr-00000001
✅ First audio chunk decoded for rtlsdr-00000001
```

**If not running**:
### 4. Check if Source is Started

In the web UI at Audio Monitoring page:
- Look for your audio source card
- Check if status shows "RUNNING" (green)
- If status is "STOPPED", click the Start button

### 5. Check Redis Connectivity

```bash
# Check if Redis is running

# Check if metrics are being published
redis-cli HGETALL eas:metrics

# For SDR sources, check if IQ samples are flowing
redis-cli PSUBSCRIBE 'sdr:samples:*'
# Wait 5 seconds - you should see messages if SDR is active
```

## Common Configuration Issues

### Issue: No Audio Sources in Database

**Symptom**: Database query returns empty result

**Solution**: Configure audio sources via web UI or SQL

#### Example: Add HTTP Stream Source

```sql
INSERT INTO audio_source_configs (
    name, 
    source_type, 
    enabled, 
    auto_start, 
    priority,
    config_params
) VALUES (
    'NOAA Weather Radio',
    'http_stream',
    true,
    true,
    100,
    '{"url": "https://stream.revma.ihrhls.com/zc1809", "sample_rate": 44100, "channels": 1}'::jsonb
);
```

#### Example: Add SDR Source

**Step 1**: Configure radio receiver
```sql
INSERT INTO radio_receivers (
    identifier, 
    frequency, 
    sample_rate, 
    modulation_type
) VALUES (
    'rtlsdr-00000001',
    162550000,  -- 162.550 MHz (NOAA Weather Radio)
    2500000,    -- 2.5 MHz IQ sample rate
    'NFM'       -- Narrow FM
);
```

**Step 2**: Create audio source linked to receiver
```sql
INSERT INTO audio_source_configs (
    name, 
    source_type, 
    enabled, 
    auto_start, 
    priority,
    config_params
) VALUES (
    'rtlsdr-noaa',
    'sdr',
    true,
    true,
    100,
    '{"sample_rate": 44100, "channels": 1, "device_params": {"receiver_id": "rtlsdr-00000001"}}'::jsonb
);
```

**Step 3**: Restart audio-service to pick up new configuration
### Issue: SDR Hardware Not Detected

**Symptom**: sdr-service logs show "No SDR devices found"

**Solution**:
1. Verify USB device is connected: `lsusb | grep RTL`
2. Check device permissions: `ls -la /dev/bus/usb`
   ```yaml
   devices:
     - /dev/bus/usb:/dev/bus/usb
   privileged: true
   ```

### Issue: Wrong Modulation Type

**Symptom**: Audio is garbled or silent even though source is running

**Solution**: Verify modulation type matches the broadcast:
- NOAA Weather Radio: **NFM** (Narrow FM)
- Commercial FM radio: **FM** (Wide FM)
- AM radio: **AM**

Update receiver configuration:
```sql
UPDATE radio_receivers 
SET modulation_type = 'NFM' 
WHERE identifier = 'rtlsdr-00000001';
```

Then restart audio-service.

### Issue: Icecast Not Available

**Symptom**: UI shows "Basic Streaming Mode" and playback is choppy

**Solution**: Enable Icecast streaming for better quality

1. Check if Icecast is running:
   ```bash
   ```

2. If not running, start it:
   ```bash
   ```

3. Verify Icecast configuration in `.env`:
   ```
   ICECAST_ENABLED=true
   ICECAST_EXTERNAL_PORT=8001
   ```

## Architecture Overview

### Separated Container Architecture

```
┌─────────────────┐
│  sdr-service    │ ── Reads SDR hardware
│  (port 5001)    │ ── Publishes IQ samples to Redis
└────────┬────────┘
         │ Redis pub/sub: sdr:samples:{receiver_id}
         ↓
┌─────────────────┐
│ audio-service   │ ── Subscribes to IQ samples
│  (port 5002)    │ ── Demodulates to audio
│                 │ ── Publishes audio to broadcast queue
│                 │ ── Streams to Icecast
│                 │ ── Serves /api/audio/stream endpoint
└────────┬────────┘
         │ HTTP streaming
         ↓
┌─────────────────┐
│   app (webapp)  │ ── Web UI
│   (port 8000)   │ ── Proxies streaming to audio-service
└─────────────────┘
```

### Data Flow for Audio Playback

1. **SDR Hardware** → USB → **sdr-service** → Redis pub/sub
2. **audio-service** subscribes to Redis → demodulates → **BroadcastQueue**
3. **BroadcastQueue** fans out to:
   - EAS monitor (SAME decoding)
   - Icecast streaming (public broadcast)
   - Web streaming (real-time UI playback)
4. **Web UI** connects to `/api/audio/stream/{source}` → audio-service serves WAV stream
5. **Browser** HTML5 audio player buffers and plays

## Expected Behavior

### When Working Correctly

**Audio Monitoring Page shows**:
- Buffer Utilization: 5-15% (healthy)
- Status: ✅ Data flowing normally
- Audio player: "▶ Playing" (not "Connecting to stream…")
- VU meters: Show live audio levels
- Waveform: Shows live oscilloscope

**Logs show**:
```
[audio-service] ✅ Successfully started 'your-source'
[audio-service] First audio chunk decoded
[audio-service] Web stream 'web-stream-your-source-abc123' started
[app] Proxying audio stream request for your-source to audio-service
```

### When Not Working

**Symptoms**:
- Buffer Utilization: 0.0%
- Status: ⚠️ No data flowing (with specific diagnostic message)
- Audio player: Stuck on "Connecting to stream…"
- VU meters: Show -∞ dB (no signal)

**Check**: Follow diagnostic checklist above

## Additional Resources

- **Setup Guide**: `docs/guides/SETUP_INSTRUCTIONS.md`
- **Audio Architecture**: `docs/architecture/AUDIO_ARCHITECTURE.md`
- **API Documentation**: `/api/docs` (when running)

## Getting Help

If you've followed all troubleshooting steps and audio still doesn't work:

1. Collect diagnostic information:
   ```bash
   # Container status
   
   # Logs from all audio-related containers
   
   # Database configuration
   ```

2. Open an issue on GitHub with:
   - Description of the problem
   - Logs (sdr.log, audio.log, app.log)
   - Database configuration (sources.txt, receivers.txt)
