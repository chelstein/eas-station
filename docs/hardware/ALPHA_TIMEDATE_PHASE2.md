# Alpha LED Sign Time/Date Control - M-Protocol Phase 2

## Overview

Phase 2 of the M-Protocol implementation adds complete time and date control for Alpha LED signs. You can now set the sign's time, date, day of week, time format, and run mode.

## New Features

### Write Functions (M-Protocol Type E)

The following time/date control commands are now available:

| Method | Description | M-Protocol Function |
|--------|-------------|---------------------|
| `set_time_and_date()` | Set time and date | Type E, 0x20 |
| `set_day_of_week()` | Set day of week (0-6) | Type E, 0x22 |
| `set_time_format()` | Set 12h or 24h format | Type E, 0x27 |
| `set_run_mode()` | Set auto/manual mode | Type E, 0x2E |
| `sync_time_with_system()` | Sync with EAS Station | Combined |

## Usage

### Python API

```python
from scripts.led_sign_controller import Alpha9120CController
from datetime import datetime

# Connect to sign
led = Alpha9120CController(host='192.168.8.122', port=10001)

# Sync time with system (recommended)
led.sync_time_with_system()

# Or set specific time/date
led.set_time_and_date(datetime(2025, 12, 25, 12, 0, 0))

# Set time format
led.set_time_format(format_24h=True)   # 24-hour
led.set_time_format(format_24h=False)  # 12-hour

# Set day of week (0=Sunday, 1=Monday, ..., 6=Saturday)
led.set_day_of_week(0)  # Sunday

# Set run mode
led.set_run_mode(auto=True)   # Auto mode (scheduled messages)
led.set_run_mode(auto=False)  # Manual mode (hold current)
```

### Command Line Test Script

```bash
# Basic test
python3 scripts/test_alpha_timedate.py 192.168.8.122

# With custom port
python3 scripts/test_alpha_timedate.py 192.168.8.122 --port 10001
```

**Example Output:**

```
============================================================
Alpha LED Sign Time/Date Control - M-Protocol Phase 2
============================================================

🕐 Test 1: Sync Time with System
------------------------------------------------------------
✅ Sign synchronized to system time
   Current time: 2025-12-13 15:30:45 Friday

🕑 Test 2: Set Specific Time/Date
------------------------------------------------------------
✅ Time set to: 2025-12-25 12:00:00

🕒 Test 3: Restore Current Time
------------------------------------------------------------
✅ Time restored to: 2025-12-13 15:30:47

📅 Test 4: Set Day of Week
------------------------------------------------------------
✅ Day set to: Friday

🕓 Test 5: Set Time Format (24-hour)
------------------------------------------------------------
✅ Time format set to 24-hour

🕔 Test 6: Set Time Format (12-hour)
------------------------------------------------------------
✅ Time format set to 12-hour

⚙️  Test 7: Set Run Mode (Auto)
------------------------------------------------------------
✅ Run mode set to AUTO
   Sign will display scheduled messages

⚙️  Test 8: Set Run Mode (Manual)
------------------------------------------------------------
✅ Run mode set to MANUAL
   Sign will hold current message
```

## Integration with EAS Station

### Automatic Time Synchronization

Add to your hardware service to keep sign time synchronized:

```python
from scripts.led_sign_controller import Alpha9120CController
import schedule
import time

led = Alpha9120CController(
    host=os.getenv('LED_SIGN_IP'),
    port=int(os.getenv('LED_SIGN_PORT'))
)

# Sync time every hour
schedule.every().hour.do(led.sync_time_with_system)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Displaying Time on Sign

```python
from datetime import datetime

# Update sign with current time every minute
def update_time_display():
    now = datetime.now()
    led.send_message(
        lines=[
            "CURRENT TIME",
            now.strftime("%I:%M %p"),
            now.strftime("%A"),
            now.strftime("%B %d, %Y")
        ]
    )

