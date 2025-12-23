# RBDS Diagnostic Guide - Version 2.44.1

## What Changed

This version resets debug counters when RBDS sync is achieved, allowing us to see exactly what happens after sync for the first 10 blocks.

**Previous Problem**: After multiple sync attempts, `_crc_check_count` would exceed 10 and debug logging would stop, making it impossible to diagnose why groups weren't being decoded.

**Fix Applied**: Reset `_crc_check_count = 0`, `_rbds_normal_blocks = 0`, and `_rbds_inverted_blocks = 0` when sync is achieved.

## What to Look For After Deploying

After deploying this version and monitoring `journalctl -u eas-station-audio.service -f | grep RBDS`, you should see one of these patterns:

### Pattern 1: Blocks Are Being Processed (Expected)

```
[INFO] RBDS SYNCHRONIZED at bit 17899 after block type 1 (pos 1), expecting position 2 next
[DEBUG] RBDS sync register state: 0x16EE5E5, dataword=0x5BB9, checkword=0x1E5
[INFO] RBDS processing first synced block: block_num=2, bit_counter=17925
[DEBUG] RBDS CRC check #1: block_num=2, reg=0xXXXXXXX, dataword=0xXXXX, checkword=0xXXX, block_crc=XXX
```

If you see this, blocks ARE being processed. Then look for:

**Success Case**:
```
[INFO] RBDS block PASSED CRC: block_num=2, dataword=0xXXXX, inverted=False
[INFO] RBDS block PASSED CRC: block_num=3, dataword=0xXXXX, inverted=False
[INFO] RBDS block PASSED CRC: block_num=0, dataword=0xXXXX, inverted=False
[INFO] RBDS block PASSED CRC: block_num=1, dataword=0xXXXX, inverted=False
[INFO] RBDS group: A=XXXX B=XXXX C=XXXX D=XXXX
```

**Failure Case**:
```
[WARNING] RBDS block FAILED CRC: block_num=2, expected_offset=360 or 848, checkword=0xXXX, block_crc=XXX
[WARNING] RBDS block FAILED CRC: block_num=3, expected_offset=436, checkword=0xXXX, block_crc=XXX
```

### Pattern 2: Blocks Are NOT Being Processed (Bug!)

```
[INFO] RBDS SYNCHRONIZED at bit 17899 after block type 1 (pos 1), expecting position 2 next
[DEBUG] RBDS sync register state: 0x16EE5E5, dataword=0x5BB9, checkword=0x1E5
(... no further RBDS messages for several seconds ...)
[DEBUG] RBDS worker status: 800 samples processed, 0 groups decoded, buffer=0 bits, crc_fails=0
```

If you see this, it means the synced block processing code is NOT being reached. This would indicate:
- Bit buffer is staying empty (no bits being generated post-sync), OR  
- The while loop in `_decode_rbds_groups()` is exiting early, OR
- There's a logic error preventing entry to the synced block processing code

### Pattern 3: Wrong Block Numbers (Bug!)

```
[INFO] RBDS SYNCHRONIZED at bit 17899 after block type 1 (pos 1), expecting position 2 next
[INFO] RBDS processing first synced block: block_num=2, bit_counter=17925
[DEBUG] RBDS CRC check #1: block_num=2, ...
[WARNING] RBDS block FAILED CRC: block_num=2, ...
[DEBUG] RBDS CRC check #2: block_num=3, ...
[WARNING] RBDS block FAILED CRC: block_num=3, ...
[DEBUG] RBDS CRC check #3: block_num=0, ...
[WARNING] RBDS block FAILED CRC: block_num=0, ...
```

If ALL blocks fail CRC immediately after sync, this indicates:
- Timing issue (blocks not aligned on 26-bit boundaries), OR
- Polarity issue (need inverted bits but trying normal first), OR
- Syndrome calculation issue

## What the Numbers Mean

### Register State at Sync
```
RBDS sync register state: 0x16EE5E5, dataword=0x5BB9, checkword=0x1E5
```
- `reg`: Full 26-bit shift register (hex)
- `dataword`: Upper 16 bits (the actual data)
- `checkword`: Lower 10 bits (the CRC checksum)

### CRC Check Details
```
RBDS CRC check #1: block_num=2, reg=0xXXXXXXX, dataword=0xXXXX, checkword=0xXXX, block_crc=XXX
```
- `block_num`: Which block in the group (0=A, 1=B, 2=C/C', 3=D)
- `dataword`: The 16-bit data extracted from register
- `checkword`: The 10-bit CRC from register
- `block_crc`: The calculated syndrome from the dataword

For a block to pass CRC:
```
(checkword XOR offset_word[block_num]) == block_crc
```

Where offset_word values are:
- A (block 0): 0x0FC (252) → syndrome 0x17F (383)
- B (block 1): 0x198 (408) → syndrome 0x00E (14)
- C (block 2): 0x168 (360) → syndrome 0x12F (303)
- D (block 3): 0x1B4 (436) → syndrome 0x297 (663)
- C' (also block 2): 0x350 (848) → syndrome 0x2EC (748)

## What to Send Me

Once you've deployed this version, capture the logs for about 60 seconds and send me:

1. **The sync achievement message** (shows what block type triggered sync and what block_num we're expecting)
2. **The first 20 lines after sync** (shows if blocks are being processed and if they're passing/failing CRC)
3. **The block_num sequence** (should be repeating 0→1→2→3→0→1→2→3...)
4. **Any polarity messages** (shows if we're using normal or inverted bits)

Example of good output:
```bash
journalctl -u eas-station-audio.service -f | grep -A 20 "RBDS SYNCHRONIZED"
```

This will help me diagnose:
- Whether blocks are being processed at all
- Whether CRC checks are passing or failing
- Whether block numbering is correct
- Whether polarity is the issue

## Expected Timeline

After deploying and restarting the service:
- Within **10-30 seconds**: Should see "RBDS SYNCHRONIZED" message
- Within **1-2 seconds after sync**: Should see "RBDS processing first synced block" message  
- Within **5 seconds after sync**: Should see either:
  - "RBDS group: A=XXXX B=XXXX C=XXXX D=XXXX" (SUCCESS!), OR
  - Multiple "RBDS block FAILED CRC" messages (need to investigate why)

## Deployment Commands

```bash
cd /opt/eas-station
sudo -u eas-station git fetch origin
sudo -u eas-station git checkout copilot/fix-rbds-sync-issue
sudo -u eas-station git pull
sudo ./update.sh
```

Then monitor:
```bash
journalctl -u eas-station-audio.service -f | grep RBDS
```

---

**Version**: 2.44.1  
**Branch**: copilot/fix-rbds-sync-issue  
**Purpose**: Enhanced debugging to diagnose why RBDS achieves sync but doesn't decode groups  
**Next Step**: Analyze debug output to identify and fix the actual decoding bug
