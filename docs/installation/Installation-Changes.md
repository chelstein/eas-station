# Installation Script Changes Summary

## What Changed

The `install.sh` script has been completely redesigned to be **fully automated** and **user-friendly** for bare metal deployments.

## Key Improvements

### 1. Fully Automated Installation
- **Before**: Users had to provide database password, timezone, location, station ID, zone codes, etc.
- **After**: Users only provide admin username/password. Everything else is auto-configured.

### 2. Secure by Default
- **Auto-generated database password** using Python's `secrets` module (32 characters, URL-safe)
- **No default passwords** anywhere in the system
- **SQL injection protection** using PostgreSQL dollar-quoting for password handling
- **SECRET_KEY** auto-generated during installation (64-character hex token)

### 3. PostgreSQL 15+ Compatibility
- **Fixed permission issues** with explicit schema grants
- **GRANT ALL ON SCHEMA public** to application user
- **GRANT CREATE ON SCHEMA public** for table creation
- **ALTER SCHEMA public OWNER** to application user
- **Default privileges** set for future tables and sequences

### 4. Integrated Database Management
- **pgAdmin 4** automatically installed and configured
- **Same credentials** work for both web interface and pgAdmin
- **Pre-configured** to work out of the box

### 5. Simplified User Experience
- **One command**: `sudo ./install.sh`
- **Two prompts**: Admin username and password
- **Zero technical knowledge** required
- **Setup wizard** for operational configuration after installation

## What Users Need to Do

### Installation (5 minutes of user interaction)

```bash
git clone https://github.com/KR8MER/eas-station.git
cd eas-station
sudo ./install.sh
```

**Prompts:**
1. Administrator username (for web interface and pgAdmin)
2. Administrator password (min 12 characters)

**That's it!** Script handles everything else automatically.

### Post-Installation (via web interface)

After installation, users access the web interface and complete the **Setup Wizard** to configure:

- Location (county, state, zone codes)
- Station callsign/ID
- Alert sources (NOAA, IPAWS)
- Hardware (LED, OLED, SDR, etc.)
- EAS broadcast settings

## What Users CANNOT Break

The following settings are **hidden from users** and managed by the installation script:

- ❌ SECRET_KEY (auto-generated, 64-character)
- ❌ POSTGRES_HOST (set to localhost)
- ❌ POSTGRES_PORT (set to 5432)
- ❌ POSTGRES_DB (set to alerts)
- ❌ POSTGRES_USER (set to eas_station)
- ❌ POSTGRES_PASSWORD (auto-generated, 32-character)
- ❌ REDIS_HOST (set to localhost)
- ❌ REDIS_PORT (set to 6379)

These are removed from the setup wizard entirely in `app_utils/setup_wizard.py`.

## Technical Details

### Generated Passwords

**Database Password:**
```python
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
```
- 32 characters, URL-safe
- Stored in `/opt/eas-station/.env`
- Never exposed to user

**SECRET_KEY:**
```python
GENERATED_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```
- 64 characters (32 bytes hex-encoded)
- Stored in `/opt/eas-station/.env`
- Never exposed to user

### SQL Injection Protection

**Before (vulnerable):**
```bash
psql -c "CREATE USER eas_station WITH PASSWORD '$DB_PASSWORD';"
```

**After (secure):**
```bash
psql <<EOF
CREATE USER eas_station WITH PASSWORD \$\$${DB_PASSWORD}\$\$;
EOF
```

PostgreSQL dollar-quoting (`$$`) safely handles special characters without escaping.

### Database Permissions (PostgreSQL 15+)

```sql
GRANT ALL ON SCHEMA public TO eas_station;
GRANT CREATE ON SCHEMA public TO eas_station;
ALTER SCHEMA public OWNER TO eas_station;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO eas_station;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO eas_station;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO eas_station;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO eas_station;
```

## Files Modified

### Core Changes
- `install.sh` - Complete redesign for automated installation
- `app_utils/setup_wizard.py` - Removed system-managed fields from wizard

### New Files
- `scripts/database/fix_database_permissions.sh` - Fix permissions on existing installations
- `scripts/database/init_database.sh` - Comprehensive database initialization
- `scripts/database/README.md` - Database troubleshooting guide
- `docs/PostgreSQL-15-Fix.md` - Technical explanation of permission fix
- `docs/QUICKSTART-BARE-METAL.md` - Step-by-step installation guide

## Compatibility

- ✅ PostgreSQL 15+ (required)
- ✅ PostgreSQL 14 and earlier (backward compatible)
- ✅ Debian 11+
- ✅ Ubuntu 20.04+
- ✅ Raspbian
- ✅ Raspberry Pi 4/5
- ✅ x86_64 Linux servers

## Migration from Previous Installations

If you installed EAS Station before these changes and are experiencing database permission errors:

```bash
# Fix permissions
sudo ./scripts/database/fix_database_permissions.sh

# Re-run migrations
sudo ./scripts/database/init_database.sh

# Restart services
sudo systemctl restart eas-station.target
```

## Benefits

1. **Lower barrier to entry** - No technical knowledge required
2. **Fewer user errors** - Less to configure means less to break
3. **Better security** - Auto-generated strong passwords, no defaults
4. **Faster deployment** - Automated installation takes 10-15 minutes total
5. **Professional setup** - Includes pgAdmin for database management
6. **PostgreSQL 15+ compatible** - Works with latest database versions

## Result

Users can go from zero to a fully functional EAS Station in **under 20 minutes** with only:
- 1 command to run
- 2 prompts to answer (username/password)
- Web-based wizard for operational configuration

No manual `.env` editing, no database configuration, no SSL setup, no service management required.
