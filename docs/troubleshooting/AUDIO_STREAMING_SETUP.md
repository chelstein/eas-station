# Audio Streaming Troubleshooting Guide

## Quick Diagnostic Checklist

If audio sources show "No data flowing" or the audio monitoring page shows 0% buffer utilization, work through these steps in order.

### 1. Check Service Health

```bash
sudo systemctl status eas-station-audio.service
sudo journalctl -u eas-station-audio.service -n 50
```

**Expected**: Service `active (running)` with log lines like:
```
Loading N audio source configurations from database
Auto-starting source: 'your-source-name'
Successfully started 'your-source-name'
```

If the service is not running:
```bash
sudo systemctl start eas-station-audio.service
```

### 2. Verify Audio Sources are Configured

In the web UI, navigate to **Settings → Audio Sources**. At least one source should be enabled with **Auto Start** on.

Alternatively, check directly:
```bash
sudo -u postgres psql alerts -c \
  "SELECT name, source_type, enabled, auto_start, priority FROM audio_source_configs;"
```

**If empty**: Add an audio source via **Settings → Audio Sources → Add Source**.

### 3. Check Redis Connectivity

```bash
redis-cli ping          # Should return PONG
redis-cli HGETALL eas:metrics
```

For SDR sources, verify IQ samples are flowing:
```bash
redis-cli PSUBSCRIBE 'sdr:samples:*'
# Wait 5 seconds — messages should appear if SDR is active; Ctrl+C to exit
```

### 4. Check SDR Service (SDR sources only)

```bash
sudo systemctl status eas-station-sdr.service
sudo journalctl -u eas-station-sdr.service -n 30
```

**Expected log lines**:
```
Auto-discovering Redis SDR sources...
Created Redis SDR source: redis-rtlsdr-noaa
Connected to Redis for receiver rtlsdr-00000001
```

If no SDR devices are found:
```bash
lsusb | grep -i "RTL\|Realtek\|Airspy"
ls -la /dev/bus/usb/
```

### 5. Check the Audio Monitoring Page

Navigate to **Audio Monitoring** in the web UI:
- **Buffer Utilization** should be 5–15% when healthy
- **Status** should show ✅ Data flowing
- **VU meters** should show live audio levels

If a source shows **STOPPED**, click the ▶ Start button on its card.

---

## Common Configuration Issues

### No Audio Sources in Database

**Symptom**: Settings → Audio Sources is empty.

**Solution**: Add sources via the web UI, or insert directly:

```sql
-- HTTP stream (internet radio / NOAA stream URL)
INSERT INTO audio_source_configs (
    name, source_type, enabled, auto_start, priority, config_params
) VALUES (
    'NOAA Weather Radio',
    'http_stream', true, true, 100,
    '{"url": "https://stream.revma.ihrhls.com/zc1809", "sample_rate": 44100, "channels": 1}'
);
```

```sql
-- SDR source (requires a RadioReceiver row first)
INSERT INTO radio_receivers (identifier, frequency, sample_rate, modulation_type)
VALUES ('rtlsdr-00000001', 162550000, 2500000, 'NFM');

INSERT INTO audio_source_configs (
    name, source_type, enabled, auto_start, priority, config_params
) VALUES (
    'rtlsdr-noaa',
    'sdr', true, true, 100,
    '{"sample_rate": 44100, "channels": 1, "device_params": {"receiver_id": "rtlsdr-00000001"}}'
);
```

After inserting, restart the audio service:
```bash
sudo systemctl restart eas-station-audio.service
```

### SDR Hardware Not Detected

**Symptom**: SDR service logs show "No SDR devices found".

```bash
# Confirm device is visible
lsusb | grep RTL

# Check udev rules (needed for non-root access)
ls /etc/udev/rules.d/*rtl* 2>/dev/null || ls /etc/udev/rules.d/*sdr* 2>/dev/null

# Reload rules if present
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### Wrong Modulation Type

**Symptom**: Audio is garbled or silent even though the source is running.

| Station type | Modulation |
|---|---|
| NOAA Weather Radio | **NFM** (Narrow FM) |
| Commercial FM | **FM** (Wide FM) |
| AM broadcast | **AM** |

```sql
UPDATE radio_receivers SET modulation_type = 'NFM'
WHERE identifier = 'rtlsdr-00000001';
```

Then restart the audio service.

### Icecast Not Streaming

**Symptom**: Web player shows "Basic Streaming Mode" or choppy playback.

```bash
sudo systemctl status icecast2
sudo journalctl -u icecast2 -n 30
```

If not installed:
```bash
sudo apt install icecast2
```

Configure Icecast credentials at **Settings → Icecast** in the web UI. All Icecast settings are stored in the database — no `.env` edits required.

---

## System Architecture

```
RTL-SDR / Airspy
      │ USB
      ▼
eas-station-sdr.service
  └─ Publishes IQ samples → Redis pub/sub: sdr:samples:{receiver_id}
      │
      ▼
eas-station-audio.service
  └─ Subscribes IQ samples → demodulates → audio PCM
  └─ Publishes to BroadcastQueue
  └─ Streams to Icecast
  └─ Serves /api/audio/stream endpoint
      │
      ▼
eas-station-web.service (app)
  └─ Web UI proxies /api/audio/stream to audio service
  └─ Browser HTML5 audio player
```

### Healthy State Indicators

| Location | What to see |
|---|---|
| Audio Monitoring page | Buffer: 5–15%, Status: ✅, VU meters active |
| `journalctl -u eas-station-audio.service` | `Successfully started 'source-name'` |
| `redis-cli HGETALL eas:metrics` | `last_audio_chunk` timestamp within last 5 s |

---

## Getting Help

Collect diagnostics before opening an issue:

```bash
# Service status
sudo systemctl status eas-station-audio.service eas-station-sdr.service

# Recent logs
sudo journalctl -u eas-station-audio.service -n 100 > /tmp/audio.log
sudo journalctl -u eas-station-sdr.service -n 100 > /tmp/sdr.log

# Redis metrics snapshot
redis-cli HGETALL eas:metrics > /tmp/redis-metrics.txt

# Audio source configuration
sudo -u postgres psql alerts -c \
  "SELECT name, source_type, enabled, auto_start FROM audio_source_configs;" \
  > /tmp/audio-sources.txt
```

Open a [GitHub issue](https://github.com/KR8MER/eas-station/issues) and attach the collected files.
