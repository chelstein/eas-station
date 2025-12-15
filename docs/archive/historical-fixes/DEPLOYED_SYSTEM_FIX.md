# Quick Fix Guide for Deployed Systems

## Problem
Website returns 504 Gateway Timeout errors after PR #1356.

## Root Cause
Virtual environment was created with `--system-site-packages` flag, causing package conflicts.

## Quick Fix (5 minutes)

### Option 1: Automated Script (Recommended)

```bash
# Download and run the fix script
curl -o /tmp/fix_website_504.sh https://raw.githubusercontent.com/KR8MER/eas-station/copilot/fix-broken-logs/scripts/fix_website_504.sh
sudo bash /tmp/fix_website_504.sh
```

The script will:
- ✓ Stop services
- ✓ Backup current venv
- ✓ Recreate venv WITHOUT system-site-packages
- ✓ Reinstall dependencies
- ✓ Restart services
- ✓ Verify fix

### Option 2: Manual Fix

```bash
# 1. Stop services
sudo systemctl stop eas-station.target

# 2. Remove broken venv
sudo rm -rf /opt/eas-station/venv

# 3. Create new venv (WITHOUT --system-site-packages)
sudo -u eas-station python3 -m venv /opt/eas-station/venv

# 4. Install dependencies
cd /opt/eas-station
sudo -u eas-station ./venv/bin/pip install --upgrade pip
sudo -u eas-station ./venv/bin/pip install -r requirements.txt

# 5. Restart services
sudo systemctl daemon-reload
sudo systemctl start eas-station.target
```

### Verification

```bash
# Check venv config (should show "false")
grep "include-system-site-packages" /opt/eas-station/venv/pyvenv.cfg

# Test website (should return HTTP 200)
curl -f http://localhost:5000/api/health

# Check service status (should show "active (running)")
sudo systemctl status eas-station-web.service
```

## Expected Results

After fix:
- ✅ Website loads normally
- ✅ No 504 errors
- ✅ Gunicorn workers start successfully
- ✅ No C extension import errors

## Troubleshooting

If still not working:

1. **Check logs for errors:**
   ```bash
   sudo journalctl -u eas-station-web.service -n 100 --no-pager
   ```

2. **Verify no port conflicts:**
   ```bash
   sudo netstat -tlnp | grep :5000
   ```

3. **Test manual startup:**
   ```bash
   sudo -u eas-station /opt/eas-station/venv/bin/python3 /opt/eas-station/wsgi.py
   ```

4. **Check nginx configuration:**
   ```bash
   sudo nginx -t
   sudo systemctl status nginx
   ```

## What This Fixes

1. **Primary Issue**: Removes `--system-site-packages` from venv
   - Eliminates C extension conflicts (numpy, scipy, gevent)
   - Prevents import errors during gunicorn startup
   - Fixes 504 timeout errors

2. **Secondary Issue**: EASMonitor backwards compatibility (already in code)
   - Fixes `audio_manager` TypeError in EAS service
   - Allows old code to work with new API

## Need Help?

See detailed documentation:
- **ROOT_CAUSE_ANALYSIS.md** - Technical explanation
- **WEBSITE_504_FIX.md** - Full fix summary
- **scripts/fix_website_504.sh** - Automated fix script

Or check logs:
```bash
sudo journalctl -u eas-station-web.service -f
```
