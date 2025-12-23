# RBDS Sync Fix - December 23, 2024

## Problem
RBDS decoding was achieving synchronization but immediately losing it with "50/50 bad blocks" error, preventing any station metadata from being decoded.

## Symptoms (From User's Logs)
```
Dec 23 12:04:51 easstation eas-station-audio[1090672]: RBDS SYNCHRONIZED at bit 24142
Dec 23 12:04:53 easstation eas-station-audio[1090672]: RBDS SYNC LOST: 50/50 bad blocks
```

The pattern showed:
1. Presync successfully found blocks with correct spacing
2. Sync was achieved
3. Within 2 seconds, ALL 50 subsequent blocks failed CRC checks
4. Sync was lost and the cycle repeated

## Root Cause Analysis

### The Bug
When presync confirms two blocks have correct 26-bit spacing, the code achieves sync but **does not reset the shift register**. This causes register corruption:

**Before Fix (Buggy):**
```python
# When sync is achieved:
self._rbds_synced = True
self._rbds_block_bit_counter = 0
self._rbds_block_number = (j + 1) % 4
# Register still contains the 26 bits of the last presync block

# Loop continues, reads next bit:
bit = self._rbds_bit_buffer[self._rbds_buffer_index]
self._rbds_reg = ((self._rbds_reg << 1) | bit) & 0x3FFFFFF

# Result: Register now has bits [1-25] of old block + bit [0] of new block
# MISALIGNED! All subsequent CRC checks will fail.
```

### Why This Happens
1. Presync finds two valid blocks spaced 26 bits apart
2. The `_rbds_reg` shift register contains the complete 26-bit second block
3. Sync is achieved at line 979, but register is NOT reset
4. The while loop continues (line 916) and reads the NEXT bit
5. This bit is shifted into the register containing the old block
6. Now the register has: bits [1-25] of the old valid block + bit [0] of the new block
7. The register is misaligned by 1 bit!
8. After reading 25 more bits, the register still contains bits from two different blocks
9. CRC check fails because it's not a properly aligned 26-bit block
10. This repeats for all 50 blocks checked → sync lost

### The Bit-Level View

**Register state when sync is achieved:**
```
_rbds_reg = [0][1][2]...[24][25]  <- Valid block that passed CRC
```

**Without reset (BUG):**
```
Next bit read: [new_0]
_rbds_reg = [1][2][3]...[25][new_0]  <- CORRUPTED! Mix of two blocks
```

**With reset (FIX):**
```
_rbds_reg = [0][0][0]...[0][0]  <- Reset to zero
Next bit read: [new_0]
_rbds_reg = [0][0][0]...[0][new_0]  <- Clean start for new block
```

## The Fix

**File:** `app_core/radio/demodulation.py`
**Line:** 982
**Change:** Added `self._rbds_reg = 0` when achieving sync

```python
# Correct spacing - SYNCED!
# CRITICAL FIX: Reset the register when achieving sync
# The current register contains a complete valid block.
# We need to start fresh with the next 26 bits for the next block.
self._rbds_reg = 0  # <-- THE FIX
self._rbds_synced = True
self._rbds_wrong_blocks = 0
self._rbds_blocks_counter = 0
self._rbds_block_bit_counter = 0
self._rbds_block_number = (j + 1) % 4
self._rbds_group_good = 0
```

## Why This Works

After the fix:
1. When sync is achieved, `_rbds_reg` is reset to 0
2. The next bit read is the first bit of the next block
3. After reading 26 bits, the register contains a complete properly aligned block
4. CRC checks succeed
5. RBDS groups are decoded successfully
6. Station metadata (PS name, Radio Text, PI code) is extracted

## Validation

Created `/tmp/rbds_sync_fix_validation.py` to demonstrate:
- Buggy behavior: Shows how register corruption causes misalignment
- Fixed behavior: Shows how reset maintains proper alignment
- Output clearly shows the difference bit-by-bit

Run with: `python3 /tmp/rbds_sync_fix_validation.py`

## Impact

**Before:** RBDS never worked - sync was lost immediately every time
**After:** RBDS should maintain sync and decode groups successfully

## Files Changed

1. `app_core/radio/demodulation.py` - Added register reset on line 982
2. `VERSION` - Bumped to 2.43.7
3. `docs/reference/CHANGELOG.md` - Added detailed fix entry

## Testing Instructions

1. Deploy the updated code to your EAS station
2. Monitor the logs: `journalctl -u eas-station-audio.service -f | grep RBDS`
3. You should see:
   - "RBDS SYNCHRONIZED at bit X" (sync achieved)
   - "RBDS block decoded: type=X, data=0xXXXX" (blocks being decoded)
   - "RBDS group: A=XXXX B=XXXX C=XXXX D=XXXX" (complete groups)
   - "RBDS decoded: PS='STATION' PI=XXXX" (station metadata)
   - "RBDS sync OK: X/50 bad blocks" (sync maintained with acceptable error rate)

4. You should NOT see:
   - "RBDS SYNC LOST: 50/50 bad blocks" immediately after sync
   - Repeated sync/lost cycles without any decoded groups

## Version

- **Version:** 2.43.7
- **Date:** December 23, 2024
- **Type:** Bug fix (one-line change)
- **Severity:** Critical - RBDS was completely non-functional

## References

- Python-radio reference implementation (working): https://github.com/ChrisDev8/python-radio/blob/main/decoder.py
- RDS/RBDS Standard: EN 62106 (IEC 62106)
- Issue: RBDS sync achieved but immediately lost with 50/50 bad blocks
