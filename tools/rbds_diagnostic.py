#!/usr/bin/env python3
"""
RBDS Diagnostic Script - Quick Check for Production Issues

This script provides a quick diagnostic view of RBDS behavior from logs.
Run this on the production system to analyze RBDS synchronization attempts.

Usage:
    # Check recent logs
    journalctl -u eas-station-audio.service -n 1000 | python3 rbds_diagnostic.py
    
    # Follow live logs with analysis
    journalctl -u eas-station-audio.service -f | python3 rbds_diagnostic.py --live
"""

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime


def parse_rbds_log_line(line: str) -> dict:
    """Parse RBDS-related log line."""
    result = {
        'timestamp': None,
        'level': None,
        'type': None,
        'message': line,
        'details': {}
    }
    
    # Extract timestamp
    ts_match = re.match(r'(\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})', line)
    if ts_match:
        result['timestamp'] = ts_match.group(1)
    
    # Extract log level
    if '[DEBUG]' in line:
        result['level'] = 'DEBUG'
    elif '[INFO]' in line:
        result['level'] = 'INFO'
    elif '[WARNING]' in line:
        result['level'] = 'WARNING'
    elif '[ERROR]' in line:
        result['level'] = 'ERROR'
    
    # Identify RBDS message type and extract details
    if 'RBDS sync search' in line:
        result['type'] = 'sync_search'
        # Extract syndrome values
        syndrome_match = re.search(r'syndrome=(\d+)/(\d+)', line)
        if syndrome_match:
            result['details']['syndrome_normal'] = int(syndrome_match.group(1))
            result['details']['syndrome_inverted'] = int(syndrome_match.group(2))
        # Extract bit counter
        bit_match = re.search(r'bit_counter=(\d+)', line)
        if bit_match:
            result['details']['bit_counter'] = int(bit_match.group(1))
    
    elif 'RBDS presync' in line:
        result['type'] = 'presync'
        if 'first block' in line:
            result['details']['event'] = 'first_block'
            block_match = re.search(r'block type (\d+)', line)
            if block_match:
                result['details']['block_type'] = int(block_match.group(1))
        elif 'spacing mismatch' in line:
            result['details']['event'] = 'spacing_mismatch'
            expected_match = re.search(r'expected (\d+)', line)
            got_match = re.search(r'got (\d+)', line)
            if expected_match and got_match:
                result['details']['expected'] = int(expected_match.group(1))
                result['details']['got'] = int(got_match.group(1))
    
    elif 'RBDS SYNCHRONIZED' in line:
        result['type'] = 'synchronized'
        bit_match = re.search(r'bit (\d+)', line)
        if bit_match:
            result['details']['bit_counter'] = int(bit_match.group(1))
    
    elif 'RBDS group:' in line:
        result['type'] = 'group_decoded'
        # Extract block values
        blocks_match = re.search(r'A=([0-9A-F]+)\s+B=([0-9A-F]+)\s+C=([0-9A-F]+)\s+D=([0-9A-F]+)', line)
        if blocks_match:
            result['details']['blocks'] = [blocks_match.group(i) for i in range(1, 5)]
    
    elif 'RBDS decoded:' in line:
        result['type'] = 'decoded_data'
        ps_match = re.search(r"PS='([^']*)'", line)
        pi_match = re.search(r'PI=([0-9A-F]+)', line)
        if ps_match:
            result['details']['ps_name'] = ps_match.group(1)
        if pi_match:
            result['details']['pi_code'] = pi_match.group(1)
    
    elif 'RBDS worker status' in line:
        result['type'] = 'worker_status'
        samples_match = re.search(r'(\d+) samples processed', line)
        groups_match = re.search(r'(\d+) groups decoded', line)
        buffer_match = re.search(r'buffer=(\d+)', line)
        if samples_match:
            result['details']['samples'] = int(samples_match.group(1))
        if groups_match:
            result['details']['groups'] = int(groups_match.group(1))
        if buffer_match:
            result['details']['buffer_size'] = int(buffer_match.group(1))
    
    elif 'RBDS Costas:' in line:
        result['type'] = 'costas_status'
        freq_match = re.search(r'freq=([\-0-9.]+)', line)
        phase_match = re.search(r'phase=([\-0-9.]+)', line)
        if freq_match:
            result['details']['freq'] = float(freq_match.group(1))
        if phase_match:
            result['details']['phase'] = float(phase_match.group(1))
    
    elif 'RBDS M&M:' in line:
        result['type'] = 'mm_status'
        match = re.search(r'(\d+) samples -> (\d+) symbols', line)
        if match:
            result['details']['samples_in'] = int(match.group(1))
            result['details']['symbols_out'] = int(match.group(2))
    
    elif 'RBDS block PASSED CRC' in line:
        result['type'] = 'crc_pass'
        block_match = re.search(r'block_num=(\d+)', line)
        dataword_match = re.search(r'dataword=0x([0-9A-F]+)', line)
        if block_match:
            result['details']['block_num'] = int(block_match.group(1))
        if dataword_match:
            result['details']['dataword'] = dataword_match.group(1)
    
    elif 'RBDS block FAILED CRC' in line:
        result['type'] = 'crc_fail'
        block_match = re.search(r'block_num=(\d+)', line)
        if block_match:
            result['details']['block_num'] = int(block_match.group(1))
    
    return result


