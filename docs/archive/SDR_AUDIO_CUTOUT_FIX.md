# SDR Audio Cutout Fix - Technical Documentation

## Problem Statement

SDR audio playback was cutting out after 5-6 seconds, and RBDS (Radio Broadcast Data System) metadata was not displaying properly in the web UI.

## Root Cause - Array Allocation Before Throttling Check

The bug was in `app_core/radio/demodulation.py` lines 467-468. A large `np.arange()` array was being created on EVERY chunk, even though RBDS processing was throttled to only run every 10th chunk:

```python
# BEFORE FIX - BUG
if self._rbds_enabled:
    sample_indices = np.arange(len(multiplex), dtype=np.float64) + self._sample_index  # EVERY chunk!
    self._sample_index += len(multiplex)
    
    if self._rbds_process_counter >= self._rbds_process_interval:  # Only 1/10 times
        # Process RBDS using sample_indices...
```

For 2.5MHz SDR with 25k sample chunks, this created 200KB arrays 10 times per second = **20 MB/sec wasted allocations**.

## The Fix

Move array creation INSIDE the throttling condition:

```python
# AFTER FIX - CORRECTED
if self._rbds_enabled:
    self._rbds_process_counter += 1
    
    if self._rbds_process_counter >= self._rbds_process_interval:  # Only 1/10 times
        # Create array ONLY when processing
        sample_indices = np.arange(len(multiplex), dtype=np.float64) + self._sample_index
        self._sample_index += len(multiplex)
        # Process RBDS...
    else:
        # Skip processing but maintain timing
        self._sample_index += len(multiplex)
        rbds_data = self._last_rbds_data
```

## Performance Impact

- **Before**: 10 allocations/sec → GC pauses every 5-6 seconds → audio cutouts
- **After**: 1 allocation/sec → No GC pauses → smooth audio + working RBDS

## Files Changed

- `app_core/radio/demodulation.py` - Lines 467-506 (main fix)
- `VERSION` - Updated to 2.42.4
- `docs/reference/CHANGELOG.md` - Documented fix
- `tests/test_rbds_demodulation.py` - Added verification test
- `scripts/verify_rbds_fix.py` - Performance verification script
