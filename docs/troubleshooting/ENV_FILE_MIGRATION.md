# Environment File Migration Guide

## Issue: Systemd EnvironmentFile JSON Parsing Errors

If you're seeing errors like this in your systemd logs:

```
ERROR: Ignoring invalid environment assignment '"endpoint": "https://...": /opt/eas-station/.env
```

This means your `.env` file contains JSON values that are not properly quoted for systemd's `EnvironmentFile` parser.

## Root Cause

Systemd's `EnvironmentFile` directive parses `.env` files line-by-line, expecting simple `KEY=VALUE` pairs. When JSON objects are used as values without proper quoting, systemd cannot parse them correctly.

### ❌ Incorrect Format (Old)
```bash
LOCATION_CONFIG={"timezone": "America/New_York", "county_name": "Your County", ...}
AZURE_OPENAI_CONFIG={"endpoint": "https://...", "key": "...", ...}
ICECAST_CONFIG={"source_password": "...", ...}
```

### ✅ Correct Format (New)
```bash
LOCATION_CONFIG='{"timezone": "America/New_York", "county_name": "Your County", ...}'
AZURE_OPENAI_CONFIG='{"endpoint": "https://...", "key": "...", ...}'
ICECAST_CONFIG='{"source_password": "...", ...}'
```

## How to Fix Your `.env` File

### Option 1: Manual Fix

1. Open your `/opt/eas-station/.env` file
2. Find all lines containing JSON objects (starting with `{`)
3. Wrap the entire JSON value in single quotes (`'`)

**Before:**
```bash
AZURE_OPENAI_CONFIG={"endpoint": "https://me-mho3uvw9-northcentralus.openai.azure.com/openai/deployments/tts-hd/audio/speech?api-version=2025-03-01-preview", "key": "XXX", "model": "tts-1", "speed": 1.05, "voice": "alloy"}
```

**After:**
```bash
AZURE_OPENAI_CONFIG='{"endpoint": "https://me-mho3uvw9-northcentralus.openai.azure.com/openai/deployments/tts-hd/audio/speech?api-version=2025-03-01-preview", "key": "XXX", "model": "tts-1", "speed": 1.05, "voice": "alloy"}'
```

### Option 2: Automated Fix Script

Run this command to automatically fix your `.env` file:

```bash
cd /opt/eas-station
sudo cp .env .env.backup.$(date +%Y%m%d-%H%M%S)
sudo sed -i -E "s/^([A-Z_]+)=(\{.*\})$/\1='\2'/" .env
```

This will:
1. Create a backup of your current `.env` file
2. Automatically add single quotes around JSON values

### Option 3: Use the Web Interface

After updating to the latest version, the web interface will automatically quote JSON values when you save environment settings through the Settings → Environment page.

## Variables That Need Quoting

The following environment variables contain JSON objects and must be quoted:

- `LOCATION_CONFIG`
- `AZURE_OPENAI_CONFIG`
- `ICECAST_CONFIG`

## After Fixing

1. Verify your `.env` file has the correct format
2. Restart the affected services:

```bash
sudo systemctl restart eas-station-hardware.service
sudo systemctl restart eas-station-web.service
sudo systemctl restart eas-station-poller.service
sudo systemctl restart eas-station-eas.service
sudo systemctl restart eas-station-audio.service
sudo systemctl restart eas-station-sdr.service
```

3. Check the service status:

```bash
sudo systemctl status eas-station-hardware.service
```

You should no longer see the "Ignoring invalid environment assignment" errors.

## Prevention

- Always use single quotes around JSON values in `.env` files
- The updated code automatically handles this when saving through the web interface
- Use the updated `.env.example` as a reference for the correct format

## Related Issues

This fix also addresses:
- Service restart loops due to invalid environment configuration
- Missing environment variables at runtime
- Configuration not being applied correctly
