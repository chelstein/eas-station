# Configuration Migration and Merge Guide

This guide explains how to use the configuration management utilities to fix common issues with environment variables and .env files.

## Common Problems

### Problem 1: .env File Missing Variables

**Symptom**: Your .env file only has ~50 variables, but .env.example has 84+

**Cause**: When you run `update.sh`, it preserves your existing .env file but doesn't add new variables that were added to .env.example in newer versions.

**Solution**: Run the merge utility to add missing variables while preserving your customizations.

```bash
# See what would be added (safe, no changes)
sudo python3 /opt/eas-station/scripts/merge_env.py --dry-run

# Merge with backup (recommended)
sudo python3 /opt/eas-station/scripts/merge_env.py --backup

# Restart services to pick up new configuration
sudo systemctl restart eas-station.target
```

**What it does**:
- ✅ Adds all missing variables from .env.example
- ✅ Preserves your custom values (passwords, API keys, etc.)
- ✅ Keeps your custom variables not in .env.example
- ✅ Maintains .env.example structure (comments, sections)
- ✅ Creates timestamped backup before making changes

### Problem 2: Settings Updated in Web UI Don't Take Effect

**Symptom**: You update settings in `/settings/alert-feeds` but changes don't apply. Old values keep appearing.

**Cause**: Systemd service files have `Environment=` lines that override .env file values. For example:

```ini
# In /etc/systemd/system/eas-station-web.service
Environment="NOAA_USER_AGENT=Old Value"
```

This overrides whatever you put in .env file.

**Solution**: Migrate environment variables from systemd files to .env file.

```bash
# See what would be migrated (safe, no changes)
sudo python3 /opt/eas-station/scripts/migrate_env.py --dry-run

# Migrate with backups (recommended)
sudo python3 /opt/eas-station/scripts/migrate_env.py --backup

# Restart services to pick up new configuration
sudo systemctl restart eas-station.target
```

**What it does**:
- ✅ Finds environment variables in systemd service files
- ✅ Moves them to .env file (systemd values take precedence during merge)
- ✅ Removes redundant Environment= lines from systemd files
- ✅ Shows configuration conflicts and resolution
- ✅ Creates backups of both .env and service files

### Problem 3: Version Info Shows "Unknown"

**Symptom**: Build information shows:
```
Commit: unknown
Branch: unknown
Date: unknown
```

**Cause**: Git metadata not being written to .env file, or .env is missing GIT_* variables.

**Solution**: This is automatically fixed by update.sh (writes git metadata to .env), but you can verify:

```bash
# Check if git metadata exists
grep "^GIT_" /opt/eas-station/.env

# If missing, run merge to add the variables
sudo python3 /opt/eas-station/scripts/merge_env.py --backup

# Then run update.sh to populate them
sudo /opt/eas-station/update.sh
```

### Problem 4: Journalctl Access Denied (Service Logs)

**Symptom**: Service logs show:
```
No systemd logs found. Services may not be running or journalctl is not accessible.
```

**Cause**: Web server user doesn't have permission to read systemd journal.

**Solution**: Add web server user to systemd-journal group.

```bash
# Add user to group (replace 'www-data' with your web server user)
sudo usermod -a -G systemd-journal www-data

# For EAS Station installations, the user is typically 'easstation'
sudo usermod -a -G systemd-journal easstation

# Restart web service
sudo systemctl restart eas-station-web.service
```

**Verification**:
```bash
# Check user's groups
groups easstation

# Should include: ... systemd-journal ...
```

## Utility Reference

### merge_env.py

Merges new variables from .env.example into existing .env file.

**Usage**:
```bash
# Basic usage (uses /opt/eas-station by default)
python3 scripts/merge_env.py [options]

# Custom installation directory
python3 scripts/merge_env.py --install-dir /path/to/install

# Options
--dry-run           # Show what would be done without making changes
--backup            # Create timestamped backup before making changes
--force             # Create .env from .env.example if .env doesn't exist
--install-dir PATH  # Installation directory (default: /opt/eas-station)
```

**Output**:
- Shows how many variables will be added
- Lists custom variables that will be preserved
- Identifies user customizations
- Creates backup: `.env.YYYYMMDD-HHMMSS.backup`

**Example**:
```bash
$ sudo python3 scripts/merge_env.py --dry-run

Configuration Analysis:
  Variables in .env.example:  84
  Variables in existing .env: 51
  New variables to add:       55  ← Missing variables
  Custom variables (kept):    22  ← Your additions
  User-customized values:     14  ← Your changes
```

### migrate_env.py

Migrates environment variables from systemd service files to .env file.