def analyze_logs(lines: list, verbose: bool = False):
    """Analyze RBDS logs and print summary."""
    # Parse all lines
    events = []
    for line in lines:
        if 'RBDS' in line:
            parsed = parse_rbds_log_line(line)
            if parsed['type']:
                events.append(parsed)
    
    if not events:
        print("❌ No RBDS log messages found")
        return
    
    # Count events by type
    event_counts = defaultdict(int)
    for event in events:
        event_counts[event['type']] += 1
    
    # Analyze results
    print("=" * 70)
    print("RBDS LOG ANALYSIS")
    print("=" * 70)
    print(f"Total RBDS events: {len(events)}")
    print()
    
    # Event breakdown
    print("Event Breakdown:")
    for event_type, count in sorted(event_counts.items()):
        print(f"  {event_type}: {count}")
    print()
    
    # Check for synchronization
    sync_count = event_counts.get('synchronized', 0)
    groups_count = event_counts.get('group_decoded', 0)
    decoded_count = event_counts.get('decoded_data', 0)
    
    print("=" * 70)
    print("DIAGNOSIS")
    print("=" * 70)
    
    if sync_count > 0 and groups_count > 0:
        print("✅ STATUS: RBDS IS WORKING!")
        print(f"   - Achieved sync {sync_count} time(s)")
        print(f"   - Decoded {groups_count} group(s)")
        print(f"   - Extracted data {decoded_count} time(s)")
        
        # Show latest decoded data
        decoded_events = [e for e in events if e['type'] == 'decoded_data']
        if decoded_events:
            latest = decoded_events[-1]
            if 'ps_name' in latest['details']:
                print(f"\n   Latest PS Name: '{latest['details']['ps_name']}'")
            if 'pi_code' in latest['details']:
                print(f"   Latest PI Code: {latest['details']['pi_code']}")
    
    elif sync_count > 0:
        print("⚠️  STATUS: SYNC ACHIEVED BUT NO GROUPS DECODED")
        print("   Possible issues:")
        print("   - CRC failures after sync")
        print("   - Signal quality issues")
        print("   - Check for 'RBDS block FAILED CRC' messages")
        
        crc_fails = event_counts.get('crc_fail', 0)
        crc_pass = event_counts.get('crc_pass', 0)
        if crc_fails > 0 or crc_pass > 0:
            print(f"\n   CRC Statistics:")
            print(f"   - Passed: {crc_pass}")
            print(f"   - Failed: {crc_fails}")
            if crc_pass + crc_fails > 0:
                success_rate = 100.0 * crc_pass / (crc_pass + crc_fails)
                print(f"   - Success Rate: {success_rate:.1f}%")
    
    elif event_counts.get('sync_search', 0) > 0:
        print("❌ STATUS: STUCK IN SYNC SEARCH (NOT SYNCING)")
        print("   This indicates the v2.44.11 fix may not be applied correctly")
        print()
        print("   Verify:")
        print("   1. Version is 2.44.11:")
        print("      cat /opt/eas-station/VERSION")
        print()
        print("   2. Run verification test:")
        print("      cd /opt/eas-station")
        print("      python3 test_rbds_standalone.py")
        print()
        print("   3. Check syndrome values:")
        
        # Analyze syndrome patterns
        sync_events = [e for e in events if e['type'] == 'sync_search']
        if sync_events:
            syndromes = []
            for e in sync_events[-10:]:  # Last 10
                if 'syndrome_normal' in e['details']:
                    syndromes.append(e['details']['syndrome_normal'])
            
            if syndromes:
                print(f"      Recent syndromes: {syndromes}")
                print(f"      Target syndromes: [383, 14, 303, 663, 748]")
                
                # Check if any match
                targets = {383, 14, 303, 663, 748}
                matches = [s for s in syndromes if s in targets]
                if matches:
                    print(f"      ⚠️ Found target syndromes but not syncing: {matches}")
                    print(f"         This suggests presync logic issue")
                else:
                    print(f"      ❌ No target syndromes found - bit stream issue")
    
    else:
        print("⚠️  STATUS: INSUFFICIENT DATA")
        print("   Not enough RBDS events to diagnose")
        print("   Try capturing more logs")
    
    print("=" * 70)
    
    if verbose:
        print()
        print("DETAILED EVENTS:")
        print("=" * 70)
        for i, event in enumerate(events[-20:]):  # Last 20 events
            print(f"{i+1}. [{event['level']}] {event['type']}")
            if event['details']:
                for key, value in event['details'].items():
                    print(f"   {key}: {value}")


def main():
    parser = argparse.ArgumentParser(
        description="RBDS Diagnostic Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Analyze last 1000 log lines
    journalctl -u eas-station-audio.service -n 1000 | python3 rbds_diagnostic.py
    
    # Detailed analysis
    journalctl -u eas-station-audio.service -n 1000 | python3 rbds_diagnostic.py -v
    
    # Live monitoring (requires manual Ctrl+C after collecting data)
    timeout 30 journalctl -u eas-station-audio.service -f | python3 rbds_diagnostic.py
        """
    )
    
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed event information')
    
    args = parser.parse_args()
    
    # Read from stdin
    lines = []
    try:
        for line in sys.stdin:
            lines.append(line.strip())
    except KeyboardInterrupt:
        pass
    
    if not lines:
        print("Error: No input provided", file=sys.stderr)
        print("Usage: journalctl ... | python3 rbds_diagnostic.py", file=sys.stderr)
        sys.exit(1)
    
    analyze_logs(lines, args.verbose)


if __name__ == "__main__":
    main()
