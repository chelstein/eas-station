# Database Authentication Fix - Summary

## Issue
Database authentication failures during migrations and service startup with error:
```
FATAL: password authentication failed for user "eas-station"
connection to server at "localhost" (::1), port 5432 failed
```

## Root Causes

### 1. IPv6 Connection Issues (MOST COMMON)
**The DATABASE_URL uses `localhost` which resolves to IPv6 (::1) first**, causing connection failures if PostgreSQL isn't properly configured for IPv6.

**Solution:** Use `127.0.0.1` instead of `localhost` in your DATABASE_URL to force IPv4 connections.

**Before (causes IPv6 issues):**
```
DATABASE_URL=postgresql+psycopg2://eas-station:PASSWORD@localhost:5432/alerts
```

**After (forces IPv4):**
```
DATABASE_URL=postgresql+psycopg2://eas-station:PASSWORD@127.0.0.1:5432/alerts
```

### 2. Services Not Restarted After Configuration
The most likely cause is that services were running **before** the `.env` file was properly configured with DATABASE_URL. Services need to be restarted to load new environment variables.

### 2. Optional Environment File in Poller Service
The `eas-station-poller.service` had `EnvironmentFile=-/opt/eas-station/.env` (with `-` prefix), making the environment file optional. If the file didn't exist or wasn't readable, the service would start without DATABASE_URL, causing failures.

### 3. Incorrect Database User in PostgreSQL
In some cases, a PostgreSQL user "eas_station" (with underscore) may have been created instead of the correct "eas-station" (with hyphen). This causes authentication to fail even when DATABASE_URL is correct.

## Solutions

### Solution 1: Run update.sh (RECOMMENDED - Easiest)

```bash
cd /opt/eas-station
sudo ./update.sh
```

**What it does:**
1. Stops all services
2. Backs up .env configuration
3. Updates code from GitHub (including fixed service files)
4. Reloads systemd daemon
5. Runs database migrations
6. Restarts all services with correct environment

**This is the simplest fix** - it handles everything automatically.

---

### Solution 2: Manual Service Restart (Quick Fix)

If you just need to restart services to pick up the .env file:

```bash
sudo systemctl daemon-reload
sudo systemctl restart eas-station.target
```

Or use the restart script:
```bash
sudo /opt/eas-station/scripts/restart_services.sh
```

---

### Solution 3: Fix Incorrect Database User (If Errors Persist)

If you still see authentication errors after restarting, you may have an incorrect database user:

```bash
sudo /opt/eas-station/scripts/database/fix_database_user.sh
```

**What it does:**
1. Detects incorrect users ("eas_station", "easstation", etc.)
2. Creates correct "eas-station" user with password from .env
3. Migrates all data ownership safely
4. Drops incorrect users
5. Updates PostgreSQL 15+ permissions

**This is safe and non-destructive** - it reassigns ownership before dropping users.

---

## Verification Steps

After applying any fix:

1. **Check service status:**
   ```bash
   sudo systemctl status eas-station.target
   ```

2. **Check for database errors:**
   ```bash
   sudo journalctl -u eas-station-web.service -n 50 --no-pager | grep -i "password\|database"
   sudo journalctl -u eas-station-poller.service -n 50 --no-pager | grep -i "password\|database"
   ```

3. **Verify all services are running:**
   ```bash
   sudo systemctl is-active eas-station-web.service
   sudo systemctl is-active eas-station-poller.service
   sudo systemctl is-active eas-station-audio.service
   sudo systemctl is-active eas-station-eas.service
   ```

4. **Test database connection:**
   ```bash
   sudo -u eas-station psql -d alerts -c "SELECT COUNT(*) FROM cap_alerts;"
   ```

---

## Technical Details

### Environment File Loading
Systemd services use `EnvironmentFile` to load variables from `/opt/eas-station/.env`:
- **Without `-` prefix**: File is **required** - service fails if missing
- **With `-` prefix**: File is **optional** - service starts without it

The fix changes the poller service from optional to required.

### Database URL Format
Your `.env` file should contain:
```
DATABASE_URL=postgresql+psycopg2://eas-station:PASSWORD@127.0.0.1:5432/alerts
```

Note the username is **eas-station** (with hyphen), not "eas_station" (with underscore).

### Why Services Need Restart
Environment variables are loaded when services **start**, not continuously. If you update `.env`, you must restart services for changes to take effect:
1. Systemd reads `EnvironmentFile` at service start
2. Python code reads `os.getenv('DATABASE_URL')` at import time
3. Changing `.env` doesn't affect running processes

---

## Prevention

To avoid this issue in the future:

1. **Always restart services after changing .env:**
   ```bash
   sudo systemctl restart eas-station.target
   ```

2. **Run update.sh for code updates:**
   ```bash
   sudo /opt/eas-station/update.sh
   ```
   This handles all necessary restarts automatically.

3. **Check logs after updates:**
   ```bash
   sudo journalctl -u eas-station.target -f
   ```

---

## Files Changed in This Fix

1. `systemd/eas-station-poller.service` - Made environment file required
2. `scripts/database/fix_database_user.sh` - New script to fix database users
3. `scripts/restart_services.sh` - New script to restart services with error detection
4. `scripts/database/README_fix_database_user.md` - Documentation for fix script

---

## Need More Help?

If issues persist after trying these solutions:

1. Check PostgreSQL is running:
   ```bash
   sudo systemctl status postgresql
   ```

2. Verify .env file exists and is readable:
   ```bash
   ls -la /opt/eas-station/.env
   cat /opt/eas-station/.env | grep DATABASE_URL
   ```

3. Check PostgreSQL users:
   ```bash
   sudo -u postgres psql -c "\du"
   ```

4. Review PostgreSQL logs:
   ```bash
   sudo journalctl -u postgresql -n 100
   ```
