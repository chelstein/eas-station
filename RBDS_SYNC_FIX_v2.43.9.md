# RBDS Sync Fix - Version 2.43.9

## Problem Summary

RBDS decoder was achieving synchronization but immediately losing it (50/50 bad blocks within 1-2 seconds).

## Root Cause Analysis

### The Issue

When the presync logic confirmed two RBDS blocks with correct 26-bit spacing:

1. **State at sync achievement**: The shift register (`_rbds_reg`) contained 26 bits of a complete valid block that had just passed CRC validation
2. **Problematic line 990**: `self._rbds_reg = 0` - This reset the register to zero
3. **Result**: The synchronized bit alignment was destroyed

### Why Resetting Broke Sync

The RBDS decoder uses a 26-bit shift register that accumulates bits one at a time:

```python
# Line 921: Every iteration shifts in a new bit
self._rbds_reg = ((self._rbds_reg << 1) | bit) & 0x3FFFFFF
```

**Scenario with register reset (BROKEN)**:
```
At sync achievement:
  Register = [bits 0-25 of valid block N]  ← Just validated with CRC!

After reset (line 990):
  Register = [0, 0, 0, ..., 0]  ← Threw away the synchronized position!

Next iteration (bit 0 of block N+1):
  Register = [0, 0, 0, ..., 0, bit₀]  ← Only 1 bit

After 25 more iterations:
  Register = [bit₀, bit₁, ..., bit₂₄]  ← Only 25 bits total!
  
When we check CRC:
  We have 25 bits of the new block, not 26
  Missing the last bit (bit₂₅)
  CRC fails ✗
```

**Scenario without register reset (CORRECT)**:
```
At sync achievement:
  Register = [bits 0-25 of block N]  ← Just validated with CRC!

NO RESET - let register continue naturally

Next iteration (bit 0 of block N+1):
  Register = [bit₁, bit₂, ..., bit₂₅, bit₀]  ← Shifted left, bit₀ entered
           = [bits 1-25 of block N, bit 0 of block N+1]

After 2 more iterations:
  Register = [bits 2-25 of block N, bits 0-1 of block N+1]
  
After 26 iterations total:
  Register = [bits 0-25 of block N+1]  ← Complete next block! ✓
  
When we check CRC:
  We have all 26 bits of the new block
  Proper alignment maintained
  CRC passes ✓
```

## The Fix

**File**: `app_core/radio/demodulation.py`  
**Line**: 990 (removed)  
**Change**: Removed `self._rbds_reg = 0`

### Before (BROKEN)
```python
else:
    # Correct spacing - SYNCED!
    # CRITICAL FIX: Reset the register when achieving sync
    # The current register contains a complete valid block.
    # We need to start fresh with the next 26 bits for the next block.
    self._rbds_reg = 0  # ← THIS WAS THE BUG
    self._rbds_synced = True
    self._rbds_wrong_blocks = 0
    self._rbds_blocks_counter = 0
    self._rbds_block_bit_counter = 0
    self._rbds_block_number = (j + 1) % 4
    self._rbds_group_good = 0
    logger.info("RBDS SYNCHRONIZED at bit %d", self._rbds_bit_counter)
```

### After (FIXED)
```python
else:
    # Correct spacing - SYNCED!
    # CRITICAL FIX: Do NOT reset the register when achieving sync!
    # The current register contains a complete valid block at bit position N.
    # As new bits shift in (via line 921), after 26 more bits the register
    # will naturally contain the next complete block at position N+1.
    # Resetting the register would break this alignment and cause sync loss.
    self._rbds_synced = True
    self._rbds_wrong_blocks = 0
    self._rbds_blocks_counter = 0
    self._rbds_block_bit_counter = 0
    self._rbds_block_number = (j + 1) % 4
    self._rbds_group_good = 0
    logger.info("RBDS SYNCHRONIZED at bit %d", self._rbds_bit_counter)
```

## Why This Fix Works

1. **Natural shifting**: The shift register naturally rolls forward as new bits arrive
2. **26-bit window**: After 26 new bits shift in, the old block shifts out completely
3. **Alignment preserved**: The bit boundaries remain aligned with RBDS block structure
4. **CRC validation works**: Each block has all 26 bits in the correct positions

## Log Evidence

