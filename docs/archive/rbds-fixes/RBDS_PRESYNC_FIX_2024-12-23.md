# RBDS Presync Fix - December 23, 2024

## Problem Summary

The RBDS decoder was stuck in an infinite presync loop, never achieving full synchronization despite receiving valid RBDS signals. The logs showed:

```
RBDS presync: first block type 0 at bit 6842 (normal polarity)
RBDS presync: first block type 3 at bit 7176 (normal polarity)
RBDS presync: first block type 3 at bit 7265 (normal polarity)
RBDS presync: first block type 2 at bit 7570 (normal polarity)
...repeating forever...
```

But **never** saw:
```
RBDS SYNCHRONIZED at bit X
```

## Root Cause

The presync algorithm uses a two-stage approach:
1. Find a block with a valid syndrome (CRC check)
2. Find another block with correct spacing (26 bits × number of blocks apart)

**The bug:** When the second block had incorrect spacing (indicating the first was a false positive), the code would:
1. Reset `_rbds_presync = False` 
2. **Discard the current block** (which had a valid syndrome!)
3. Continue searching from the next bit

This created an infinite loop where valid RBDS blocks were being thrown away before they could be paired up.

### Example of Buggy Behavior

```
Bit 1000: Find syndrome match → Save as first block, presync=True
Bit 1030: Find syndrome match → Check spacing (30 ≠ 26) → DISCARD, presync=False
Bit 1031: Continue searching...
Bit 1060: Find syndrome match → Save as first block, presync=True
Bit 1085: Find syndrome match → Check spacing (25 ≠ 26) → DISCARD, presync=False
... loop forever, never finding two correctly-spaced blocks
```

## The Fix

Changed the spacing mismatch handler from **discarding** the current block to **reusing** it:

### Before (Buggy Code)
```python
if expected_bits != actual_bits:
    # Wrong spacing - false positive, reset presync and CONTINUE searching
    self._rbds_presync = False  # ❌ Discards current block!
    # ... logging ...
```

### After (Fixed Code)
```python
if expected_bits != actual_bits:
    # Wrong spacing - false positive first block
    # CRITICAL FIX: Don't discard the current block! It has a valid syndrome,
    # so treat it as the new first block candidate.
    self._rbds_lastseen_offset = j  # ✅ Save current block
    self._rbds_lastseen_offset_counter = self._rbds_bit_counter  # ✅ Save position
    # Keep presync=True since we have a new first block candidate
    # ... logging ...
```

## Why This Works

A valid syndrome match is valuable data:
- Syndrome matches have a ~1 in 1024 chance of being random false positives
- Finding a syndrome match means we're likely near real RBDS data
- By keeping each valid match, we maximize the chance of finding two correctly-spaced blocks

### Example of Fixed Behavior

```
Bit 1000: Find syndrome match → Save as first block, presync=True
Bit 1030: Find syndrome match → Check spacing (30 ≠ 26) → Save as NEW first block, presync=True
Bit 1056: Find syndrome match → Check spacing (26 = 26) ✓ → SYNCHRONIZED!
```

The key insight: When spacing fails, the **current** block is more likely to be correct than the **previous** block. So we should keep the current block and discard the previous one.

## Expected Results After Fix

After deploying this fix, the RBDS decoder should:

1. ✅ Achieve synchronization within a few seconds
2. ✅ Log "RBDS SYNCHRONIZED at bit X"
3. ✅ Begin decoding RBDS groups
4. ✅ Display station information (PS, RT, PTY, etc.)

Watch for these log messages:
```
[INFO] RBDS SYNCHRONIZED at bit X
[INFO] RBDS group: A=XXXX B=XXXX C=XXXX D=XXXX
[INFO] RBDS sync OK: Y/50 bad blocks, polarity: N normal, M inverted
```

## Testing Instructions

1. Deploy the updated code:
   ```bash
   cd /opt/eas-station
   sudo ./update.sh
   ```

2. Restart the audio service:
   ```bash
   sudo systemctl restart eas-station-audio.service
   ```

3. Monitor the logs:
   ```bash
   journalctl -u eas-station-audio.service -f | grep RBDS
   ```

4. Expected to see within 30 seconds:
   - "RBDS SYNCHRONIZED at bit X"
   - "RBDS group: A=XXXX B=XXXX C=XXXX D=XXXX"
   - Radio station information appearing in the UI

## Files Changed

- `app_core/radio/demodulation.py` (lines 964-982): Fixed presync spacing handler
- `VERSION`: Incremented to 2.43.8
- `docs/reference/CHANGELOG.md`: Documented the fix

## Technical Details

The RBDS decoder uses a syndrome-based block synchronization algorithm similar to python-radio and PySDR:

- **Syndrome**: A 10-bit CRC checksum that identifies block type (A, B, C, D, or C')
- **Presync**: Two-stage process to find initial synchronization
  - Stage 1: Find any block with valid syndrome
  - Stage 2: Find second block at correct spacing (validates both blocks are real)
- **Synced**: Process blocks at exact 26-bit intervals, tracking error rate

The fix ensures Stage 2 doesn't throw away valid Stage 1 candidates, allowing the decoder to eventually find two correctly-spaced real RBDS blocks.

## Related Issues

This fix addresses the "still not working" issue where presync was repeatedly finding blocks but never achieving full sync. Previous fixes addressed:

- Register corruption after achieving sync (2.43.7)
- Debug log flooding (2.43.6)
- Missing RBDS constants (2.43.5)

With all these fixes in place, RBDS decoding should now work reliably.
