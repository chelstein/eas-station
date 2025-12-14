# Airspy "No Match" After Installing Package - Service File Not Updated

## Problem

After installing the `airspy` package, the service still gets "no match" errors:

```
Found 1 SoapySDR device(s): ['AirSpy One [b58069dc39399513]']
Device.make() returned 'no match' for wxj93 (attempt 1/3)
```

But `SoapySDRUtil --probe="driver=airspy"` works fine from command line.

## Root Cause

**The systemd service file was not updated with the new PYTHONPATH!**

Check your current PYTHONPATH:
```bash
systemctl show eas-station-sdr.service | grep PYTHONPATH
```

If you see:
```
PYTHONPATH=/opt/eas-station:/usr/lib/python3/dist-packages
```

This is the OLD hardcoded path. It's missing `/usr/lib/python3.12/dist-packages` (or your Python version's dist-packages).

## Solution

You need to either:

### Option 1: Re-run install.sh (Recommended)

This will update the systemd service file with dynamically detected paths:

```bash
cd /opt/eas-station
git pull
sudo ./install.sh
```

The install script will detect your Python version's site-packages and update the service file.

### Option 2: Manually Update Service File

Edit the service file:

```bash
sudo systemctl edit --full eas-station-sdr.service
```

Find this line:
```
Environment="PYTHONPATH=/opt/eas-station:/usr/lib/python3/dist-packages"
```

Change it to include your Python version's path. For Python 3.12:
```
Environment="PYTHONPATH=/opt/eas-station:/usr/local/lib/python3.12/dist-packages:/usr/lib/python3/dist-packages:/usr/lib/python3.12/dist-packages"
```

Then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart eas-station-sdr.service
```

### Option 3: Quick Path Detection

Run this to get the correct PYTHONPATH:

```bash
python3 -c "import site; print('/opt/eas-station:' + ':'.join(site.getsitepackages()))"
```

Copy that output and use it in the service file (Option 2).

## Verification

After fixing, verify the service has the correct path:

```bash
systemctl show eas-station-sdr.service | grep PYTHONPATH
```

Should show multiple Python paths like:
```
PYTHONPATH=/opt/eas-station:/usr/local/lib/python3.12/dist-packages:/usr/lib/python3/dist-packages:/usr/lib/python3.12/dist-packages
```

Then check the service logs:

```bash
sudo journalctl -u eas-station-sdr.service -f
```

Should show:
```
✅ Successfully opened device
✅ Tuned wxj93 to 162.550 MHz
```

## Why This Happens

The install.sh script (v2.27.8+) includes code to dynamically detect Python paths and update the systemd service file. But if you:

1. Install the repository
2. Run install.sh (gets old hardcoded path)
3. Update the code with `git pull`
4. Don't re-run install.sh

Then you have the NEW Python code but the OLD systemd service file with hardcoded paths.

The service needs to be regenerated with the new dynamic path detection.

---

**See Also**:
- [AIRSPY_NO_OPEN_FIX.md](AIRSPY_NO_OPEN_FIX.md) - Original airspy package issue
- [FRONTEND_AIRSPY_ERROR_AFTER_FIX.md](FRONTEND_AIRSPY_ERROR_AFTER_FIX.md) - Service restart troubleshooting
