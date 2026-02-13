# RBDS Fix v2.44.13 - Sample Rate Mismatch and Filter Design

**Date**: December 24, 2024  
**Version**: 2.44.13  
**Status**: Ready for Testing

---

## Problem Summary

RBDS decoding was completely broken on Airspy R2, showing:
- Costas loop frequency ~14 Hz (should be ~3 Hz)
- Syndromes never matching target values
- "0 groups decoded" after thousands of samples
- Continuous sync search with no success

---

## Root Cause Analysis

### The Sample Rate Confusion

**Airspy R2 Hardware**: Only supports 2.5 MHz or 10 MHz sample rates (hardware limitation)

**Early Decimation in Driver**:
```
Airspy @ 2.5 MHz → Early decimation (10x) → 250 kHz to demodulator
```

**The Bug**: RBDS filters were designed for the wrong sample rate!

### What Was Wrong

**Old Code (BROKEN)**:
```
1. Decimate 250 kHz → 25 kHz with 10 kHz lowpass filter
   ❌ 10 kHz lowpass REMOVED the 57 kHz RBDS subcarrier!
2. Try to mix down 57 kHz (but it's already gone)
3. Process noise/garbage
4. Never achieve sync
```

**Filter Design Mismatch**:
- Bandpass filter: Designed for 25 kHz, but needed for 250 kHz
- Lowpass filter: Designed for 25 kHz, but needed for 250 kHz
- Result: Filters operated at 10x wrong frequency!

---

## The Fix

### Correct Signal Processing Order

**New Code (FIXED)**:
```
1. Start with 250 kHz multiplex (contains 57 kHz RBDS)
2. Bandpass filter 54-60 kHz (extract RBDS subcarrier)
   ✅ Designed at 250 kHz sample rate
3. Mix down by 57 kHz to baseband (0 Hz)
   ✅ RBDS now at baseband ±3 kHz
4. Lowpass filter 7.5 kHz (remove mixing artifacts)
   ✅ Designed at 250 kHz sample rate
5. Decimate 250 kHz → ~25 kHz
   ✅ Safe now - RBDS is at baseband
6. Resample to exactly 19 kHz (for symbol timing)
7. M&M timing recovery
8. Costas loop phase correction
9. BPSK demod + differential decoding
```

**Key Principle**: **Extract BEFORE filtering!**
- Bandpass → Mix → Lowpass → Decimate
- NOT: Lowpass → Decimate → Mix (old broken order)

### Filter Math Verification

At 250 kHz sample rate:
- **Bandpass 54-60 kHz**: Normalized freq 0.216-0.240 ✅ Valid
- **Mix by 57 kHz**: Normalized freq 0.228 ✅ Valid
- **Lowpass 7.5 kHz**: Normalized freq 0.030 ✅ Valid
- **Result**: RBDS at baseband ±3 kHz, preserved perfectly ✅

---

## Changes Made

### `app_core/radio/demodulation.py`

**RBDSWorker class**:
1. Added constants:
   - `RBDS_MIN_SAMPLE_RATE = 120000` Hz
   - `RBDS_INTERMEDIATE_RATE = 25000` Hz

2. **`_init_rbds_state()`**: Redesigned filter initialization
   - Removed old decimation filter (was removing RBDS)
   - Bandpass filter now designed at `sample_rate` (250 kHz)
   - Lowpass filter now designed at `sample_rate` (250 kHz)
   - Added validation: skip RBDS if sample rate < 120 kHz

3. **`_process_rbds()`**: Reordered DSP chain
   - Step 1: Bandpass 54-60 kHz (extract RBDS)
   - Step 2: Mix down 57 kHz (to baseband)
   - Step 3: Lowpass 7.5 kHz (remove aliases)
   - Step 4: Decimate to ~25 kHz
   - Step 5: Resample to 19 kHz
   - Steps 6-8: M&M → Costas → BPSK (unchanged)

---

## Testing Instructions

### Monitor RBDS Logs

```bash
# Watch RBDS processing in real-time
journalctl -u eas-station-audio.service -f | grep RBDS
```

### What to Look For

**Before Fix** (broken):
```
RBDS sync search: bit_counter=108645, syndrome=480/654 (normal/inverted), target syndromes=[383, 14, 303, 663, 748]
RBDS Costas: freq=13.934 Hz, phase=4.00 rad
RBDS worker status: 5000 samples processed, 0 groups decoded, buffer=0 bits, crc_fails=0
```
- Syndromes never match [383, 14, 303, 663, 748]
- Costas frequency ~14 Hz (wrong - should be ~3 Hz)
- **0 groups decoded**

