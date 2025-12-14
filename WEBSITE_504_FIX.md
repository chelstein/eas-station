# Fix Summary: Website 504 Errors After PR #1356

## What Was Broken

After PR #1356, the website returned 504 Gateway Timeout errors, even after complete reinstallation.

## Root Cause

**PR #1356 added the `--system-site-packages` flag to venv creation in install.sh.**

This caused system Python packages to conflict with venv packages, breaking gunicorn worker startup.

### The Problem Chain

1. `python3 -m venv --system-site-packages` creates a venv with access to ALL system Python packages
2. System packages (numpy, scipy) have C extensions compiled for system Python
3. Venv packages (gevent) have C extensions compiled for venv Python  
4. When both are loaded, C extension conflicts occur
5. Gunicorn workers fail to import gevent → crash during startup
6. Nginx waits for workers to respond → timeout → **504 Gateway Timeout**

## What Was Fixed

**Commit e2b77d5**: Removed `--system-site-packages` flag from install.sh

This prevents C extension conflicts and allows gunicorn to start normally.

## How to Deploy

```bash
# Stop services
sudo systemctl stop eas-station.target

# Pull the fix
cd /opt/eas-station
git pull origin copilot/fix-broken-logs

# Recreate venv WITHOUT --system-site-packages
sudo rm -rf /opt/eas-station/venv
sudo -u eas-station python3 -m venv /opt/eas-station/venv
sudo -u eas-station /opt/eas-station/venv/bin/pip install --upgrade pip
sudo -u eas-station /opt/eas-station/venv/bin/pip install -r requirements.txt

# Restart
sudo systemctl daemon-reload
sudo systemctl start eas-station.target
```

## Verification

```bash
# Should show: include-system-site-packages = false
grep "include-system-site-packages" /opt/eas-station/venv/pyvenv.cfg

# Should return HTTP 200
curl -f http://localhost:5000/api/health
```

See ROOT_CAUSE_ANALYSIS.md for full technical details.
