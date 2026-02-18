# GPIO Status OLED Display

## Overview

The EAS Station now includes a dedicated OLED screen that displays real-time GPIO status information. This screen provides at-a-glance monitoring of GPIO pin activations, making it easy to verify that GPIO relays are functioning correctly.

## Features

- **Real-Time Status**: Updates every 5 seconds with current GPIO state
- **Active Pin Summary**: Shows which GPIO pins are currently active
- **Recent Activity**: Displays the last GPIO activation with time elapsed
- **Daily Statistics**: Shows total activations for the current day
- **Automatic Rotation**: Cycles through other OLED screens when enabled

## Display Layout

```
╔══════════════════════════════╗
║   ◢ GPIO STATUS ◣           ║
║                              ║
║ Active Pins: 2               ║
║                              ║
║ GPIO17, GPIO27               ║
║                              ║
║ Last: GPIO17 15s ago         ║
║                              ║
║ Today: 24 activations        ║
╚══════════════════════════════╝
```

### Screen Elements

| Line | Content | Description |
|------|---------|-------------|
| 1 | Header | Screen title with decorative borders |
| 2 | Active Pins | Count of currently active GPIO pins |
| 3 | Pin List | Comma-separated list of active pins (up to 3 shown) |
| 4 | Last Activation | Most recent activation with time elapsed |
| 5 | Daily Count | Total successful activations today |

## Configuration

The GPIO status screen is automatically created by the database migration `20260218_add_gpio_oled_and_flash.py`. It is configured with:

- **Display Type**: OLED
- **Priority**: 2 (Normal)
- **Refresh Interval**: 5 seconds
- **Display Duration**: 15 seconds
- **Enabled**: Yes (by default)

### Screen Configuration

The screen uses the following template configuration:

```json
{
  "clear": true,
  "lines": [
    {
      "text": "◢ GPIO STATUS ◣",
      "font": "medium",
      "wrap": false,
      "invert": true,
      "spacing": 1,
      "y": 0
    },
    {
      "text": "Active Pins: {gpio.active_count}",
      "font": "small",
      "wrap": false,
      "y": 15,
      "max_width": 124
    },
    {
      "text": "{gpio.active_pins_summary}",
      "y": 27,
      "max_width": 124,
      "allow_empty": true
    },
    {
      "text": "Last: {gpio.last_activation_summary}",
      "y": 45,
      "wrap": false,
      "max_width": 124,
      "allow_empty": true
    },
    {
      "text": "Today: {gpio.activations_today} activations",
      "y": 56,
      "wrap": false,
      "max_width": 124
    }
  ]
}
```

### Data Source

The screen fetches data from the `/api/gpio/status` endpoint, which provides:

```json
{
  "success": true,
  "pins": [...],
  "timestamp": "2026-02-18T12:34:56",
  "active_count": 2,
  "active_pins_summary": "GPIO17, GPIO27",
  "last_activation_summary": "GPIO17 15s ago",
  "activations_today": 24
}
```

## Use Cases

### 1. Operation Verification

Quickly verify that GPIO pins are activating correctly:
- During system testing
- After configuration changes
- When troubleshooting alert forwarding

### 2. Real-Time Monitoring

Monitor GPIO activity without accessing the web interface:
- At-a-glance status in equipment rooms
- During emergency situations
- For 24/7 operations centers

### 3. Historical Tracking

Keep track of daily GPIO usage:
- Verify activation frequency
- Monitor system health
- Audit GPIO operations

## Display Behavior

### Active Pin Summary

The active pins summary adapts based on how many pins are active:

| Active Pins | Display |
|-------------|---------|
| 0 | "No active pins" |
| 1-3 | "GPIO17, GPIO22, GPIO27" |
| 4+ | "GPIO17, GPIO22, GPIO27 +2 more" |

### Time Formatting

Last activation time is formatted for readability:

| Elapsed Time | Display |
|--------------|---------|
| < 60 seconds | "15s ago" |
| < 60 minutes | "5m ago" |
| ≥ 60 minutes | "2h ago" |

### No Recent Activity

When there are no recent activations:
- Last activation shows: "No recent activations"
- This indicates the system is idle

## Integration with Screen Rotation

The GPIO status screen is part of the OLED screen rotation system:

