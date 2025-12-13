# Alpha LED Sign Advanced Control - M-Protocol Phases 3-5

## Overview

Phases 3-5 complete the M-Protocol implementation with speaker control, brightness management, and text file reading capabilities. Combined with Phases 1-2, this provides comprehensive control of Alpha LED signs.

## New Features

### Phase 3: Speaker/Beep Control

| Method | Description | M-Protocol Function |
|--------|-------------|---------------------|
| `set_speaker()` | Enable/disable speaker | Type E, 0x23 |
| `beep()` | Make sign beep | Combined |

### Phase 4: Brightness Control

| Method | Description | M-Protocol Function |
|--------|-------------|---------------------|
| `set_brightness()` | Set brightness 0-100% | Type E, 0x30 |

### Phase 5: File Management

| Method | Description | M-Protocol Function |
|--------|-------------|---------------------|
| `read_text_file()` | Read text from file label | Type B, 0x42 |

## Usage

### Python API

```python
from scripts.led_sign_controller import Alpha9120CController

# Connect to sign
led = Alpha9120CController(host='192.168.8.122', port=10001)

# === Phase 3: Speaker Control ===

# Enable speaker for alerts
led.set_speaker(True)

# Make sign beep
led.beep(1)

# Disable speaker
led.set_speaker(False)

# === Phase 4: Brightness Control ===

# Set full brightness
led.set_brightness(100)

# Set medium brightness
led.set_brightness(50)

# Set dim (night mode)
led.set_brightness(25)

# Enable auto brightness
led.set_brightness(0, auto=True)

# === Phase 5: File Reading ===

# Read text from file '0'
text = led.read_text_file('0')
print(f"File contains: {text}")

# Read from file 'A'
text = led.read_text_file('A')
```

### Command Line Test Script

```bash
# Test all advanced features
python3 scripts/test_alpha_advanced.py 192.168.8.122

# With custom port
python3 scripts/test_alpha_advanced.py 192.168.8.122 --port 10001
```

**Example Output:**

```
============================================================
Alpha LED Sign Advanced Features - M-Protocol Phases 3-5
============================================================

🔊 Phase 3: Speaker/Beep Control
------------------------------------------------------------

🔊 Test 1: Enable Speaker
✅ Speaker enabled

🔔 Test 2: Test Beep
✅ Beep command sent (listen for beep)

🔇 Test 3: Disable Speaker
✅ Speaker disabled

💡 Phase 4: Brightness Control
------------------------------------------------------------

💡 Test 4: Set Brightness to 100% (Full)
✅ Brightness set to 100% (full)

🌓 Test 5: Set Brightness to 50% (Medium)
✅ Brightness set to 50% (medium)
   Sign should dim slightly

🌙 Test 6: Set Brightness to 25% (Night Mode)
✅ Brightness set to 25% (dim)
   Sign should be dim (night mode)

☀️  Test 7: Restore Full Brightness
✅ Brightness restored to 100%

📁 Phase 5: Text File Reading
------------------------------------------------------------

📖 Test 10: Read Text File '0'
✅ Successfully read file '0':
   Content: ALPHA LED TEST M-PROTOCOL PHASES 3-5 COMPLETE
   Length: 45 characters
```

## Integration Examples

### Emergency Alert with Audio and Visual

```python
from scripts.led_sign_controller import Alpha9120CController

led = Alpha9120CController(host='192.168.8.122', port=10001)

def send_emergency_alert(message: str):
    """Send emergency alert with maximum visibility."""
    
    # Enable speaker for audio alert
    led.set_speaker(True)
    
    # Set full brightness
    led.set_brightness(100)
    
    # Send message with red flashing
    led.send_flashing_message(
        lines=[
            "⚠ EMERGENCY ALERT ⚠",
            message,
            "TAKE SHELTER NOW",
            "DO NOT DELAY"
        ]
    )
    
    # Beep for attention
    led.beep(3)
    
    print("Emergency alert sent with audio and visual")

# Usage
send_emergency_alert("TORNADO WARNING")
```

### Auto-Dim for Night Operation

```python
from datetime import datetime

def adjust_brightness_for_time():
    """Auto-adjust brightness based on time of day."""
    
    hour = datetime.now().hour
    
    if 6 <= hour < 8:
        # Morning - medium brightness
        led.set_brightness(75)
    elif 8 <= hour < 20:
        # Daytime - full brightness
        led.set_brightness(100)
    elif 20 <= hour < 22:
        # Evening - dim
        led.set_brightness(50)
    else:
        # Night - very dim or off
        led.set_brightness(25)
    
    print(f"Brightness adjusted for {hour}:00")

# Run periodically
import schedule
schedule.every().hour.do(adjust_brightness_for_time)
```

### Read Current Display

```python
def verify_message_displayed():
    """Verify what's currently displayed on sign."""
    
    # Read file 0 (default display file)
    current_text = led.read_text_file('0')
    
    if current_text:
        print(f"Sign is displaying: {current_text}")
        return current_text
    else:
        print("Could not read current display")
        return None

# Usage
verify_message_displayed()
```

### Business Hours Automation

```python
from datetime import datetime

def business_hours_automation():
    """Fully automated sign operation."""
    
    hour = datetime.now().hour
    is_weekend = datetime.now().weekday() >= 5
    
    if is_weekend:
        # Weekend - low brightness, speaker off
        led.set_brightness(50)
        led.set_speaker(False)
        led.send_message(["WEEKEND", "CLOSED", "", ""])
    elif 8 <= hour < 17:
        # Business hours - full brightness, speaker on
        led.set_brightness(100)
        led.set_speaker(True)
        led.send_message(["OPEN", "WELCOME", "8AM - 5PM", ""])
    else:
        # After hours - dim, speaker off
        led.set_brightness(25)
        led.set_speaker(False)
        led.send_message(["CLOSED", "OPEN TOMORROW", "8:00 AM", ""])

# Run every hour
schedule.every().hour.do(business_hours_automation)
```

