# SDR Audio and Tuning Troubleshooting Guide

## Overview

This guide helps diagnose SDR audio problems and frequency tuning issues in EAS Station.

## Quick Diagnostic Steps

### 1. Check Service Status

First, verify that SDR and audio services are running:

```bash
# Check all services
docker compose ps

# Check SDR service specifically
docker compose logs -f sdr-service

# Check audio service
docker compose logs -f audio-service
```

**Look for**:
- ✅ "✅ SDR Service started successfully"
- ✅ "Configured X radio receiver(s) from database"
- ✅ "Started X receiver(s) with auto_start"
- ❌ "Failed to open device"
- ❌ "No radio receivers configured"

### 2. Verify SDR Hardware Detection

Check if your SDR device is detected by the system:

```bash
# List USB devices
lsusb

# Check SoapySDR device enumeration
docker compose exec sdr-service python3 -c "import SoapySDR; print(SoapySDR.Device.enumerate())"
```

**Expected output for RTL-SDR**:
```
[{driver='rtlsdr', label='Generic RTL2832U', serial='00000001'}]
```

**Expected output for Airspy**:
```
[{driver='airspy', label='Airspy', serial='0xXXXXXXXX'}]
```

### 3. Check Receiver Configuration

Connect to the database and check receiver settings:

```bash
docker compose exec app psql -U postgres -d alerts -c "SELECT id, identifier, driver, frequency_hz, sample_rate, gain, modulation_type, audio_output, enabled, auto_start FROM radio_receivers;"
```

**Verify**:
- `enabled` = true
- `auto_start` = true  
- `frequency_hz` = correct frequency (e.g., 162550000 for NOAA WX7)
- `sample_rate` = valid for your SDR:
  - RTL-SDR: 2,400,000 (2.4 MHz) typical
  - Airspy R2: 2,500,000 or 10,000,000 ONLY (hardware limitation)
- `gain` = appropriate value:
  - RTL-SDR: 40-49.6 dB recommended
  - Airspy: 21 dB or leave NULL for AGC
- `modulation_type` = 'NFM' for NOAA, 'FM' or 'WFM' for broadcast FM
- `audio_output` = true if you want demodulated audio

### 4. Check Redis IQ Sample Flow

Verify that IQ samples are being published to Redis:

```bash
# Monitor Redis pub/sub channel
docker compose exec redis redis-cli

# In Redis CLI:
SUBSCRIBE sdr:samples:*

# You should see messages if SDR is working
# Press Ctrl+C to exit
```

**If no messages**:
- SDR service may not be publishing
- Receiver may not be started
- Hardware may not be accessible

### 5. Check Audio Source Configuration

Verify audio source is configured for SDR:

```bash
docker compose exec app psql -U postgres -d alerts -c "SELECT id, name, source_type, config_params, enabled, auto_start FROM audio_source_configs WHERE source_type='redis_sdr';"
```

**Required config_params**:
```json
{
  "receiver_id": "your-receiver-identifier",
  "demod_mode": "NFM",
  "iq_sample_rate": 2400000
}
```

### 6. Check Audio Service Logs

Look for demodulation and audio processing:

```bash
docker compose logs audio-service | grep -E "Creating|demodulator|IQ sample|audio chunk"
```

**Expected messages**:
- "Creating NFM demodulator: 2400000Hz IQ → 44100Hz audio"
- "✅ First audio chunk decoded for receiver-1: 4096 samples"

## Common Issues and Solutions

### Issue: "No audio from SDR"

**Possible Causes**:

1. **Gain too low or zero**
   - Symptom: Signal strength shows 0.0 or very low values
   - Solution: Set gain in receiver config (40 dB for RTL-SDR, 21 dB for Airspy)
   
2. **Wrong modulation type**
   - Symptom: Audio sounds like noise or static
   - Solution: Use NFM for NOAA Weather, FM/WFM for broadcast FM
   
3. **Audio output disabled**
   - Symptom: IQ samples flowing but no audio
   - Solution: Set `audio_output = true` in receiver config

