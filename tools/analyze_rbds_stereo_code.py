#!/usr/bin/env python3
"""
EAS Station - Emergency Alert System
Copyright (c) 2025-2026 Timothy Kramer (KR8MER)

RBDS and Stereo Code Path Analyzer

Static code analysis to verify RBDS and stereo paths are correctly implemented.
"""

import sys
import re
import pathlib
from typing import Dict, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]


def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}\n")


def print_subsection(title: str):
    """Print formatted subsection header."""
    print(f"\n{'-'*80}")
    print(f" {title}")
    print(f"{'-'*80}\n")


def analyze_demodulation_py():
    """Analyze the demodulation.py file for RBDS and stereo implementation."""
    print_section("Analyzing app_core/radio/demodulation.py")
    
    file_path = ROOT / "app_core" / "radio" / "demodulation.py"
    with open(file_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Check for key components
    checks = {
        'RBDSData class': r'class RBDSData',
        'DemodulatorStatus class': r'class DemodulatorStatus',
        'FMDemodulator class': r'class FMDemodulator',
        'RBDSDecoder class': r'class RBDSDecoder',
        'stereo_enabled config': r'stereo_enabled.*bool',
        'enable_rbds config': r'enable_rbds.*bool',
        '_extract_rbds method': r'def _extract_rbds',
        '_decode_stereo method': r'def _decode_stereo',
        '_rbds_symbol_to_bit method': r'def _rbds_symbol_to_bit',
        'RBDS bandpass filter': r'_rbds_bandpass.*=',
        'RBDS lowpass filter': r'_rbds_lowpass.*=',
        'Pilot filter': r'_pilot_filter.*=',
        'L+R filter': r'_lpr_filter.*=',
        'L-R filter': r'_dsb_filter.*=',
    }
    
    print("Component Verification:")
    for name, pattern in checks.items():
        if re.search(pattern, content):
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name} NOT FOUND")
    
    # Analyze filter design
    print_subsection("Filter Design Analysis")
    
    # Find where filters are designed
    filter_design_patterns = {
        'Audio filters use config.sample_rate': r'_design_fir_[^(]*\([^,]*,\s*config\.sample_rate',
        'RBDS filters use config.sample_rate': r'_rbds.*=.*_design_fir.*config\.sample_rate',
        'Pilot filter uses config.sample_rate': r'_pilot_filter.*=.*_design_fir.*config\.sample_rate',
    }
    
    for name, pattern in filter_design_patterns.items():
        if re.search(pattern, content):
            print(f"  ✅ {name}")
        else:
            print(f"  ⚠️  {name} - Pattern not matched (may use different approach)")
    
    # Check for CRITICAL FIX comments
    print_subsection("Code Comments and Critical Fixes")
    
    critical_fixes = []
    for i, line in enumerate(lines, 1):
        if 'CRITICAL FIX' in line or 'CRITICAL:' in line:
            critical_fixes.append((i, line.strip()))
    
    if critical_fixes:
        print(f"Found {len(critical_fixes)} critical fix comments:")
        for line_num, comment in critical_fixes[:10]:  # Show first 10
            print(f"  Line {line_num}: {comment[:100]}")
    else:
        print("  No critical fix comments found")
    
    # Check sample rate usage
    print_subsection("Sample Rate Usage")
    
    sample_rate_patterns = {
        'config.sample_rate (original IQ rate)': r'config\.sample_rate',
        'self._intermediate_rate (decimated rate)': r'self\._intermediate_rate',
        'audio_sample_rate (output rate)': r'audio_sample_rate',
    }
    
    for name, pattern in sample_rate_patterns.items():
        matches = len(re.findall(pattern, content))
        print(f"  {name}: {matches} occurrences")
    
    # Check key methods exist and what they do
    print_subsection("Key Method Analysis")
    
    methods_to_check = [
        ('_extract_rbds', 'Extracts RBDS from multiplex'),
        ('_decode_stereo', 'Decodes stereo from multiplex'),
        ('_rbds_symbol_to_bit', 'Differential BPSK decoding'),
        ('_decode_rbds_groups', 'Decodes RBDS group data'),
        ('_rbds_crc', 'RBDS CRC validation'),
    ]
    
    for method_name, description in methods_to_check:
        pattern = rf'def {method_name}\('
        if re.search(pattern, content):
            # Find the method and check its docstring
            match = re.search(rf'def {method_name}\(.*?\):\s*"""(.*?)"""', content, re.DOTALL)
            if match:
                docstring = match.group(1).strip().split('\n')[0]
                print(f"  ✅ {method_name}: {docstring[:60]}")
            else:
                print(f"  ✅ {method_name}: Present (no docstring)")
        else:
            print(f"  ❌ {method_name}: NOT FOUND")


