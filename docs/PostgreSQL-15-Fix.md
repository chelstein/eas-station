# PostgreSQL 15+ Permission Fix

## Problem

When running `install.sh` on systems with PostgreSQL 15 or later, the database initialization fails with errors like:

```
ERROR:app:Database initialization failed: (psycopg2.errors.InsufficientPrivilege) permission denied for schema public
LINE 2: CREATE TABLE roles (
```

And runtime errors:

```
ERROR: (psycopg2.errors.UndefinedTable) relation "rwt_schedule_config" does not exist
ERROR: (psycopg2.errors.UndefinedTable) relation "screen_rotations" does not exist
```

## Root Cause

PostgreSQL 15 introduced a security change where regular users no longer have automatic CREATE privileges on the `public` schema. Previously, `GRANT ALL PRIVILEGES ON DATABASE` was sufficient, but now explicit schema-level permissions are required.

## Solution

### For New Installations

The `install.sh` script has been updated to include the necessary permission grants:

```bash
# Grant schema privileges (required for PostgreSQL 15+)
sudo -u postgres psql -d alerts -c "GRANT ALL ON SCHEMA public TO eas_station;"
sudo -u postgres psql -d alerts -c "GRANT CREATE ON SCHEMA public TO eas_station;"
sudo -u postgres psql -d alerts -c "ALTER SCHEMA public OWNER TO eas_station;"

# Grant privileges on all existing tables and sequences
sudo -u postgres psql -d alerts -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO eas_station;"
sudo -u postgres psql -d alerts -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO eas_station;"

# Grant default privileges for future objects
sudo -u postgres psql -d alerts -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO eas_station;"
sudo -u postgres psql -d alerts -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO eas_station;"
```

Just run the updated `install.sh` script as normal:

```bash
sudo ./install.sh
```

### For Existing Installations

If you've already run `install.sh` and are experiencing permission errors, use the database fix script:

```bash
# Make scripts executable (if needed)
chmod +x scripts/database/fix_database_permissions.sh
chmod +x scripts/database/init_database.sh

# Fix permissions
sudo ./scripts/database/fix_database_permissions.sh

# Then re-run migrations
sudo ./scripts/database/init_database.sh
```

Or manually:

```bash
# Fix permissions
sudo ./scripts/database/fix_database_permissions.sh

# Run migrations
cd /opt/eas-station
sudo -u eas-station /opt/eas-station/venv/bin/alembic upgrade head

# Restart services
sudo systemctl restart eas-station.target
```

## What Was Changed

### Files Modified

1. **install.sh** 
   - Added PostgreSQL 15+ compatible permission grants
   - Made installation interactive with minimal prompts
   - Collects only database password and timezone upfront
   - Creates admin account during installation
   - Directs users to setup wizard for location/station configuration

### Files Added

1. **scripts/database/fix_database_permissions.sh** - Standalone script to fix permissions on existing installations
2. **scripts/database/init_database.sh** - Comprehensive database initialization script
3. **scripts/database/README.md** - Database utilities documentation

## Verification

After running the fix, verify tables exist:

```bash
sudo -u postgres psql -d alerts -c "\dt"
```

You should see tables including:
- rwt_schedule_config
- screen_rotations
- display_screens
- roles
- users
- alert_sources
- And many more...

## Technical Details

### Database Configuration

The install.sh script creates:
- **Database**: `alerts`
- **Username**: `eas_station`
- **Password**: Set by user during installation (no default)
- **Host**: `localhost`
- **Port**: `5432`

These credentials are automatically written to `/opt/eas-station/.env`

**Security Note**: The installer never uses default passwords. Users must provide their own secure database password during installation.

### Why This Happened

From PostgreSQL 15 release notes:

> "The public schema is no longer world-writable. Previously, all users had CREATE and USAGE privileges on the public schema. Now, only the database owner has those privileges by default."

This change improves security but requires explicit permission grants for application users.

## Compatibility

- ✅ PostgreSQL 15 and later (required)
- ✅ PostgreSQL 14 and earlier (backward compatible)
- ✅ Bare metal deployments
- ✅ All Linux distributions (tested on Debian, Ubuntu, Raspbian)

## References

- [PostgreSQL 15 Release Notes](https://www.postgresql.org/docs/15/release-15.html)
- [PostgreSQL GRANT Documentation](https://www.postgresql.org/docs/current/sql-grant.html)
- [PostgreSQL ALTER DEFAULT PRIVILEGES](https://www.postgresql.org/docs/current/sql-alterdefaultprivileges.html)
