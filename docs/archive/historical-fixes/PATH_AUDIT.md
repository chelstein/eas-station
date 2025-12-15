# Thorough Path Audit - All Hardcoded Paths Fixed

## Summary
Performed comprehensive audit of all hardcoded paths in the codebase. All Docker-era paths have been fixed for bare metal deployment.

## Paths Fixed

### 1. Configuration Files
- ✅ `webapp/routes_ipaws.py`: `/app-config/.env` → `{project_root}/.env`
- ✅ `poller/cap_poller.py`: `/app-config/.env` → `{project_root}/.env`
- ✅ `systemd/eas-station-poller.service`: `/app-config/.env` → `/opt/eas-station/.env`
- ✅ `.env.example`: Updated to reflect bare metal defaults

### 2. Directory Paths
- ✅ `webapp/admin/environment.py`: `/app/captures` → `/opt/eas-station/radio_captures`
- ✅ `webapp/admin/environment.py`: `/app/uploads` → `/opt/eas-station/uploads`
- ✅ `.env.example`: `RADIO_CAPTURE_DIR=/app/captures` → `/opt/eas-station/radio_captures`
- ✅ `.env.example`: `UPLOAD_FOLDER=/app/uploads` → `/opt/eas-station/uploads`

### 3. Stream Profiles
- ✅ `app_core/audio/stream_profiles.py`: `/app-config/stream-profiles` → `{project_root}/stream-profiles`

### 4. SSL Certificates
- ✅ `webapp/admin/environment.py`: Removed `/app-config/certs/live`, added `{project_root}/certs/live`
- ✅ **Verified**: `/etc/letsencrypt/live` is CORRECT (standard certbot path)

## Paths Verified as Correct

### Let's Encrypt SSL Certificates
**Path**: `/etc/letsencrypt/live/{domain}/`
- ✅ This is the standard system path used by certbot
- ✅ Used by install.sh for certificate generation
- ✅ Referenced in nginx configuration
- ✅ No changes needed

**Search order**:
1. `/etc/letsencrypt/live/{domain}/` - Standard Let's Encrypt (primary)
2. `/opt/eas-station/certs/live/{domain}/` - Project directory (fallback)

### External URLs (Not Application Paths)
- `app_utils/system.py`: `https://www.raspberrypi.com/app/uploads/...` (Raspberry Pi website URL)
  - ✅ This is a web URL, not a filesystem path

## Files Excluded from Changes

### Docker-Specific Tools (Intentionally Left Unchanged)
- `tools/restore_backup.py`: Docker volume backup tool (Docker-specific functionality)
- `tools/validate_restore.py`: Now uses project directory (already fixed in earlier commit)

### Legacy Files
- `legacy/*`: Old code preserved for reference, not active

## Verification Commands Used

```bash
# Search for all /app-config references
grep -r "/app-config" --include="*.py" --include="*.sh" --include="*.service"

# Search for all /app/ references
grep -r "/app/\|/app-config" --include="*.service" --include="*.py" --include="*.sh"

# Verify Let's Encrypt path usage
grep -rn "letsencrypt\|certbot" --include="*.py" --include="*.sh"

# Check all systemd services
find systemd -name "*.service" -type f
```

## Final State - Bare Metal Paths

All paths now correctly use `/opt/eas-station` as the base directory for bare metal installations:

```
/opt/eas-station/
├── .env                        # Configuration file
├── radio_captures/             # SDR capture files
├── uploads/                    # User uploads
├── stream-profiles/            # Icecast stream profiles
└── certs/                      # Self-signed certs (fallback)
    └── live/{domain}/
```

System paths (standard Linux locations):
```
/etc/letsencrypt/live/{domain}/ # Let's Encrypt certificates (primary)
```

## Environment Variable Overrides

For custom deployments or Docker compatibility:
- `CONFIG_PATH` - Override config file location
- `STREAM_PROFILES_DIR` - Override stream profiles directory
- `RADIO_CAPTURE_DIR` - Override radio capture directory
- `UPLOAD_FOLDER` - Override upload directory

Example for Docker:
```bash
export CONFIG_PATH=/app-config/.env
export STREAM_PROFILES_DIR=/app-config/stream-profiles
export RADIO_CAPTURE_DIR=/app/captures
export UPLOAD_FOLDER=/app/uploads
```
