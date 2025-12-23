# RBDS Diagnostic Tool

**ONE tool to detect all RBDS issues. Should have existed from day one.**

## What This Is

After 35+ pull requests trying to fix RBDS synchronization, this tool automatically detects all known implementation issues and analyzes runtime behavior.

## Usage

### Check Code Implementation
```bash
python3 tools/rbds_auto_diagnostic.py
```

### Analyze Log File
```bash
python3 tools/rbds_auto_diagnostic.py --logs /var/log/rbds.log
```

### Analyze Live Logs
```bash
journalctl -u eas-station-audio.service -n 1000 | python3 tools/rbds_auto_diagnostic.py --logs -
```

### Run All Checks
```bash
python3 tools/rbds_auto_diagnostic.py --all
```

## What It Checks

### Code Implementation
1. **DSP Processing Order** - M&M timing must come before Costas phase correction
2. **Differential Decoding** - Must use modulo arithmetic, not != operator
3. **Bit Buffer Management** - Must use index-based processing, not pop(0)
4. **Register Reset** - Must reset after processing each block in synced mode
5. **Polarity Handling** - Must check both normal and inverted polarity
6. **CRC Logic** - Must match python-radio reference implementation
7. **Presync Spacing** - Must retain blocks on spacing mismatch
8. **Anti-Patterns** - Various bugs from previous failed fixes

### Runtime Log Analysis
- Synchronization success rate
- Group decoding success
- CRC failure patterns
- Sync loss frequency
- Presync behavior

## Expected Output

### Healthy Implementation
```
Total Findings: 9
  🔴 CRITICAL: 0
  🟠 ERROR: 0
  🟡 WARNING: 1
  🟢 INFO: 0
  ✅ PASS: 8

✅ All checks passed - RBDS implementation looks good
```

### Problem Detection
```
Total Findings: 12
  🔴 CRITICAL: 2
  🟠 ERROR: 1
  🟡 WARNING: 3
  
❌ CRITICAL issues found - RBDS will NOT work
```

## Why This Matters

Without this tool, we had 35+ PRs that:
- Fixed symptoms without identifying root causes
- Created more documentation than actual fixes
- Cluttered the repository root with "final fix" promises
- Failed to catch regressions

**This tool catches issues BEFORE they hit production.**

## Integration

Run before merging any RBDS-related changes:
```bash
python3 tools/rbds_auto_diagnostic.py
```

Exit codes:
- 0 = All checks passed or warnings only
- 1 = Errors found
- 2 = Critical issues found

## Related Files

- `/docs/archive/rbds-fixes/` - Documentation from 35+ failed PRs (historical reference)
- `/app_core/radio/demodulation.py` - RBDS implementation
- `/docs/development/AGENTS.md` - Development guidelines
