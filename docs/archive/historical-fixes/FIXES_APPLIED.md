# Fixes Applied: Alert Feeds Configuration Issue

## Problem Statement
When visiting `/settings/alert-feeds` and trying to update polling configuration, users encountered:
```
[Errno 30] Read-only file system: '/app-config'
```

## Root Cause
The application had hardcoded paths from a previous Docker-based architecture:
- `/app-config/.env` - Docker persistent volume path
- `/app-config/stream-profiles` - Docker profile storage
- `/app-config/certs/live` - Docker certificate storage

The system has since migrated to **bare metal installation**, where:
- Root filesystem is read-only (standard Linux security)
- `/app-config` directory doesn't exist and can't be created
- Configuration should use the project directory instead

## Files Fixed

### 1. `webapp/routes_ipaws.py`
**Changed:** Default config path from `/app-config/.env` to `{project_root}/.env`
- `_get_config_path()`: Now returns project directory `.env` by default
- `_update_env_file()`: Added better error handling with clear permission messages
- Supports `CONFIG_PATH` environment variable override for custom deployments

### 2. `poller/cap_poller.py`
**Changed:** Default config path from `/app-config/.env` to `{project_root}/.env`
- `_resolve_config_path()`: Now returns project directory `.env` by default
- Removed Docker-specific comments
- Updated logging messages to reflect bare metal deployment

### 3. `app_core/audio/stream_profiles.py`
**Changed:** Default profiles directory from `/app-config/stream-profiles` to `{project_root}/stream-profiles`
- Added `_get_default_profiles_dir()` function
- Supports `STREAM_PROFILES_DIR` environment variable override
- Updated docstrings to reflect bare metal installation

### 4. `webapp/admin/environment.py`
**Changed:** SSL certificate search paths
- Removed `/app-config/certs/live` hardcoded path
- Added project directory relative path: `{project_root}/certs/live`
- Still searches `/etc/letsencrypt/live` first (standard Let's Encrypt location)

### 5. `tools/validate_restore.py`
**Changed:** Configuration file search paths
- Removed Docker-specific paths (`/app-config/.env`, `/app/.env`)
- Now searches project directory and current directory only
- Updated for bare metal validation

### 6. `templates/settings/alert_feeds.html`
**Added:** CSS styling for textarea element
- Custom feeds textarea now properly styled
- Consistent with other form elements
- Better user experience

## How It Works Now

### Configuration File Location
```
Priority order:
1. $CONFIG_PATH (if set) - allows custom override
2. {project_root}/.env - default for bare metal
```

### For Bare Metal Installation (Default)
```bash
# Config file location
/opt/eas-station/.env

# Stream profiles location
/opt/eas-station/stream-profiles/

# SSL certificates location
/etc/letsencrypt/live/{domain}/
# or /opt/eas-station/certs/live/{domain}/
```

### For Docker/Container Deployment (Optional)
Set environment variable to use custom path:
```bash
export CONFIG_PATH=/app-config/.env
export STREAM_PROFILES_DIR=/app-config/stream-profiles
```

## Testing Recommendations

1. **Test Configuration Updates**
   ```bash
   # Navigate to /settings/alert-feeds
   # Update NOAA user agent
   # Update IPAWS settings
   # Update custom feeds
   # Verify changes are saved to project_root/.env
   ```

2. **Test Polling**
   ```bash
   # Run poller manually
   python3 poller/cap_poller.py --continuous --interval 120
   # Verify it loads config from project_root/.env
   # Check logs for "Using fallback config path" messages (should NOT appear)
   ```

3. **Verify No Permission Errors**
   ```bash
   # Check that no "[Errno 30] Read-only file system" errors occur
   # Verify config file is created/updated in project directory
   # Confirm stream profiles directory is created if needed
   ```

## Benefits

1. **Works Out of the Box**: No need to create `/app-config` or modify root filesystem
2. **Follows Linux Best Practices**: Uses project directory for application data
3. **Flexible**: Supports custom paths via environment variables
4. **Better Error Messages**: Clear guidance when permission issues occur
5. **Docker Compatible**: Can still use Docker paths with CONFIG_PATH override

## Migration Notes

For existing installations with `/app-config/.env`:
- If `/app-config` exists and is writable, set `CONFIG_PATH=/app-config/.env`
- Or copy `/app-config/.env` to project directory: `cp /app-config/.env /opt/eas-station/.env`
- Update systemd service files to set `CONFIG_PATH` if using custom location
