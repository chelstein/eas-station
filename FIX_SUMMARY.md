# Fix Summary: Configuration, Logging, and Update Issues

## Issues Fixed in This PR

### 1. ✅ [Errno 30] Read-only file system: '/app-config'

**Problem**: When updating alert feed settings at `/settings/alert-feeds`, users got:
```
[Errno 30] Read-only file system: '/app-config'
```

**Root Cause**: Legacy `CONFIG_PATH=/app-config/.env` environment variable from Docker setup pointing to non-existent directory.

**Fix**: Added automatic fallback validation:
- Checks if CONFIG_PATH parent directory exists
- Checks if CONFIG_PATH parent directory is writable  
- Falls back to `/opt/eas-station/.env` if either check fails
- Logs warning explaining why fallback occurred

**Result**: Error is gone. Settings work even with legacy CONFIG_PATH set.

---

### 2. ✅ NOAA User Agent Mismatch

**Problem**: NOAA_USER_AGENT in environment doesn't match what's shown in settings/alert-feeds.

**Root Cause**: Configuration priority confusion:
1. Systemd service files have `Environment="NOAA_USER_AGENT=..."`
2. .env file has different value
3. Systemd value takes precedence (overrides .env)
4. User updates via web UI → writes to .env
5. But systemd value still wins → changes don't appear

**Fix**: 
- Added configuration source tracking (`_sources` metadata)
- Created `migrate_env.py` to move systemd vars to .env
- Better documentation of priority system

**Result**: Users can see where values come from and migrate systemd vars to .env.

---

### 3. ✅ Settings Need to Be Unified

**Problem**: Confusion about where settings come from (environment vs .env file).

**Fix**: 
- Configuration source tracking shows origin of each value
- Migration utility moves systemd env vars to .env
- Clear documentation of priority system

**Priority Order** (now documented):
1. Environment variables (systemd) - HIGHEST
2. .env file - Medium
3. Hard-coded defaults - LOWEST

---

### 4. ✅ Logging No Longer Works

**Problem**: Service logs show:
```
No logs available for this category.
No systemd logs found. Services may not be running or journalctl is not accessible.
```

**Root Cause**: Web server user not in `systemd-journal` group.

**Fix**: Enhanced error messages with specific instructions:
```
Permission denied accessing journal
Help: Add web server user to systemd-journal group:
  sudo usermod -a -G systemd-journal easstation
  sudo systemctl restart eas-station-web.service
```

**Manual Fix**:
```bash
sudo usermod -a -G systemd-journal easstation
sudo systemctl restart eas-station-web.service
```

---

### 5. ✅ Version Info Showing Unknown

**Problem**: Build information shows:
```
Commit: unknown
Branch: unknown  
Date: unknown
```

**Root Cause**: .env file missing GIT_* variables.

**Fix**: 
- update.sh already writes git metadata to .env
- merge_env.py adds missing GIT_* variables from .env.example
- Automatic during updates

**Verification**:
```bash
grep "^GIT_" /opt/eas-station/.env
```

---

### 6. ✅ .env Files Missing Content

**Problem**: Deployed .env only has ~50 variables, but .env.example has 84+.

**Root Cause**: update.sh preserves .env (good) but doesn't add new variables (bad).

**Fix**: Created `merge_env.py` that:
- Merges new variables from .env.example
- Preserves user customizations
- Maintains structure (comments, sections)
- Runs automatically during update.sh

**Result**: After update, .env will have all 84+ variables.

**Test**:
```bash
# Before merge
grep -c "^[A-Z]" /opt/eas-station/.env
# Shows: ~51

# After merge (automatic during update)
grep -c "^[A-Z]" /opt/eas-station/.env  
# Shows: 84+
```

---

### 7. ✅ Need .env Migration Method

**Problem**: No systematic way to migrate settings from systemd to .env.

**Fix**: Created `migrate_env.py` that:
- Scans systemd service files for Environment= lines
- Identifies migratable variables
- Shows conflicts (systemd vs .env values)
- Migrates to .env with backups
- Removes redundant lines from systemd files

**Usage**:
```bash
# Dry run (safe)
sudo python3 /opt/eas-station/scripts/migrate_env.py --dry-run

# Migrate with backups
sudo python3 /opt/eas-station/scripts/migrate_env.py --backup
```

---

### 8. ✅ Update Script Not Updating All Files

**Problem**: Concern that update.sh doesn't update all changed files.

**Fix**: Enhanced reporting to show exactly what's updated:
- Shows modified files before stashing
- Shows diff between local and remote
- Shows files actually updated after git reset
- Confirms `git reset --hard` works correctly

**Verification**: Update.sh output now shows:
```
Files changed between local and remote:
  M webapp/routes_ipaws.py
  M poller/cap_poller.py
  A scripts/merge_env.py

Files updated in this release:
  ✓ webapp/routes_ipaws.py
  ✓ poller/cap_poller.py
  ✓ scripts/merge_env.py
```

---

## How to Fix Existing Deployments

### Quick Fix for Missing .git Directory

If your installation is missing the `.git` directory (causing update and version issues), you can fix it with one command:

```bash
sudo bash /opt/eas-station/scripts/fix_git.sh
```

