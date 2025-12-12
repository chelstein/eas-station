# 🚀 Quick Fix Guide - One Command Solution

## For Existing Deployments

### Having Issues? Run This One Command:

```bash
sudo bash /opt/eas-station/scripts/fix_git.sh
```

**This fixes:**
- ✅ Version showing "unknown"
- ✅ Updates not working properly
- ✅ Files not matching GitHub
- ✅ Read-only /app-config errors

---

## Step-by-Step (Copy & Paste)

### 1. Get Latest Code

```bash
cd ~/eas-station
git pull
```

### 2. Copy Fix Script to Installation

```bash
sudo cp ~/eas-station/scripts/fix_git.sh /opt/eas-station/scripts/
sudo cp ~/eas-station/scripts/merge_env.py /opt/eas-station/scripts/
sudo cp ~/eas-station/scripts/migrate_env.py /opt/eas-station/scripts/
sudo chmod +x /opt/eas-station/scripts/*.sh /opt/eas-station/scripts/*.py
```

### 3. Run the Fix

```bash
sudo bash /opt/eas-station/scripts/fix_git.sh
```

Choose **Option 1** (Clone fresh from GitHub) - it's the safest and most reliable.

### 4. Merge Missing .env Variables

```bash
sudo python3 /opt/eas-station/scripts/merge_env.py --backup
```

### 5. Restart Services

```bash
sudo systemctl restart eas-station.target
```

### 6. Verify Everything Works

```bash
# Check version info
cd /opt/eas-station
git log -1 --oneline

# Check .env completeness
grep -c "^[A-Z]" .env
# Should show 80+ (not 50)

# Visit web interface
# Go to Help → Version
# Should show actual commit, branch, and date (not "unknown")
```

---

## What Each Script Does

### `fix_git.sh` - Fixes Update Issues
Restores the `.git` directory that was accidentally excluded during installation.

**Before:** No .git → version unknown → updates broken  
**After:** Has .git → version correct → updates work

### `merge_env.py` - Adds Missing Configuration
Adds all new variables from .env.example to your .env file.

**Before:** 51 variables in .env (missing 33)  
**After:** 84 variables in .env (complete)

### `migrate_env.py` - Fixes Setting Conflicts
Moves environment variables from systemd files to .env.

**Before:** systemd vars override .env → settings don't stick  
**After:** all in .env → settings work as expected

---

## Troubleshooting

### "Permission denied"
```bash
# Make sure you're using sudo
sudo bash /opt/eas-station/scripts/fix_git.sh
```

### "Script not found"
```bash
# Copy from your original clone first
sudo cp ~/eas-station/scripts/fix_git.sh /opt/eas-station/scripts/
```

### "Git repository is healthy"
```bash
# .git already exists - no fix needed!
# Just run update.sh to get latest changes
cd /opt/eas-station
sudo ./update.sh
```

---

## After the Fix

You can now:

### Update Normally
```bash
cd /opt/eas-station
sudo ./update.sh
```

### See Correct Version Info
Visit: **Help → Version** in web interface
- Commit: Shows actual git hash
- Branch: Shows "main"  
- Date: Shows commit date
- Message: Shows commit message

### Trust That Files Match GitHub
```bash
cd /opt/eas-station
sudo -u easstation git status
# Should show: "On branch main, Your branch is up to date"
```

---

## Prevention for Future

This issue is now **permanently fixed** for new installations.

The install.sh script has been updated to:
- ✅ Preserve .git directory (not exclude it)
- ✅ Verify .git was copied
- ✅ Set proper ownership
- ✅ Show which update method will be used

So future clean installs won't have this problem!

---

## Need Help?

- Full documentation: `docs/guides/CONFIGURATION_MIGRATION.md`
- Fix summary: `FIX_SUMMARY.md`
- Scripts help: `scripts/README.md`

Or open an issue on GitHub: https://github.com/KR8MER/eas-station/issues
