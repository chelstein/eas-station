# SDR Service ALSA/Audio Errors Troubleshooting

## Problem

You may see ALSA, PulseAudio, or Jack audio errors in the `eas-station-sdr` service logs:

```
ALSA lib control.c:1575:(snd_ctl_open_noupdate) Invalid CTL hw:0
RtApiAlsa::probeDevices: control open, card = 0, No such file or directory.
RtApiPulse::probeDevices: pa_context_connect() failed: Connection refused
RtApiJack::probeDevices: Jack server not found or connection error!
```

These errors appear during SDR device enumeration and opening, even though you're not trying to use audio devices.

## Root Cause

The errors are caused by the **`soapysdr-module-audio`** package, which is sometimes installed as a dependency of SoapySDR. This module uses the RtAudio library to provide audio device support for SoapySDR.

When SoapySDR enumerates devices (via `SoapySDR.Device.enumerate()` or `SoapySDR.Device()`), it **loads ALL available SoapySDR modules**, including soapysdr-module-audio. This module then probes for ALSA, PulseAudio, and Jack audio devices, generating error messages when these audio systems are not available or accessible.

### Why Audio Modules Load

- SoapySDR has a plugin architecture where modules auto-register during enumeration
- All modules in `SOAPY_SDR_PLUGIN_PATH` are loaded when SoapySDR initializes
- soapysdr-module-audio probes for audio devices even though we only want SDR hardware

### Impact

**These errors are cosmetic - they do NOT prevent SDR devices from working:**
- ✅ Your Airspy/RTL-SDR/HackRF will still be detected and opened correctly
- ✅ Radio reception and EAS monitoring will work normally
- ❌ The errors clutter the logs and make debugging harder
- ❌ In rare cases, the audio module probing can cause timing issues during device opening

## Solution Options

### Option 1: Suppress the Errors (Recommended)

The EAS Station systemd service already includes environment variables to suppress these errors:

```ini
Environment="ALSA_CONFIG_PATH=/dev/null"
Environment="PULSE_SERVER=/dev/null"
Environment="SOAPY_SDR_LOG_LEVEL=WARNING"
```

These settings:
- Prevent ALSA from loading its configuration (not needed for SDR)
- Prevent PulseAudio connection attempts (not needed for SDR)
- Prevent SoapySDR from logging debug messages (reduces log verbosity)

**The errors may still appear in logs** because they come from C libraries (librtaudio) that write directly to stderr, bypassing Python logging and environment variable suppression.

### Option 2: Uninstall soapysdr-module-audio (Most Effective)

If you don't need audio device support in SoapySDR, you can completely eliminate these errors by uninstalling the audio module:

```bash
# Debian/Ubuntu/Raspberry Pi OS
sudo apt-get remove soapysdr-module-audio

# Verify it's removed
dpkg -l | grep soapysdr-module-audio
```

**When to use this approach:**
- ✅ If you only use USB SDR devices (Airspy, RTL-SDR, HackRF, etc.)
- ❌ If you need SoapySDR to support audio devices as SDR sources (rare)

After removing the package, restart the SDR service:

```bash
sudo systemctl restart eas-station-sdr
```

### Option 3: Filter Logs (Workaround)

If you want to keep the audio module but hide the errors from view:

```bash
# View logs without ALSA/RtApi errors
journalctl -u eas-station-sdr -f | grep -v -E '(ALSA lib|RtApi|Jack server|pa_context)'
```

## Verification

After applying a solution, check that your SDR device is working:

```bash
# Check service status
sudo systemctl status eas-station-sdr

# View logs (should see "Found N SoapySDR device(s)")
journalctl -u eas-station-sdr -n 50

# Test device enumeration manually (with error suppression)
sudo -u eas-station bash -c '
export PYTHONPATH=/opt/eas-station:/usr/lib/python3/dist-packages
export ALSA_CONFIG_PATH=/dev/null
export PULSE_SERVER=/dev/null
export SOAPY_SDR_LOG_LEVEL=WARNING
cd /opt/eas-station && source venv/bin/activate
python3 -c "
import SoapySDR
devices = SoapySDR.Device.enumerate()
print(f\"Found {len(devices)} device(s)\")
for d in devices:
    print(f\"  - {dict(d)}\")
"'
```

## Why This Happens

The EAS Station SDR service is designed to:
1. Have **exclusive USB access** to SDR hardware (Airspy, RTL-SDR, etc.)
2. Read IQ samples from the USB device
3. Publish samples to Redis for downstream audio processing

It does NOT need:
- ❌ ALSA audio device access
- ❌ PulseAudio connections
- ❌ Jack audio server
- ❌ soapysdr-module-audio functionality

However, SoapySDR's plugin architecture loads ALL available modules during initialization, causing these unnecessary audio system probes.

## Related Issues

- **"Device.make() returned 'no match'"**: Sometimes the audio module probing causes timing issues during device opening. The retry logic (3 attempts with exponential backoff) usually resolves this.
- **Systemd sandboxing**: The service must run with relaxed security (`NoNewPrivileges=true`, `PrivateTmp=true` only) to allow USB device access.
- **Docker vs Bare Metal**: These errors are more common on bare metal installations because Docker runs privileged without systemd sandboxing.

## Summary

| Issue | Impact on Functionality | Recommended Action |
|-------|-------------------------|-------------------|
| ALSA errors in logs | None (cosmetic only) | Suppress with env vars (already configured) |
```
ALSA lib control.c:1575:(snd_ctl_open_noupdate) Invalid CTL hw:0
RtApiAlsa::probeDevices: control open, card = 0, No such file or directory.
RtApiPulse::probeDevices: pa_context_connect() failed: Connection refused
RtApiJack::probeDevices: Jack server not found or connection error!
```

**Bottom line**: If your SDR device is working (check web UI for signal/audio), you can safely ignore these errors. They're just noise from an unnecessary audio module.