def analyze_redis_sdr_adapter():
    """Analyze redis_sdr_adapter.py for RBDS/stereo metadata propagation."""
    print_section("Analyzing app_core/audio/redis_sdr_adapter.py")
    
    file_path = ROOT / "app_core" / "audio" / "redis_sdr_adapter.py"
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for RBDS and stereo handling
    checks = {
        'stereo_enabled configuration': r'stereo_enabled.*=',
        'enable_rbds configuration': r'enable_rbds.*=',
        'DemodulatorConfig creation': r'DemodulatorConfig\(',
        'stereo_pilot_locked metadata': r'stereo_pilot_locked',
        'stereo_pilot_strength metadata': r'stereo_pilot_strength',
        'is_stereo metadata': r'is_stereo',
        'RBDS data extraction': r'rbds_data',
        'rbds_ps_name metadata': r'rbds_ps_name',
        'rbds_pi_code metadata': r'rbds_pi_code',
        'rbds_radio_text metadata': r'rbds_radio_text',
        'rbds_pty metadata': r'rbds_pty',
        'RBDS_PROGRAM_TYPES import': r'from.*RBDS_PROGRAM_TYPES',
    }
    
    print("Metadata Propagation Verification:")
    for name, pattern in checks.items():
        if re.search(pattern, content):
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name} NOT FOUND")
    
    # Check _update_metrics method
    print_subsection("Metrics Update Method")
    
    if '_update_metrics' in content:
        # Extract the method
        match = re.search(r'def _update_metrics\(.*?\):(.*?)(?=\n    def|\nclass|\Z)', content, re.DOTALL)
        if match:
            method_body = match.group(1)
            
            # Count metadata assignments
            rbds_assignments = len(re.findall(r"metadata\['rbds_", method_body))
            stereo_assignments = len(re.findall(r"metadata\['stereo_", method_body))
            
            print(f"  RBDS metadata assignments: {rbds_assignments}")
            print(f"  Stereo metadata assignments: {stereo_assignments}")
            
            if rbds_assignments > 0:
                print(f"  ✅ RBDS metadata is propagated to frontend")
            else:
                print(f"  ⚠️  RBDS metadata propagation may be incomplete")
            
            if stereo_assignments > 0:
                print(f"  ✅ Stereo metadata is propagated to frontend")
            else:
                print(f"  ⚠️  Stereo metadata propagation may be incomplete")
    
    # Check for demodulator status retrieval
    print_subsection("Demodulator Status Retrieval")
    
    status_checks = [
        'get_last_status() call',
        'status.rbds_data access',
        'status.stereo_pilot_locked access',
    ]
    
    for check in status_checks:
        if any(keyword in content for keyword in check.split()):
            print(f"  ✅ {check}")
        else:
            print(f"  ❌ {check} NOT FOUND")


def analyze_database_models():
    """Analyze database models for RBDS and stereo configuration."""
    print_section("Analyzing app_core/models.py")
    
    file_path = ROOT / "app_core" / "models.py"
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check RadioReceiver model
    print("RadioReceiver Model Configuration:")
    
    config_fields = {
        'stereo_enabled': r'stereo_enabled.*=.*db\.Column',
        'enable_rbds': r'enable_rbds.*=.*db\.Column',
        'deemphasis_us': r'deemphasis_us.*=.*db\.Column',
        'audio_sample_rate': r'audio_sample_rate.*=.*db\.Column',
    }
    
    for field, pattern in config_fields.items():
        if re.search(pattern, content):
            # Extract the field definition
            match = re.search(rf'{pattern}.*', content)
            if match:
                print(f"  ✅ {field}: {match.group(0)[:80]}")
        else:
            print(f"  ❌ {field} NOT FOUND")
    
    # Check to_config method
    print_subsection("Configuration Export (to_config method)")
    
    if 'def to_config(' in content:
        # Find the method
        match = re.search(r'def to_config\(.*?\):(.*?)(?=\n    def|\nclass|\Z)', content, re.DOTALL)
        if match:
            method_body = match.group(1)
            
            exports = {
                'stereo_enabled': 'stereo_enabled' in method_body,
                'enable_rbds': 'enable_rbds' in method_body,
                'deemphasis_us': 'deemphasis_us' in method_body,
            }
            
            print("Configuration fields exported to ReceiverConfig:")
            for field, exported in exports.items():
                if exported:
                    print(f"  ✅ {field}")
                else:
                    print(f"  ❌ {field} NOT EXPORTED")


