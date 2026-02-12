# Troubleshooting: Update Script Not Pulling Changes

## Symptom
When running `update.sh`, you see the same version and commit before and after:
```
Old Version: 2.44.11
New Version: 2.44.11
Old Commit: 9c705446
New Commit: 9c705446
```

## Root Causes

### 1. On an Inactive Branch
Your installation may be on a development/feature branch that's no longer being updated.

**Check current branch:**
```bash
cd /opt/eas-station
git branch --show-current
```

**Solution - Switch to main branch:**
```bash
cd /opt/eas-station
sudo -u eas-station git fetch origin
sudo -u eas-station git checkout main
sudo -u eas-station git reset --hard origin/main
sudo ./update.sh
```

### 2. Already Up to Date
If you're on the correct branch and still see no updates, the branch may genuinely be up to date.

**Check for updates manually:**
```bash
cd /opt/eas-station
sudo -u eas-station git fetch origin
git log HEAD..origin/$(git branch --show-current)
```

If this shows no commits, your installation is current.

### 3. Git Ownership Issues
Git operations may be failing due to ownership problems.

**Fix ownership:**
```bash
sudo chown -R eas-station:eas-station /opt/eas-station
```

Then run update again:
```bash
sudo /opt/eas-station/update.sh
```

## Chicken-and-Egg Problem: Getting a Fixed update.sh

If `update.sh` itself is broken and won't pull changes, you need to bootstrap the fix:

### Option 1: Manual Git Pull (Recommended)
```bash
cd /opt/eas-station
sudo -u eas-station git fetch origin
sudo -u eas-station git checkout main  # or your preferred branch
sudo -u eas-station git reset --hard origin/main
sudo ./update.sh
```

### Option 2: Direct Download of update.sh
```bash
cd /opt/eas-station
sudo wget -O update.sh.new https://raw.githubusercontent.com/KR8MER/eas-station/main/update.sh
sudo chmod +x update.sh.new
sudo mv update.sh update.sh.backup
sudo mv update.sh.new update.sh
sudo chown eas-station:eas-station update.sh
sudo ./update.sh
```

### Option 3: Full Re-clone (Nuclear Option)
```bash
# Backup your .env file first!
sudo cp /opt/eas-station/.env /tmp/eas-station.env.backup

# Re-clone
cd /opt
sudo mv eas-station eas-station.old
sudo git clone https://github.com/KR8MER/eas-station.git
cd eas-station
sudo chown -R eas-station:eas-station .

# Restore config
sudo cp /tmp/eas-station.env.backup .env
sudo chown eas-station:eas-station .env

# Run update to install everything
sudo ./update.sh
```

## Prevention

### Always Use Main Branch for Production
Development/feature branches may become stale. For production deployments:
```bash
cd /opt/eas-station
sudo -u eas-station git checkout main
```

### Verify Branch After Installation
```bash
cd /opt/eas-station
git branch --show-current  # Should show "main"
git remote -v              # Should show github.com/KR8MER/eas-station
```

## Related Issues
- Git directory ownership problems: See [INSTALLATION_DETAILS.md](../installation/INSTALLATION_DETAILS.md#git-ownership)
- Update script behavior: See `update.sh` comments for EAS_SKIP_PULL and related flags
