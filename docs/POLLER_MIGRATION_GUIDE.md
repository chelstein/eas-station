# EAS Station Alert Poller - Unified System

## Overview

The EAS Station uses **ONE unified poller service** that polls all alert sources (NOAA, IPAWS, and custom) together in a single efficient cycle.

## Service File

**Unified Service**: `eas-station-poller.service`
- Polls NOAA weather alerts
- Polls IPAWS/FEMA alerts
- Polls any custom CAP-compliant sources
- Single configuration file
- One poll interval for all sources

## Configuration

All configuration is in `/app-config/.env` (or CONFIG_PATH):

```bash
# Required for NOAA API compliance
NOAA_USER_AGENT=EAS Station/2.12 (+https://example.com; contact@example.com)

# Poll interval (applies to all sources)
POLL_INTERVAL_SEC=120

# IPAWS feed (optional, has sensible default)
IPAWS_CAP_FEED_URLS=https://apps.fema.gov/IPAWSOPEN_EAS_SERVICE/rest/public/recent/{timestamp}

# Custom CAP sources (optional)
CAP_ENDPOINTS=https://custom-cap-server.example.com/feed

# Location settings (zone codes for NOAA filtering)
# Configured via web UI at /settings/location
```

## Starting the Poller

```bash
# Enable and start the unified poller
sudo systemctl enable eas-station-poller
sudo systemctl start eas-station-poller

# Check status
sudo systemctl status eas-station-poller

# View logs
sudo journalctl -u eas-station-poller -f

# Look for this log message:
# "Starting alert polling cycle [NOAA + IPAWS] (2 endpoints) for..."
```

## Web UI Configuration

Visit `/settings/alert-feeds` to configure:
- **NOAA User Agent** - Required for NOAA API compliance
- **IPAWS Feed** - Select environment (production/staging) and feed type
- **Custom Sources** - Add any additional CAP-compliant alert feeds
- **Poll Interval** - Single interval for all sources (minimum 120 seconds)

## Architecture Benefits

✅ **Simple** - One service, one config file, one poll interval  
✅ **Efficient** - Polls all sources in a single cycle  
✅ **Flexible** - Easy to add custom CAP sources  
✅ **Clear logging** - Shows "NOAA|IPAWS" in data_source field

## Troubleshooting

### "No endpoints configured"
- Ensure NOAA_USER_AGENT is set (required for NOAA API)
- Check zone codes are configured in location settings
- For IPAWS, either set IPAWS_CAP_FEED_URLS or use default

### Service won't start
- Check logs: `sudo journalctl -u eas-station-poller -n 50`
- Verify database connection: `POSTGRES_HOST`, `POSTGRES_PASSWORD`, etc.
- Ensure `/app-config/.env` exists and is readable

### No alerts being fetched
- Verify NOAA_USER_AGENT is configured correctly
- Check zone codes match your location
- Review logs for API errors (rate limiting, authentication issues)

## Questions?

- Check GitHub Issues: https://github.com/KR8MER/eas-station/issues
- See main documentation: /docs/
