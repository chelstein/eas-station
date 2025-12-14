# Deployment Instructions - Website Timeout Fix

## Summary
**Fixed critical bug causing website to be completely inaccessible with timeouts.**

The root cause was that the systemd service was using `app:app` as the gunicorn entry point, which bypassed the entire `wsgi.py` initialization code. This caused database initialization to happen on the first HTTP request instead of at worker startup, resulting in 504 Gateway Timeout errors.

## What Was Changed
- `systemd/eas-station-web.service`: Changed from `app:app` to `wsgi:application`
- `VERSION`: Bumped to 2.27.5
- Documentation updated with root cause analysis

## How to Deploy This Fix

### Option 1: Update and Restart (Recommended)
```bash
# Navigate to installation directory
cd /opt/eas-station

# Pull the latest changes
git fetch
git checkout copilot/fix-logging-format
git pull origin copilot/fix-logging-format

# Reload systemd configuration (required after changing .service file)
sudo systemctl daemon-reload

# Restart the web service
sudo systemctl restart eas-station-web.service

# Verify it's running
sudo systemctl status eas-station-web.service
```

### Option 2: Full Update Script
```bash
cd /opt/eas-station
./update.sh
```

## Verification Steps

### 1. Check Service Status
```bash
sudo systemctl status eas-station-web.service
```

**Expected output:**
- Status should be "active (running)"
- No errors about database initialization
- Workers should start successfully

### 2. Check Startup Logs
```bash
sudo journalctl -u eas-station-web.service -n 100 --no-pager
```

**Look for these messages** (indicating successful startup):
```
WSGI PRE-IMPORT: Worker PID XXXX about to import app module...
WSGI POST-IMPORT: Worker PID XXXX successfully imported app module
WSGI STARTUP: Worker PID XXXX initializing database...
WSGI STARTUP: Worker PID XXXX database initialization complete ✓
```

**Should NOT see:**
- "Database initialization failed"
- "504 Gateway Timeout"
- "Worker timeout"
- Multiple workers trying to initialize database simultaneously

### 3. Test Website Access
```bash
# Test from command line
curl -I http://localhost:5000/

# Or open in browser
http://your-server-ip:5000/
```

**Expected:** Website loads immediately without timeout

### 4. Verify Database Connection
```bash
# Check that database is accessible
psql -U eas_station -d eas_station -c "SELECT COUNT(*) FROM cap_alerts;"
```

## Troubleshooting

### If Service Won't Start

1. **Check if systemd config is reloaded:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart eas-station-web.service
   ```

2. **Check PostgreSQL is running:**
   ```bash
   sudo systemctl status postgresql
   ```

3. **Check database credentials:**
   ```bash
   grep DATABASE_URL /opt/eas-station/.env
   ```

4. **Check for errors in logs:**
   ```bash
   sudo journalctl -u eas-station-web.service -n 200 --no-pager | grep -i "error\|fatal\|failed"
   ```

### If Website Still Times Out

1. **Verify the fix was applied:**
   ```bash
   grep "wsgi:application" /opt/eas-station/systemd/eas-station-web.service
   ```
   
   Should show:
   ```
   wsgi:application
   ```
   
   If it still shows `app:app`, the file wasn't updated. Re-run deployment steps.

2. **Check if old service file is in use:**
   ```bash
   # Check actual service file location
   systemctl cat eas-station-web.service | grep "wsgi:application"
   ```
   
   If it doesn't show `wsgi:application`, the systemd service is using a different file location. Find it with:
   ```bash
   systemctl show eas-station-web.service | grep FragmentPath
   ```

3. **Reinstall service file:**
   ```bash
   sudo cp /opt/eas-station/systemd/eas-station-web.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl restart eas-station-web.service
   ```

## What This Fix Does

### Before (Broken)
1. Gunicorn starts with `app:app`
2. Loads `app.py` directly
3. `wsgi.py` is never executed
4. Database initialization happens in `@app.before_request` handler
5. First HTTP request triggers DB init
6. DB init takes 10+ seconds
7. Request times out → 504 Gateway Timeout
8. Website is inaccessible

### After (Fixed)
1. Gunicorn starts with `wsgi:application`
2. Loads `wsgi.py` first
3. `wsgi.py` eagerly initializes database BEFORE accepting requests
4. Workers become ready only after DB is initialized
5. First HTTP request is instant (DB already ready)
6. No timeouts, no race conditions
7. Website works immediately

## Technical Details

### Why wsgi.py Instead of app.py?

The `wsgi.py` file is specifically designed as the production entry point for WSGI servers like Gunicorn. It:
- Configures logging early (before app import)
- Initializes database eagerly (at worker startup, not on first request)
- Provides comprehensive error handling with diagnostic output
- Handles setup mode properly
- Ensures workers are fully ready before accepting connections

### Why Was app:app Being Used?

This appears to have been a long-standing configuration issue. The systemd service file has been using `app:app` for a while, which works for development but causes issues in production with multiple workers and lazy initialization.

### Database Initialization Timing

**Lazy initialization (app:app):**
- Pros: Fast startup
- Cons: First request slow, race conditions, timeouts, hard to debug

**Eager initialization (wsgi:application):**
- Pros: Predictable startup, no race conditions, no request timeouts, better error messages
- Cons: Slightly slower worker startup (but workers don't accept requests until ready)

## Support

If you encounter any issues after deploying this fix:
1. Check the logs as described in Troubleshooting section
2. Verify PostgreSQL is running
3. Ensure database credentials in `.env` are correct
4. Check that you ran `sudo systemctl daemon-reload` after updating the service file

For persistent issues, check `/var/log/eas-station/` for detailed error logs created by wsgi.py during startup.
