# SDR Service Isolation Architecture

## Problem

Previously, multiple containers had USB device passthrough and SDR access:
- `audio-service` - Had `/dev/bus/usb` passthrough
- `noaa-poller` - Had `/dev/bus/usb` passthrough + `SDR_ARGS`
- `ipaws-poller` - Had `/dev/bus/usb` passthrough + `SDR_ARGS`

**This caused USB device contention** - multiple processes trying to open the same AirSpy/RTL-SDR device simultaneously, resulting in:
- "Unable to open AirSpy device" errors
- Receiver never starting
- Audio pipeline failures
- Intermittent connection issues

## Solution

### New Clean Architecture

```
┌─────────────┐
│ sdr-service │  ◀── ONLY container with USB access
│             │
│  • SDR HW   │
│  • Audio    │
│  • EAS      │
│  • Icecast  │
└──────┬──────┘
       │
       ├─────▶ Redis (metrics)
       │
       └─────▶ Icecast (streaming)

┌────────────┐     ┌────────────┐
│noaa-poller │     │ipaws-poller│  ◀── NO USB access
│            │     │            │
│ CAP XML    │     │  CAP XML   │     (HTTP only)
│ polling    │     │  polling   │
└────────────┘     └────────────┘

┌────────────┐
│    app     │  ◀── Web UI only
│   (Flask)  │
└────────────┘
```

### Container Responsibilities

#### `sdr-service` (Renamed from `audio-service`)
**Purpose**: ALL SDR and audio processing

**Responsibilities**:
- Exclusive USB device access (`/dev/bus/usb`)
- SDR hardware management (AirSpy, RTL-SDR, etc.)
- Audio capture and demodulation
- EAS/SAME decoding
- Icecast streaming
- Metrics publishing to Redis

**Why Together**: Audio pipeline requires low latency. Splitting SDR → Audio across containers adds latency and complexity.

#### `noaa-poller` / `ipaws-poller`
**Purpose**: CAP XML feed polling ONLY

**Responsibilities**:
- HTTP polling of NOAA/IPAWS CAP feeds
- Alert parsing and database storage
- NO hardware access needed

**Changes**: Removed:
- `/dev/bus/usb` device passthrough
- `SDR_ARGS` environment variable
- `privileged: true` flag (no longer needed)

#### `app`
**Purpose**: Web interface

**Responsibilities**:
- Flask web UI
- User management
- Configuration interface
- Status dashboards
- NO hardware access

### Key Benefits

1. **No USB Contention**
   - Only one container can access SDR hardware
   - Eliminates device access conflicts
   - Reliable hardware initialization

2. **Clean Separation of Concerns**
   - SDR service = Hardware
   - Pollers = Internet
   - App = User Interface

3. **Independent Restarts**
   - Restart pollers without affecting SDR
   - Restart SDR without affecting alerting
   - Improved service reliability

4. **Better Security**
   - Reduced privilege scope
   - Pollers no longer need `privileged` mode
   - Hardware access isolated to one container

5. **Easier Debugging**
   - Clear responsibility boundaries
   - Logs are container-specific
   - Failures don't cascade

## Migration Guide

### For Docker Compose Deployments

**No action required** - the service rename is automatic:
```bash
docker-compose pull
docker-compose up -d
```

Old `audio-service` → New `sdr-service` (same functionality)

### For Portainer Stacks

1. Pull latest changes from Git
2. Redeploy stack
3. Old containers will be removed and replaced

### Verification

Check that only `sdr-service` has USB access:
```bash
# Should show one container
docker ps --filter "name=sdr-service"

# Should show USB passthrough
docker inspect eas-sdr-service | grep -A5 Devices

# Should NOT show USB passthrough
docker inspect eas-station-noaa-poller-1 | grep -A5 Devices
docker inspect eas-station-ipaws-poller-1 | grep -A5 Devices
```

Verify SDR is working:
```bash
# Check sdr-service logs
docker logs -f eas-sdr-service

# Should see:
# ✅ Started SDR receiver: wxj93 (Weather Radio)
# ✅ Audio controller initialized
```

## Troubleshooting

### Problem: "audio-service not found"

**Cause**: Service renamed to `sdr-service`

**Solution**:
```bash
docker-compose down
docker-compose up -d
```

### Problem: SDR still not connecting

**Cause**: May need to restart to release USB lock

**Solution**:
```bash
# Stop all containers
docker-compose down

# Unplug and replug USB device
# Or reboot host

# Start services
docker-compose up -d
```

### Problem: Pollers complaining about missing SDR

**Cause**: Old code may reference SDR

**Solution**: Pollers should NOT use SDR. If you see SDR-related errors in poller logs, they can be ignored - pollers only need HTTP access.

## Files Changed

### Infrastructure Changes
- `docker-compose.yml` - Service rename and USB removal from pollers

### Code Refactoring (2025-12-04)
- `app_core/radio/drivers.py` - Removed unused `DualThreadSDRMixin` inheritance (416 lines of orphaned code)
- `app_core/radio/dual_thread.py` - Deleted entire file (was never used)
- `app.py` - Removed dead `_initialize_radio_receivers()` function (28 lines)
- `poller/cap_poller.py` - Disabled RadioManager initialization (pollers have no USB access)
- `docs/troubleshooting/SDR_WATERFALL_TROUBLESHOOTING.md` - Updated to reflect containerized architecture
- `docs/architecture/SDR_SERVICE_ISOLATION.md` - This document

**Total cleanup**: ~500 lines of duplicated/orphaned code removed

## Related Issues

- Fixes "Unable to open AirSpy device" errors
- Fixes "Receiver is not running" errors
- Improves overall system stability
- Reduces USB contention issues

## References

- [SDR Setup Guide](../hardware/SDR_SETUP.md)
- [Audio Architecture](../audio/AUDIO_MONITORING.md)
- [Troubleshooting](../troubleshooting/SDR_WATERFALL_TROUBLESHOOTING.md)
