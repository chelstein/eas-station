# GPIO Flash Patterns for Stack Lights

## Overview

The EAS Station GPIO controller now supports configurable flash patterns for stack lights and visual indicators. This feature allows you to create attention-grabbing alternating flash patterns with two-phase operation.

## Features

- **Configurable Flash Rate**: Adjust flash interval from 50ms to 5000ms (20Hz to 0.2Hz)
- **Two-Phase Alternating**: Link two GPIO pins to create alternating on/off patterns
- **Independent Operation**: Each pin can flash independently or work with a partner
- **Thread-Safe**: Flash patterns run in dedicated threads with proper cleanup
- **Integrated Lifecycle**: Flash automatically starts/stops with pin activation/deactivation

## Configuration

Flash patterns are configured in the GPIO pin map stored in the database. Each pin can have the following flash-related settings:

```json
{
  "17": {
    "name": "Red Stack Light",
    "active_high": true,
    "hold_seconds": 5.0,
    "watchdog_seconds": 300.0,
    "flash_enabled": true,
    "flash_interval_ms": 500,
    "flash_partner_pin": 27
  },
  "27": {
    "name": "Amber Stack Light",
    "active_high": true,
    "hold_seconds": 5.0,
    "watchdog_seconds": 300.0,
    "flash_enabled": true,
    "flash_interval_ms": 500,
    "flash_partner_pin": 17
  }
}
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `flash_enabled` | boolean | `false` | Enable flash pattern for this pin |
| `flash_interval_ms` | integer | `500` | Flash interval in milliseconds (50-5000ms) |
| `flash_partner_pin` | integer | `null` | BCM GPIO pin number of partner pin for alternating pattern |

## Use Cases

### 1. Single Flashing Light

For a single flashing indicator (e.g., alert beacon):

```json
{
  "17": {
    "name": "Alert Beacon",
    "flash_enabled": true,
    "flash_interval_ms": 1000
  }
}
```

This creates a 1Hz (1 second on, 1 second off) flashing pattern.

### 2. Alternating Stack Lights

For two-phase alternating lights (common in emergency equipment):

```json
{
  "17": {
    "name": "Red Light",
    "flash_enabled": true,
    "flash_interval_ms": 500,
    "flash_partner_pin": 27
  },
  "27": {
    "name": "Amber Light",
    "flash_enabled": true,
    "flash_interval_ms": 500,
    "flash_partner_pin": 17
  }
}
```

This creates a 2Hz alternating pattern where one light is on while the other is off.

### 3. Rapid Attention Flash

For critical alerts requiring immediate attention:

```json
{
  "17": {
    "name": "Critical Alert",
    "flash_enabled": true,
    "flash_interval_ms": 100
  }
}
```

This creates a rapid 10Hz flash pattern.

## How It Works

### Activation
1. When a GPIO pin with `flash_enabled: true` is activated
2. The controller starts a dedicated flash thread for that pin
3. The thread alternates the pin state at the configured interval
4. If a partner pin is configured, it operates in opposite phase

### Pattern Logic
```
Phase 0: Pin A = ON,  Pin B = OFF
  [wait flash_interval_ms]
Phase 1: Pin A = OFF, Pin B = ON
  [wait flash_interval_ms]
Phase 0: Pin A = ON,  Pin B = OFF
  [repeat...]
```

### Deactivation
1. When the pin is deactivated, the flash thread receives a stop signal
2. The thread cleanly exits and restores the pin to its proper state
3. If the pin is still marked as "active", it's set to solid ON
4. Otherwise, it's set to OFF

## Logging

Flash pattern operations are logged for diagnostics:

```
INFO: Started flash pattern on GPIO pin 17 (interval=500ms with partner GPIO27)
INFO: Stopped flash pattern on GPIO pin 17
```

Any errors in the flash pattern thread are also logged:
```
ERROR: Error in flash pattern for pin 17: [error details]
ERROR: Flash pattern thread crashed for pin 17: [error details]
```

## Best Practices

1. **Choose Appropriate Intervals**
   - Slow (1000-2000ms): General awareness, non-urgent alerts
   - Medium (500ms): Standard attention-getting, most stack lights
   - Fast (100-200ms): Critical situations, immediate attention required

2. **Partner Pin Selection**
   - Ensure partner pins are properly configured
   - Both pins should have matching flash intervals
   - Test the alternating pattern to ensure correct phasing

3. **Hardware Considerations**
   - Verify your relay/driver can handle the switching frequency
   - Some mechanical relays may have limited switching life at high frequencies
   - Consider solid-state relays for high-frequency applications

4. **Power Management**
   - Flashing reduces average power consumption by ~50% compared to solid on
   - Useful for battery-powered installations
   - Consider duty cycle for heat-sensitive equipment

## API Integration

Flash patterns are automatically handled by the GPIO controller. No special API calls are needed:

```python
# Standard activation - flash starts automatically if configured
controller.activate(
    pin=17,
    activation_type=GPIOActivationType.AUTOMATIC,
    reason="Tornado Warning"
)

# Standard deactivation - flash stops automatically
controller.deactivate(pin=17)
```

## Troubleshooting

### Flash Not Working

1. **Check Configuration**
   - Verify `flash_enabled: true` in pin configuration
   - Ensure `flash_interval_ms` is within valid range (50-5000)

2. **Check Logs**
   - Look for "Started flash pattern" messages
   - Check for error messages in flash thread

3. **Verify GPIO Hardware**
   - Ensure basic GPIO operations work
   - Test pin without flash first

### Partner Pin Not Alternating

1. **Check Partner Configuration**
   - Both pins must reference each other as partners
   - Both pins must have matching flash intervals
   - Both pins must be activated

2. **Check Phasing**
   - Patterns are synchronized at activation time
   - If timing seems off, deactivate and reactivate both pins

## Examples

### Emergency Alert System Stack Light
```json
{
  "17": {
    "name": "EAS Red Light",
    "active_high": true,
    "flash_enabled": true,
    "flash_interval_ms": 500,
    "flash_partner_pin": 27
  },
  "27": {
    "name": "EAS Amber Light",
    "active_high": true,
    "flash_enabled": true,
    "flash_interval_ms": 500,
    "flash_partner_pin": 17
  }
}
```

### Warning Beacon
```json
{
  "22": {
    "name": "Warning Beacon",
    "active_high": true,
    "flash_enabled": true,
    "flash_interval_ms": 1000
  }
}
```

### Multi-Level Alert System
```json
{
  "17": {
    "name": "Level 1 - Advisory",
    "active_high": true,
    "flash_enabled": true,
    "flash_interval_ms": 2000
  },
  "27": {
    "name": "Level 2 - Warning",
    "active_high": true,
    "flash_enabled": true,
    "flash_interval_ms": 500
  },
  "22": {
    "name": "Level 3 - Emergency",
    "active_high": true,
    "flash_enabled": true,
    "flash_interval_ms": 100
  }
}
```

## Technical Details

### Thread Safety
- Flash threads use threading locks for state access
- Stop events ensure clean shutdown
- Thread cleanup with timeout prevents hanging

### Performance
- Minimal CPU usage (threads sleep between toggles)
- No impact on other GPIO operations
- Efficient event-driven design

### Compatibility
- Works with both gpiozero and lgpio backends
- Compatible with mock factory for testing
- No changes needed to existing GPIO code

## See Also

- [GPIO Configuration Guide](GPIO_CONFIGURATION.md)
- [Hardware Settings](HARDWARE_SETTINGS.md)
- [API Reference](../reference/GPIO_API.md)
