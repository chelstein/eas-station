# Disk Space Cleanup Guide

## Overview

This guide helps you reclaim disk space from accumulated Docker data. EAS Station containers can accumulate significant disk space over time due to:

1. **Container writable layers** - Temporary files stored in `/tmp` before tmpfs was configured
2. **Docker build cache** - Cached layers from container builds
3. **Unused images** - Old container images from previous versions
4. **Redis AOF files** - Redis append-only file can grow large
5. **Audio archives** - Accumulated audio files in `/tmp/eas-audio` (if enabled)

## Before You Start

**⚠️ WARNING**: These commands will delete data. Make sure you have backups of any important configuration.

**✅ Safe to delete**: Container writable layers, build cache, old images
**⚠️ Be careful**: Docker volumes contain your database and configuration
**❌ Don't delete**: The `app-config` volume (contains your settings)

## Step 1: Check Current Disk Usage

```bash
# Check overall disk usage
df -h

# Check Docker disk usage breakdown
docker system df

# Detailed breakdown
docker system df -v
```

## Step 2: Stop the Stack

```bash
cd /path/to/eas-station
docker compose down
```

## Step 3: Remove Container Writable Layers

**This removes accumulated temporary files from container filesystems:**

```bash
# Remove all stopped containers (this clears their writable layers)
docker container prune -f

# If you want to be more aggressive, remove ALL containers
docker rm -f $(docker ps -aq)
```

## Step 4: Clean Docker Build Cache

**This removes cached layers from builds:**

```bash
# Remove build cache (safe - will be rebuilt on next build)
docker builder prune -f

# More aggressive - remove ALL cache including build cache
docker builder prune -af
```

## Step 5: Remove Unused Images

**This removes old container images:**

```bash
# Remove dangling images (untagged images from old builds)
docker image prune -f

# Remove ALL unused images (more aggressive)
docker image prune -af
```

## Step 6: Clean Up Volumes (CAREFUL!)

**⚠️ WARNING**: This will delete data stored in volumes!

```bash
# List all volumes to see what exists
docker volume ls

# Remove ONLY unused volumes (won't touch volumes still in use)
docker volume prune -f

# If you want to clean specific volumes (DANGEROUS - read below first):
# DO NOT remove these volumes unless you want to lose data:
# - app-config (your settings - you'll need to reconfigure)
# - redis-data (Redis state)
# - alerts-db-data (your database - you'll lose all alerts)

# Only remove these if you want to start fresh:
# docker volume rm eas-station_certbot-conf
# docker volume rm eas-station_certbot-www
# docker volume rm eas-station_nginx-logs
# docker volume rm eas-station_icecast-logs
```

## Step 7: Complete System Cleanup

**All-in-one cleanup command (SAFE - doesn't touch volumes in use):**

```bash
# This removes:
# - All stopped containers
# - All dangling images
# - All unused build cache
# - All unused networks
# - All unused volumes (only those not attached to any container)
docker system prune -af --volumes
```

## Step 8: Rebuild and Restart

```bash
cd /path/to/eas-station

# Rebuild containers (will use less space with tmpfs now)
docker compose build

# Start the stack
docker compose up -d

# Check disk usage after cleanup
docker system df
df -h
```

## What the New tmpfs Configuration Does

After redeploying with the updated docker-compose files:

1. **`/tmp` directories use RAM**: All temporary files in containers are stored in RAM (tmpfs) instead of disk
2. **Automatic cleanup**: tmpfs clears on container restart - no manual cleanup needed
3. **Size limits**: 
   - audio-service: 512MB max
   - sdr-service: 256MB max  
   - app: 512MB max
   - pollers: 256MB each
4. **Redis AOF auto-rewrite**: Redis will automatically rewrite its append-only file when it doubles in size (max ~128MB)

## Monitoring Disk Usage

**Add this to your maintenance routine:**

```bash
# Weekly disk usage check
docker system df

# Check specific volume sizes
docker volume ls | awk '{print $2}' | xargs -I {} sh -c 'echo "Volume: {}"; docker run --rm -v {}:/data alpine du -sh /data'

# Monitor Redis data size
docker exec eas-redis redis-cli INFO persistence | grep aof_current_size
```

## Preventing Future Issues

1. **Enable automatic cleanup**: Add to your crontab or system scheduler:
   ```bash
   # Every Sunday at 2 AM, clean up unused Docker resources
   0 2 * * 0 docker system prune -af --volumes
   ```

2. **Monitor disk space**: Set up alerts when disk usage exceeds 80%

3. **Keep audio archiving disabled**: Unless you need it for debugging, keep `EAS_SAVE_AUDIO_FILES=false`

4. **Regular restarts**: Restart containers periodically to clear tmpfs:
   ```bash
   # Monthly restart to clear tmpfs
   docker compose restart
   ```

## Emergency: Disk Full Right Now

If your disk is completely full and Docker won't start:

```bash
# 1. Stop everything
docker stop $(docker ps -aq)

# 2. Emergency cleanup (removes everything possible)
docker system prune -af --volumes

# 3. Remove ALL containers and images
docker rm -f $(docker ps -aq)
docker rmi -f $(docker images -q)

# 4. Rebuild from scratch
cd /path/to/eas-station
docker compose up -d --build
```

## Expected Space Savings

After running these cleanup steps, you should see:

- **Container layers**: 20-50GB recovered (depends on how long system was running)
- **Build cache**: 5-15GB recovered
- **Old images**: 10-30GB recovered (if you have multiple old versions)
- **Unused volumes**: Variable (depends on what volumes you remove)

**Total expected savings**: 35-95GB depending on how long the system has been accumulating data.

## Need Help?

If you're still running out of space after cleanup:

1. Check if `redis-data` volume is unusually large
2. Check if `alerts-db-data` volume has grown large (you may need to archive old alerts)
3. Verify no other Docker stacks are consuming space: `docker ps -a`
4. Check for large log files: `docker compose logs --tail=0 | wc -l`
