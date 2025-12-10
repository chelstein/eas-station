# EAS Station SDR - Working Memory & Knowledge Base
**Last Updated**: 2025-12-08
**Status**: All critical issues resolved ✅

---

## 📋 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Code Flow Diagrams](#code-flow-diagrams)
3. [All Fixed Issues](#all-fixed-issues)
4. [Where to Look for Common Problems](#where-to-look-for-common-problems)
5. [Testing Guide](#testing-guide)
6. [Known Working Configurations](#known-working-configurations)

---

## 🏗️ Architecture Overview

### Separated Service Architecture

The EAS Station uses a **separated architecture** where SDR hardware operations are isolated from audio processing:

```
┌──────────────────────────────────────┐
│   USB SDR Hardware                   │
│   (Airspy R2, RTL-SDR, HackRF)      │
└─────────────┬────────────────────────┘
              │ USB passthrough (/dev/bus/usb)
              ▼
┌──────────────────────────────────────┐
│  sdr-hardware-service (Container)    │
│  File: sdr_hardware_service.py       │
│                                      │
│  ┌────────────┐   ┌─────────────┐   │
│  │ USB Reader │──▶│ Ring Buffer │   │
│  │  Thread    │   │ (1s samples)│   │
│  └────────────┘   └──────┬──────┘   │
│                          │           │
│         ┌────────────────▼─────┐     │
│         │ Publisher Thread     │     │
│         │ • FFT/Spectrum       │     │
│         │ • zlib+base64 encode │     │
│         │ • Redis publish      │     │
│         └──────────┬───────────┘     │
└────────────────────┼─────────────────┘
                     │ Redis pub/sub
                     │ sdr:samples:{id}
                     ▼
          ┌─────────────────────┐
          │ Redis Broker        │
          │ • sdr:samples:{id}  │
          │ • sdr:metrics       │
          │ • sdr:spectrum:{id} │
          └──────────┬──────────┘
                     │
         ┌───────────┴────────────┐
         ▼                        ▼
┌──────────────────┐   ┌──────────────────┐
│ audio-service    │   │ Web UI (nginx)   │
│ (eas_monitoring) │   │ Flask app        │
│                  │   │                  │
│ • Demodulation   │   │ • Audio playback │
│ • EAS/SAME decode│   │ • Configuration  │
│ • Icecast output │   │ • Monitoring     │
└──────────────────┘   └──────────────────┘
```

**Key Principle**: USB SDR access is EXCLUSIVE to sdr-service. All other services receive IQ samples via Redis.

---

## 📊 Code Flow Diagrams

### 1. Receiver Addition → Audio Demodulation Flow

```
┌────────────────────────────────────────────────────────────┐
│ USER ACTION: Add Receiver in Web UI                       │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ Web UI → POST /api/radio/receivers                        │
│ File: app_core/routes/radio_routes.py                     │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ Save to Database                                           │
│ Model: RadioReceiver (app_core/models.py:661)            │
│ Fields:                                                    │
│   - identifier, driver, frequency_hz                       │
│   - sample_rate, audio_sample_rate                        │
│   - modulation_type, gain, ppm_correction                 │
│   - enabled=True, auto_start=True                         │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ sdr-service Reads Database (on startup or reload)         │
│ File: sdr_hardware_service.py:282 (initialize_radio_      │
│       receivers)                                           │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ RadioManager.configure_from_records()                      │
│ File: app_core/radio/manager.py:291                       │
│ • Converts RadioReceiver → ReceiverConfig                 │
│ • Creates driver instance (RTLSDRReceiver/AirspyReceiver) │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ RadioManager.start_all()                                   │
│ File: app_core/radio/manager.py:383                       │
│ • Calls receiver.start() for each receiver                │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ _SoapySDRReceiver.start()                                  │
│ File: app_core/radio/drivers.py:464                       │
│ 1. Verify dependencies (SoapySDR, NumPy)  ✅ FIXED        │
│ 2. Validate sample rate (Airspy: 2.5/10 MHz) ✅ FIXED     │
│ 3. Validate PPM correction (-200 to +200)    ✅ FIXED     │
│ 4. Open SoapySDR device handle                            │
│ 5. Configure sample rate, frequency, gain                 │
│ 6. Start USB reading thread                               │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ USB Reader Thread                                          │
│ File: app_core/radio/drivers.py:1084 (_usb_read_loop)    │
│ • Activates SoapySDR stream                               │
│ • Reads IQ samples in chunks (32K samples)                │
│ • Writes to SDRRingBuffer                                 │
│ • Handles timeouts with exponential backoff  ✅ FIXED     │
│ • Timeout threshold: 30 (configurable)       ✅ FIXED     │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ SDRRingBuffer                                              │
│ File: app_core/radio/ring_buffer.py:83                    │
│ • 1-second circular buffer (thread-safe)                  │
│ • Single producer (USB) / single consumer (publisher)     │
│ • Overflow handling with exponential backoff ✅ FIXED     │
│ • Logs: 5s → 10s → 20s → 60s → 300s        ✅ FIXED     │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ Publisher Thread                                           │
│ File: sdr_hardware_service.py:269 (publish_samples_and_   │
│       metrics)                                             │
│ 1. Reads samples from ring buffer                         │
│ 2. Computes FFT spectrum (2048 bins)                      │
│ 3. Compresses samples (zlib)                              │
│ 4. Encodes to base64                                      │
│ 5. Publishes to Redis: sdr:samples:{receiver_id}          │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ Redis Pub/Sub                                              │
│ Channel: sdr:samples:{receiver_id}                         │
│ Message Format (JSON):                                     │
│ {                                                          │
│   "receiver_id": "noaa_wx7",                              │
│   "timestamp": 1733688000.0,                              │
│   "sample_count": 32768,                                  │
│   "sample_rate": 2500000,                                 │
│   "center_frequency": 162550000,                          │
│   "encoding": "zlib+base64",                              │
│   "samples": "eJzt..." (base64 encoded)                   │
│ }                                                          │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ audio-service: RedisSDRSourceAdapter                       │
│ File: app_core/audio/redis_sdr_adapter.py:47              │
│ 1. Subscribes to sdr:samples:{receiver_id}                │
│ 2. Pre-creates demodulator at startup        ✅ FIXED     │
│    (uses iq_sample_rate from config or 2.5MHz default)    │
│ 3. Receives Redis messages in subscriber thread           │
│ 4. Decodes base64 → decompress zlib → numpy array        │
│ 5. Updates demodulator if sample rate changed             │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ FMDemodulator.process()                                    │
│ File: app_core/radio/demodulation.py:127                  │
│ 1. Normalizes modulation_type to uppercase   ✅ FIXED     │
│ 2. Computes FM deviation gain:                            │
│    • WFM/FM: ±75 kHz deviation                           │
│    • NFM: ±5 kHz deviation                               │
│ 3. Phase discriminator (angle difference)                 │
│ 4. Stereo decoding (if WFM and stereo_enabled)           │
│ 5. De-emphasis filter (75μs for North America)           │
│ 6. Resamples IQ rate → audio rate (e.g., 2.5MHz → 48kHz) │
│ 7. Soft-clip with tanh() to prevent distortion           │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ Audio Output                                               │
│ • BroadcastQueue → Web streaming (/api/audio/stream)     │
│ • Icecast output (for VLC, Winamp, etc.)                  │
│ • EAS/SAME decoder (eas_monitoring_service.py)           │
└────────────────────────────────────────────────────────────┘
```

### 2. Web Audio Playback Flow (After Fixes)

```
┌────────────────────────────────────────────────────────────┐
│ USER ACTION: Visit /audio_monitoring page                 │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ Page Load: templates/audio_monitoring.html                │
│ JavaScript: loadAudioSources()                            │
│ API Call: GET /api/audio/sources                         │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ Render Audio Player HTML                                  │
│ • Creates <audio> element for each source                 │
│ • Sets data-proxy-url="/api/audio/stream/{name}"         │
│ • NO Icecast mode toggle (removed)          ✅ FIXED     │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ initializeAudioPlayers()                                   │
│ File: templates/audio_monitoring.html:938                │
│ • Calls shouldUseIcecastStream() → always FALSE ✅ FIXED  │
│ • Always calls switchToProxyStream()         ✅ FIXED     │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ switchToProxyStream()                                      │
│ File: templates/audio_monitoring.html:1009               │
│ • Sets audioEl.src = "/api/audio/stream/{name}"          │
│ • Adds cache buster (?ts=timestamp)                      │
│ • Sets streamType = "https-stream"          ✅ FIXED     │
│ • Status: "Ready. Press play to listen."    ✅ FIXED     │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ USER: Clicks Play Button                                  │
│ • Browser makes HTTP request to /api/audio/stream/{name} │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ Flask Route: GET /api/audio/stream/<source_name>         │
│ File: app_core/routes/audio_routes.py                     │
│ • Streams audio chunks from BroadcastQueue                │
│ • MIME: audio/wav (PCM 16-bit)                           │
│ • HTTPS secure (no mixed-content errors)                 │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│ Audio Playback Success                                     │
│ • Status: "Streaming."                      ✅ FIXED     │
│ • VU meters update in real-time                          │
│ • EAS/SAME decoding continues in background               │
└────────────────────────────────────────────────────────────┘
```

---

## ✅ All Fixed Issues

### Critical Fixes (Blocking Issues)

#### ✅ Issue #1: SoapySDR Verification
**File**: `sdr_hardware_service.py:148`
**Problem**: Service could start without SoapySDR installed
**Fix**: Added `verify_soapysdr_installation()` called at startup:
- Verifies SoapySDR Python bindings
- Verifies NumPy
- Tests USB device enumeration
- Fails immediately with clear error if missing

**How to Test**:
```bash
# Check logs for verification output
# Should see: "✅ SoapySDR Python bindings installed"
```

#### ✅ Issue #2: Database Connection Retry
**File**: `sdr_hardware_service.py:228`
**Problem**: Service crashed if PostgreSQL wasn't ready
**Fix**: Added exponential backoff retry loop:
- 10 attempts, max 30s wait
- Tests connection with "SELECT 1"
- Stores Flask app for later use

**How to Test**:
```bash
# Stop database, start sdr-service, watch logs
# Should see retry attempts, then success when DB starts
```

#### ✅ Issue #3: No Receivers Configured Warning
**File**: `sdr_hardware_service.py:282`
**Problem**: Service appeared healthy but did nothing
**Fix**: Prominent ERROR-level banner with instructions:
- 80-character banner
- Step-by-step configuration guide
- Publishes warning to Redis for UI display

**How to Test**:
```bash
# Disable all receivers in database
# Should see prominent warning banner
```

#### ✅ Issue #4: Airspy R2 Sample Rate Validation
**File**: `app_core/radio/drivers.py:1408`
**Problem**: Invalid rates logged warning but hardware rejected them
**Fix**: Changed to ValueError exception:
- ONLY 2.5 MHz or 10 MHz accepted
- Clear error message
- Fails at receiver start, not during streaming

**How to Test**:
```bash
# Try to add Airspy receiver with invalid rate (e.g., 3 MHz)
# Should be rejected with clear error message
```

#### ✅ Issue #5: Redis Reconnection
**File**: `sdr_hardware_service.py:191`
**Problem**: Service crashed if Redis became unavailable
**Fix**: Enhanced connection validation:
- Pings connection before reuse
- Exponential backoff retry (5 attempts)
- Automatically reconnects if lost

**How to Test**:
```bash
# Restart Redis while sdr-service running
# Should see "Redis connection lost, reconnecting..." then success
```

### High Priority Fixes

#### ✅ Issue #7: Ring Buffer Overflow Logging
**File**: `app_core/radio/ring_buffer.py:202`
**Problem**: Overflow logged every 5s indefinitely
**Fix**: Exponential backoff: 5s → 10s → 20s → 40s → 80s → 160s → 300s (max)

**How to Test**:
```bash
# Overflow occurs when processing can't keep up with USB data rate
# Check logs for increasing intervals between overflow messages
```

#### ✅ Issue #8: Pre-create Demodulator
**File**: `app_core/audio/redis_sdr_adapter.py:129`
**Problem**: Demodulator not created until first message
**Fix**: Always create at startup:
- Uses iq_sample_rate from config or defaults to 2.5 MHz
- Recreates if sample rate changes

**How to Test**:
```bash
# Check logs for "Pre-created demodulator" message
```

#### ✅ Issue #9: Normalize Modulation Type
**Files**: `app_core/radio/demodulation.py:79`, `app_core/audio/redis_sdr_adapter.py:79`
**Problem**: Case sensitivity (fm vs FM) caused wrong gain
**Fix**: Normalize to uppercase in multiple locations

**How to Test**:
```bash
# Add receiver with lowercase modulation type "fm"
# Should work identically to uppercase "FM"
```

#### ✅ Issue #10: PPM Correction Validation
**File**: `app_core/radio/drivers.py:668`
**Problem**: Extreme PPM values tuned to wrong frequency
**Fix**: Validates range -200 to +200 PPM, raises ValueError if out of range

**How to Test**:
```bash
# Try to set PPM correction to 500 (invalid)
# Should be rejected with clear error
```

#### ✅ Issue #11: Device Enumeration Logging
**File**: `app_core/radio/drivers.py:294`
**Problem**: Failures logged at DEBUG, users didn't know
**Fix**: Changed to WARNING level with helpful messages

**How to Test**:
```bash
# Check logs for device enumeration messages
```

#### ✅ Issue #12: Configurable Timeout Threshold
**File**: `app_core/radio/drivers.py:173`
**Problem**: Hardcoded 10 timeouts too low for weak signals
**Fix**: Environment variable SDR_MAX_CONSECUTIVE_TIMEOUTS (default: 30)

**How to Test**:
```bash
SDR_MAX_CONSECUTIVE_TIMEOUTS=50
```

#### ✅ Issue #13: Database Session Management
**File**: `sdr_hardware_service.py:682`
**Problem**: reload_receivers used unclear session management
**Fix**: Store Flask app in _state, use proper app_context()

**How to Test**:
```bash
# Trigger reload via Redis command
```

### Web Audio Playback Fixes

#### ✅ Issue #14: Confusing Icecast Toggle
**File**: `templates/audio_monitoring.html`
**Problem**: Users couldn't listen due to confusing Icecast vs HTTPS toggle
**Fix**: Complete simplification:
- Removed stream mode toggle UI
- Removed getPreferredStreamMode/setPreferredStreamMode functions
- shouldUseIcecastStream() always returns false
- Web playback ALWAYS uses HTTPS proxy
- Clear messaging: "Secure HTTPS Streaming"
- Icecast links shown as "Open in external player (VLC, Winamp)"

**How to Test**:
```bash
# Visit /audio_monitoring page
# Should see NO toggle buttons
# Should see "Secure HTTPS Streaming" message
# Press play → audio should stream immediately
```

---

## 🔍 Where to Look for Common Problems

### Problem: "No audio from SDR"

**Checklist**:
1. ✅ Check SoapySDR verification logs:
   ```bash
   ```
   Expected: "✅ SoapySDR Python bindings installed"

2. ✅ Check if receivers are configured:
   ```bash
   ```
   If present: Add receiver in web UI

3. ✅ Check USB device access:
   ```bash
   ```
   Expected: "✅ USB device enumeration working (N device(s) found)"

4. ✅ Check receiver started:
   ```bash
   ```
   Expected: "✅ Started N receiver(s) with auto_start"

5. ✅ Check Redis samples being published:
   ```bash
   ```
   Should see messages flowing

6. ✅ Check audio-service receiving samples:
   ```bash
   ```
   Expected: "✅ First audio chunk decoded for {receiver_id}"

**Files to Check**:
- `sdr_hardware_service.py:796` - SoapySDR verification
- `sdr_hardware_service.py:282` - Receiver initialization
- `app_core/radio/drivers.py:464` - Receiver start
- `app_core/radio/drivers.py:1084` - USB read loop
- `app_core/audio/redis_sdr_adapter.py:147` - Redis subscriber

### Problem: "Airspy receiver won't start"

**Common Causes**:
1. **Invalid sample rate**: Airspy R2 ONLY supports 2.5 MHz or 10 MHz
   - File: `app_core/radio/drivers.py:1410`
   - Error: "Invalid Airspy R2 sample rate: X Hz"
   - Fix: Change sample rate to 2500000 or 10000000

2. **USB permissions**: Container needs privileged mode
   - Check: `privileged: true` and `devices: /dev/bus/usb`

3. **Device busy**: Another process using the SDR
   - Check: `SoapySDRUtil --find`
   - Fix: Stop other SDR applications

**Files to Check**:
- `app_core/radio/drivers.py:1400` - AirspyReceiver class
- `app_core/radio/discovery.py:264` - Airspy fallback capabilities

### Problem: "Web audio player not working"

**Post-Fix Checklist** (After Issue #14 fix):
1. ✅ Should NOT see Icecast vs HTTPS toggle
2. ✅ Should see "Secure HTTPS Streaming" message
3. ✅ Press play → should stream immediately
4. ✅ Browser console should show NO errors

**If Still Not Working**:
1. Check audio source is running:
   ```bash
   curl http://localhost:5000/api/audio/sources
   ```
   Expected: `"status": "running"`

2. Check proxy stream URL:
   ```bash
   curl -I http://localhost:5000/api/audio/stream/noaa_wx7
   ```
   Expected: `200 OK`, `Content-Type: audio/wav`

3. Check browser console for errors (F12)
   - Look for 403/404/500 errors
   - Look for CORS errors

**Files to Check**:
- `templates/audio_monitoring.html:1034` - shouldUseIcecastStream
- `templates/audio_monitoring.html:1009` - switchToProxyStream
- `app_core/routes/audio_routes.py` - /api/audio/stream route

### Problem: "Ring buffer overflows"

**Meaning**: Processing can't keep up with USB data rate

**Checklist**:
1. Check overflow log interval (should increase):
   ```bash
   ```
   Expected: Intervals increase: 5s → 10s → 20s → 40s → etc.

2. Check CPU usage:
   ```bash
   ```
   If >80%: Processing too slow

3. Check if demodulator is enabled unnecessarily:
   - If only need IQ data, set modulation_type='IQ' (no demodulation)

**Files to Check**:
- `app_core/radio/ring_buffer.py:202` - Overflow logging
- `app_core/radio/drivers.py:1084` - USB read loop

### Problem: "Database connection failed"

**Post-Fix Behavior** (After Issue #2 fix):
- Service should retry 10 times with exponential backoff
- Logs should show: "Database connection failed (attempt X/10)"
- Should eventually succeed when database is ready

**If Still Failing After 10 Attempts**:
1. Check database is running:
   ```bash
   ```

2. Check connection string:
   ```bash
   ```

3. Check database credentials in .env:
   ```
   POSTGRES_HOST=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_DB=alerts
   ```

**Files to Check**:
- `sdr_hardware_service.py:228` - initialize_database

---

## 🧪 Testing Guide

### Critical Path Tests

#### Test 1: SoapySDR Not Installed
**Expected**: Service fails gracefully with clear error

```bash
# Simulate missing SoapySDR (rename the module temporarily)
# Should see: "❌ SoapySDR Python bindings NOT installed"
# Service should exit with code 1

# Restore
```

#### Test 2: Database Not Available
**Expected**: Service retries and waits

```bash
# Stop database before starting sdr-service
# Should see retry attempts: "Database connection failed (attempt 1/10)"

# Start database - service should connect
# Should see: "✅ Database connection established"
```

#### Test 3: No Receivers Configured
**Expected**: Prominent warning displayed

```bash
# Disable all receivers
# Should see 80-character banner: "❌ NO SDR RECEIVERS CONFIGURED IN DATABASE"
```

#### Test 4: Invalid Airspy Sample Rate
**Expected**: Configuration rejected

```bash
# Try to add Airspy receiver with 3 MHz rate via web UI
# POST /api/radio/receivers with sample_rate=3000000
# Should get error: "Invalid Airspy R2 sample rate"
```

#### Test 5: Web Audio Playback
**Expected**: Immediate playback over HTTPS

```bash
# 1. Visit http://localhost:8888/audio_monitoring
# 2. Should see NO "Icecast vs Built-in" toggle
# 3. Should see "Secure HTTPS Streaming" message
# 4. Press play button
# 5. Audio should start streaming immediately
# 6. Browser console should show NO errors (F12)
```

### Integration Tests

#### Test 6: Full Receiver Flow
**Test**: Add receiver → Start → Audio output

```bash
# 1. Add receiver via web UI (/settings/radio)
#    - Driver: airspy
#    - Frequency: 162.550 MHz
#    - Sample Rate: 2500000
#    - Modulation: FM
#    - Auto-start: Yes

# 2. Check logs
# Should see: "Configured 1 radio receiver(s) from database"

# Should see: "✅ Started 1 receiver(s) with auto_start"

# 3. Check Redis samples
# Should see messages flowing

# 4. Check audio-service
# Should see: "✅ First audio chunk decoded"

# 5. Listen via web UI
# Visit /audio_monitoring, press play
# Should hear audio
```

#### Test 7: Sample Rate Change During Operation
**Test**: Change sample rate while receiver running

```bash
# 1. Start receiver with 2.5 MHz
# 2. Via web UI, change to 10 MHz
# 3. Check logs
# Should see: "IQ sample rate changed: 2500000Hz -> 10000000Hz"
# Should see: "✅ Demodulator updated for rate 10000000Hz"
```

#### Test 8: Weak Signal Timeout Handling
**Test**: Verify timeout threshold is configurable

```bash
#    SDR_MAX_CONSECUTIVE_TIMEOUTS: 50

# 2. Restart sdr-service

# 3. Tune to weak/no signal frequency
# 4. Check logs for timeout behavior
# Should tolerate 50 timeouts before reconnecting
```

#### Test 9: Redis Connection Loss
**Test**: Verify automatic reconnection

```bash
# 1. Start sdr-service with receiver running
# 2. Restart Redis

# 3. Check sdr-service logs
# Should see: "Redis connection lost, reconnecting..."
# Should see: "✅ Connected to Redis at redis:6379"
```

#### Test 10: Ring Buffer Overflow Recovery
**Test**: Verify exponential backoff logging

```bash
# 1. Cause overflow (simulate slow processing)
# 2. Check logs

# Should see increasing intervals:
# "Ring buffer overflow... Next log in 5s"
# "Ring buffer overflow... Next log in 10s"
# "Ring buffer overflow... Next log in 20s"
# "Ring buffer overflow... Next log in 40s"
# ... up to 300s max
```

---

## ⚙️ Known Working Configurations

### Configuration 1: Airspy R2 + NOAA Weather

```yaml
# Receiver Configuration
Identifier: noaa_wx7
Driver: airspy
Frequency: 162.550 MHz (162550000 Hz)
Sample Rate: 2.5 MHz (2500000 Hz)  # Airspy R2 valid rate
Audio Sample Rate: 48000 Hz
Modulation: FM (or WFM)
Stereo: Yes
De-emphasis: 75 μs (North America standard)
PPM Correction: 0.0
Gain: 21 (linearity mode)
Auto-start: Yes
Enabled: Yes
```

**Expected Behavior**:
- ✅ Receiver starts immediately
- ✅ IQ samples published to Redis
- ✅ Audio demodulated to 48kHz stereo
- ✅ Web playback works over HTTPS
- ✅ Icecast stream available for external players

### Configuration 2: RTL-SDR + FM Broadcast

```yaml
# Receiver Configuration
Identifier: fm_broadcast
Driver: rtlsdr
Frequency: 98.7 MHz (98700000 Hz)
Sample Rate: 2.4 MHz (2400000 Hz)  # RTL-SDR common rate
Audio Sample Rate: 48000 Hz
Modulation: WFM (wideband FM)
Stereo: Yes
De-emphasis: 75 μs
PPM Correction: -2.5 (typical for cheap RTL-SDR)
Gain: 49.6 (max)
Auto-start: Yes
Enabled: Yes
```

**Expected Behavior**:
- ✅ Receiver starts immediately
- ✅ Stereo FM broadcast decoded
- ✅ Web playback works
- ✅ RDS/RBDS data extracted (if enable_rbds=True)

### Configuration 3: Separated Architecture (systemd)

```yaml

sdr-service:
  image: eas-station:latest
  command: ["python", "sdr_hardware_service.py"]
  privileged: true  # Required for USB
  devices:
    - /dev/bus/usb:/dev/bus/usb  # USB passthrough
  environment:
    SDR_MAX_CONSECUTIVE_TIMEOUTS: 30  # Configurable threshold
  ulimits:
    memlock:
      soft: -1  # Required for USB DMA
      hard: -1

audio-service:
  image: eas-station:latest
  command: ["python3", "eas_monitoring_service.py"]
  # NO USB access - receives samples via Redis

redis:
  image: redis:7-alpine
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
```

**Expected Behavior**:
- ✅ sdr-service has exclusive USB access
- ✅ audio-service receives IQ via Redis
- ✅ Services can restart independently
- ✅ Clean separation of concerns

---

## 📚 Quick Reference

### Important Files

| File | Purpose | Lines | Key Functions |
|------|---------|-------|---------------|
| `sdr_hardware_service.py` | Main SDR service | 870 | main(), verify_soapysdr_installation(), initialize_database() |
| `app_core/radio/drivers.py` | SDR drivers | 1494 | _SoapySDRReceiver, AirspyReceiver, RTLSDRReceiver |
| `app_core/radio/manager.py` | Receiver coordination | 455 | RadioManager.configure_from_records(), start_all() |
| `app_core/radio/ring_buffer.py` | USB buffering | 345 | SDRRingBuffer.write(), read() |
| `app_core/radio/demodulation.py` | FM/AM demodulation | 652 | FMDemodulator.process(), create_demodulator() |
| `app_core/audio/redis_sdr_adapter.py` | Redis IQ bridge | 322 | RedisSDRSourceAdapter._start_capture() |
| `app_core/models.py` | Database models | - | RadioReceiver (line 661), to_receiver_config() (line 718) |
| `templates/audio_monitoring.html` | Web audio playback | 2368 | shouldUseIcecastStream(), switchToProxyStream() |

### Redis Channels

| Channel | Content | TTL | Publisher |
|---------|---------|-----|-----------|
| `sdr:samples:{id}` | IQ samples (zlib+base64) | - | sdr-service |
| `sdr:metrics` | Health metrics | 30s | sdr-service |
| `sdr:spectrum:{id}` | FFT spectrum | 5s | sdr-service |
| `sdr:ring_buffer:{id}` | Buffer stats | 10s | sdr-service |
| `sdr:heartbeat` | Service heartbeat | 10s | sdr-service |
| `sdr:commands` | Control commands | - | Web UI |
| `sdr:command_result:{id}` | Command responses | 30s | sdr-service |
| `sdr:status` | Service status | 300s | sdr-service |

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SDR_MAX_CONSECUTIVE_TIMEOUTS` | 30 | Max USB timeouts before reconnect |
| `REDIS_HOST` | redis | Redis server hostname |
| `POSTGRES_HOST` | alerts-db | PostgreSQL hostname |
| `CONFIG_PATH` | /app-config/.env | Persistent config file |

### What Was Fixed
- ✅ **13 critical and high-priority issues resolved**
- ✅ **1 web audio playback issue fixed**
- ✅ **All startup validation checks added**
- ✅ **All error handling improved**
- ✅ **All confusing UI elements removed**

### What Works Now
- ✅ SoapySDR verification prevents startup without dependencies
- ✅ Database connection retries handle startup delays
- ✅ Prominent warnings when no receivers configured
- ✅ Airspy R2 sample rates validated (2.5/10 MHz only)
- ✅ Redis reconnection handles temporary outages
- ✅ Ring buffer overflow logging doesn't spam
- ✅ Demodulator pre-created to avoid dropping initial audio
- ✅ Modulation types normalized (case-insensitive)
- ✅ PPM correction validated (-200 to +200)
- ✅ Device enumeration failures logged prominently
- ✅ Timeout thresholds configurable for weak signals
- ✅ Database session management fixed for reload command
- ✅ Web audio playback ALWAYS uses HTTPS (no confusing toggle)
- ✅ Clear messaging: "Secure HTTPS Streaming"

### Architecture Highlights
- **Separated services**: USB access isolated to sdr-service
- **Redis pub/sub**: IQ samples flow from sdr-service to audio-service
- **Robust buffering**: 1-second ring buffer handles USB timing variations
- **Dual-thread USB**: Reader + publisher threads for 24/7 reliability
- **Clean web audio**: HTTPS streaming, no mixed-content issues

**Status**: Production-ready for 24/7 operation ✅

---

**Last Updated**: 2025-12-08
**Next Review**: When adding new SDR drivers or modulation types