4. **No audio source configured**
   - Symptom: SDR works but audio-service not processing
   - Solution: Create AudioSourceConfig with type='redis_sdr'

### Issue: "Wrong frequency / not tuning correctly"

**Possible Causes**:

1. **Frequency in Hz not MHz**
   - Symptom: Database shows 162.550 instead of 162550000
   - Solution: Frequency must be in Hz (multiply MHz by 1,000,000)
   
2. **Airspy sample rate invalid**
   - Symptom: Airspy not working or logging rate errors
   - Solution: Use ONLY 2,500,000 or 10,000,000 Hz for Airspy R2

3. **Driver mismatch**
   - Symptom: "Device not found" errors
   - Solution: Verify driver matches hardware ('rtlsdr' or 'airspy')

### Issue: "SDR service crashes or restarts"

**Possible Causes**:

1. **USB permissions**
   - Symptom: "Permission denied" or "Unable to open device"
   - Solution: Ensure Docker has USB device access (`--device=/dev/bus/usb`)
   
2. **Device in use**
   - Symptom: "Device or resource busy"
   - Solution: Only one application can access SDR at a time
   
3. **Sample rate overflow**
   - Symptom: "SOAPY_SDR_OVERFLOW" errors
   - Solution: System may be too slow, try lower sample rate

## Configuration Examples

### NOAA Weather Radio (RTL-SDR)

```sql
INSERT INTO radio_receivers (identifier, display_name, driver, frequency_hz, sample_rate, gain, modulation_type, audio_output, enabled, auto_start)
VALUES ('noaa-wx7', 'NOAA Weather WX7', 'rtlsdr', 162550000, 2400000, 40.0, 'NFM', true, true, true);
```

### FM Broadcast Station (Airspy R2)

```sql
INSERT INTO radio_receivers (identifier, display_name, driver, frequency_hz, sample_rate, gain, modulation_type, audio_output, stereo_enabled, enabled, auto_start)
VALUES ('fm-wkqx', 'WKQX 101.1 FM', 'airspy', 101100000, 2500000, 21.0, 'WFM', true, true, true, true);
```

## Advanced Diagnostics

### View SDR Metrics in Redis

```bash
docker compose exec redis redis-cli

# In Redis CLI:
GET sdr:metrics

# Should return JSON with receiver status, signal strength, etc.
```

### Manual SDR Test

Test SDR hardware directly:

```bash
docker compose exec sdr-service python3 /app/scripts/sdr_diagnostics.py

# Test capture from specific device:
docker compose exec sdr-service python3 /app/scripts/sdr_diagnostics.py --test-capture --driver rtlsdr --frequency 162550000
```

### Check Demodulator Configuration

```bash
docker compose exec app python3 -c "
from app_core.radio.demodulation import FMDemodulator, DemodulatorConfig
config = DemodulatorConfig(modulation_type='NFM', sample_rate=2400000, audio_sample_rate=44100)
demod = FMDemodulator(config)
print(f'Audio gain: {demod._audio_gain}')
print(f'Expected ~8.0 for NFM at 2.4 MHz')
"
```

## Getting Help

If issues persist after following this guide:

1. **Collect logs**:
   ```bash
   docker compose logs sdr-service > sdr-service.log
   docker compose logs audio-service > audio-service.log
   ```

2. **Check receiver config**:
   ```bash
   docker compose exec app psql -U postgres -d alerts -c "\x" -c "SELECT * FROM radio_receivers;"
   ```

3. **Check hardware**:
   ```bash
   lsusb > hardware.log
   docker compose exec sdr-service python3 /app/scripts/sdr_diagnostics.py > diagnostics.log
   ```

4. **Provide information**:
   - SDR hardware model (RTL-SDR v3, Airspy R2, etc.)
   - Frequency you're trying to receive
   - Complete error messages from logs
   - Output of diagnostic commands above

## Related Documentation

- [SDR Setup Guide](../guides/SDR_SETUP_GUIDE.md)
- [Audio System Architecture](../architecture/AUDIO_SYSTEM_ARCHITECTURE.md)
- [Diagnostics Scripts](../../scripts/README.md)
