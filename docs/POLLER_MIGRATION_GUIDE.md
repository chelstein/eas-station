# Migrating to Unified Alert Poller

## Overview

The EAS Station alert polling system has been simplified from **two separate services** (noaa-poller and ipaws-poller) to **ONE unified service** that polls all sources together.

## Benefits

- ✅ **Simpler configuration** - One service, one config file, one poll interval
- ✅ **More efficient** - Polls NOAA and IPAWS in a single cycle
- ✅ **Flexible** - Easy to add custom CAP sources
- ✅ **Better logging** - Clear source identification (NOAA|IPAWS) in logs

## Migration Steps

### 1. Stop Old Services

```bash
sudo systemctl stop eas-station-noaa-poller
sudo systemctl stop eas-station-ipaws-poller
sudo systemctl disable eas-station-noaa-poller
sudo systemctl disable eas-station-ipaws-poller
```

### 2. Remove CAP_POLLER_MODE from Configuration

Edit `/app-config/.env` and remove or comment out:
```bash
# CAP_POLLER_MODE=NOAA  # REMOVE THIS LINE
```

### 3. Enable Unified Poller Service

```bash
sudo systemctl enable eas-station-poller
sudo systemctl start eas-station-poller
```

### 4. Verify Operation

```bash
# Check service status
sudo systemctl status eas-station-poller

# View logs
sudo journalctl -u eas-station-poller -f

# Look for this log message:
# "Starting alert polling cycle [NOAA + IPAWS] (2 endpoints) for..."
```

### 5. Configure Sources via Web UI (Optional)

Visit `/settings/alert-feeds` to configure:
- NOAA User Agent (required)
- IPAWS feed selection
- Custom CAP endpoints

## Configuration File

### Before (Old System)
```bash
# Separate services with CAP_POLLER_MODE
CAP_POLLER_MODE=NOAA  # Used by noaa-poller service
CAP_POLLER_MODE=IPAWS # Used by ipaws-poller service
POLL_INTERVAL_SEC=120
```

### After (Unified System)
```bash
# No CAP_POLLER_MODE needed - polls all sources
POLL_INTERVAL_SEC=120
NOAA_USER_AGENT=EAS Station/2.12 (+https://example.com; contact@example.com)
IPAWS_CAP_FEED_URLS=https://apps.fema.gov/IPAWSOPEN_EAS_SERVICE/rest/public/recent/{timestamp}
CAP_ENDPOINTS=  # Optional: Add custom sources here
```

## Backward Compatibility

The old separate service files (`eas-station-noaa-poller.service` and `eas-station-ipaws-poller.service`) still work but are **deprecated** and will be removed in a future release.

If you continue using them:
- You'll see deprecation warnings in logs
- They will not receive new features
- They may be removed in version 3.x

## Troubleshooting

### "No endpoints configured"
- Ensure NOAA_USER_AGENT is set (required for NOAA API)
- Check zone codes are configured in location settings
- For IPAWS, either set IPAWS_CAP_FEED_URLS or use default

### "CAP_POLLER_MODE is DEPRECATED"
- Remove `CAP_POLLER_MODE` from your .env file
- Stop and disable old separate services
- Enable the unified `eas-station-poller` service

### Service won't start
- Check logs: `sudo journalctl -u eas-station-poller -n 50`
- Verify database connection: `POSTGRES_HOST`, `POSTGRES_PASSWORD`, etc.
- Ensure `/app-config/.env` exists and is readable

## Rollback

If you need to revert to the old system:

```bash
sudo systemctl stop eas-station-poller
sudo systemctl disable eas-station-poller

# Add back to .env:
# CAP_POLLER_MODE=NOAA  # or IPAWS

sudo systemctl enable eas-station-noaa-poller
sudo systemctl enable eas-station-ipaws-poller
sudo systemctl start eas-station-noaa-poller
sudo systemctl start eas-station-ipaws-poller
```

## Questions?

- Check GitHub Issues: https://github.com/KR8MER/eas-station/issues
- See main documentation: /docs/
