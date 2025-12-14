# Web App Startup Issue - Root Cause Analysis and Fix

**Date:** 2025-12-14  
**Version:** 2.27.4  
**Issue:** Web app failing to start with no logs

## Root Cause

The application startup failure was caused by **wsgi.py attempting to initialize the database even when app.py had already detected the database was unavailable**.

### The Problem

1. **app.py** (during module import):
   - Calls `check_database_connectivity()` 
   - Detects database is unavailable
   - Sets `SETUP_MODE = True` with reason `'database'`
   - Continues initialization to allow /setup UI to run

2. **wsgi.py** (after app.py imports):
   - Ignores setup mode status
   - Attempts `initialize_database()` anyway
   - Tries to connect to unavailable database
   - Previously: Raised RuntimeError and crashed
   - This prevented the /setup UI from being accessible

### The Architecture Conflict

The app has built-in "setup mode" functionality that allows it to start without a database and present a /setup web UI for configuration. However, wsgi.py was fighting against this design by forcing database initialization during worker startup, regardless of whether the database was available.

## The Fix

Modified `wsgi.py` line 64 to respect setup mode:

```python
# Before:
if not os.environ.get("SKIP_DB_INIT"):

# After:  
if not os.environ.get("SKIP_DB_INIT") and not application.config.get('SETUP_MODE'):
```

Added else clause to log when setup mode is active:

```python
elif application.config.get('SETUP_MODE'):
    logger.warning("WSGI: Skipping database initialization - application is in setup mode (%s)", setup_reasons)
    logger.warning("WSGI: Visit /setup to complete configuration")
```

## Benefits

1. **Respects App Architecture** - wsgi.py now honors the setup mode flag set by app.py
2. **Eliminates Duplicate Attempts** - No redundant database connection attempts when connectivity already failed
3. **Cleaner Logs** - Single set of error messages instead of duplicates from app.py and wsgi.py
4. **Proper Failure Mode** - App starts in setup mode when database unavailable, allowing configuration through /setup UI
5. **Production Ready** - When database IS available, initialization proceeds normally

## Testing Results

### Without Database (Setup Mode)
```
✓ app.py detects database unavailable
✓ Sets SETUP_MODE = True with reason 'database'
✓ wsgi.py detects setup mode and skips database init
✓ Application starts successfully
✓ HTTP requests redirect to /setup for configuration
```

### With Database (Normal Mode)
```
✓ app.py detects database is available
✓ Sets SETUP_MODE = False
✓ wsgi.py proceeds with database initialization
✓ All 15 initialization steps complete successfully
✓ Application fully operational
✓ HTTP requests work normally
```

## Production Deployment Requirements

For the app to start successfully in production, the following must be present:

1. **PostgreSQL 16+ running** with PostGIS extension
   ```bash
   sudo systemctl start postgresql
   sudo -u postgres psql -d alerts -c "CREATE EXTENSION IF NOT EXISTS postgis;"
   ```

2. **Database and user created**
   ```bash
   sudo -u postgres createuser eas_station --password
   sudo -u postgres createdb -O eas_station alerts
   ```

3. **.env file** with DATABASE_URL and other required configuration
   ```
   DATABASE_URL=postgresql+psycopg2://eas_station:password@localhost:5432/alerts
   SECRET_KEY=<random-64-character-hex-string>
   ```

4. **Python dependencies installed**
   ```bash
   pip install -r requirements.txt
   ```

## Related Changes

- **VERSION**: Bumped from 2.27.3 to 2.27.4 (bug fix)
- **CHANGELOG**: Documented fix under "Unreleased" section
- **wsgi.py**: Added setup mode check before database initialization

## Files Modified

- `wsgi.py` - Added setup mode check
- `VERSION` - Bumped to 2.27.4
- `docs/reference/CHANGELOG.md` - Documented fix
