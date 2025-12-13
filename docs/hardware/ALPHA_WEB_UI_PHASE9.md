# Alpha LED Sign Web UI Dashboard - Phase 9

**Complete web-based management interface for Alpha LED signs via M-Protocol**

---

## Overview

The Alpha LED Sign Dashboard provides a comprehensive web interface for managing and monitoring Alpha LED signs through the EAS Station system. All M-Protocol functions (Phases 1-5) are accessible through an intuitive, mobile-responsive web interface.

**Key Features:**
- Real-time diagnostics monitoring
- One-click time synchronization  
- Interactive brightness control
- Speaker/audio management
- File content reading
- Comprehensive testing suite
- Auto-refresh diagnostics (30s interval)
- No CLI access required

---

## Accessing the Dashboard

**URL:** `https://your-eas-station/alpha-sign`

**Requirements:**
- Authenticated user account
- `hardware.manage` permission
- Alpha LED sign configured (LED_SIGN_IP and LED_SIGN_PORT set)

**Navigation:**
1. Log in to EAS Station web interface
2. Click **Hardware** in navigation menu
3. Select **Alpha LED Sign**

---

## Dashboard Sections

### 1. Connection Status & Quick Actions

**Connection Status Panel:**
- Real-time connection indicator (Connected / Disconnected)
- Sign model information
- Firmware version
- Serial number
- Auto-refresh indicator (30-second intervals)

**Quick Actions:**
- **Sync Time with System** - Immediately synchronize sign time with EAS Station
- **Refresh Diagnostics** - Manually trigger diagnostics refresh

### 2. Sign Diagnostics

**Information Displayed:**
- Serial number
- Model number
- Firmware version

**Auto-Refresh:**
- Diagnostics automatically refresh every 30 seconds
- Manual refresh available via button
- Loading indicators during refresh

### 3. System Health

**Metrics Monitored:**
- **Temperature**: Internal sign temperature (°F and °C)
- **Memory Usage**: Total and available memory

**Health Indicators:**
- Real-time temperature monitoring
- Memory statistics
- Alerts for abnormal conditions

### 4. Time & Date Control

**Time Format Selection:**
- **12-Hour Format**: AM/PM display
- **24-Hour Format**: Military time

**Run Mode:**
- **Auto Mode**: Enable scheduled message rotation
- **Manual Mode**: Hold current message (useful during emergencies)

**Actions:**
- **Apply Settings**: Save time format and run mode
- **Sync Time**: Quick sync button in header

**Use Cases:**
- Keep sign synchronized with EAS Station time
- Switch to manual mode during emergency alerts
- Configure time format for user preference

### 5. Speaker Control

**Settings:**
- **Enabled**: Speaker active for alerts
- **Disabled**: Silent operation (quiet hours)

**Testing:**
- **Test Beep**: Send 3 beeps to verify audio functionality
- Listen for beeps from physical sign

**Use Cases:**
- Enable speaker for emergency alerts
- Disable during night hours
- Test audio before critical alerts

### 6. Brightness Control

**Manual Brightness:**
- **Interactive Slider**: 0-100% brightness
- **Real-time Value Display**: Shows current level
- **Instant Application**: Changes apply immediately

**Quick Presets:**
- **25%**: Night mode / Low brightness
- **50%**: Medium / Energy saving
- **75%**: Bright / Daytime
- **100%**: Full brightness / Emergencies

**Auto Brightness:**
- **Auto Mode**: Uses ambient light sensor (if equipped)
- Automatically adjusts to environmental conditions

**Use Cases:**
- Full brightness during emergencies
- Night mode for energy savings
- Business hours scheduling
- Light pollution reduction

### 7. File Reader

**Functionality:**
- Read text content from sign file labels
- Support for files: 0-9 and A-Z
- Verify what's currently displayed

**File Labels:**
- **0**: Primary display file (default)
- **1-9**: Numbered text files
- **A-Z**: Lettered text files

**Process:**
1. Select file label from dropdown
2. Click "Read File" button
3. Content displays in textarea
4. Copy or verify as needed

**Use Cases:**
- Verify message delivery
- Read scheduled messages
- Audit sign content
- Troubleshoot display issues

### 8. System Testing

**Comprehensive Test Suite:**
- Tests all M-Protocol functions (Phases 1-5)
- Real-time progress display
- Individual test results
- Pass/fail summary with percentage

**Tests Included:**
- Phase 1: Diagnostics (read serial, model, firmware, memory, temperature)
- Phase 2: Time/Date sync
- Phase 3: Speaker control
- Phase 4: Brightness control
- Phase 5: File reading

**Results Display:**
- ✅ Green checkmark: Test passed
- ❌ Red X: Test failed
- Detailed error messages for failures
- Overall pass percentage

**Use Cases:**
- Verify M-Protocol communication
- Troubleshoot connection issues
- Validate sign capabilities
- Pre-deployment testing

---

## API Endpoints

All endpoints require authentication and `hardware.manage` permission.

### GET /api/alpha/diagnostics

**Description:** Read all sign diagnostics

