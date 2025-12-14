# Root Cause Analysis: PR #1356 Breaking Website

## The Problem

After PR #1356 was merged, the website fails to load with 504 Gateway Timeout errors, even after reinstallation.

## Changes Made in PR #1356

Based on the comment from @KR8MER, PR #1356 included:

1. **eas_service.py**: Refactored EASMonitor API (audio_manager → audio_source)
2. **install.sh**: Added `--system-site-packages` flag to venv creation
3. **update.sh**: Added self-restart mechanism
4. **webapp/routes_logs.py**: Added ANSI escape code handling

## Root Cause: The `--system-site-packages` Flag

### Why It Breaks Everything

The `--system-site-packages` flag was added to the venv creation in install.sh:

```bash
python3 -m venv --system-site-packages "$VENV_DIR"
```

**This is the root cause of the 504 errors.**

### How It Breaks

When you create a venv with `--system-site-packages`:

1. **System packages are visible** inside the venv
2. **Import order**: Python checks venv packages first, then falls back to system packages
3. **C Extension Conflicts**: System packages with C extensions (numpy, scipy, etc.) conflict with venv packages

### Specific Failure Mode

The systemd service file includes this workaround:
```
Environment="PYTHONNOUSERSITE=1"
```

This is supposed to disable system site-packages. However:

1. If the systemd daemon wasn't reloaded after the service file was updated
2. If the venv was recreated with `--system-site-packages` after the env var was added
3. If there's a timing issue where imports happen before the env var takes effect

The conflict still occurs, causing:
- Import errors during gunicorn worker startup
- C extension conflicts between system gevent and venv gevent
- Version mismatches between system Flask and venv Flask
- Worker timeout → 504 Gateway Timeout

## Why Other Changes Are Innocent

### eas_service.py changes
- **Impact**: None on web service
- **Reason**: This is a separate service (eas-station-eas.service)
- **Effect**: Would break EAS service, not the website

### update.sh changes  
- **Impact**: None on runtime
- **Reason**: Only affects the update process
- **Effect**: Cannot cause 504 errors

### webapp/routes_logs.py changes
- **Impact**: None (verified)
- **Reason**: ANSI pattern is syntactically correct and doesn't break imports
- **Effect**: Would only affect log viewing, not site loading

## The Fix

The issue is NOT with my backwards compatibility fix for EASMonitor. That fix is correct and necessary.

The REAL fix is to remove the `--system-site-packages` flag from install.sh OR ensure that PYTHONNOUSERSITE=1 is properly set before any Python code runs.

### Option 1: Remove --system-site-packages (RECOMMENDED)

Remove the flag from install.sh and reinstall:

```bash
# In install.sh, change:
python3 -m venv --system-site-packages "$VENV_DIR"
# To:
python3 -m venv "$VENV_DIR"
```

Then install system packages that are actually needed into the venv explicitly.

### Option 2: Ensure PYTHONNOUSERSITE Works

Add PYTHONNOUSERSITE=1 to the venv activation script:

```bash
echo 'export PYTHONNOUSERSITE=1' >> /opt/eas-station/venv/bin/activate
```

## Verification Steps

After fixing, verify:

1. Check venv was created without system packages:
   ```bash
   grep -r "system-site-packages" /opt/eas-station/venv/pyvenv.cfg
   # Should show: include-system-site-packages = false
   ```

2. Verify PYTHONNOUSERSITE is set:
   ```bash
   sudo systemctl show eas-station-web.service | grep PYTHONNOUSERSITE
   ```

3. Check for package conflicts:
   ```bash
   /opt/eas-station/venv/bin/python3 -c "import sys; print('System packages:', 'NOT INCLUDED' if '--no-user-site' in sys.flags else 'INCLUDED')"
   ```

## Conclusion

**The `--system-site-packages` flag in install.sh is what broke the website**, not the EASMonitor API changes. My backwards compatibility fix for EASMonitor is still needed and correct, but it doesn't address the root cause of the 504 errors.
