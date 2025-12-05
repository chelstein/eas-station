# SDR Frequency & Hardware Validation - Quick Reference

## Summary

✅ **The frontend ALREADY accepts frequency in MHz!**  
✅ **Hardware-specific validation is ALREADY working!**

No code changes were needed - both features are fully functional.

## How to Use

### 1. Add a Receiver

Navigate to: **Settings → Radio Receivers → Add Receiver**

### 2. Select Your Hardware

The system detects your SDR device (RTL-SDR, Airspy, etc.)

### 3. Choose Service Type

Click one of the service type buttons:
- **NOAA Weather Radio**
- **FM Broadcast**
- **AM Broadcast**

### 4. Enter Frequency in MHz

**The input field accepts MHz, NOT Hz!**

Examples:
- NOAA: Type `162.550` (not 162550000)
- FM: Type `97.9` (not 97900000)  
- AM: Type `800` (kHz shown as 0.800 MHz)

The system automatically:
- ✅ Validates as you type
- ✅ Shows green checkmark if valid
- ✅ Shows red error if invalid
- ✅ Converts to Hz internally

### 5. Select Sample Rate

**The dropdown only shows valid rates for YOUR hardware!**

#### For Airspy R2:
You will ONLY see:
- 2.5 MHz (2,500,000 Hz) ⭐ Recommended
- 10 MHz (10,000,000 Hz)

These are the ONLY rates Airspy R2 supports!

#### For RTL-SDR:
You will see multiple options:
- 250 kHz (250,000 Hz)
- 1.024 MHz (1,024,000 Hz)
- 2.048 MHz (2,048,000 Hz)
- 2.4 MHz (2,400,000 Hz) ⭐ Recommended
- 2.56 MHz (2,560,000 Hz)

### 6. Save

The backend validates:
- ✅ Frequency is valid for service type
- ✅ Sample rate is valid for hardware
- ✅ All parameters are compatible

If there's a problem, you'll see a specific error message like:
```
Error: Airspy R2 only supports 2.5 MHz and 10 MHz sample rates.
Configured rate 2.4 MHz is invalid.
```

## Validation Rules

### NOAA Weather Radio

**Valid Frequencies (MHz):**
- 162.400 (WX1)
- 162.425 (WX2)
- 162.450 (WX3)
- 162.475 (WX4)
- 162.500 (WX5)
- 162.525 (WX6)
- 162.550 (WX7)

Type any of these in MHz. System rejects anything else.

### FM Broadcast

**Valid Range:** 88.1 - 108.0 MHz

**Channel Spacing:** Must end in .1, .3, .5, .7, or .9

Examples:
- ✅ 97.9 MHz
- ✅ 101.1 MHz
- ❌ 97.8 MHz (must be odd tenth)
- ❌ 88.0 MHz (must be .1 or higher)

### AM Broadcast

**Valid Range:** 530 - 1700 kHz (shown as 0.530 - 1.700 MHz)

**Channel Spacing:** 10 kHz increments

Examples:
- ✅ 800 kHz (0.800 MHz)
- ✅ 1010 kHz (1.010 MHz)
- ❌ 805 kHz (must be 10 kHz increment)

## Hardware Constraints

### Airspy R2

**Sample Rates:** ONLY 2.5 MHz or 10 MHz
- No other rates work!
- Hardware limitation, not software

**Why?** The Airspy R2 ADC runs at a fixed 20 MSPS with limited decimation options.

### RTL-SDR

**Sample Rates:** 250 kHz - 3.2 MHz typically
- Common: 250k, 1.024M, 2.048M, 2.4M, 2.56M
- Most flexible SDR for sample rates

### SDR++ Server / Remote

**Sample Rates:** Determined by remote hardware
- System queries remote capabilities
- Shows only valid rates for remote SDR

## Real-Time Validation Examples

### ✅ Valid Configuration
```
Service: NOAA Weather Radio
Frequency: 162.550 MHz
Sample Rate: 2.4 MHz (RTL-SDR)
Driver: rtlsdr

Result: Green checkmark ✅
Display: "162.550 MHz (NOAA WX7)"
```

### ❌ Invalid Frequency
```
Service: NOAA Weather Radio
Frequency: 162.600 MHz (not a valid NOAA frequency)

Result: Red X ❌
Error: "Invalid NOAA frequency. Valid frequencies: 162.400, 162.425, 162.450, 162.475, 162.500, 162.525, 162.550 MHz"
```

### ❌ Invalid Sample Rate for Hardware
```
Service: NOAA Weather Radio
Frequency: 162.550 MHz
Sample Rate: 2.4 MHz
Driver: airspy (Airspy R2)

Result: Dropdown won't even show 2.4 MHz!
Only shows: 2.5 MHz, 10 MHz

Backend validation if you somehow bypass:
Error: "Airspy R2 only supports 2.5 MHz and 10 MHz sample rates."
```

### ❌ Invalid FM Frequency
```
Service: FM Broadcast
Frequency: 97.8 MHz

Result: Red X ❌
Error: "FM frequencies must end in .1, .3, .5, .7, or .9 (e.g., 97.9)"
```

## Where to Find More Info

**Detailed Documentation:**
- `docs/frontend/SDR_FREQUENCY_VALIDATION.md` - Complete technical guide
- `docs/troubleshooting/SDR_AUDIO_TUNING_ISSUES.md` - Troubleshooting

**Code Locations:**
- Frontend: `templates/settings/radio.html`
- Backend Validation: `webapp/routes_settings_radio.py`
- Hardware Validation: `app_core/radio/discovery.py`
- Service Config: `app_core/radio/service_config.py`

## API Endpoints (for developers)

### Validate Frequency
```
POST /api/radio/validate-frequency
Body: {"service_type": "NOAA", "frequency": "162.550"}
```

### Get Hardware Capabilities
```
GET /api/radio/capabilities/airspy
```

### Get Service Configuration
```
GET /api/radio/service-config/NOAA
```

## Common Questions

**Q: Why can't I use 2.4 MHz sample rate with Airspy?**  
A: Hardware limitation. Airspy R2 only supports 2.5 MHz and 10 MHz. This is enforced by the hardware itself, not software.

**Q: Why do I enter MHz but see Hz in logs?**  
A: Frontend accepts MHz for user convenience. Backend stores Hz for precision. You never need to work with Hz directly.

**Q: Can I bypass the validation?**  
A: No. Three layers of validation (Frontend UI, API, Database) prevent invalid configurations.

**Q: What if I don't see my hardware in the dropdown?**  
A: Run device discovery or check USB connections. See `docs/troubleshooting/SDR_AUDIO_TUNING_ISSUES.md`

## Quick Test

Try adding a receiver:
1. Select "NOAA Weather Radio"
2. Type `162.550` in frequency field
3. Watch for green checkmark ✅
4. See "162.550 MHz (NOAA WX7)" display
5. Select sample rate from dropdown (only valid rates shown)
6. Click Save

If you see the green checkmark, the MHz input is working!  
If dropdown only shows valid rates for your hardware, validation is working!

---

**Everything is already implemented and working!** No changes needed.
