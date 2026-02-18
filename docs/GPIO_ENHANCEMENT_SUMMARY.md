# GPIO Enhancement Summary

## Overview

This pull request significantly enhances the GPIO functionality in the EAS Station with three major improvements:

1. **GPIO Status OLED Screen** - Real-time monitoring of GPIO pins on the OLED display
2. **Flash Patterns for Stack Lights** - Configurable two-phase alternating flash patterns
3. **Enhanced Logging** - Improved GPIO operation logging and audit trail

## Changes Made

### 1. Database Migration

**File**: `app_core/migrations/versions/20260218_add_gpio_oled_and_flash.py`

- Added new OLED screen "oled_gpio_status"
- Configured to display GPIO status with 5-second refresh interval
- Shows active pins, recent activations, and daily statistics

### 2. API Enhancement

**File**: `webapp/routes/system_controls.py`

Enhanced `/api/gpio/status` endpoint with new fields:
- `active_count`: Number of currently active GPIO pins
- `active_pins_summary`: Formatted string of active pins (e.g., "GPIO17, GPIO27")
- `last_activation_summary`: Most recent activation with elapsed time (e.g., "GPIO17 15s ago")
- `activations_today`: Count of successful activations since midnight

### 3. GPIO Controller Enhancements

**File**: `app_utils/gpio.py`

#### New Configuration Options
- `flash_enabled`: Enable/disable flash pattern for pin
- `flash_interval_ms`: Flash interval in milliseconds (50-5000ms)
- `flash_partner_pin`: Partner pin for two-phase alternating pattern

#### New Methods
- `_start_flash(pin)`: Start flash pattern thread
- `_stop_flash(pin)`: Stop flash pattern thread
- Enhanced `_add_config()` to parse flash settings from database

#### Flash Pattern Implementation
- Dedicated thread per pin with stop event
- Alternating on/off pattern at configured interval
- Partner pin support for two-phase alternating
- Thread-safe operation with proper cleanup
- Automatic lifecycle integration (starts on activate, stops on deactivate)

#### Enhanced Logging
- Success indicators (✓) for GPIO firing events
- Hardware availability detection and logging
- Detailed activation/deactivation information
- Enhanced error messages for troubleshooting

### 4. Documentation

**Files**: `docs/hardware/`

- `GPIO_FLASH_PATTERNS.md`: Comprehensive guide to flash pattern configuration
- `GPIO_OLED_STATUS.md`: Documentation for GPIO status OLED screen

Both documents include:
- Configuration examples
- Use cases
- Troubleshooting guides
- Best practices
- API integration details

## Testing

### Code Review
- ✅ Passed code review with 3 minor issues identified and fixed
- ✅ Fixed boolean column comparisons to use idiomatic SQLAlchemy
- ✅ Added named constants for magic numbers

### Security Check
- ✅ Passed CodeQL security analysis with 0 alerts

### Manual Verification
- ✅ Database migration structure validated
- ✅ API endpoint enhancements verified
- ✅ GPIO configuration loading tested
- ✅ Flash thread management validated

## Use Cases

### 1. Stack Lights for Emergency Alerts

Configure two GPIO pins as alternating stack lights:

```json
{
  "17": {
    "name": "Red Stack Light",
    "flash_enabled": true,
    "flash_interval_ms": 500,
    "flash_partner_pin": 27
  },
  "27": {
    "name": "Amber Stack Light",
    "flash_enabled": true,
    "flash_interval_ms": 500,
    "flash_partner_pin": 17
  }
}
```

### 2. OLED Status Monitoring

The GPIO status screen automatically appears in OLED rotation showing:
- Number of active pins
- Which pins are active
- Last activation time
- Daily activation count

### 3. Operation Verification

Enhanced logging provides detailed information for troubleshooting:
```
INFO: ✓ GPIO pin 17 fired successfully: device=OutputDevice, active_high=True, type=automatic
INFO: Started flash pattern on GPIO pin 17 (interval=500ms with partner GPIO27)
INFO: ✓ GPIO pin 17 deactivated successfully: active_time=30.50s, forced=False
```

## Configuration Example

To configure GPIO pins with flash patterns, update the hardware settings in the database:

```json
{
  "gpio_enabled": true,
  "pin_map": {
    "17": {
      "name": "Red Light",
      "active_high": true,
      "hold_seconds": 5.0,
      "watchdog_seconds": 300.0,
      "flash_enabled": true,
      "flash_interval_ms": 500,
      "flash_partner_pin": 27
    },
    "27": {
      "name": "Amber Light",
      "active_high": true,
      "hold_seconds": 5.0,
      "watchdog_seconds": 300.0,
      "flash_enabled": true,
      "flash_interval_ms": 500,
      "flash_partner_pin": 17
    }
  }
}
```

## Deployment

1. Run database migrations:
   ```bash
   alembic upgrade head
   ```

2. Restart services:
   ```bash
   sudo systemctl restart eas-station.target
   ```

3. Verify GPIO status OLED screen appears in rotation

4. Configure flash patterns as needed via hardware settings

## Future Enhancements

Potential improvements for future versions:

1. **UI Controls**: Add web UI for configuring flash patterns
2. **Flash Indicators**: Show flash status in GPIO control panel
3. **Pattern Presets**: Pre-configured flash patterns (slow, medium, fast, emergency)
4. **Duty Cycle**: Adjustable on/off ratio (currently 50/50)
5. **Phase Offset**: Configure phase offset between partner pins
6. **Multiple Patterns**: Support for more complex multi-pin patterns

## Breaking Changes

None. All changes are backward compatible:
- Existing GPIO configurations continue to work without flash
- New fields default to flash disabled
- API endpoint maintains existing response structure (new fields are additional)

## Performance Impact

- **Minimal CPU Usage**: Flash threads sleep between toggles
- **Low Memory**: Small overhead per flash thread (~1KB)
- **No Impact**: Does not affect non-flash GPIO operations
- **Optimized Queries**: Database queries for OLED use indexes

## Support

For issues or questions:
1. Check documentation in `docs/hardware/`
2. Review troubleshooting sections
3. Check logs for detailed error messages
4. Contact maintainer via GitHub issues

## License

EAS Station - Emergency Alert System
Copyright (c) 2025-2026 Timothy Kramer (KR8MER)

Dual-licensed:
- GNU Affero General Public License v3 (AGPL-3.0) for open-source use
- Commercial License for proprietary use

See LICENSE and LICENSE-COMMERCIAL files for details.
