# RBDS Diagnostic Tools

## collect-rbds-diagnostics.sh

Comprehensive diagnostic log collection script for troubleshooting RBDS decoding issues.

### Quick Start

```bash
# Run the collection script (requires sudo for journalctl)
cd /opt/eas-station
sudo ./tools/collect-rbds-diagnostics.sh
```

The script will:
1. Collect 60-90 seconds of detailed RBDS logs
2. Capture system configuration (Redis, audio, radio settings)
3. Check signal quality metrics
4. Create an analysis guide
5. Package everything into a tar.gz archive

### Output

All diagnostics are saved to `/tmp/rbds-diagnostics-YYYYMMDD-HHMMSS/` and archived as `/tmp/rbds-diagnostics-YYYYMMDD-HHMMSS.tar.gz`

### Files Collected

- **rbds-basic.log** - Basic RBDS activity (60 sec)
- **rbds-detailed.log** - M&M timing, Costas, bit stats (90 sec)  
- **rbds-sync-events.log** - Presync and sync attempts (60 sec)
- **rbds-full-context.log** - Complete logs with context (30 sec)
- **redis-config.log** - RBDS Redis configuration
- **audio-config.log** - Audio pipeline settings
- **radio-config.log** - Radio receiver settings
- **signal-strength.log** - Signal quality metrics
- **service-status.log** - Service health
- **system-info.txt** - System specifications
- **ANALYSIS-GUIDE.md** - How to analyze the logs

### What to Look For

The script creates an **ANALYSIS-GUIDE.md** file that explains:
- How to interpret syndrome values
- M&M timing stability indicators
- Bit distribution analysis
- Costas loop tracking behavior
- Common failure patterns and their signatures

### Quick Analysis Commands

After running the script:

```bash
# Replace TIMESTAMP with actual timestamp from script output
cd /tmp/rbds-diagnostics-TIMESTAMP

# View syndrome patterns (should match targets [383, 14, 303, 663, 748])
grep 'syndrome=' rbds-detailed.log | head -20

# Check M&M timing stability
grep 'RBDS M&M:' rbds-detailed.log | head -10

# Verify bit distribution (should be ~50% ones)
grep 'RBDS bits:' rbds-detailed.log | head -10

# Check if sync was ever achieved
grep 'SYNCHRONIZED' rbds-sync-events.log

# View signal strength (should be strong at 8 miles)
cat signal-strength.log
```

### Sharing Results

To share diagnostics:

```bash
# Archive is automatically created
ls -lh /tmp/rbds-diagnostics-*.tar.gz

# Copy to accessible location
cp /tmp/rbds-diagnostics-*.tar.gz ~/
```

Then share the `.tar.gz` file or specific log excerpts as requested.

### Troubleshooting the Script

If the script fails:

```bash
# Check if services are running
systemctl status eas-station-audio.service

# Check if redis is accessible
redis-cli ping

# Verify journalctl access (requires sudo)
sudo journalctl -u eas-station-audio.service -n 10
```

### Manual Log Collection

If the script doesn't work, collect manually:

```bash
# Basic RBDS logs (60 seconds)
journalctl -u eas-station-audio.service -f | grep RBDS > /tmp/rbds-manual.log &
sleep 60
killall journalctl

# View the log
cat /tmp/rbds-manual.log
```
