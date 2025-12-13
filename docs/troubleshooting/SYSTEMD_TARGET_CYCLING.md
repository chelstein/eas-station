# Systemd Target Cycling Issue

## Problem Description

The `eas-station.target` was repeatedly stopping and starting, as shown in journal logs:

```
Dec 12 16:58:29 ohc137 systemd[1]: Stopped target eas-station.target - EAS Station Services.
Dec 12 16:58:39 ohc137 systemd[1]: Reached target eas-station.target - EAS Station Services.
Dec 12 17:28:08 ohc137 systemd[1]: Stopped target eas-station.target - EAS Station Services.
Dec 12 17:28:19 ohc137 systemd[1]: Reached target eas-station.target - EAS Station Services.
```

This cycling pattern repeated frequently throughout the day.

## Root Cause

The issue was caused by improper systemd dependency configuration:

1. **Hard Dependencies on Infrastructure Services**: The `eas-station.target` used `Requires=postgresql.service redis.service nginx.service`. When any of these services restarted (for updates, config changes, or failures), systemd would stop and restart the entire EAS station target and all its services.

2. **Missing PartOf Directive**: Individual EAS services (`eas-station-web.service`, `eas-station-sdr.service`, etc.) did not have `PartOf=eas-station.target`, which meant they weren't properly bound to the target lifecycle.

3. **Missing Target Membership**: Services had `WantedBy=multi-user.target` but not `WantedBy=eas-station.target`, so they weren't properly registered as members of the EAS station target.

## Solution

The fix involved three changes to the systemd unit files:

### 1. Changed Target Dependencies from Hard to Soft

**File**: `systemd/eas-station.target`

**Before**:
```ini
Requires=postgresql.service redis.service nginx.service
```

**After**:
```ini
Wants=postgresql.service redis.service nginx.service
```

**Explanation**: `Wants=` creates a soft dependency. If PostgreSQL, Redis, or Nginx restart, the EAS station services continue running. `Requires=` creates a hard dependency that propagates stop/restart actions.

### 2. Added PartOf Directive to All Services

**Files**: All `systemd/eas-station-*.service` files

**Addition**:
```ini
[Unit]
Description=...
Documentation=...
PartOf=eas-station.target    # NEW LINE
After=...
```

**Explanation**: `PartOf=` ensures that when the target stops or restarts, the service also stops or restarts. This is a one-way dependency - changes to the service don't affect the target.

### 3. Added Target to WantedBy

**Files**: All `systemd/eas-station-*.service` files

**Before**:
```ini
[Install]
WantedBy=multi-user.target
```

**After**:
```ini
[Install]
WantedBy=multi-user.target eas-station.target
```

**Explanation**: This makes services proper members of both `multi-user.target` (for system startup) and `eas-station.target` (for grouped management).

## Services Modified

The following files were updated:

- `systemd/eas-station.target` - Changed `Requires=` to `Wants=`
- `systemd/eas-station-web.service` - Added `PartOf=` and `WantedBy=` target
- `systemd/eas-station-sdr.service` - Added `PartOf=` and `WantedBy=` target
- `systemd/eas-station-audio.service` - Added `PartOf=` and `WantedBy=` target
- `systemd/eas-station-eas.service` - Added `PartOf=` and `WantedBy=` target
- `systemd/eas-station-hardware.service` - Added `PartOf=` and `WantedBy=` target
- `systemd/eas-station-poller.service` - Added `PartOf=` and `WantedBy=` target

## Applying the Fix

To apply this fix on a running system:

1. Pull the latest changes:
   ```bash
   cd /opt/eas-station
   git pull
   ```

2. Reload systemd configuration:
   ```bash
   sudo systemctl daemon-reload
   ```

3. Re-enable services to update symlinks:
   ```bash
   sudo systemctl disable eas-station-*.service
   sudo systemctl enable eas-station-*.service
   ```

4. Restart the target (optional):
   ```bash
   sudo systemctl restart eas-station.target
   ```

5. Verify no cycling occurs:
   ```bash
   sudo journalctl -u eas-station.target -f
   ```

## Verification

After applying the fix, the target should remain stable even when:

- PostgreSQL is restarted
- Redis is restarted  
- Nginx is restarted
- Individual EAS services are restarted

Monitor with:
```bash
# Watch target status
sudo journalctl -u eas-station.target -f

# Check all services
sudo systemctl status eas-station-*.service

# Verify target is active
sudo systemctl status eas-station.target
```

## Systemd Dependency Overview

For reference, here's how the dependencies work:

| Directive | Effect | Use Case |
|-----------|--------|----------|
| `Requires=` | Hard dependency - if required unit stops/restarts, this unit also stops/restarts | Critical dependencies that must be present |
| `Wants=` | Soft dependency - if wanted unit stops/restarts, this unit continues running | Optional dependencies |
| `PartOf=` | Lifecycle binding - if parent stops/restarts, this unit also stops/restarts (one-way) | Services that belong to a target |
| `After=` | Ordering - this unit starts after listed units | Ensure proper startup order |
| `WantedBy=` | Installation target - creates symlink in target's `.wants/` directory | Define which target wants this unit |

## Related Documentation

- [systemd.unit(5)](https://www.freedesktop.org/software/systemd/man/systemd.unit.html) - Unit file documentation
- [systemd.target(5)](https://www.freedesktop.org/software/systemd/man/systemd.target.html) - Target unit documentation
- [systemd.service(5)](https://www.freedesktop.org/software/systemd/man/systemd.service.html) - Service unit documentation

## Version History

- **v2.23.7** - Fixed systemd target cycling issue (December 2025)
