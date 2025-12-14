# Root Cause Analysis: Airspy "No Match" on Bare Metal

## Summary

Airspy SDR device worked in Docker but failed on bare metal with "Device.make() returned 'no match'" error, even after installing the `airspy` package.

## Timeline of Issues and Fixes

### Issue 1: Missing Airspy Firmware Package (v2.27.9)
**Symptom**: `sudo SoapySDRUtil --probe="driver=airspy"` failed  
**Root Cause**: `airspy` package not installed (only library, not firmware)  
**Fix**: Added `airspy` to apt install list in install.sh  
**Status**: ✅ Fixed - SoapySDRUtil now works

### Issue 2: Hardcoded PYTHONPATH in install.sh (v2.27.8)
**Symptom**: Service couldn't import SoapySDR after venv isolation  
**Root Cause**: install.sh had hardcoded `/usr/lib/python3/dist-packages`  
**Fix**: Added dynamic path detection to install.sh  
**Status**: ✅ Fixed - but only for NEW installations

### Issue 3: update.sh Didn't Apply Path Detection (v2.27.10) ⭐ **THE BUG**
**Symptom**: After `git pull` + restart, service still got "no match"  
**Root Cause**: update.sh just copied static files, didn't update systemd paths  
**Why It Matters**: User has Python 3.13, needs `/usr/lib/python3.13/dist-packages`  
**Fix**: Added dynamic path detection to update.sh  
**Status**: ✅ Fixed - commit 6a93b44

## Why Docker Worked But Bare Metal Didn't

| Aspect | Docker | Bare Metal |
|--------|--------|------------|
| Python venv | No venv or --system-site-packages | Isolated venv (no --system-site-packages) |
| SoapySDR access | Direct system packages | Needs PYTHONPATH to reach system packages |
| Update method | Full rebuild (paths auto-detected) | git pull + restart (paths NOT updated) |

## The Specific Problem

**User's System**: Python 3.13  
**Old Service File**: `PYTHONPATH=/opt/eas-station:/usr/lib/python3/dist-packages`  
**Needed**: `PYTHONPATH=/opt/eas-station:/usr/lib/python3.13/dist-packages:/usr/lib/python3/dist-packages`

When the venv Python tries to import SoapySDR, it searches PYTHONPATH. The old path doesn't include Python 3.13's dist-packages, so import fails or gets wrong version.

## The Fix

```bash
cd /opt/eas-station
git pull
sudo ./update.sh  # ← Applies dynamic path detection
```

**What update.sh v2.27.10+ does**:
1. Detects ALL Python site-packages paths (using `site.getsitepackages()`)
2. Detects SoapySDR plugin directories (searches `/usr/lib/*/SoapySDR/modules*`)
3. Updates `/etc/systemd/system/eas-station-sdr.service` with sed
4. Reloads systemd daemon
5. Restarts services

## Verification

After running update.sh, check:

```bash
systemctl show eas-station-sdr.service | grep PYTHONPATH
```

Should show:
```
PYTHONPATH=/opt/eas-station:/usr/local/lib/python3.13/dist-packages:/usr/lib/python3/dist-packages:/usr/lib/python3.13/dist-packages:...
```

Then check logs:
```bash
sudo journalctl -u eas-station-sdr.service -n 50 | grep -E "Found|opened|Locked"
```

Should show:
```
✅ Found 1 SoapySDR device(s): ['AirSpy One [b58069dc39399513]']
✅ Successfully opened device
✅ Tuned wxj93 to 162.550 MHz
✅ Receiver wxj93: Locked
```

## Lessons Learned

1. **Always mirror install.sh logic in update.sh** - Both need dynamic detection
2. **Test with different Python versions** - Paths change between 3.10, 3.12, 3.13
3. **Don't assume git pull is enough** - Systemd files need runtime updates
4. **When debugging, check systemd environment** - Not just code changes

## Related Files

- `install.sh` - Lines 1537-1600 (dynamic path detection)
- `update.sh` - Lines 602-680 (now has same logic)
- `systemd/eas-station-sdr.service` - Gets updated by both scripts
- `docs/troubleshooting/AIRSPY_SERVICE_FILE_NOT_UPDATED.md` - User guide

---

**Fixed in**: v2.27.10 (commit 6a93b44)  
**Date**: 2025-12-14  
**Affects**: All bare metal installations using Python 3.13  
**Workaround**: Run `sudo ./update.sh` instead of just `git pull`
