#!/bin/bash
# RBDS Diagnostic Log Collection Script
# Collects detailed logs to diagnose RBDS synchronization issues
# Created: 2024-12-23

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Output directory
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTPUT_DIR="/tmp/rbds-diagnostics-${TIMESTAMP}"
mkdir -p "${OUTPUT_DIR}"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}RBDS Diagnostic Log Collection${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Output directory: ${OUTPUT_DIR}"
echo ""

# Function to run a command and save output
collect_log() {
    local name=$1
    local description=$2
    local command=$3
    local duration=${4:-30}
    
    echo -e "${YELLOW}Collecting: ${description}${NC}"
    echo "  Command: ${command}"
    echo "  Duration: ${duration} seconds"
    
    local output_file="${OUTPUT_DIR}/${name}.log"
    
    if [[ "$command" == journalctl* ]]; then
        # For journalctl, capture in background and kill after duration
        eval "${command}" > "${output_file}" 2>&1 &
        local pid=$!
        sleep "${duration}"
        kill "${pid}" 2>/dev/null || true
        wait "${pid}" 2>/dev/null || true
    else
        # For other commands, run directly
        eval "${command}" > "${output_file}" 2>&1 || echo "Command failed (this may be OK)" >> "${output_file}"
    fi
    
    local line_count=$(wc -l < "${output_file}" 2>/dev/null || echo "0")
    echo -e "  ${GREEN}✓${NC} Captured ${line_count} lines to ${name}.log"
    echo ""
}

# ============================================================================
# 1. Basic RBDS Activity Logs
# ============================================================================
echo -e "${BLUE}=== 1. Basic RBDS Activity ===${NC}"
collect_log "rbds-basic" \
    "Basic RBDS log patterns" \
    "journalctl -u eas-station-audio.service -f | grep RBDS" \
    60

# ============================================================================
# 2. Detailed Signal Processing Logs
# ============================================================================
echo -e "${BLUE}=== 2. Detailed Signal Processing ===${NC}"
collect_log "rbds-detailed" \
    "M&M timing, Costas loop, bit statistics" \
    "journalctl -u eas-station-audio.service -f | grep -E 'RBDS|M&M|Costas|bits:'" \
    90

# ============================================================================
# 3. Presync and Sync Activity
# ============================================================================
echo -e "${BLUE}=== 3. Presync and Sync Events ===${NC}"
collect_log "rbds-sync-events" \
    "Presync, sync, and group decode events" \
    "journalctl -u eas-station-audio.service -f | grep -E 'presync|SYNCHRONIZED|group:'" \
    60

# ============================================================================
# 4. Full Context Logs (Last 500 lines + 30 seconds new)
# ============================================================================
echo -e "${BLUE}=== 4. Full Context Logs ===${NC}"
collect_log "rbds-full-context" \
    "Complete logs with full context" \
    "journalctl -u eas-station-audio.service -f -n 500" \
    30

# ============================================================================
# 5. System Configuration
# ============================================================================
echo -e "${BLUE}=== 5. System Configuration ===${NC}"

collect_log "redis-config" \
    "Redis configuration values" \
    "redis-cli KEYS '*rbds*' | xargs -I {} sh -c 'echo \"{}:\" && redis-cli GET {}'" \
    0

collect_log "audio-config" \
    "Audio service configuration" \
    "redis-cli KEYS '*audio*' | head -20 | xargs -I {} sh -c 'echo \"{}:\" && redis-cli GET {}'" \
    0

collect_log "radio-config" \
    "Radio receiver configuration" \
    "redis-cli KEYS '*radio*' | head -20 | xargs -I {} sh -c 'echo \"{}:\" && redis-cli GET {}'" \
    0

# ============================================================================
# 6. Signal Quality Metrics
# ============================================================================
echo -e "${BLUE}=== 6. Signal Quality Metrics ===${NC}"

collect_log "signal-strength" \
    "Current signal strength and SNR" \
    "echo 'Signal Strength:' && redis-cli GET radio:signal_strength && echo 'SNR:' && redis-cli GET radio:snr && echo 'RSSI:' && redis-cli GET radio:rssi" \
    0

# ============================================================================
# 7. Service Status
# ============================================================================
echo -e "${BLUE}=== 7. Service Status ===${NC}"

collect_log "service-status" \
    "Audio service status" \
    "systemctl status eas-station-audio.service" \
    0

collect_log "service-journal-errors" \
    "Recent service errors" \
    "journalctl -u eas-station-audio.service --since '5 minutes ago' | grep -i error" \
    0

# ============================================================================
# 8. System Information
# ============================================================================
echo -e "${BLUE}=== 8. System Information ===${NC}"

cat > "${OUTPUT_DIR}/system-info.txt" << EOF
System Information
==================
Date: $(date)
Hostname: $(hostname)
Uptime: $(uptime)
CPU: $(lscpu | grep "Model name" | cut -d: -f2 | xargs)
Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')
Disk: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 " used)"}')
Kernel: $(uname -r)
EAS-Station Version: $(cat /opt/eas-station/VERSION 2>/dev/null || echo "Unknown")
EOF

