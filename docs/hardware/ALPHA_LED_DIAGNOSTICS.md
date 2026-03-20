# Alpha LED Sign Diagnostics - M-Protocol Phase 1

## Overview

Phase 1 of the M-Protocol implementation adds comprehensive diagnostic capabilities for Alpha LED signs. You can now query the sign for status information, configuration, and health metrics.

## New Features

### Read Functions (M-Protocol Type F)

The following read commands are now available:

| Method | Description | M-Protocol Function |
|--------|-------------|---------------------|
| `read_serial_number()` | Read sign serial number | Type F, 0x24 |
| `read_model_number()` | Read sign model | Type F, 0x25 |
| `read_firmware_version()` | Read firmware version | Type F, 0x26 |
| `read_memory_configuration()` | Query memory usage | Type F, 0x30 |
| `read_temperature()` | Read internal temperature | Type F, 0x35 |
| `get_diagnostics()` | Read all diagnostic data | Combined |

## Usage

### Python API

```python
from scripts.led_sign_controller import Alpha9120CController

# Connect to sign
led = Alpha9120CController(host='192.168.8.122', port=10001)

# Read serial number
serial = led.read_serial_number()
print(f"Serial: {serial}")

# Read firmware version
firmware = led.read_firmware_version()
print(f"Firmware: {firmware}")

# Read temperature
temp = led.read_temperature()
print(f"Temperature: {temp}°F")

# Get all diagnostics at once
diagnostics = led.get_diagnostics()
for key, value in diagnostics.items():
    print(f"{key}: {value}")
```

### Command Line Test Script

A test script is provided to verify functionality:

```bash
# Basic test
python3 scripts/test_alpha_diagnostics.py 192.168.8.122

# With custom port
python3 scripts/test_alpha_diagnostics.py 192.168.8.122 --port 10001
```

**Example Output:**

```
============================================================
Alpha LED Sign Diagnostics - M-Protocol Phase 1
============================================================

📋 Reading Sign Information...
------------------------------------------------------------
✅ Serial Number: A9120C-12345
✅ Model Number: Alpha 9120C
✅ Firmware Version: v2.15

💾 Reading Memory Configuration...
------------------------------------------------------------
✅ Memory Info:
   - raw_response: TOTAL 64K FREE 32K
   - total_memory: 64
   - free_memory: 32

🌡️  Reading Temperature Sensor...
------------------------------------------------------------
✅ Temperature: 72.0°F (22.2°C)

🔍 Comprehensive Diagnostics...
------------------------------------------------------------
✅ Complete diagnostic report:
   connected: True
   host: 192.168.8.122
   port: 10001
   serial_number: A9120C-12345
   model_number: Alpha 9120C
   firmware_version: v2.15
   memory_info:
      - raw_response: TOTAL 64K FREE 32K
      - total_memory: 64
      - free_memory: 32
   temperature: 72.0
```

## Integration with EAS Station

### Hardware Service Integration

The diagnostics functions integrate automatically with the hardware service:

```python
# In hardware_service.py or similar
from scripts.led_sign_controller import Alpha9120CController

led = Alpha9120CController(
    host=os.getenv('LED_SIGN_IP', '192.168.8.122'),
    port=int(os.getenv('LED_SIGN_PORT', '10001'))
)

# Periodically check sign health
diagnostics = led.get_diagnostics()
if diagnostics['temperature'] and diagnostics['temperature'] > 150:
    logger.warning(f"Sign temperature high: {diagnostics['temperature']}°F")
```

### Future Web UI Integration

Phase 9 will add a web UI dashboard displaying this information:

```
Alpha LED Sign Status Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Sign Information
   Serial: A9120C-12345
   Model: Alpha 9120C
   Firmware: v2.15

💾 Memory Status
   Total: 64 KB
   Free: 32 KB (50%)
   
🌡️ Temperature
   72°F (22°C) ✅ Normal

🔌 Connection
   Status: Connected
   Host: 192.168.8.122:10001
   Last Update: 2 minutes ago
```

## Bidirectional Communication

All read functions use bidirectional communication:

1. **Send command** → Sign receives Type F read request
2. **Wait for ACK** → Sign acknowledges with 0x06 byte
3. **Read data** → Sign sends requested data
4. **Parse response** → Data decoded and returned

**Waveshare adapter requirements:**
- TCP Timeout: 0 (no timeout)
- AutoFrame: Enable
- Socket Distribution: on

These settings are **critical** for bidirectional communication to work.

## Error Handling

All read functions return `None` if the command fails:

```python
serial = led.read_serial_number()

if serial is None:
    # Sign didn't respond or doesn't support this function
    print("Serial number not available")
else:
    print(f"Serial: {serial}")
```

Common failure reasons:
- Sign doesn't support the command (older firmware)
- Waveshare timeout too aggressive
- Network connection lost
- Sign returned NAK (command rejected)

## Sign Compatibility

**Tested:**
- ✅ Alpha Premier (4-line)
- ✅ Alpha 9120C

**Expected to work:**
- ✅ Most Alpha signs with M-Protocol firmware
- ✅ BetaBrite signs (may vary by model)

**May not support:**
- ⚠️ Older signs without Type F commands
- ⚠️ Non-Alpha signs using different protocols

If a function returns `None`, the sign may not support that specific command. This is normal for older models.

## Troubleshooting

### No Response from Sign

**Symptom:** All read functions return `None`

**Check:**
1. ✅ Connection working: `led.connected == True`
2. ✅ Can send messages: `led.send_message(['TEST'])`
3. ✅ Waveshare TCP timeout = 0
4. ✅ Waveshare AutoFrame = Enable
5. ✅ Waveshare Socket Distribution = on

### NAK Responses

**Symptom:** Logs show "Sign returned NAK"

**Reason:** Sign doesn't support this specific function

**Solution:** This is expected for some signs. The function will return `None` and you should handle that gracefully.

### Timeout Errors

**Symptom:** "Timeout reading response"

**Solutions:**
1. Increase timeout in Waveshare (should be 0)
2. Check network latency
3. Verify sign is responding (test with basic message)

### Garbled Responses

**Symptom:** Data contains unexpected characters

**Check:**
1. ✅ Baud rate: 9600 for Alpha signs
2. ✅ Data format: 8-N-1
3. ✅ AutoFrame settings: 500ms, 512 bytes

## Next Steps

**Phase 2: Complete Time/Date Control**
- Set time and date
- Set time format (12h/24h)
- Sync with EAS Station time

**Phase 3: Speaker/Beep Control**
- Configure speaker
- Beep on message
- Custom tone patterns

See `/tmp/M_PROTOCOL_IMPLEMENTATION_PLAN.md` for the complete roadmap.

## Reference

- **M-Protocol Specification:** https://alpha-american.com/alpha-manuals/M-Protocol.pdf
- **Bidirectional Communication Guide:** `docs/hardware/BIDIRECTIONAL_LED_COMMUNICATION.md`
- **Serial-to-Ethernet Adapters:** `docs/hardware/SERIAL_TO_ETHERNET_ADAPTERS.md`

## Support

- **Test Script:** `scripts/test_alpha_diagnostics.py`
- **LED Controller:** `scripts/led_sign_controller.py`
- **GitHub Issues:** https://github.com/KR8MER/eas-station/issues
