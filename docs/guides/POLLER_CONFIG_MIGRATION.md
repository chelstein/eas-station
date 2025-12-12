# Poller Configuration Guide

## Overview

**Note:** This guide describes the legacy separate-poller configuration. As of version 2.20+, the system uses a **unified poller** that polls both NOAA and IPAWS from a single configuration file (`/app-config/.env`).

## Current Configuration (Unified Poller)

The unified poller automatically polls all configured sources:
- NOAA Weather Alerts
- FEMA IPAWS Alerts  
- Custom CAP endpoints

All configuration is done through the web UI at **Settings → Alert Feeds** or via `/app-config/.env`.

### Configuration via Web UI

1. Navigate to **Settings → Alert Feeds**
2. Configure NOAA settings (User Agent)
3. Configure IPAWS settings (Environment and Feed Type)
4. Add custom CAP endpoints if desired
5. Set poll interval (default: 120 seconds)

### Expected Unified Poller Logs

```
INFO:__main__:Starting Alert Poller with LED Integration - Unified Mode (NOAA + IPAWS)
INFO:__main__:Starting alert polling cycle [NOAA + IPAWS] (2 endpoints) for ...
INFO:__main__:Polling: https://api.weather.gov/alerts/active?zone=OHZ016
INFO:__main__:🔢 SAME/FIPS codes: ['039137']
```

## Legacy Documentation (Pre-2.20)

<details>
<summary>Click to expand legacy separate-poller documentation</summary>

### Why This Change?

- **Configuration Conflicts**: Both pollers were reading the same config file, causing NOAA to inherit IPAWS settings and vice versa
- **Independent Control**: Each poller can now be configured independently without affecting the other

## Old Configuration Structure

```
/app-config/
├── .env          # Main app configuration (web UI, database, etc.)
├── noaa.env      # NOAA Weather poller configuration (LEGACY - not used in 2.20+)
└── ipaws.env     # IPAWS (FEMA) poller configuration (LEGACY - not used in 2.20+)
```

</details>

## Troubleshooting

### "IPAWS.env not found" Error

If you see an error about `IPAWS.env` or `noaa.env` not existing:

1. **This is expected** - These files are no longer used in version 2.20+
2. The system now uses `/app-config/.env` for all configuration
3. Configure alert sources via **Settings → Alert Feeds** in the web UI
4. No migration is needed - the unified poller will work automatically

### Empty FIPS Codes

If logs show `🔢 SAME/FIPS codes: []`:

1. Check location settings in **Settings → Location**
2. Ensure county and state are properly configured
3. FIPS codes are automatically generated from location settings

### Poller Not Running

If the poller isn't fetching alerts:

1. Check the service status: `systemctl status eas-station-poller.service`
2. View logs: `journalctl -u eas-station-poller.service -f`
3. Verify configuration in **Settings → Alert Feeds**
4. Check poll interval is set (minimum 30 seconds recommended)

## Configuration Reference

### Environment Variables

All configuration is in `/app-config/.env`:

**NOAA Configuration:**
- `NOAA_USER_AGENT` - Required user agent string for NOAA API compliance

**IPAWS Configuration:**
- `IPAWS_CAP_FEED_URLS` - Comma-separated IPAWS feed URLs
- `IPAWS_DEFAULT_LOOKBACK_HOURS` - Hours to look back for alerts (default: 12)

**Custom Sources:**
- `CAP_ENDPOINTS` - Comma-separated URLs for additional CAP feeds

**Polling:**
- `POLL_INTERVAL_SEC` - Seconds between polls (minimum: 30, recommended: 120)

**Location:**
- Location settings are configured via **Settings → Location** in the web UI
- SAME/FIPS codes are automatically generated

## Additional Resources

- **Web UI Configuration:** Settings → Alert Feeds
- **System Logs:** `/logs?type=polling`  
- **Service Status:** `systemctl status eas-station-poller.service`
- **Main Documentation:** [System Architecture](../architecture/SYSTEM_ARCHITECTURE.md)