echo -e "  ${GREEN}✓${NC} System information saved to system-info.txt"
echo ""

# ============================================================================
# 9. Create Summary Report
# ============================================================================
echo -e "${BLUE}=== 9. Creating Summary Report ===${NC}"

cat > "${OUTPUT_DIR}/ANALYSIS-GUIDE.md" << 'EOF'
# RBDS Diagnostic Log Analysis Guide

## Files in This Directory

### Basic Logs
- **rbds-basic.log** - Core RBDS activity (60 seconds)
- **rbds-detailed.log** - M&M timing, Costas, bit stats (90 seconds)
- **rbds-sync-events.log** - Presync and sync attempts (60 seconds)
- **rbds-full-context.log** - Complete logs with context (30 seconds)

### Configuration
- **redis-config.log** - RBDS-related Redis keys
- **audio-config.log** - Audio pipeline configuration
- **radio-config.log** - Radio receiver settings
- **signal-strength.log** - Current signal quality metrics

### Service Status
- **service-status.log** - Service health and status
- **service-journal-errors.log** - Recent errors
- **system-info.txt** - System specifications

## What to Look For

### 1. Syndrome Analysis (rbds-detailed.log)
Search for: `RBDS sync search: bit_counter=`

**Questions:**
- Are syndrome values consistently wrong by similar amounts?
- Do you see syndrome values like 775, 16, 906, 524, etc.?
- Are they always 4-7 bits different from targets [383, 14, 303, 663, 748]?

### 2. M&M Timing (rbds-detailed.log)
Search for: `RBDS M&M:`

**Questions:**
- Is the symbol count consistent? (e.g., "374 samples -> 24 symbols")
- Does it vary by more than ±2 symbols between calls?
- Are there timing slips or jumps?

### 3. Bit Statistics (rbds-detailed.log)
Search for: `RBDS bits:`

**Questions:**
- What percentage of bits are ones? (Should be close to 50%)
- Is it consistently around 33% or 66%? (Indicates possible inversion)
- Does the percentage vary wildly? (Indicates noise)

### 4. Costas Loop (rbds-detailed.log)
Search for: `RBDS Costas:`

**Questions:**
- Is frequency offset stable? (Should be < 5 Hz)
- Does frequency drift over time?
- Does phase wrap around frequently? (Could indicate tracking issues)

### 5. Presync Activity (rbds-sync-events.log)
Search for: `RBDS presync:`

**Questions:**
- Do you see "first block type X" messages?
- Are they for exact matches or fuzzy matches?
- If fuzzy, how many bit errors? (1-2 is OK, >2 is concerning)
- Do you see spacing mismatches?

### 6. Sync Achievement (rbds-sync-events.log)
Search for: `RBDS SYNCHRONIZED`

**Questions:**
- Does sync ever happen?
- If yes, does it stay synced or lose sync quickly?
- If no, why? (Check presync spacing mismatches)

### 7. Signal Quality (signal-strength.log)
**Questions:**
- What is the signal strength? (Should be > 60 dBμV at 8 miles)
- What is the SNR? (Should be > 40 dB for FM)
- Are values stable or fluctuating?