**After Fix** (working):
```
RBDS SYNCHRONIZED at bit 12345
RBDS first synced block PASSED CRC: block_num=0, dataword=0x1234
RBDS group decoded: type=0A, station=WXYZ
RBDS PS: "WXYZ FM"
RBDS Radio Text: "Your emergency alert station"
```
- Should see "RBDS SYNCHRONIZED"
- Should see successful CRC checks
- Should see groups decoded > 0
- Costas frequency should stabilize around 3 Hz

### Deployment Steps

1. **Stop the audio service**:
   ```bash
   sudo systemctl stop eas-station-audio.service
   ```

2. **Deploy the update**:
   ```bash
   cd /opt/eas-station
   git pull
   sudo systemctl restart eas-station-audio.service
   ```

3. **Monitor logs**:
   ```bash
   journalctl -u eas-station-audio.service -f | grep RBDS
   ```

4. **Wait for RBDS sync** (may take 30-60 seconds):
   - Look for "RBDS SYNCHRONIZED" message
   - Look for station name decoding (PS field)
   - Look for groups decoded > 0

---

## Why This Fix Is Different

### Previous Failed Attempts (35+ PRs!)

Most focused on:
- Bit order (MSB vs LSB)
- Differential decoding formula
- CRC calculation
- Syndrome values
- Processing order (M&M vs Costas)

**None addressed the fundamental problem**: The RBDS signal was being filtered out BEFORE any decoding could happen!

### This Fix Addresses the Real Issue

1. **Sample rate mismatch**: Filters designed for wrong rate
2. **Processing order**: Extract subcarrier BEFORE filtering it out
3. **Hardware specific**: Accounts for Airspy R2's early decimation

---

## Expected Behavior

### On Airspy R2 at 2.5 MHz

**Sample Rate Flow**:
```
Airspy hardware: 2,500,000 Hz
    ↓ (early decimation 10x in driver)
Multiplex to RBDSWorker: 250,000 Hz
    ↓ (bandpass 54-60 kHz)
RBDS subcarrier extracted: 250,000 Hz
    ↓ (mix down 57 kHz)
Baseband RBDS: 250,000 Hz
    ↓ (lowpass 7.5 kHz, decimate)
Intermediate: ~25,000 Hz
    ↓ (resample)
Symbol rate: 19,000 Hz
    ↓ (M&M → Costas → BPSK)
Decoded bits: 1187.5 baud
```

### Other SDRs

Should still work correctly:
- **RTL-SDR** @ 250 kHz: Same as Airspy (no early decim, but filters correct)
- **Airspy** @ 10 MHz: Early decim 40x → 250 kHz → same path
- **SDRplay**: Depends on configured rate

---

## Success Metrics

✅ **Sync achieved**: "RBDS SYNCHRONIZED" in logs  
✅ **CRC passes**: "block PASSED CRC" messages  
✅ **Groups decoded**: Counter > 0  
✅ **Station info**: PS name and/or Radio Text decoded  
✅ **Costas stable**: Frequency ~3 Hz (not 14 Hz)

---

## Rollback Procedure

If this fix causes issues:

```bash
cd /opt/eas-station
git checkout v2.44.12  # Previous version
sudo systemctl restart eas-station-audio.service
```

---

## Technical Notes

### Why Bandpass Filter Wasn't Used Before?

It was **designed but never applied**! The old code:
1. Designed bandpass at intermediate_rate (25 kHz) - invalid for 54-60 kHz!
2. Never called in `_process_rbds()`
3. Only used decimation lowpass filter

Now:
1. Designed at sample_rate (250 kHz) - valid for 54-60 kHz ✅
2. Applied FIRST in processing chain ✅
3. Extracts RBDS before any destructive filtering ✅

### Nyquist Considerations

For bandpass filter at 250 kHz:
- Nyquist frequency: 125 kHz
- Target: 54-60 kHz
- Safe: 60 kHz < 125 kHz ✅

For 57 kHz mixing at 250 kHz:
- No aliasing: 57 kHz < 125 kHz ✅
- Clean downconversion to 0 Hz ✅

---

## Questions?

If RBDS still doesn't sync after this fix:
1. Check FM station has RBDS (not all do)
2. Check signal strength (need good RF signal)
3. Verify sample rate: `grep "RBDS rates" /var/log/syslog | tail`
4. Report syndrome values and Costas frequency in logs

---

**This should be the final fix. The mathematical analysis is sound and the signal flow is correct.**