1. **Manual Navigation**: Use the OLED button to cycle through screens
2. **Automatic Rotation**: Screen appears every ~2-3 minutes in rotation
3. **Priority System**: Normal priority (2) means it rotates with other standard screens

To adjust rotation behavior:
1. Go to Admin > Hardware Settings > OLED Display
2. Configure screen rotation preferences
3. Enable/disable screens as needed

## Enabling/Disabling

### Via Database

```sql
-- Disable the GPIO status screen
UPDATE display_screens 
SET enabled = false 
WHERE name = 'oled_gpio_status';

-- Re-enable
UPDATE display_screens 
SET enabled = true 
WHERE name = 'oled_gpio_status';
```

### Via Web UI

1. Navigate to Admin > Hardware Settings > OLED Display
2. Go to Screen Management section
3. Find "oled_gpio_status" screen
4. Toggle enabled status
5. Save and restart services

## Customization

### Adjusting Refresh Rate

To update more or less frequently:

```sql
UPDATE display_screens 
SET refresh_interval = 10  -- Update every 10 seconds
WHERE name = 'oled_gpio_status';
```

Valid range: 1-300 seconds

### Adjusting Display Duration

To show for longer/shorter time in rotation:

```sql
UPDATE display_screens 
SET duration = 20  -- Show for 20 seconds
WHERE name = 'oled_gpio_status';
```

Valid range: 3-60 seconds

### Changing Priority

To show more/less frequently:

```sql
UPDATE display_screens 
SET priority = 1  -- Higher priority (0=emergency, 1=high, 2=normal, 3=low)
WHERE name = 'oled_gpio_status';
```

## Troubleshooting

### Screen Not Showing

1. **Check if OLED is enabled**
   - Go to Admin > Hardware Settings
   - Verify "Enable OLED Display" is checked

2. **Verify screen is enabled**
   ```sql
   SELECT name, enabled 
   FROM display_screens 
   WHERE name = 'oled_gpio_status';
   ```

3. **Check screen rotation**
   - Ensure screen rotation is configured
   - Verify the screen is included in rotation

4. **Restart hardware service**
   ```bash
   sudo systemctl restart eas-station-hardware
   ```

### Data Not Updating

1. **Check API endpoint**
   ```bash
   curl http://localhost:5000/api/gpio/status
   ```

2. **Verify GPIO controller is running**
   - Check if GPIO pins are configured
   - Ensure GPIO control is enabled in settings

3. **Check refresh interval**
   - May be set too long
   - Adjust if needed

### Incorrect Data

1. **Check GPIO activation logs**
   - Verify database contains GPIO activation records
   - Check for timestamp issues

2. **Verify timezone settings**
   - Ensure system timezone is correct
   - Check database timezone configuration

## API Enhancements

The `/api/gpio/status` endpoint was enhanced to provide summary data for the OLED screen:

### New Response Fields

```json
{
  "active_count": 2,
  "active_pins_summary": "GPIO17, GPIO27",
  "last_activation_summary": "GPIO17 15s ago",
  "activations_today": 24
}
```

These fields are automatically calculated:
- **active_count**: Number of currently active pins
- **active_pins_summary**: Formatted string of active pin names
- **last_activation_summary**: Most recent successful activation with elapsed time
- **activations_today**: Count of successful activations since midnight (UTC)

## Performance Considerations

- **Low Overhead**: Queries are optimized for minimal database load
- **Caching**: Consider enabling caching for high-traffic systems
- **Indexing**: Database indexes on `activated_at` improve query performance

## Future Enhancements

Potential improvements for future versions:

1. **Flash Pattern Indication**: Show which pins are flashing
2. **Partner Pin Grouping**: Display alternating pairs together
3. **Failure Indicators**: Highlight pins with recent errors
4. **Graphical Indicators**: Add LED-style status icons
5. **Behavior Display**: Show which alert behaviors are assigned

## See Also

- [OLED Configuration Guide](OLED_CONFIGURATION.md)
- [GPIO Flash Patterns](GPIO_FLASH_PATTERNS.md)
- [Hardware Settings](HARDWARE_SETTINGS.md)
- [Display Screens Reference](../reference/DISPLAY_SCREENS.md)