**Response:**
```json
{
  "success": true,
  "diagnostics": {
    "serial_number": "A9120C-12345",
    "model": "Alpha 9120C",
    "firmware": "v2.15",
    "memory": "64K total, 32K free",
    "temperature": "72.0°F (22.2°C)"
  },
  "connection": {
    "host": "192.168.8.122",
    "port": 10001,
    "connected": true
  }
}
```

### POST /api/alpha/sync-time

**Description:** Sync sign time with EAS Station system time

**Request:** Empty POST

**Response:**
```json
{
  "success": true,
  "message": "Time synchronized successfully"
}
```

### POST /api/alpha/set-time-format

**Description:** Set 12-hour or 24-hour time format

**Request:**
```json
{
  "format_24h": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Time format set to 24-hour"
}
```

### POST /api/alpha/set-run-mode

**Description:** Set auto (scheduled) or manual (hold) run mode

**Request:**
```json
{
  "auto": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Run mode set to AUTO"
}
```

### POST /api/alpha/speaker

**Description:** Enable or disable speaker

**Request:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Speaker enabled"
}
```

### POST /api/alpha/beep

**Description:** Make sign beep

**Request:**
```json
{
  "count": 3
}
```

**Response:**
```json
{
  "success": true,
  "message": "Beep command sent (3 beeps)"
}
```

### POST /api/alpha/brightness

**Description:** Set brightness level (0-100%) or auto mode

**Request (Manual):**
```json
{
  "level": 75
}
```

**Request (Auto):**
```json
{
  "auto": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Brightness set to 75%"
}
```

### GET /api/alpha/read-file/<label>

**Description:** Read text from file label (0-9, A-Z)

**Parameters:**
- `label`: File label (0-9 or A-Z)

**Response:**
```json
{
  "success": true,
  "label": "0",
  "content": "ALPHA LED TEST M-PROTOCOL INTEGRATION",
  "length": 37
}
```

### POST /api/alpha/test-all

**Description:** Run comprehensive test suite of all M-Protocol functions

**Request:** Empty POST

**Response:**
```json
{
  "success": true,
  "results": {
    "phase1_diagnostics": {
      "success": true,
      "data": {
        "serial_number": "A9120C-12345",
        "model": "Alpha 9120C"
      }
    },
    "phase2_time_sync": {
      "success": true
    },
    "phase3_speaker": {
      "success": true
    },
    "phase4_brightness": {
      "success": true
    },
    "phase5_read_file": {
      "success": true,
      "content": "TEST MESSAGE"
    }
  },
  "summary": {
    "passed": 5,
    "total": 5,
    "percentage": 100.0
  }
}
```

---

## Configuration

**Required Environment Variables:**

```bash
# Alpha LED Sign Configuration
LED_SIGN_IP=192.168.8.122        # IP address of Waveshare adapter
LED_SIGN_PORT=10001              # TCP port (default: 10001)
LED_SIGN_ENABLED=true            # Enable LED sign controller
```

**Set via Web UI:**
1. Navigate to Settings → Environment Variables
2. Scroll to "LED Display" section
3. Set **LED Sign IP Address**: `192.168.8.122`
4. Set **LED Sign Port**: `10001`
5. Save Changes
6. Click "Restart Now" to apply

**Waveshare Adapter Requirements:**
- Mode: TCP Server
- Port: 10001
- TCP Timeout: 0 (critical for bidirectional communication)
- AutoFrame: Enable
- Socket Distribution: on

---

## Use Cases & Examples

### Emergency Alert with Maximum Visibility

**Scenario:** Tornado warning - need maximum visibility and audio

**Steps:**
1. Navigate to Alpha Sign Dashboard
2. Speaker Control → Enable speaker
3. Brightness Control → Set to 100%
4. Apply settings
5. Use LED Control page to send emergency message

**Result:** Sign at full brightness with audio enabled

### Night Mode Energy Saving

**Scenario:** Reduce brightness overnight to save energy

**Steps:**
1. Navigate to Alpha Sign Dashboard
2. Brightness Control → Click "25% (Night)" preset
3. Sign dims to 25% brightness

**Automation Option:**
- Create scheduled task to call `/api/alpha/brightness` with `level: 25` at 10 PM
- Restore to 100% at 6 AM

### Verify Displayed Message

**Scenario:** Confirm what's actually shown on sign

**Steps:**
1. Navigate to Alpha Sign Dashboard
2. File Reader → Select "0 (Primary)"
3. Click "Read File"
4. Content displays in textarea

**Result:** See exact text currently on sign

### Pre-Deployment Testing

**Scenario:** Test all functions before going live

**Steps:**
1. Navigate to Alpha Sign Dashboard
2. System Testing → Click "Run Full Test Suite"
3. Wait for results
4. Review pass/fail status
5. Address any failures

**Result:** Comprehensive validation of all M-Protocol functions

### Time Synchronization

**Scenario:** Keep sign time accurate

**Steps:**
1. Navigate to Alpha Sign Dashboard
2. Click "Sync Time with System"
3. Confirmation toast appears

**Automation Option:**
- Time syncs automatically on hardware service restart
- Can schedule periodic sync via cron calling `/api/alpha/sync-time`

---

## Troubleshooting

### Connection Shows "Disconnected"

**Possible Causes:**
- Waveshare adapter not powered
- IP address incorrect
- Network connectivity issue
- Port mismatch

**Solutions:**
1. Verify LED_SIGN_IP and LED_SIGN_PORT in Environment Variables
2. Test network: `ping 192.168.8.122`
3. Test TCP port: `nc -z -v 192.168.8.122 10001`
4. Check Hardware Service logs for errors
5. Verify Waveshare adapter configuration

### Diagnostics Not Loading

**Possible Causes:**
- Sign doesn't support M-Protocol Type F
- Communication timeout
- Waveshare AutoFrame disabled

**Solutions:**
1. Verify sign model supports M-Protocol
2. Enable AutoFrame in Waveshare settings
3. Set TCP Timeout to 0 in Waveshare settings
4. Check logs for specific error messages

### Speaker Control Not Working

**Possible Causes:**
- Sign has no speaker hardware
- Speaker disabled in sign settings
- Volume turned down

**Solutions:**
1. Verify sign has speaker capability
2. Check physical volume control on sign
3. Test beep function to verify hardware
4. Some Alpha signs don't support speaker control

### Brightness Not Changing

**Possible Causes:**
- Sign brightness locked
- Hardware issue
- Communication failure

**Solutions:**
1. Try different brightness levels (0%, 50%, 100%)
2. Verify sign responds to other commands
3. Check sign manual for brightness lock feature
4. Test with physical brightness controls

### File Reading Returns Empty

**Possible Causes:**
- File label has no content
- Wrong file label selected
- Sign doesn't support file reading

**Solutions:**
1. Try reading file "0" (primary display)
2. Send message to file first via LED Control page
3. Verify sign model supports M-Protocol Type B
4. Check Hardware Service logs for errors

### Auto-Refresh Not Working

**Possible Causes:**
- JavaScript error
- Page not in focus
- Browser privacy settings

**Solutions:**
1. Check browser console for errors
2. Refresh the page
3. Ensure browser allows background updates
4. Try manual refresh button

---

## Security

**Authentication:**
- All endpoints require valid user session
- Login required before accessing dashboard

**Authorization:**
- `hardware.manage` permission required
- Enforced on all API endpoints and page access

**CSRF Protection:**
- All POST requests include CSRF token
- Automatic token injection via JavaScript
- Tokens validated server-side

**Input Validation:**
- Brightness: 0-100 range
- File labels: A-Z, 0-9 only
- Boolean values: true/false only
- JSON payload validation

**Error Handling:**
- Sensitive information sanitized
- No stack traces exposed to users
- Errors logged server-side
- User-friendly error messages

---

## Browser Compatibility

**Supported Browsers:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Mobile Support:**
- Responsive design for tablets and phones
- Touch-optimized controls
- Mobile-friendly layout

**Requirements:**
- JavaScript enabled
- Cookies enabled (for authentication)
- Modern CSS support (flexbox, grid)

---

## Performance

**Auto-Refresh:**
- Diagnostics refresh every 30 seconds
- Minimal server load
- Silent background refresh (no toasts)

**API Response Times:**
- Diagnostics: 1-3 seconds (depends on sign response)
- Write operations: <1 second (ACK/NAK)
- File reading: 1-2 seconds
- Test suite: 5-10 seconds

**Optimization:**
- Cached connection status
- Debounced brightness slider
- Lazy-loaded test results

---

## Future Enhancements

**Potential Phase 10+ Features:**
- Message scheduling from web UI
- Graphics editor (pixel/line drawing)
- File creation and deletion
- Run table configuration
- Historical diagnostics charts
- Brightness scheduling by time/day
- Multi-sign support

---

## Related Documentation

- [Alpha Diagnostics Phase 1](ALPHA_DIAGNOSTICS_PHASE1.md) - Read functions
- [Alpha Time/Date Phase 2](ALPHA_TIMEDATE_PHASE2.md) - Time control  
- [Alpha Advanced Phases 3-5](ALPHA_ADVANCED_PHASES3-5.md) - Speaker, brightness, files
- [Waveshare Setup Guide](WAVESHARE_RS232_WIFI_SETUP.md) - Adapter configuration
- [Serial-to-Ethernet Adapters](SERIAL_TO_ETHERNET_ADAPTERS.md) - Multiple adapter guide

---

## Support

**Issues:**
- GitHub: https://github.com/KR8MER/eas-station/issues
- Check Hardware Service logs: `sudo journalctl -u eas-station-hardware.service -f`

**Testing:**
- Use test script: `python3 scripts/test_alpha_diagnostics.py 192.168.8.122`
- Run web UI test suite from dashboard

**Community:**
- Documentation: `/help` page in EAS Station
- M-Protocol Manual: https://alpha-american.com/alpha-manuals/M-Protocol.pdf

---

**Phase 9 Web UI Dashboard: Complete!** 🎉

Full browser-based control of Alpha LED signs - real-time monitoring, one-click controls, comprehensive testing - all without CLI access!