**Usage**:
```bash
# Basic usage (must run as root)
sudo python3 scripts/migrate_env.py [options]

# Options
--dry-run           # Show what would be done without making changes
--backup            # Create timestamped backups before making changes
--install-dir PATH  # Installation directory (default: /opt/eas-station)
--systemd-dir PATH  # Systemd directory (default: /etc/systemd/system)
```

**What it migrates**:
- NOAA_USER_AGENT
- IPAWS_CAP_FEED_URLS
- CAP_ENDPOINTS
- POLL_INTERVAL_SEC
- CONFIG_PATH
- LOG_LEVEL
- Database connection settings
- Redis settings

**What it keeps in systemd** (system-level):
- PATH
- PYTHONUNBUFFERED
- PYTHONPATH
- HOME, USER, LOGNAME

**Example**:
```bash
$ sudo python3 scripts/migrate_env.py --dry-run

Found 3 service file(s)
  • eas-station-web.service
  • eas-station-poller.service
  • eas-station-sdr.service

Found 5 migratable variable(s):
  • NOAA_USER_AGENT=EAS Station/2.12
  • POLL_INTERVAL_SEC=120
  • POSTGRES_PASSWORD=***
  • REDIS_URL=redis://localhost:6379/0
  • LOG_LEVEL=INFO

Configuration conflicts:
  • NOAA_USER_AGENT
    .env file:    My Custom User Agent
    systemd:      EAS Station/2.12
    → Will use systemd value (currently active)
```

## Automatic Execution

### During Updates

The merge utility runs automatically during `update.sh`:

1. Backs up existing .env
2. Pulls latest code (includes updated .env.example)
3. Runs `merge_env.py --backup`
4. Adds new variables while preserving customizations
5. Writes git metadata to .env

**No manual intervention needed** - updates now keep your .env file complete!

## Best Practices

### After Installation

1. **Review merged .env**: Check that your custom values are correct
2. **Remove defaults**: Change placeholder values (passwords, API keys, etc.)
3. **Migrate from systemd**: Run `migrate_env.py` if you have Environment= lines in service files

### Before Updates

1. **Backup manually** (optional - update.sh does this automatically):
   ```bash
   cp /opt/eas-station/.env /opt/eas-station/.env.manual-backup
   ```

### After Updates

1. **Check for new variables**: Run `merge_env.py --dry-run` to see if anything is missing
2. **Review changes**: Check the .env file for new configuration options
3. **Update as needed**: Configure new features (TTS, GPIO, etc.)

## Troubleshooting

### Merge Failed

**Error**: "Permission denied"

**Solution**: Run with sudo
```bash
sudo python3 scripts/merge_env.py --backup
```

### Variables Still Missing

**Check**:
1. Did merge actually run? Look for "Merge complete!" message
2. Check the .env file directly: `less /opt/eas-station/.env`
3. Count variables: `grep -c "^[A-Z]" /opt/eas-station/.env`
   - Should be 80+ after merge
   - Less than 60 means merge didn't work

**Fix**:
```bash
# Force a fresh merge
sudo python3 /opt/eas-station/scripts/merge_env.py --backup --install-dir /opt/eas-station
```

### Settings Still Not Working

**Check configuration priority**:
```bash
# Check if systemd has environment variables
grep -r "Environment=" /etc/systemd/system/eas-station*.service

# If found, migrate them
sudo python3 /opt/eas-station/scripts/migrate_env.py --backup
sudo systemctl daemon-reload
sudo systemctl restart eas-station.target
```

### Backup Restoration

**To restore from backup**:
```bash
# List backups
ls -lt /opt/eas-station/.env.*.backup

# Restore specific backup
sudo cp /opt/eas-station/.env.20251212-143022.backup /opt/eas-station/.env
sudo systemctl restart eas-station.target
```

## Configuration Priority Explained

**How settings are loaded** (priority order):

1. **Environment variables** (from systemd service files) - HIGHEST
   ```ini
   # /etc/systemd/system/eas-station-web.service
   Environment="NOAA_USER_AGENT=From Systemd"
   ```

2. **.env file** (persistent configuration)
   ```bash
   # /opt/eas-station/.env
   NOAA_USER_AGENT=From Env File
   ```

3. **Hard-coded defaults** (in Python code) - LOWEST

**Result**: Systemd value wins if both are set!

**Best Practice**: Use .env file for all configuration, remove Environment= lines from systemd files.

## Related Documentation

- [Installation Guide](../installation/README.md)
- [Update Guide](../QUICKSTART-BARE-METAL.md#updating)
- [Configuration Reference](../reference/CONFIGURATION.md)
- [Troubleshooting Guide](../troubleshooting/README.md)