## M-Protocol Details

### Speaker Control (0x23)

**Enable/Disable:**
- `'E'` = Enable speaker (beep on messages)
- `'D'` = Disable speaker (silent operation)

**Use Cases:**
- Emergency alerts (enable)
- Quiet hours (disable)
- Night operation (disable)

### Brightness Control (0x30)

**Manual Brightness:**
- 0-100% range mapped to sign's brightness levels
- 0 = Off
- 25 = Dim (night mode)
- 50 = Medium
- 75 = Bright
- 100 = Full brightness

**Auto Mode:**
- Set `auto=True` to enable automatic brightness
- Sign adjusts based on ambient light (if sensor equipped)

### Read Text File (0x42)

**File Labels:**
- Single ASCII character: '0'-'9', 'A'-'Z'
- File '0' is typically the default display file
- Files 'A'-'Z' are user-defined storage

**Response Format:**
- ACK (0x06) + Text Data + ETX (0x03)
- Returns `None` if file doesn't exist or NAK received
- Returns empty string `""` if file exists but empty

## Sign Compatibility

**Full Support:**
- ✅ Alpha Premier 4-line
- ✅ Alpha 9120C
- ✅ Most Alpha signs with M-Protocol

**Feature Support Varies:**
- Speaker: Most Alpha signs support
- Brightness: Most Alpha signs support
- File Reading: May vary by model/firmware
- Auto Brightness: Requires ambient light sensor

**Graceful Degradation:**
- All functions return `False` or `None` if not supported
- No exceptions thrown
- Check return values and handle accordingly

## Error Handling

```python
# Speaker control
if led.set_speaker(True):
    print("Speaker enabled")
else:
    print("Speaker not supported or failed")

# Brightness control
if led.set_brightness(50):
    print("Brightness set to 50%")
else:
    print("Brightness control not supported")

# File reading
text = led.read_text_file('0')
if text is not None:
    print(f"File contains: {text}")
else:
    print("Could not read file")
```

## Complete Feature Summary

With all 5 phases implemented, you now have:

### Phase 1: Diagnostics (Read)
- Read serial number, model, firmware
- Query memory and temperature
- Comprehensive diagnostics

### Phase 2: Time/Date Control (Write)
- Set time, date, day of week
- Set time format (12h/24h)
- Set run mode (auto/manual)
- Sync with system time

### Phase 3: Speaker Control (Write)
- Enable/disable speaker
- Beep for alerts

### Phase 4: Brightness Control (Write)
- Manual brightness (0-100%)
- Auto brightness mode

### Phase 5: File Management (Read)
- Read text files by label

## Integration with EAS Station

### Hardware Service Integration

```python
# In hardware_service.py
from scripts.led_sign_controller import Alpha9120CController
import os

led = Alpha9120CController(
    host=os.getenv('LED_SIGN_IP'),
    port=int(os.getenv('LED_SIGN_PORT'))
)

# Auto-adjust brightness by time
def adjust_brightness_schedule():
    hour = datetime.now().hour
    if 22 <= hour or hour < 6:
        led.set_brightness(25)  # Night mode
    else:
        led.set_brightness(100)  # Day mode

# Enable speaker for emergency alerts only
def send_alert(alert_data):
    if alert_data['severity'] == 'Extreme':
        led.set_speaker(True)
        led.set_brightness(100)
    else:
        led.set_speaker(False)
    
    led.send_message(format_alert(alert_data))
```

## Troubleshooting

### Speaker Not Working

**Symptoms:** No beep sound

**Check:**
1. ✅ Sign has speaker hardware
2. ✅ Speaker cable connected
3. ✅ Volume not muted (check sign manual)
4. ✅ `set_speaker(True)` returns `True`

### Brightness Not Changing

**Symptoms:** Brightness stays same

**Check:**
1. ✅ Sign supports brightness control
2. ✅ Not in auto mode (override with manual)
3. ✅ Ambient light sensor not overriding (if equipped)

### Cannot Read Files

**Symptoms:** `read_text_file()` returns `None`

**Check:**
1. ✅ File exists on sign
2. ✅ Correct file label ('0', 'A', etc.)
3. ✅ Sign supports Type B read commands
4. ✅ Waveshare bidirectional settings correct

## Reference

- **Phase 1 Guide:** `docs/hardware/ALPHA_DIAGNOSTICS_PHASE1.md`
- **Phase 2 Guide:** `docs/hardware/ALPHA_TIMEDATE_PHASE2.md`
- **M-Protocol Spec:** https://alpha-american.com/alpha-manuals/M-Protocol.pdf
- **Bidirectional Communication:** `docs/hardware/BIDIRECTIONAL_LED_COMMUNICATION.md`

## Support

- **Test Script:** `scripts/test_alpha_advanced.py`
- **LED Controller:** `scripts/led_sign_controller.py`
- **GitHub Issues:** https://github.com/KR8MER/eas-station/issues

## Next Steps

**Future Enhancements (Optional):**
- Phase 6: Run tables (scheduled messages)
- Phase 7: Graphics (pixel drawing)
- Phase 8: File writing (create/delete files)
- Phase 9: Web UI dashboard

**Current Implementation Complete:**
- ✅ Read diagnostics
- ✅ Write time/date
- ✅ Control speaker
- ✅ Control brightness
- ✅ Read files

**Ready for production use!**
