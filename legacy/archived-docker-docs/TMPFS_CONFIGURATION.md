# tmpfs Configuration Guide

## Overview

EAS Station uses tmpfs (temporary filesystem) to store temporary files in RAM instead of on disk. This provides:

- **Faster I/O performance**: RAM is significantly faster than disk storage
- **Reduced disk wear**: Especially important for SD cards (Raspberry Pi) and SSDs
- **Reduced disk space usage**: Temporary files don't consume disk storage
- **Automatic cleanup**: tmpfs is cleared when containers restart

## Default Configuration

The default tmpfs allocation is designed for **4GB RAM systems** (such as VPS):

| Container | Default Size | Purpose |
|-----------|-------------|---------|
| `sdr-service` | 64M | SDR sample buffers |
| `audio-service` | 128M | Audio processing buffers |
| `hardware-service` | 64M | Hardware communication buffers |
| `app` | 128M | Flask application temp files |
| `noaa-poller` | 64M | CAP XML parsing |
| `ipaws-poller` | 64M | CAP XML parsing |
| **TOTAL** | **512M** | ~12% of 4GB RAM |

## Recommended Configurations by System RAM

### 4GB RAM System (VPS, Low-End Server)
**Total: 512MB (12% of RAM)**

Use the defaults in `stack.env`:
```ini
TMPFS_SDR_SERVICE=64M
TMPFS_AUDIO_SERVICE=128M
TMPFS_HARDWARE_SERVICE=64M
TMPFS_APP=128M
TMPFS_NOAA_POLLER=64M
TMPFS_IPAWS_POLLER=64M
```

### 8GB RAM System (Desktop, Small Server)
**Total: 1GB (12% of RAM)**

Double all values:
```ini
TMPFS_SDR_SERVICE=128M
TMPFS_AUDIO_SERVICE=256M
TMPFS_HARDWARE_SERVICE=128M
TMPFS_APP=256M
TMPFS_NOAA_POLLER=128M
TMPFS_IPAWS_POLLER=128M
```

### 16GB RAM System (Raspberry Pi 5, Desktop)
**Total: 2GB (12% of RAM)**

Quadruple all values:
```ini
TMPFS_SDR_SERVICE=256M
TMPFS_AUDIO_SERVICE=512M
TMPFS_HARDWARE_SERVICE=256M
TMPFS_APP=512M
TMPFS_NOAA_POLLER=256M
TMPFS_IPAWS_POLLER=256M
```

### 32GB+ RAM System (Server, Workstation)
**Total: 4GB (12% of RAM)**

Use generous amounts:
```ini
TMPFS_SDR_SERVICE=512M
TMPFS_AUDIO_SERVICE=1024M
TMPFS_HARDWARE_SERVICE=512M
TMPFS_APP=1024M
TMPFS_NOAA_POLLER=512M
TMPFS_IPAWS_POLLER=512M
```

## How to Configure

### Method 1: Edit stack.env (Portainer Git Deployment)

1. Edit your `stack.env` file in the repository
2. Update the `TMPFS_*` values according to your system RAM
3. Commit and push changes
4. In Portainer: **Stacks** → **eas-station** → **Pull and redeploy**

### Method 2: Portainer Environment Variables

1. In Portainer, navigate to **Stacks** → **eas-station**
2. Click **Editor**
3. Scroll to **Environment variables** section
4. Add or modify the variables:
   ```
   TMPFS_SDR_SERVICE=256M
   TMPFS_AUDIO_SERVICE=512M
   TMPFS_HARDWARE_SERVICE=256M
   TMPFS_APP=512M
   TMPFS_NOAA_POLLER=256M
   TMPFS_IPAWS_POLLER=256M
   ```
5. Click **Update the stack**

### Method 3: Persistent .env File (Survives Redeployments)

The persistent configuration in `/app-config/.env` automatically includes these values. To edit:

1. Access your EAS Station web interface
2. Navigate to **Admin** → **System Operations** → **Environment Configuration**
3. Add or modify the tmpfs variables
4. Save and restart services

Or edit directly via shell:

```bash
# Access the app container
docker exec -it eas-station_app bash

# Edit persistent config
nano /app-config/.env

# Add or modify these lines:
TMPFS_SDR_SERVICE=256M
TMPFS_AUDIO_SERVICE=512M
TMPFS_HARDWARE_SERVICE=256M
TMPFS_APP=512M
TMPFS_NOAA_POLLER=256M
TMPFS_IPAWS_POLLER=256M

# Save and exit, then restart
exit
docker compose restart
```