def analyze_integration_path():
    """Analyze the complete integration path from config to display."""
    print_section("Integration Path Analysis")
    
    print("Configuration Flow:")
    print("  1. Database: RadioReceiver.stereo_enabled, RadioReceiver.enable_rbds")
    print("  2. Model: RadioReceiver.to_config() → ReceiverConfig")
    print("  3. Adapter: RedisSDRSourceAdapter._create_demodulator()")
    print("  4. Config: DemodulatorConfig(stereo_enabled, enable_rbds)")
    print("  5. Demod: FMDemodulator.__init__ sets _stereo_enabled, _rbds_enabled")
    print("  6. Process: FMDemodulator.demodulate() extracts data")
    print("  7. Status: Returns DemodulatorStatus with rbds_data, stereo_pilot_locked")
    print("  8. Metrics: RedisSDRSourceAdapter._update_metrics() adds to metadata")
    print("  9. Frontend: Metadata displayed via /api/audio/sources endpoint")
    
    print_subsection("Key Decision Points")
    
    decisions = [
        ("RBDS Enabled?", "Sample rate >= 114 kHz AND enable_rbds=True"),
        ("Stereo Enabled?", "Sample rate >= 76 kHz AND stereo_enabled=True AND modulation=FM/WFM"),
        ("Filter Sample Rate", "Always use ORIGINAL config.sample_rate (before decimation)"),
        ("Status Propagation", "DemodulatorStatus → adapter._update_metrics() → Redis metadata"),
    ]
    
    for decision, criteria in decisions:
        print(f"  • {decision}")
        print(f"    → {criteria}")


def check_for_issues():
    """Check for potential issues in the implementation."""
    print_section("Potential Issues Check")
    
    issues_found = []
    
    # Check demodulation.py
    demod_path = ROOT / "app_core" / "radio" / "demodulation.py"
    with open(demod_path, 'r') as f:
        demod_content = f.read()
    
    # Issue 1: Check if intermediate_rate is used incorrectly for filters
    if re.search(r'_pilot_filter.*intermediate_rate', demod_content):
        issues_found.append({
            'file': 'demodulation.py',
            'issue': 'Pilot filter may use intermediate_rate instead of config.sample_rate',
            'severity': 'HIGH',
            'impact': 'Pilot detection will fail - filter frequency mismatch'
        })
    
    # Issue 2: Check if RBDS filters use intermediate_rate
    if re.search(r'_rbds.*intermediate_rate', demod_content):
        issues_found.append({
            'file': 'demodulation.py',
            'issue': 'RBDS filter may use intermediate_rate instead of config.sample_rate',
            'severity': 'HIGH',
            'impact': 'RBDS extraction will fail - filter frequency mismatch'
        })
    
    # Issue 3: Check if stereo carrier uses intermediate_rate for time
    if re.search(r'38000.*time.*intermediate', demod_content):
        issues_found.append({
            'file': 'demodulation.py',
            'issue': 'Stereo carrier timing may use intermediate_rate',
            'severity': 'HIGH',
            'impact': 'Stereo decoding will produce wrong frequency - phase errors'
        })
    
    # Check redis_sdr_adapter.py
    adapter_path = ROOT / "app_core" / "audio" / "redis_sdr_adapter.py"
    with open(adapter_path, 'r') as f:
        adapter_content = f.read()
    
    # Issue 4: Check if RBDS data is actually extracted from status
    if 'status.rbds_data' not in adapter_content:
        issues_found.append({
            'file': 'redis_sdr_adapter.py',
            'issue': 'RBDS data not extracted from demodulator status',
            'severity': 'MEDIUM',
            'impact': 'RBDS metadata not shown in frontend even if decoded'
        })
    
    # Issue 5: Check if both 'enable_rbds' and 'rbds_enabled' are checked
    enable_rbds_count = len(re.findall(r'enable_rbds', adapter_content))
    rbds_enabled_count = len(re.findall(r'rbds_enabled', adapter_content))
    
    if enable_rbds_count == 0 and rbds_enabled_count == 0:
        issues_found.append({
            'file': 'redis_sdr_adapter.py',
            'issue': 'RBDS not configured from device_params',
            'severity': 'HIGH',
            'impact': 'RBDS will never be enabled regardless of database settings'
        })
    
    # Report findings
    if issues_found:
        print(f"❌ Found {len(issues_found)} potential issues:\n")
        for i, issue in enumerate(issues_found, 1):
            print(f"{i}. [{issue['severity']}] {issue['file']}")
            print(f"   Issue: {issue['issue']}")
            print(f"   Impact: {issue['impact']}\n")
    else:
        print("✅ No obvious issues detected in static analysis")
        print("   (Note: This doesn't guarantee correctness - runtime testing needed)")


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print(" EAS Station - RBDS and Stereo Code Path Analyzer")
    print(" Static analysis of FM demodulation implementation")
    print("="*80)
    
    try:
        analyze_demodulation_py()
        analyze_redis_sdr_adapter()
        analyze_database_models()
        analyze_integration_path()
        check_for_issues()
        
        print_section("Analysis Complete")
        print("Review the output above for any issues or missing components.")
        print("For runtime verification, run with actual SDR hardware or test signals.")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
