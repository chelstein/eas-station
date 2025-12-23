# RBDS Experimental Fix - Version 2.44.9

## Executive Summary

After analyzing the RBDS failure (30+ PRs, still "0 groups decoded"), I've identified that the fundamental issue is **symbol corruption in the M&M/Costas processing chain**. The bits coming out are completely random, not just inverted or reversed.

**Root Cause**: M&M timing recovery may be confused by carrier phase offset in the complex signal.

**Experimental Fix**: Swapped the order of Costas loop and M&M timing recovery.

## What Changed

### DSP Processing Order

**OLD (PySDR approach):**
```
Baseband mixing → M&M Symbol Timing → Costas Phase Lock → BPSK Demodulation
```

**NEW (Experimental):**
```
Baseband mixing → Costas Phase Lock → M&M Symbol Timing → BPSK Demodulation
```

### Rationale

1. M&M timing recovery operates on complex signals
2. If carrier has large phase offset, M&M's complex calculations may fail
3. By removing phase offset FIRST (Costas), M&M operates on clean signal
4. This contradicts PySDR tutorial, but their conditions may differ

### Files Modified

- `app_core/radio/demodulation.py` - Swapped M&M/Costas order (lines ~515-545)
- `tools/rbds_bit_permutations_test.py` - New diagnostic tool (for future debugging)
- `VERSION` - Updated to 2.44.9
- `docs/reference/CHANGELOG.md` - Documented change

## Testing Instructions

### 1. Deploy Version 2.44.9

```bash
cd /opt/eas-station
git fetch origin
git checkout copilot/debug-rbds-demodulation
git pull
sudo systemctl restart eas-station-audio.service
```

### 2. Monitor Logs

```bash
journalctl -u eas-station-audio.service -f | grep RBDS
```

### 3. Success Criteria

**✓ If it WORKS, you'll see:**
```
RBDS SYNCHRONIZED at bit X
RBDS first synced block PASSED CRC: block_num=3
RBDS block PASSED CRC: block_num=0  ← Multiple blocks passing!
RBDS block PASSED CRC: block_num=1
RBDS group: A=XXXX B=XXXX C=XXXX D=XXXX  ← Group decoded!
RBDS decoded: PS='STATION' PI=XXXX  ← Station name appearing!
RBDS worker status: X samples processed, Y groups decoded  ← Y > 0!
```

**✗ If it still FAILS, you'll see:**
```
RBDS sync search: bit_counter=X, syndrome=XXX/YYY  ← Still searching...
RBDS worker status: X samples processed, 0 groups decoded  ← Still zero!
```

## What Was Verified Before This Fix

### Proven CORRECT (Not the Problem)
- ✓ CRC calculation (tested with test_rbds_bit_order.py)
- ✓ Differential decoding logic (tested with permutation tool)
- ✓ Block syndrome values [383, 14, 303, 663, 748]
- ✓ Bit-to-register shifting (MSB-first, correct)
- ✓ Presync algorithm (checks all bit positions)
- ✓ Polarity checking (tries both normal and inverted)

### Identified Problem
- ✗ **Symbols are GARBAGE** - syndromes are completely random (164, 358, 36, 704, etc.)
- ✗ This means bits coming out of M&M→Costas→BPSK chain are wrong
- ✗ Not just inverted, not just reversed - fundamentally corrupted

## Next Steps If This Doesn't Work

If swapping M&M/Costas doesn't fix it, the issue is likely:

1. **M&M timing implementation bug** - Need to review complex M&M algorithm
2. **Sample rate mismatch** - 19 kHz resampling may be incorrect
3. **Costas loop not actually locking** - Phase/freq logging looks OK but may be fake
4. **Missing signal conditioning** - May need additional filtering or AGC
5. **Hardware/RF issue** - RBDS subcarrier at 57 kHz may not exist or be too weak

### Additional Diagnostics to Try

If still failing after this:

```bash
# Check if RBDS subcarrier exists at 57 kHz
# Run spectrum analysis on FM multiplex signal
# Look for peak at 57 kHz (should be 1-10% of pilot at 19 kHz)
```

## Technical Details

### Why This Might Fix It

Mueller & Muller clock recovery computes timing error from phase relationships:
```python
x = (out_rail_current - out_rail_prev2) * conj(out_prev)
y = (out_current - out_prev) * conj(out_rail_prev)
mm_val = real(y - x)
```

If `out_prev` has large phase rotation (e.g., 45° offset from carrier), the complex multiplication produces incorrect timing error. By running Costas first to align the constellation to the real axis, M&M operates on clean `out_prev` values with minimal phase variation.

### Why PySDR Does It Differently

PySDR tutorial may assume:
- Different sample rates
- Different signal conditioning
- Simulation vs. real RF
- Different BPSK implementation

Our real-world SDR may have different characteristics.

## Version History

- **v2.44.8** - Fixed register reset bug in synced mode (one-line fix)
- **v2.44.9** - Experimental M&M/Costas swap to fix symbol corruption

---

**Status**: Experimental - Awaiting user testing  
**Priority**: Critical - RBDS has been broken for 30+ PRs  
**Author**: GitHub Copilot AI  
**Date**: December 23, 2024