## Analysis Workflow

1. **Check if RBDS is enabled**
   - Look in redis-config.log for `rbds:enabled` = true
   
2. **Verify signal quality**
   - Check signal-strength.log for strong signal (8 miles = excellent)
   
3. **Examine syndrome patterns**
   - Open rbds-detailed.log
   - Find syndrome values
   - Calculate how many bits differ from targets
   
4. **Check M&M timing stability**
   - Look for "RBDS M&M:" lines
   - Verify symbol counts are consistent
   
5. **Analyze bit distribution**
   - Find "RBDS bits:" lines
   - Check if % ones is around 50%
   
6. **Review presync attempts**
   - Open rbds-sync-events.log
   - Count how many presync attempts
   - Check if spacing validation ever succeeds

## Common Issues and Signatures

### Issue: Perfect signal but no syndrome matches
**Signature:**
- Strong signal (> 60 dBμV)
- Syndromes consistently 4-7 bits off
- M&M producing symbols
- Costas tracking

**Likely Cause:** Bit corruption in M&M or differential decoding

### Issue: Presync finds blocks but spacing always wrong
**Signature:**
- See "presync: first block type X"
- See "spacing mismatch (expected 26, got XXX)"
- Never see "SYNCHRONIZED"

**Likely Cause:** False positive syndrome matches (noise) or timing drift

### Issue: Sync achieved but immediately lost
**Signature:**
- See "SYNCHRONIZED at bit X"
- See "SYNC LOST" shortly after
- See many "block FAILED CRC"

**Likely Cause:** Weak signal or phase slips in Costas loop

### Issue: No activity at all
**Signature:**
- No "RBDS" log lines
- No M&M, Costas, or bits logs

**Likely Cause:** RBDS not enabled, or station doesn't broadcast RBDS

## Next Steps

Based on what you find, provide:

1. **Syndrome pattern** - List 10 consecutive syndrome values from logs
2. **M&M behavior** - Show 5 consecutive M&M timing lines
3. **Bit statistics** - Report % ones over 10 measurements
4. **Presync results** - Did it find any blocks? What spacing errors?
5. **Signal strength** - What are the actual dBμV and SNR values?

With this information, the exact failure point can be identified.
EOF

echo -e "  ${GREEN}✓${NC} Analysis guide created: ANALYSIS-GUIDE.md"
echo ""

# ============================================================================
# 10. Create Archive
# ============================================================================
echo -e "${BLUE}=== 10. Creating Archive ===${NC}"

cd /tmp
ARCHIVE_NAME="rbds-diagnostics-${TIMESTAMP}.tar.gz"
tar -czf "${ARCHIVE_NAME}" "rbds-diagnostics-${TIMESTAMP}/"

echo -e "  ${GREEN}✓${NC} Archive created: /tmp/${ARCHIVE_NAME}"
echo ""

# ============================================================================
# Summary
# ============================================================================
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Collection Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Output directory: ${OUTPUT_DIR}"
echo "Archive: /tmp/${ARCHIVE_NAME}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Review the logs in: ${OUTPUT_DIR}"
echo "2. Read: ${OUTPUT_DIR}/ANALYSIS-GUIDE.md"
echo "3. Share the archive: /tmp/${ARCHIVE_NAME}"
echo ""
echo -e "${YELLOW}Quick Analysis:${NC}"
echo "  # View syndrome patterns"
echo "  grep 'syndrome=' ${OUTPUT_DIR}/rbds-detailed.log | head -20"
echo ""
echo "  # View M&M timing"
echo "  grep 'RBDS M&M:' ${OUTPUT_DIR}/rbds-detailed.log | head -10"
echo ""
echo "  # View bit statistics"
echo "  grep 'RBDS bits:' ${OUTPUT_DIR}/rbds-detailed.log | head -10"
echo ""
echo "  # Check for sync events"
echo "  grep 'SYNCHRONIZED' ${OUTPUT_DIR}/rbds-sync-events.log"
echo ""
echo -e "${BLUE}================================================${NC}"