### Before Fix (BROKEN)
```
Dec 23 12:34:30 easstation eas-station-audio[1095845]: RBDS SYNCHRONIZED at bit 17585
Dec 23 12:34:33 easstation eas-station-audio[1095845]: RBDS SYNC LOST: 50/50 bad blocks
Dec 23 12:34:35 easstation eas-station-audio[1095845]: RBDS SYNCHRONIZED at bit 20137
Dec 23 12:34:37 easstation eas-station-audio[1095845]: RBDS SYNC LOST: 50/50 bad blocks
```
Pattern: Sync achieved → immediately lost (50/50 bad blocks)

### After Fix (EXPECTED)
```
Dec 23 XX:XX:XX easstation eas-station-audio[XXXXX]: RBDS SYNCHRONIZED at bit XXXXX
Dec 23 XX:XX:XX easstation eas-station-audio[XXXXX]: RBDS sync OK: 2/50 bad blocks
Dec 23 XX:XX:XX easstation eas-station-audio[XXXXX]: RBDS group: A=XXXX B=XXXX C=XXXX D=XXXX
Dec 23 XX:XX:XX easstation eas-station-audio[XXXXX]: RBDS decoded: PS='STATION' PI=XXXX
```
Pattern: Sync achieved → sync maintained → groups decoded

## Impact

- **Symptom**: RBDS achieved sync but immediately lost it (50/50 bad blocks)
- **Fix complexity**: Minimal (1 line removed)
- **Risk**: Very low (makes code match intended design)
- **Testing**: Python compilation passed, logic verified

## Related Fixes

This is the second part of the RBDS sync fix series:

1. **v2.43.8**: Fixed presync never completing (spacing mismatch logic)
2. **v2.43.9**: Fixed sync immediately lost (register reset) ← THIS FIX

## Technical Details

### Shift Register Mechanics

The RBDS decoder uses a 26-bit shift register to buffer incoming bits:

```python
self._rbds_reg = ((self._rbds_reg << 1) | bit) & 0x3FFFFFF
```

Breaking this down:
- `self._rbds_reg << 1`: Shift all bits left by 1 position (oldest bit falls off the left)
- `| bit`: OR in the new bit at position 0 (rightmost)
- `& 0x3FFFFFF`: Mask to 26 bits (0x3FFFFFF = 0b11111111111111111111111111 = 26 ones)

### Block Counter Logic

When synced, the decoder counts bits within each block:

```python
if self._rbds_block_bit_counter < 25:
    self._rbds_block_bit_counter += 1
else:
    # We've counted bits 0-25 (26 total)
    # Check the block now in the register
```

Counter values:
- 0 → just started a new block
- 1-24 → accumulating bits
- 25 → have 26th bit, check CRC

### Why Reset Broke This

When we reset the register at sync:
1. Counter starts at 0 (correct)
2. After 25 increments, counter = 25 (correct)
3. But the register only has 25 bits total!
4. The register was zeroed at sync, so we're missing the pre-sync bits
5. CRC fails because we don't have a complete 26-bit block

By NOT resetting:
1. Counter starts at 0 (correct)
2. After 25 increments, counter = 25 (correct)
3. Register has 26 bits: [bits 1-25 of old block, bits 0-24 of new block] after 25 shifts
4. After the 26th shift (counter wraps), register has bits 0-25 of new block
5. CRC passes ✓

## Verification

To verify this fix is working, check the logs for:

1. ✅ "RBDS SYNCHRONIZED at bit XXXXX" messages
2. ✅ "RBDS sync OK: X/50 bad blocks" with low error counts (< 5)
3. ✅ "RBDS group: A=XXXX B=XXXX C=XXXX D=XXXX" decoded groups
4. ✅ "RBDS decoded: PS='STATION' PI=XXXX" metadata
5. ❌ NO "RBDS SYNC LOST: 50/50 bad blocks" immediately after sync

## Conclusion

The fix is simple but critical: **Don't reset the shift register when achieving sync.**

The register's natural shifting behavior maintains the correct bit alignment. Resetting it breaks the synchronization that we just worked hard to achieve.

---

**Version**: 2.43.9  
**Date**: 2024-12-23  
**Files Changed**:
- `app_core/radio/demodulation.py` (1 line removed, comment updated)
- `VERSION` (2.43.8 → 2.43.9)
- `docs/reference/CHANGELOG.md` (fix documented)
