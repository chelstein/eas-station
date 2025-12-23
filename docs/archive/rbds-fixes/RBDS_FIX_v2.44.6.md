# RBDS Decoding Fix - Version 2.44.6

## Problem Diagnosed

From analysis of diagnostic logs in `bugs/rbds-diagnostics-20251223-152622/`:

### Symptoms
- RBDS achieves SYNCHRONIZED state repeatedly
- 100% of CRC checks fail after sync (except rare 2-4% random successes)
- Pattern: SYNCHRONIZED → 50/50 bad blocks → SYNC LOST (repeats)
- Signal processing works perfectly (Costas loop, M&M timing, bit extraction)

### Root Cause: 26-Bit Block Misalignment

**The Bug:**
When RBDS presync found two blocks with correct spacing and achieved sync, the code would:
1. Set `_rbds_synced = True`
2. Set `_rbds_block_bit_counter = 0`
3. Wait for 26 MORE bits before processing the first block

This caused a 26-bit offset! The 26-bit register ALREADY contained a valid block (the one that triggered sync), but the code waited for 26 additional bits, causing all subsequent CRC checks to fail because block boundaries were misaligned.

**Evidence:**
- Sync achieved at bit 34184 (register contains valid block)
- First block processed at bit 34210 (34184 + 26 bits later)
- Register 0x24CDAA1 has syndrome 366 (expected 663 for Block D)
- Syndrome 366 indicates the block is corrupted/misaligned
- Only 2 out of 50 blocks passed CRC (4% random success from noise)

## The Fix

Modified `app_core/radio/demodulation.py` in the `_decode_rbds_groups()` method:

**Before:** When sync achieved, set block_bit_counter=0 and wait for 26 more bits

**After:** When sync achieved, immediately process the current 26-bit block inline before any more bits shift into the register

### Key Changes

1. **Immediate Block Processing**: When presync finds correct spacing, extract and process the current register contents immediately
2. **CRC Verification**: Check both normal and inverted polarity on the sync block
3. **State Initialization**: Properly initialize counters with the processed block counted
4. **Block Alignment**: Set block_number to the NEXT expected block (not current)

### Code Location

File: `app_core/radio/demodulation.py`
Function: `_decode_rbds_groups()`
Lines: ~999-1091 (presync spacing verification section)

## Testing

### Unit Tests Created

1. `test_rbds_bit_order.py` - Verifies CRC calculation correctness
2. `analyze_rbds_failure.py` - Analyzes actual failed blocks from logs
3. `test_block_reversal.py` - Tests various bit order transformations

All tests confirm the CRC algorithm itself is correct; the issue was block alignment.

### Expected Behavior After Fix

1. Sync achieved when presync finds two blocks with correct spacing
2. First synced block is processed IMMEDIATELY (syndrome should match)
3. CRC checks should pass for valid RBDS data
4. Blocks should maintain correct 26-bit alignment
5. Group decoding should succeed (PI code, station name, radio text)

## Deployment

### Update Command
```bash
cd /opt/eas-station
sudo -u eas-station git fetch origin
sudo -u eas-station git checkout copilot/diagnose-rbds-issues
sudo -u eas-station git pull
sudo ./update.sh
```

### Monitor Logs
```bash
journalctl -u eas-station-audio.service -f | grep RBDS
```

### Success Indicators

Look for these log patterns:

**✓ Good - Block Passed CRC:**
```
[INFO] RBDS SYNCHRONIZED at bit XXXXX
[INFO] RBDS first synced block PASSED CRC: block_num=X, dataword=0xXXXX, polarity=normal
[INFO] RBDS block PASSED CRC: block_num=X, dataword=0xXXXX, inverted=False
[INFO] RBDS group: A=XXXX B=XXXX C=XXXX D=XXXX
```

**✗ Bad - Still Failing:**
```
[INFO] RBDS SYNCHRONIZED at bit XXXXX  
[WARNING] RBDS first synced block FAILED CRC: block_num=X, expected_offset=XXX, checkword=0xXXX, block_crc=XXX
[WARNING] RBDS SYNC LOST: 50/50 bad blocks
```

## Technical Details

### RBDS Block Structure
- 26 bits total per block
- 16-bit dataword (information)
- 10-bit checkword (CRC)
- 4 blocks per group: A, B, C/C', D

### Syndrome Values
- Block A: 383 (0x17F) - PI code
- Block B: 14 (0x00E) - Group type
- Block C: 303 (0x12F) - Data
- Block D: 663 (0x297) - Data  
- Block C': 748 (0x2EC) - Alternate C

### CRC Polynomial
- g(x) = x^10 + x^8 + x^7 + x^5 + x^4 + x^3 + 1
- Binary: 0x5B9 (10110111001)

## Version History

- **2.44.5**: Diagnostic logs collected, bug identified
- **2.44.6**: Block alignment fix implemented

## Related Documents

- `RBDS_DIAGNOSTIC_v2.44.1.md` - Diagnostic guide
- `RBDS_CODE_AUDIT_2024-12-23.md` - Previous code audit
- `bugs/rbds-diagnostics-20251223-152622/` - Diagnostic log archive

## Author Notes

This fix resolves a subtle timing bug introduced when the presync logic was refactored. The reference implementations (python-radio, PySDR) process blocks immediately upon sync, but the eas-station implementation was deferring processing by 26 bits, causing perpetual misalignment.

The fix ensures that when a valid 26-bit block is detected during presync (confirmed by syndrome match and correct spacing), that exact block is processed before any additional bits shift into the register.
