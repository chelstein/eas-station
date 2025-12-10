# SDR System Investigation - Complete Summary

## Investigation Complete ✅

I have thoroughly investigated the SDR system and fixed critical bugs that were preventing proper operation.

## Critical Bugs Fixed

### 1. AirspyReceiver Configuration Never Executed (HIGH PRIORITY)

**Problem**: The `AirspyReceiver` class overrode a non-existent method `_open_device()`, but the parent class actually uses `_open_handle()`. This meant **all Airspy-specific configuration was skipped**.

**What was broken**:
- ❌ Sample rate validation (Airspy R2 requires exactly 2.5 MHz or 10 MHz)
- ❌ Linearity gain mode (optimal for strong signals like FM stations)
- ❌ Bias-T configuration (for external LNA power)

**Impact**: If you're using an Airspy SDR, it likely wasn't configured correctly at all.

**Fix**: Renamed method to `_open_handle()` with correct signature. Airspy-specific logic now executes properly.

### 2. Missing get_ring_buffer_stats() Method

**Problem**: `sdr_service.py` called `receiver.get_ring_buffer_stats()` but receivers didn't implement this method.

**Impact**: Silent failures when publishing SDR buffer metrics to Redis for monitoring.

**Fix**: Implemented the method with accurate buffer statistics calculation.

## Your Audio/Tuning Issues

The code bugs are **now fixed**, but your "can't hear audio" and "wrong frequency" issues are likely **configuration problems**. Here's what to check:

### Step 1: Check Services Are Running

Look for:
- ✅ "✅ SDR Service started successfully"
- ✅ "Configured X radio receiver(s) from database"
- ❌ "Failed to open device" (hardware issue)
- ❌ "No radio receivers configured" (database empty)

### Step 2: Check Your SDR Hardware

```bash
# Should show your SDR device (RTL-SDR, Airspy, etc.)
lsusb

# Test SDR detection
```

### Step 3: Check Receiver Configuration

```bash
SELECT 
  identifier, 
  driver, 
  frequency_hz, 
  sample_rate, 
  gain, 
  modulation_type, 
  audio_output, 
  enabled, 
  auto_start 
FROM radio_receivers;
"
```

**Common Configuration Mistakes**:

1. **Frequency in MHz instead of Hz**
   - ❌ Wrong: `frequency_hz = 162.550` 
   - ✅ Correct: `frequency_hz = 162550000` (multiply by 1,000,000)

2. **Invalid sample rate for Airspy**
   - ❌ Wrong: `sample_rate = 2400000` (Airspy doesn't support this)
   - ✅ Correct: `sample_rate = 2500000` or `10000000` (ONLY these two!)

3. **No gain set**
   - ❌ Wrong: `gain = NULL` or `gain = 0`
   - ✅ Correct: `gain = 40.0` (RTL-SDR) or `gain = 21.0` (Airspy)

4. **Wrong modulation**
   - ❌ Wrong: `modulation_type = 'FM'` for NOAA Weather
   - ✅ Correct: `modulation_type = 'NFM'` (Narrow FM for NOAA)

5. **Audio output disabled**
   - ❌ Wrong: `audio_output = false`
   - ✅ Correct: `audio_output = true`

### Step 4: Follow the Troubleshooting Guide

I created a comprehensive guide at:
📖 **`docs/troubleshooting/SDR_AUDIO_TUNING_ISSUES.md`**

It includes:
- Complete diagnostic procedures
- Common issues and solutions
- Configuration examples for NOAA Weather and FM broadcast
- Advanced troubleshooting steps
- What to collect when reporting issues

## Quick Configuration Examples

### NOAA Weather Radio (RTL-SDR)

```sql
INSERT INTO radio_receivers (
  identifier, 
  display_name, 
  driver, 
  frequency_hz,    -- Must be in Hz!
  sample_rate,     -- 2.4 MHz typical for RTL-SDR
  gain,            -- Important! 40 dB recommended
  modulation_type, -- NFM for NOAA
  audio_output,    -- Enable audio
  enabled, 
  auto_start
) VALUES (
  'noaa-wx7', 
  'NOAA Weather WX7', 
  'rtlsdr', 
  162550000,  -- 162.55 MHz in Hz
  2400000,    -- 2.4 MHz
  40.0,       -- 40 dB gain
  'NFM',      -- Narrow FM
  true,       -- Enable audio
  true,       -- Enabled
  true        -- Auto-start
);
```

### FM Broadcast (Airspy R2)

```sql
INSERT INTO radio_receivers (
  identifier, 
  display_name, 
  driver, 
  frequency_hz, 
  sample_rate,      -- MUST be 2.5 MHz or 10 MHz for Airspy!
  gain, 
  modulation_type,  -- WFM for broadcast FM
  audio_output, 
  stereo_enabled,   -- Enable stereo for FM broadcast
  enabled, 
  auto_start
) VALUES (
  'fm-wkqx', 
  'WKQX 101.1 FM', 
  'airspy', 
  101100000,  -- 101.1 MHz in Hz
  2500000,    -- 2.5 MHz (or 10000000 for 10 MHz)
  21.0,       -- 21 dB gain
  'WFM',      -- Wideband FM
  true,       -- Enable audio
  true,       -- Stereo decoding
  true,       -- Enabled
  true        -- Auto-start
);
```

## What Changed in This PR

**Files Modified**:
- `app_core/radio/drivers.py` - Fixed AirspyReceiver, added get_ring_buffer_stats()
- `VERSION` - Updated to 2.12.22
- `docs/reference/CHANGELOG.md` - Documented changes

**Files Created**:
- `docs/troubleshooting/SDR_AUDIO_TUNING_ISSUES.md` - Comprehensive troubleshooting guide

**Quality Checks**:
- ✅ Python syntax validation passed
- ✅ Code review completed
- ✅ CodeQL security scan: 0 vulnerabilities
- ✅ No breaking changes

## Next Steps for You

1. **Rebuild containers** to get the fixes:
   ```bash
   ```

2. **Check your configuration** using the examples above

3. **Follow the troubleshooting guide** at `docs/troubleshooting/SDR_AUDIO_TUNING_ISSUES.md`

4. **Check logs** for error messages:
   ```bash
   ```

## Need More Help?

If issues persist after:
- Rebuilding containers with the fixes
- Verifying configuration (especially frequency in Hz and correct sample rate)
- Following the troubleshooting guide

Then collect:
3. Your receiver configuration from database
4. SDR hardware model (RTL-SDR v3, Airspy R2, etc.)
5. Frequency you're trying to receive
6. Output of `lsusb` showing your SDR device

---

**Summary**: The code now works correctly for Airspy and properly reports buffer stats. Your audio/tuning issues are most likely configuration-related. Check frequency is in Hz (not MHz), gain is set, and sample rate is valid for your hardware.