### Method 4: Command Line Override

For temporary testing:

```bash
# Set environment variables before starting
export TMPFS_SDR_SERVICE=256M
export TMPFS_AUDIO_SERVICE=512M
export TMPFS_HARDWARE_SERVICE=256M
export TMPFS_APP=512M
export TMPFS_NOAA_POLLER=256M
export TMPFS_IPAWS_POLLER=256M

# Start the stack
docker compose up -d
```

## Disabling tmpfs

If you prefer to use disk instead of RAM (e.g., for systems with very limited RAM):

### Option 1: Set to 0
```ini
TMPFS_SDR_SERVICE=0
TMPFS_AUDIO_SERVICE=0
TMPFS_HARDWARE_SERVICE=0
TMPFS_APP=0
TMPFS_NOAA_POLLER=0
TMPFS_IPAWS_POLLER=0
```

### Option 2: Comment Out
```ini
# TMPFS_SDR_SERVICE=64M
# TMPFS_AUDIO_SERVICE=128M
# TMPFS_HARDWARE_SERVICE=64M
# TMPFS_APP=128M
# TMPFS_NOAA_POLLER=64M
# TMPFS_IPAWS_POLLER=64M
```

## Monitoring tmpfs Usage

### Check Current Allocation

```bash
# View tmpfs mounts in all containers
docker exec eas-station_app df -h | grep tmpfs
docker exec eas-station_audio-service df -h | grep tmpfs
docker exec eas-station_sdr-service df -h | grep tmpfs
```

### Check Actual Usage

```bash
# See how much tmpfs is actually being used
docker exec eas-station_app du -sh /tmp
docker exec eas-station_audio-service du -sh /tmp
docker exec eas-station_sdr-service du -sh /tmp
```

### Monitor RAM Usage

```bash
# Check container memory usage
docker stats

# Or with specific containers
docker stats eas-station_app eas-station_audio-service eas-station_sdr-service
```

## Troubleshooting

### Problem: Containers failing to start with "cannot allocate memory"

**Cause**: Total tmpfs allocation exceeds available RAM

**Solution**: Reduce tmpfs sizes or disable tmpfs:
```ini
# Minimal allocation for 2GB RAM systems
TMPFS_SDR_SERVICE=32M
TMPFS_AUDIO_SERVICE=64M
TMPFS_HARDWARE_SERVICE=32M
TMPFS_APP=64M
TMPFS_NOAA_POLLER=32M
TMPFS_IPAWS_POLLER=32M
# Total: 256M (~12% of 2GB)
```

### Problem: "no space left on device" in /tmp

**Cause**: tmpfs size too small for workload

**Solution**: Increase the size for the affected service:
```ini
# If audio-service /tmp fills up:
TMPFS_AUDIO_SERVICE=256M  # or larger
```

### Problem: System running out of RAM

**Cause**: tmpfs + container memory exceeds total RAM

**Solution**: Reduce tmpfs allocation or add swap:
```bash
# Option 1: Reduce tmpfs
# Edit stack.env and reduce all TMPFS_* values

# Option 2: Add swap space (Linux)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Best Practices

1. **Rule of Thumb**: Allocate 10-15% of total RAM to tmpfs
2. **Monitor Usage**: Check tmpfs usage weekly to optimize sizes
3. **Start Conservative**: Use defaults, then increase if needed
4. **Document Changes**: Note why you changed from defaults
5. **Test After Changes**: Verify all services start successfully

## Performance Impact

### With tmpfs (RAM)
- ✅ Fast I/O (microseconds)
- ✅ No disk wear
- ✅ Reduced disk space usage
- ⚠️ Requires available RAM
- ⚠️ Data lost on restart (by design)

### Without tmpfs (Disk)
- ✅ No RAM consumption
- ✅ Survives restarts
- ⚠️ Slower I/O (milliseconds)
- ⚠️ Disk wear (SD card concern)
- ⚠️ Consumes disk space

## Related Documentation

- [Portainer Deployment Guide](PORTAINER_DEPLOYMENT.md)
- [System Requirements](../guides/SETUP_INSTRUCTIONS.md#system-requirements)
- [Performance Tuning](../guides/HELP.md#performance-tuning)

---

**Last Updated**: 2025-12-04  
**Applies to**: EAS Station v2.3.12+
