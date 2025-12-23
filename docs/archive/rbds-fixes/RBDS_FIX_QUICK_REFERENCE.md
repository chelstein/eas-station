# RBDS Fix - Quick Reference

## What Was Fixed

**Version 2.43.4** - Fixed critical buffer management issue in RBDS decoder

### The Problem
Your logs showed:
```
RBDS presync: spacing mismatch (expected 52, got 55)
RBDS bits: 32 new bits, 17 ones (53.1%), buffer=0
```

The `buffer=0` was the smoking gun - bits were being consumed and lost during failed presync attempts.

### The Solution
Changed from **destructive pop-based** to **preserving index-based** bit processing.

**Before** (broken):
```python
while self._rbds_bit_buffer:
    bit = self._rbds_bit_buffer.pop(0)  # DESTROYS bit
    # If presync fails, bits are gone forever
```

**After** (fixed):
```python
while self._rbds_buffer_index < len(self._rbds_bit_buffer):
    bit = self._rbds_bit_buffer[self._rbds_buffer_index]  # PRESERVES bit
    self._rbds_buffer_index += 1
    # If presync fails, bits remain for retry

# Only remove after successful processing
del self._rbds_bit_buffer[:self._rbds_buffer_index]
```

## What You Should See Now

### In Logs

**Before Fix:**
```
RBDS bits: 32 new bits, buffer=0
RBDS presync: spacing mismatch
RBDS bits: 24 new bits, buffer=0
RBDS presync: spacing mismatch
[repeats forever, never syncs]
```

**After Fix:**
```
RBDS bits: 32 new bits, buffer=32
RBDS bits: 24 new bits, buffer=56
RBDS presync: first block type 0 at bit 104
RBDS presync: spacing mismatch - resetting presync
RBDS bits: 32 new bits, buffer=88
[buffer continues to grow]
RBDS SYNCHRONIZED at bit 312  ← SUCCESS!
RBDS group: A=1234 B=5678 C=9ABC D=DEF0
```

### In UI

Navigate to **Audio Monitoring** page, you should now see under your FM station:

**RBDS/RDS Metadata section:**
- Station Name (PS): "WXYZ-FM" 
- Program ID (PI): 0x1234
- Program Type (PTY): "Rock" or similar
- Radio Text (RT): "Now Playing: Artist - Song"
- Traffic Program (TP): Yes/No
- Music/Speech (M/S): Music or Speech

## Testing Steps

1. **Restart the audio service** (to load new code):
   ```bash
   sudo systemctl restart eas-station-audio.service
   ```

2. **Watch the logs**:
   ```bash
   journalctl -u eas-station-audio.service -f | grep RBDS
   ```

3. **What to look for**:
   - ✅ `buffer=X` where X grows (not always 0)
   - ✅ `RBDS SYNCHRONIZED at bit X` (THE key success message)
   - ✅ `RBDS group: A=XXXX B=XXXX C=XXXX D=XXXX`
   - ✅ `RBDS sync OK: X/50 bad blocks`

4. **Check the UI**:
   - Open Audio Monitoring page
   - Look for your FM station
   - Scroll to "FM Stereo / RBDS Information"
   - Should see station metadata

## If It Still Doesn't Work

1. **Verify RBDS is enabled**:
   - Go to Admin → Radio Receiver Settings
   - Check "Extract RBDS/RDS" is checked
   - Only works with WFM (Wide FM), not NFM (Narrow FM)

2. **Check sample rate**:
   - Logs should show: "RBDS ENABLED: creating worker thread at X Hz"
   - Need at least 114 kHz sample rate (250 kHz+ recommended)
   - If you see "RBDS DISABLED: sample_rate=X Hz is below 114 kHz minimum", increase sample rate

3. **Verify station broadcasts RBDS**:
   - Not all FM stations broadcast RBDS/RDS
   - Try a major commercial station first
   - Look for "RBDS signal too weak" in logs (means station has no RBDS)

4. **Check signal strength**:
   - Weak signals produce noise that fails CRC
   - Try adjusting antenna or tuning to stronger station

## Technical Details

- **Reference**: https://github.com/ChrisDev8/python-radio/blob/main/decoder.py
- **Changed file**: `app_core/radio/demodulation.py` method `_decode_rbds_groups()`
- **Key change**: Lines 897-909, 1077-1084
- **Demo script**: `python3 tools/demo_rbds_fix.py`

## Version History

- **2.43.0**: PySDR-style RBDS with M&M + Costas loop
- **2.43.1**: Fixed M&M timing return bug
- **2.43.2**: Fixed presync false positives
- **2.43.3**: Fixed undefined variable in M&M
- **2.43.4**: Fixed buffer management (THIS FIX) ← **Should work now!**

---

**Expected outcome**: RBDS should now successfully synchronize and decode station metadata! 🎉
