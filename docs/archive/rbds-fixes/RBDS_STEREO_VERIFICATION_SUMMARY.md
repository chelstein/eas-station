# RBDS and Stereo Path Verification Summary

## Executive Summary

**Date**: December 20, 2024
**Version**: 2.43.0
**Status**: ✅ **RBDS UPGRADED TO PySDR-STYLE IMPLEMENTATION**

The RBDS decoding has been completely rewritten using industry-standard techniques from the [PySDR RDS Tutorial](https://pysdr.org/content/rds.html). This fixes audio stalling issues and provides proper signal synchronization for real-world FM broadcasts.

---

## What Changed (December 20, 2024)

### Previous Issues Fixed

1. **Audio stalling after 5-6 seconds**
   - **Cause**: RBDS bit buffer grew unbounded; decode loop had no limit
   - **Fix**: Max 6000 bits, max 100 iterations per call, auto-clear on 200 CRC failures

2. **RBDS not decoding on real stations**
   - **Cause**: Early-late gate timing inadequate; no frequency synchronization
   - **Fix**: Mueller & Muller clock recovery + Costas loop

### New PySDR-Style Implementation

| Component | Old | New |
|-----------|-----|-----|
| **Symbol Timing** | Early-late gate | Mueller & Muller |
| **Freq Sync** | None | Costas loop |
| **Samples/Symbol** | 4 | 16 |
| **Target Rate** | 4,750 Hz | 19,000 Hz |
| **Lowpass Filter** | 2.4 kHz, variable taps | 7.5 kHz, 101 taps |
| **Buffer Limit** | Unbounded | 6,000 bits max |
| **Decode Iterations** | Unbounded | 100 max per call |

---

## How RBDS Works Now

### Signal Flow

```
FM Multiplex (from discriminator)
    ↓
Bandpass Filter (54-60 kHz) ─────────── Extract RBDS subcarrier
    ↓
Mix with 57 kHz carrier ─────────────── Phase-continuous local oscillator
    ↓
Lowpass Filter (7.5 kHz, 101 taps) ─── Matched filter
    ↓
Resample to 19 kHz ──────────────────── 16 samples/symbol
    ↓
Costas Loop ─────────────────────────── Correct frequency offset
    ↓
Mueller & Muller Clock Recovery ─────── Find optimal sample points
    ↓
Differential BPSK Decode ────────────── Bits
    ↓
CRC Check & Group Assembly ──────────── PI, PS, RT, PTY
    ↓
Metadata to Frontend
```

### Key Components Explained

#### Costas Loop
The Costas loop is essential for RBDS. It corrects **frequency offset** - even 1-2 Hz error causes phase rotation that corrupts symbols. The loop:
- Tracks phase error using `real(sample) × imag(sample)`
- Adjusts local oscillator frequency and phase
- Converges in ~100-500 symbols

#### Mueller & Muller Clock Recovery
M&M finds the **optimal sampling instant** for each symbol:
- Uses linear interpolation for sub-sample accuracy
- Computes timing error from transition edges
- Tracks timing drift across chunks
- Much more robust than early-late gate

#### Bounded Execution
To prevent audio stalling:
- **Max iterations**: 100 blocks per call (~2.5ms)
- **Buffer limit**: 6,000 bits (~5 seconds of data)
- **Failure detection**: 200 consecutive CRC failures = clear buffer
- **Adaptive skip**: Skip 4 bits at a time when scanning garbage

---

## Technical Parameters

### RBDS Configuration

```python
# Symbol rate (fixed by standard)
symbol_rate = 1187.5  # baud

# PySDR-style parameters
samples_per_symbol = 16        # Was 4
target_rate = 19000            # Hz (16 × 1187.5)
lowpass_cutoff = 7500          # Hz
lowpass_taps = 101             # Fixed

# Costas loop gains (damping=0.707, BW~0.01)
costas_alpha = 0.132           # Phase gain
costas_beta = 0.00932          # Frequency gain

# Buffer limits
max_bit_buffer = 6000          # bits
max_decode_iterations = 100    # per call
max_consecutive_failures = 200 # before clear
```

### Sample Rate Requirements

| Feature | Minimum | Recommended | Reason |
|---------|---------|-------------|--------|
| **RBDS** | 114 kHz | 250+ kHz | 2× Nyquist of 57 kHz |
| **Stereo** | 76 kHz | 250+ kHz | 2× Nyquist of 38 kHz |

---

## What This Means for Users

### RBDS Will Now Work If:
1. Sample rate ≥ 114 kHz ✓
2. `enable_rbds=True` in receiver settings ✓
3. Station broadcasts RDS/RBDS ✓
4. Decent signal strength ✓

### Audio Will Not Stall Because:
1. Decode loop limited to 100 iterations ✓
2. Buffer capped at 6,000 bits ✓
3. Auto-clear after 200 failures ✓
4. Signal quality check rejects noise ✓

### What You'll See:
- `rbds_ps_name`: Station callsign (e.g., "WXYZ-FM")
- `rbds_radio_text`: Now playing info
- `rbds_pty`: Program type (Rock, News, etc.)
- `rbds_pi_code`: Station identifier

---

## Troubleshooting

### RBDS Not Decoding

1. **Check logs for signal quality**:
   ```
   journalctl -u eas-service | grep RBDS
   ```
   Look for "RBDS signal too weak" or "consecutive CRC failures"

2. **Check sample rate**:
   - Must be ≥ 114 kHz
   - Look for "RBDS configuration" at startup

3. **Check if station has RBDS**:
   - Not all FM stations broadcast RBDS
   - Try a major commercial station first

4. **Check signal strength**:
   - Weak signals produce noise that fails CRC
   - Try moving antenna or tuning to stronger station

### Audio Stalling (Should Not Happen Anymore)

The new implementation has multiple safeguards. If stalling still occurs:
1. Check for other blocking operations in audio pipeline
2. Look for CPU overload (especially on Raspberry Pi)
3. Report issue with logs

---

## Files Modified

### Code Changes
- `app_core/radio/demodulation.py` - Complete RBDS rewrite
  - Added `_rbds_costas_loop()` method
  - Added `_rbds_mm_clock_recovery()` method
  - Updated `_extract_rbds()` with new pipeline
  - Updated `_decode_rbds_groups()` with bounded execution

### Documentation Updated
- `docs/audio/RBDS_STEREO_PATH_VERIFICATION.md` - Technical details
- `RBDS_STEREO_VERIFICATION_SUMMARY.md` - This file

---

## References

- [PySDR RDS Tutorial](https://pysdr.org/content/rds.html) - Implementation basis
- NRSC-4-B - RBDS Standard Specification
- IEC 62106 - Radio Data System specification

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.43.0 | Dec 20, 2024 | PySDR-style RBDS with M&M + Costas loop |
| 2.42.2 | Dec 19, 2024 | Initial verification and documentation |

---

**Status**: ✅ RBDS fully functional with proper synchronization
**Last Updated**: December 20, 2024
