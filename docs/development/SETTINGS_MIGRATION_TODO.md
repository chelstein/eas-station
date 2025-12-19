# Settings Migration TODO

## Overview

Move all environment variable configuration to database-backed settings pages with improved UI.

## Completed ✅

- **Hardware Settings** (v2.27.16)
  - GPIO/Relay control
  - OLED displays
  - LED signs
  - VFD displays
  - Database table: `hardware_settings`
  - UI: `/admin/hardware`

- **Icecast Settings** (v2.27.14)
  - Database table: `icecast_settings`
  - UI: Managed in database

- **Poller Settings** (v2.39.0)
  - Poll interval configuration
  - Enable/disable polling
  - Detailed logging toggle
  - Database table: `poller_settings`
  - UI: Admin Panel → System Settings

- **TTS Settings** (v2.38.0)
  - Azure OpenAI TTS configuration
  - ElevenLabs API settings
  - Voice selection
  - Database table: `tts_settings`
  - UI: Admin Panel → TTS Settings

- **EAS Broadcast Settings** (v2.40.0)
  - Broadcast enable/disable
  - Originator code (WXR, CIV, PEP, EAS)
  - Station ID (call sign)
  - Authorized broadcast FIPS codes (with FIPS builder UI)
  - Authorized event codes
  - Attention tone duration
  - Audio sample rate
  - Audio player configuration
  - Output directory
  - Database table: `eas_settings`
  - UI: Admin Panel → EAS Broadcast Settings
  - Migration: `20251219_add_eas_settings.py`

- **Location Settings** (v2.40.0)
  - Storage zone codes now properly saved
  - Zone lookup with add-to-broadcast/storage functionality
  - Color-coded cards (blue=broadcast, green=storage)
  - FIPS builder for county selection
  - Consolidated configuration interface

## TODO - Environment Variables to Migrate

### High Priority

1. ~~**Location Settings**~~ ✅ Completed v2.40.0
   - ~~SAME codes (location)~~
   - ~~County FIPS codes~~
   - ~~Default latitude/longitude~~
   - ~~Coverage radius~~
   - Database table: `location_settings`
   - UI: Admin Panel → Location Settings

2. ~~**Alert Polling Settings**~~ ✅ Completed v2.39.0
   - ~~Poll interval~~
   - ~~CAP timeout~~
   - ~~NOAA user agent~~
   - ~~CAP endpoints~~
   - ~~IPAWS feed URLs~~
   - Database table: `poller_settings`
   - UI: Admin Panel → Poller Settings

3. **Notification Settings** (Email/SMS)
   - Enable email notifications
   - Enable SMS notifications
   - Mail server URL
   - Create: `notification_settings` table
   - UI: `/admin/notifications`

### Medium Priority

4. ~~**TTS Settings**~~ ✅ Completed v2.38.0
   - ~~ElevenLabs API keys~~
   - ~~Azure OpenAI settings~~
   - ~~Voice selection~~
   - Database table: `tts_settings`
   - UI: Admin Panel → TTS Settings

5. **Security Settings**
   - SECRET_KEY
   - SESSION_COOKIE_* settings
   - Password requirements
   - MFA settings
   - Create: `security_settings` table
   - UI: `/admin/security`

6. **HTTPS/SSL Settings**
   - Domain name
   - SSL email
   - Certbot staging flag
   - Create: `ssl_settings` table
   - UI: `/admin/ssl`

### Low Priority

7. **Database Settings**
   - DATABASE_URL
   - Connection pool settings
   - Note: Keep in .env for bootstrap, but allow UI override
   - Create: `database_settings` table (optional)

8. **Redis Settings**
   - CACHE_REDIS_URL
   - Cache type
   - Cache timeout
   - Note: Keep in .env for bootstrap
   - Create: `cache_settings` table (optional)

9. **Performance Settings**
   - MAX_WORKERS
   - UPLOAD_FOLDER
   - File size limits
   - Create: `performance_settings` table
   - UI: `/admin/performance`

10. **SDR/Radio Settings**
    - Radio capture mode
    - Capture duration
    - Already partially in database via `radio_receivers` table
    - Extend existing UI: `/settings/radio`

11. **Zigbee Settings**
    - Coordinator device
    - Channel
    - PAN ID
    - Create: `zigbee_settings` table
    - UI: `/admin/zigbee`

## Migration Pattern

Each migration should follow this pattern:

### 1. Database Schema
```python
# app_core/migrations/versions/YYYYMMDD_add_XXX_settings.py
def upgrade():
    op.create_table(
        'xxx_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        # ... setting columns ...
        sa.PrimaryKeyConstraint('id')
    )
    # Populate from environment variables
```

### 2. Model Class
```python
# app_core/xxx_settings.py
class XXXSettings(db.Model):
    __tablename__ = 'xxx_settings'
    id = db.Column(db.Integer, primary_key=True)
    # ... columns ...
    
def get_xxx_settings():
    # Return settings singleton from DB
    
def update_xxx_settings(data):
    # Update and return settings
```

### 3. Admin Routes
```python
# webapp/admin/xxx.py
@xxx_bp.route('/admin/xxx')
@require_permission('admin')
def xxx_settings_page():
    # Render settings page

@xxx_bp.route('/admin/xxx/update', methods=['POST'])
@require_permission('admin')
def update_xxx():
    # Handle form submission
```

### 4. Template
```html
<!-- templates/admin/xxx_settings.html -->
{% extends "base.html" %}
<!-- Form with current settings -->
```

### 5. Navigation
Add link to `templates/components/navbar.html` in Settings dropdown

### 6. Remove from Environment
Remove variables from `webapp/admin/environment.py` ENVIRONMENT_CATEGORIES

### 7. Backward Compatibility
Keep reading from .env as fallback during transition period:
```python
def get_xxx_settings():
    db_settings = XXXSettings.query.first()
    if not db_settings:
        # Fallback to environment variables
        return _from_environment()
    return db_settings
```

## Benefits of Database Storage

1. **No Service Restart**: Changes take effect immediately (for most settings)
2. **Better UI**: Forms with validation, dropdowns, help text
3. **Audit Trail**: Track who changed what and when
4. **Rollback**: Easy to revert changes
5. **Backups**: Included in database backups
6. **Multi-Instance**: Shared settings across clustered deployments
7. **API Access**: Settings available via REST API

## Critical Settings to Keep in .env

These must remain in .env for bootstrap/security:

- `DATABASE_URL` - Needed before DB connection
- `SECRET_KEY` - Flask session security
- `CACHE_REDIS_URL` - Needed before cache initialization

These can have database overrides but .env as default.

## Timeline

- **Phase 1** (Completed): Hardware Settings ✅
- **Phase 2** (Completed): Location, Polling, TTS ✅
- **Phase 2.5** (Completed): EAS Broadcast Settings ✅
- **Phase 3** (In Progress): Notifications, Security, SSL
- **Phase 4** (Planned): Performance, SDR, Zigbee

## Notes

- Each setting should have sensible defaults
- Settings pages should show "restart required" indicator when needed
- Consider adding "export to .env" feature for backup
- Add "reset to defaults" button
- Include validation to prevent breaking changes