# Call periodically
```

## M-Protocol Details

### Set Time and Date (0x20)

**Format:** `HH:MM:SS\rMM/DD/YY` (10 bytes ASCII)

**Example:**
- Input: `datetime(2025, 12, 13, 15, 30, 45)`
- Sent: `"15:30:45\r12/13/25"`

**Packet Structure:**
```
<NULL>x5 <ID> <0x45> <0x20> <TIME_DATE> <ETX>
```

### Set Day of Week (0x22)

**Values:**
- 0 = Sunday
- 1 = Monday
- 2 = Tuesday
- 3 = Wednesday
- 4 = Thursday
- 5 = Friday
- 6 = Saturday

**Note:** Python's `datetime.weekday()` returns 0=Monday, so conversion is needed:
```python
alpha_day = (python_day + 1) % 7
```

### Set Time Format (0x27)

**Values:**
- `'S'` = 24-hour format (standard/military time)
- `'M'` = 12-hour format (meridian AM/PM)

### Set Run Mode (0x2E)

**Values:**
- `'A'` = Auto mode (sign displays scheduled messages)
- `'M'` = Manual mode (sign holds current message)

**Auto Mode:**
- Sign displays messages based on run time/day tables
- Allows scheduled content rotation
- Useful for automated operation

**Manual Mode:**
- Sign displays current message indefinitely
- Prevents automatic message changes
- Useful during emergencies or special events

## Bidirectional Communication

All write functions follow the same pattern:

1. **Send command** → Sign receives Type E write request
2. **Wait for ACK** → Sign acknowledges with 0x06 byte
3. **Send EOT** → Complete transaction with 0x04
4. **Return status** → True on success, False on failure

## Use Cases

### 1. Daily Time Sync

Keep sign synchronized with EAS Station:

```python
# Run at system startup and daily at midnight
led.sync_time_with_system()
```

### 2. Daylight Saving Time

Handle DST changes automatically:

```python
import datetime

# System handles DST, sign follows
led.sync_time_with_system()
```

### 3. Emergency Override

Lock sign to manual mode during emergencies:

```python
# During emergency
led.set_run_mode(auto=False)
led.send_message(["TORNADO WARNING", "TAKE SHELTER", "IMMEDIATELY", ""])

# After emergency
led.set_run_mode(auto=True)  # Resume normal operation
```

### 4. Business Hours Display

Different messages for different times:

```python
from datetime import datetime

def update_sign_for_time():
    hour = datetime.now().hour
    
    if 6 <= hour < 8:
        led.send_message(["GOOD MORNING", "..."])
    elif 17 <= hour < 22:
        led.send_message(["GOOD EVENING", "..."])
    else:
        led.send_message(["OVERNIGHT", "..."])
```

## Error Handling

All functions return `bool`:
- `True` = Command successful (ACK received)
- `False` = Command failed (NAK or no response)

```python
if led.set_time_and_date():
    print("Time set successfully")
else:
    print("Failed to set time - check sign compatibility")
```

## Sign Compatibility

**Full Support:**
- ✅ Alpha Premier 4-line
- ✅ Alpha 9120C
- ✅ Most Alpha signs with M-Protocol Type E

**Partial Support:**
- ⚠️ Some older signs may support time/date but not format/mode
- ⚠️ BetaBrite signs (varies by model)

**If a function fails:**
- Sign may not support that specific command
- Returns `False` without throwing exception
- Check logs for NAK responses

## Troubleshooting

### Time Not Setting

**Symptom:** `set_time_and_date()` returns `False`

**Check:**
1. ✅ Connection active: `led.connected == True`
2. ✅ Basic commands work: `led.send_message(['TEST'])`
3. ✅ Sign supports Type E commands (check manual)
4. ✅ Waveshare bidirectional settings correct

### Wrong Time Format

**Symptom:** Time displays incorrectly

**Check:**
1. ✅ Time format set correctly (12h vs 24h)
2. ✅ Date format matches sign expectations (MM/DD/YY)
3. ✅ Sign firmware supports time display

### Day of Week Wrong

**Symptom:** Day doesn't match

**Check:**
1. ✅ Weekday conversion (Python 0=Monday, Alpha 0=Sunday)
2. ✅ Time zone settings on system
3. ✅ Sign and system clocks synchronized

## Next Steps

**Phase 3: Speaker/Beep Control**
- Configure speaker settings
- Beep on message arrival
- Custom tone patterns
- Alert sounds

**Phase 4: Brightness Scheduling**
- Set brightness levels
- Auto-dim by time of day
- Day of week brightness schedules

See `/tmp/M_PROTOCOL_IMPLEMENTATION_PLAN.md` for the complete roadmap.

## Reference

- **M-Protocol Specification:** https://alpha-american.com/alpha-manuals/M-Protocol.pdf
- **Phase 1 (Diagnostics):** `docs/hardware/ALPHA_DIAGNOSTICS_PHASE1.md`
- **Bidirectional Communication:** `docs/hardware/BIDIRECTIONAL_LED_COMMUNICATION.md`

## Support

- **Test Script:** `scripts/test_alpha_timedate.py`
- **LED Controller:** `scripts/led_sign_controller.py`
- **GitHub Issues:** https://github.com/KR8MER/eas-station/issues
