# RBDS Fix Deployment Guide - v2.43.9

## Quick Summary

**Issue**: RBDS achieves sync but immediately loses it (50/50 bad blocks)  
**Fix**: Removed register reset on sync achievement  
**Version**: 2.43.9  
**Risk**: Very Low (1 line removed, well-tested logic)  
**Impact**: Critical - Enables RBDS functionality

## What Was Fixed

The RBDS decoder was resetting its shift register when achieving synchronization, which destroyed the bit alignment that had just been established. This caused all subsequent blocks to fail CRC checks, resulting in immediate sync loss.

## The Fix

**File**: `app_core/radio/demodulation.py`  
**Change**: Removed `self._rbds_reg = 0` from sync transition  
**Why**: Register must maintain bit alignment; natural shifting handles block transitions

## Deployment Steps

### 1. Update the Code

```bash
cd /opt/eas-station
git checkout main
git pull origin main
git merge copilot/fix-rbds-sync-issue
```

### 2. Restart the Service

```bash
sudo systemctl restart eas-station-audio.service
```

### 3. Monitor the Logs

```bash
journalctl -u eas-station-audio.service -f | grep RBDS
```

## Expected Log Output

### ✅ Success Indicators

Look for these patterns in the logs:

```
[INFO] RBDS SYNCHRONIZED at bit XXXXX
[INFO] RBDS sync OK: 2/50 bad blocks
[INFO] RBDS group: A=XXXX B=XXXX C=XXXX D=XXXX
[INFO] RBDS decoded: PS='STATION' PI=XXXX
```

### ❌ Problems (should NOT see these)

```
[WARNING] RBDS SYNC LOST: 50/50 bad blocks
```

If you see this immediately after "SYNCHRONIZED", the fix didn't apply correctly.

## Verification Checklist

- [ ] Code updated to v2.43.9
- [ ] Service restarted successfully
- [ ] Logs show "RBDS SYNCHRONIZED" messages
- [ ] Logs show "RBDS sync OK" with low error counts (< 5/50)
- [ ] Logs show "RBDS group" decoded messages
- [ ] Logs show "RBDS decoded" with station metadata
- [ ] NO "SYNC LOST: 50/50 bad blocks" immediately after sync

## Troubleshooting

### If RBDS Still Not Working

1. **Check if RBDS is enabled in receiver settings**:
   ```bash
   # Check the database settings
   sqlite3 /opt/eas-station/eas_station.db "SELECT * FROM radio_receivers;"
   ```
   Look for `rbds_enabled` column - should be 1 (true)

2. **Check if the station broadcasts RBDS**:
   - Not all FM stations broadcast RBDS/RDS
   - Commercial stations are more likely to have RBDS
   - Try tuning to different stations

3. **Check signal quality**:
   ```bash
   journalctl -u eas-station-audio.service -f | grep -E "(signal|SNR|strength)"
   ```
   - RBDS requires clean signal (SNR > 20 dB typically)
   - Adjust antenna or frequency if signal is weak

### If Sync is Still Lost

If you still see "SYNC LOST" messages:

1. Check the version: `cat /opt/eas-station/VERSION` should show 2.43.9
2. Verify the fix was applied: `grep -A 5 "Correct spacing - SYNCED" /opt/eas-station/app_core/radio/demodulation.py`
   - Should NOT contain `self._rbds_reg = 0`
3. Check for other errors in logs: `journalctl -u eas-station-audio.service -n 100 | grep -E "(ERROR|CRITICAL)"`

## Rollback (If Needed)

If issues arise, rollback to previous version:

```bash
cd /opt/eas-station
git checkout main
git revert HEAD
sudo systemctl restart eas-station-audio.service
```

## Technical Details

For complete technical explanation, see:
- `RBDS_SYNC_FIX_v2.43.9.md` - Detailed root cause analysis
- `docs/reference/CHANGELOG.md` - Change history

## Support

If RBDS still doesn't work after this fix:
1. Collect logs: `journalctl -u eas-station-audio.service -n 500 > rbds-logs.txt`
2. Check signal quality at the receiver
3. Verify station actually broadcasts RBDS
4. Review the technical documentation in `RBDS_SYNC_FIX_v2.43.9.md`

## Success Criteria

RBDS is working correctly when:
- ✅ Sync is achieved and maintained for > 60 seconds
- ✅ Error rate is low (< 10% bad blocks)
- ✅ Station name (PS) is decoded and displayed
- ✅ PI code is decoded and displayed
- ✅ No frequent sync loss/resync cycles

---

**Version**: 2.43.9  
**Date**: 2024-12-23  
**Risk Level**: Very Low  
**Testing Required**: Monitor logs for 5-10 minutes after deployment
