# Frontend Still Shows Error After Airspy Fix

## Problem

After installing the `airspy` package and verifying SoapySDRUtil works, the EAS Station web frontend still shows:
```
Unable to open SoapySDR device for driver 'airspy'
```

## Root Cause

The SDR service may not have the updated environment variables or may need to be fully restarted with the new configuration.

## Solution Steps

### Step 1: Verify Service Environment

Check if the SDR service has the correct PYTHONPATH:

```bash
systemctl show eas-station-sdr.service | grep PYTHONPATH
```

Expected: Should include `/usr/lib/python3/dist-packages` or multiple Python paths.

If missing or incorrect, the service file needs to be regenerated:

```bash
# Re-run the relevant part of install.sh or manually update
sudo systemctl edit --full eas-station-sdr.service
# Add to the [Service] section:
Environment="PYTHONPATH=/opt/eas-station:/usr/lib/python3/dist-packages:/usr/lib/python3.12/dist-packages"
```

### Step 2: Full Service Restart

A simple restart may not be enough. Do a full stop/start:

```bash
# Stop the service completely
sudo systemctl stop eas-station-sdr.service

# Reload systemd to pick up any config changes
sudo systemctl daemon-reload

# Start the service with fresh environment
sudo systemctl start eas-station-sdr.service

# Check status
sudo systemctl status eas-station-sdr.service
```

### Step 3: Check Service Logs

Look for the actual error:

```bash
sudo journalctl -u eas-station-sdr.service -f
```

Common issues to look for:
- `ImportError: No module named 'SoapySDR'` = PYTHONPATH issue
- `Unable to open AirSpy device` = Device/firmware issue (should be fixed now)
- `No match` = Configuration issue in database

### Step 4: Verify Database Configuration

Check what's configured in the database:

```bash
sudo -u eas-station /opt/eas-station/venv/bin/python3 << 'EOF'
import os
os.chdir('/opt/eas-station')
from app import app, db
from app_core.models import RadioReceiver

with app.app_context():
    receivers = RadioReceiver.query.all()
    for r in receivers:
        print(f"Receiver: {r.name}")
        print(f"  Driver: {r.driver}")
        print(f"  Serial: {r.serial}")
        print(f"  Enabled: {r.enabled}")
        print()
EOF
```

**Issue**: If the serial number in the database doesn't match the actual device (`b58069dc39399513`), update it:

1. Go to Settings → Radio Receivers
2. Edit the receiver
3. Either:
   - Set Serial to `b58069dc39399513` (exact match)
   - OR leave Serial **empty** to auto-detect

### Step 5: Clear and Re-discover

If still failing, delete the receiver and re-discover:

1. **Web UI**: Settings → Radio Receivers
2. Delete the existing Airspy receiver
3. Click **Discover Devices**
4. It should now find the Airspy with correct serial
5. Click **Add This Device**
6. Apply the "NOAA Weather Radio (Airspy)" preset
7. Save

### Step 6: Test Import Directly

Verify the service user can import SoapySDR:

```bash
sudo -u eas-station /opt/eas-station/venv/bin/python3 -c "import SoapySDR; devices = SoapySDR.Device.enumerate(); print('Found devices:', devices)"
```

Expected: Should list your Airspy device.

If this fails with ImportError, the PYTHONPATH fix didn't apply correctly.

## Quick Fix Commands

Run these in sequence:

```bash
# 1. Stop service
sudo systemctl stop eas-station-sdr.service

# 2. Verify airspy package installed
dpkg -l | grep airspy

# 3. Reload systemd
sudo systemctl daemon-reload

# 4. Start service
sudo systemctl start eas-station-sdr.service

# 5. Watch logs for errors
sudo journalctl -u eas-station-sdr.service -f
```

Then refresh the web UI and check Settings → Radio Receivers.

## Still Not Working?

### Check PYTHONPATH in Running Service

```bash
# Get the PID
PID=$(systemctl show eas-station-sdr.service -p MainPID --value)

# Check environment
sudo cat /proc/$PID/environ | tr '\0' '\n' | grep PYTHONPATH
```

Should show: `PYTHONPATH=/opt/eas-station:/usr/lib/python3/dist-packages:...`

### Manual PYTHONPATH Fix

If PYTHONPATH is wrong, edit the service file:

```bash
sudo systemctl edit --full eas-station-sdr.service
```

Find the line:
```
Environment="PYTHONPATH=/opt/eas-station:/usr/lib/python3/dist-packages"
```

Change to include ALL Python paths:
```
Environment="PYTHONPATH=/opt/eas-station:/usr/local/lib/python3.12/dist-packages:/usr/lib/python3/dist-packages:/usr/lib/python3.12/dist-packages"
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl restart eas-station-sdr.service
```

## Expected Working State

When everything is working:

```bash
$ sudo journalctl -u eas-station-sdr.service -n 20
```

Should show:
```
✅ SoapySDR Python bindings installed (API version: ...)
✅ NumPy installed
✅ USB device enumeration working (1 device(s) found)
   Device 0: airspy (serial: b58069dc39399513)
✅ Successfully opened device
```

And the web UI should show:
- **Status**: Locked (green)
- **Signal strength**: > 0.0 dBFS

---

**Related Fixes**:
- Airspy package installation: [AIRSPY_NO_OPEN_FIX.md](AIRSPY_NO_OPEN_FIX.md)
- PYTHONPATH issues: Install script v2.27.8+
- SDR setup guide: [SDR_SETUP.md](../hardware/SDR_SETUP.md)