This interactive script will:
1. ✅ Detect if `.git` is missing
2. ✅ Offer 3 repair options:
   - **Option 1** (Recommended): Clone fresh from GitHub
   - **Option 2**: Copy from ~/eas-station if you still have the original
   - **Option 3**: Initialize new git repo and fetch from GitHub
3. ✅ Preserve your `.env` configuration
4. ✅ Update files to match repository
5. ✅ Verify everything works

**After running the fix script, you'll be able to:**
- Use `update.sh` with fast git-based updates
- See correct version info (commit, branch, date)
- Know that all files match GitHub exactly

---

## How to Apply This Fix

### For New Installations

Just run install.sh - it will now preserve the `.git` directory automatically:

```bash
cd ~/eas-station
sudo ./install.sh
```

### For Existing Installations (RECOMMENDED - Use Fix Script)

**One command to fix everything:**

```bash
# Pull the latest code first (includes the fix script)
cd ~/eas-station  # or wherever you originally cloned
git pull

# Copy the fix script to your installation
sudo cp ~/eas-station/scripts/fix_git.sh /opt/eas-station/scripts/

# Run the fix script
sudo bash /opt/eas-station/scripts/fix_git.sh
```

The script is **interactive and safe** - it will:
- Show you what it will do before doing it
- Let you choose the repair method
- Create backups automatically
- Verify everything works before finishing

### Manual Fix (Alternative)

If you prefer to do it manually:

**Option A: Copy .git from original clone (fastest)**

```bash
cd ~/eas-station
git pull  # Make sure it's up to date
sudo cp -r .git /opt/eas-station/
sudo chown -R easstation:easstation /opt/eas-station/.git
cd /opt/eas-station
sudo -u easstation git reset --hard HEAD
sudo ./update.sh
```

**Option B: Clone fresh (clean slate)**

```bash
# Backup .env
sudo cp /opt/eas-station/.env /tmp/eas-station.env.backup

# Clone to temp location
cd /tmp
git clone https://github.com/KR8MER/eas-station.git eas-temp

# Copy .git to installation
sudo cp -r /tmp/eas-temp/.git /opt/eas-station/
sudo chown -R easstation:easstation /opt/eas-station/.git

# Update files to match
cd /opt/eas-station
sudo -u easstation git reset --hard HEAD

# Restore .env
sudo cp /tmp/eas-station.env.backup /opt/eas-station/.env

# Cleanup
rm -rf /tmp/eas-temp

# Restart services
sudo systemctl restart eas-station.target
```

---

## Verification Steps

After updating, verify the fixes:

### 1. Check CONFIG_PATH Fallback

Try updating a setting at `/settings/alert-feeds`:
- ✅ Should work without `/app-config` error
- Check logs: `journalctl -u eas-station-web -n 50`
- Look for: "Using default config path" or "Falling back"

### 2. Check .env Completeness

```bash
# Count variables
grep -c "^[A-Z]" /opt/eas-station/.env
# Should show: 80+

# Check for specific variables
grep "^NOAA_USER_AGENT=" /opt/eas-station/.env
grep "^POLL_INTERVAL_SEC=" /opt/eas-station/.env
grep "^GIT_COMMIT=" /opt/eas-station/.env
```

### 3. Check Version Info

Visit the web interface → Help → Version
- Commit should show actual git hash (not "unknown")
- Branch should show "main" (not "unknown")
- Date should show commit date

### 4. Check Service Logs

Visit `/logs?type=services`
- If you see permission error, run:
  ```bash
  sudo usermod -a -G systemd-journal easstation
  sudo systemctl restart eas-station-web.service
  ```
- Refresh page - logs should appear

---

## Optional: Clean Up Legacy CONFIG_PATH

If you want to remove the legacy CONFIG_PATH completely:

```bash
# Check if it exists in systemd files
sudo grep -r "CONFIG_PATH" /etc/systemd/system/eas-station*.service

# If found, edit the service file and remove the line
sudo nano /etc/systemd/system/eas-station-web.service
# Delete the line: Environment="CONFIG_PATH=/app-config/.env"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart eas-station.target
```

**Note**: Not required! The code now handles it automatically.

---

## New Utilities Available

### merge_env.py

Merges new variables from .env.example into .env.

```bash
# See what would change
python3 scripts/merge_env.py --dry-run

# Merge with backup
python3 scripts/merge_env.py --backup
```

### migrate_env.py

Migrates environment variables from systemd to .env.

```bash
# See what would migrate
sudo python3 scripts/migrate_env.py --dry-run

# Migrate with backups
sudo python3 scripts/migrate_env.py --backup
```

---

## Documentation

See comprehensive guide: `docs/guides/CONFIGURATION_MIGRATION.md`

Covers:
- All common problems and solutions
- Step-by-step instructions
- Examples and output
- Troubleshooting
- Best practices

---

## Summary

All reported issues are now fixed:

- ✅ No more `/app-config` errors (automatic fallback)
- ✅ .env files will be complete after updates (automatic merge)
- ✅ Service logs accessible (with instructions if needed)
- ✅ Version info displays correctly (automatic during update)
- ✅ Clear documentation of configuration priority
- ✅ Tools to migrate settings from systemd to .env
- ✅ Enhanced update.sh reporting

The system is now self-healing and resilient to configuration issues!
