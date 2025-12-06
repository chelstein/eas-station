# Quick tmpfs Configuration Guide

## TL;DR - Copy and Paste

### For 4GB RAM (VPS) - DEFAULT ✅
```ini
# Already set in stack.env - no changes needed!
TMPFS_SDR_SERVICE=64M
TMPFS_AUDIO_SERVICE=128M
TMPFS_HARDWARE_SERVICE=64M
TMPFS_APP=128M
TMPFS_NOAA_POLLER=64M
TMPFS_IPAWS_POLLER=64M
```

### For 16GB RAM (Raspberry Pi 5)
Add these to your `.env` or Portainer environment variables:
```ini
TMPFS_SDR_SERVICE=256M
TMPFS_AUDIO_SERVICE=512M
TMPFS_HARDWARE_SERVICE=256M
TMPFS_APP=512M
TMPFS_NOAA_POLLER=256M
TMPFS_IPAWS_POLLER=256M
```

### For 8GB RAM
```ini
TMPFS_SDR_SERVICE=128M
TMPFS_AUDIO_SERVICE=256M
TMPFS_HARDWARE_SERVICE=128M
TMPFS_APP=256M
TMPFS_NOAA_POLLER=128M
TMPFS_IPAWS_POLLER=128M
```

### For 32GB+ RAM (Server)
```ini
TMPFS_SDR_SERVICE=512M
TMPFS_AUDIO_SERVICE=1024M
TMPFS_HARDWARE_SERVICE=512M
TMPFS_APP=1024M
TMPFS_NOAA_POLLER=512M
TMPFS_IPAWS_POLLER=512M
```

## How to Apply

### Option 1: Portainer (Easiest)
1. Go to **Stacks** → **eas-station** → **Editor**
2. Scroll to **Environment variables**
3. Click **+ Add environment variable** for each line above
4. Click **Update the stack**

### Option 2: Edit stack.env
1. Edit `stack.env` in your repository
2. Paste the appropriate configuration
3. Commit and push
4. In Portainer: **Pull and redeploy**

### Option 3: Command Line
```bash
# Edit persistent config
docker exec -it eas-station_app nano /app-config/.env
# Add the lines, save, exit
docker compose restart
```

## What Does This Do?

- Stores temporary files in **RAM** instead of **disk**
- Makes file operations **much faster**
- **Saves disk space** (important for SD cards)
- **Reduces wear** on SD cards and SSDs

## Troubleshooting

**Problem**: Containers won't start  
**Fix**: Your values are too high. Use the 4GB defaults.

**Problem**: Still slow  
**Fix**: Your values are too low. Use next size up (8GB → 16GB values).

**Problem**: Out of memory errors  
**Fix**: Reduce all values by half or use defaults.

## Full Documentation

See [TMPFS_CONFIGURATION.md](TMPFS_CONFIGURATION.md) for complete details.
