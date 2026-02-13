#!/usr/bin/env python3
"""
EAS Station - Emergency Alert System
Copyright (c) 2025-2026 Timothy Kramer (KR8MER)

RBDS and Stereo Configuration Validator

This script validates that RBDS and stereo settings are correctly
configured in the database and will be properly used by the demodulator.

Usage:
    python3 tools/validate_rbds_stereo_config.py
"""

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def validate_database_config():
    """Validate RBDS and stereo configuration in database."""
    print("="*80)
    print(" Validating RBDS and Stereo Configuration")
    print("="*80)
    
    try:
        from app import create_app
        from app_core.models import RadioReceiver
        from app_core.extensions import db
        
        app = create_app()
        
        with app.app_context():
            receivers = RadioReceiver.query.all()
            
            if not receivers:
                print("\n⚠️  No radio receivers configured in database")
                print("   Add receivers via Settings > Radio Settings")
                return 0
            
            print(f"\nFound {len(receivers)} radio receiver(s):\n")
            
            issues_found = []
            
            for receiver in receivers:
                print(f"{'─'*80}")
                print(f"Receiver: {receiver.display_name} ({receiver.identifier})")
                print(f"{'─'*80}")
                
                # Basic info
                print(f"  Driver: {receiver.driver}")
                print(f"  Frequency: {receiver.frequency_hz / 1e6:.6f} MHz")
                print(f"  IQ Sample Rate: {receiver.sample_rate:,} Hz")
                print(f"  Audio Sample Rate: {receiver.audio_sample_rate:,} Hz" if receiver.audio_sample_rate else "  Audio Sample Rate: Auto")
                print(f"  Modulation: {receiver.modulation_type}")
                print(f"  Enabled: {'Yes' if receiver.enabled else 'No'}")
                print(f"  Auto-start: {'Yes' if receiver.auto_start else 'No'}")
                
                print(f"\n  RBDS Configuration:")
                print(f"    Enabled: {'Yes' if receiver.enable_rbds else 'No'}")
                
                # Check RBDS requirements
                if receiver.enable_rbds:
                    nyquist = receiver.sample_rate / 2
                    rbds_subcarrier = 57_000
                    
                    if receiver.sample_rate < 114_000:
                        print(f"    ❌ ISSUE: Sample rate too low for RBDS")
                        print(f"       Current: {receiver.sample_rate:,} Hz")
                        print(f"       Minimum: 114,000 Hz (2× Nyquist of 57 kHz subcarrier)")
                        print(f"       RBDS will be disabled automatically")
                        issues_found.append(f"{receiver.identifier}: RBDS enabled but sample rate too low")
                    elif rbds_subcarrier > nyquist:
                        print(f"    ❌ ISSUE: Nyquist frequency too low for RBDS")
                        print(f"       Nyquist: {nyquist:,} Hz")
                        print(f"       RBDS Subcarrier: {rbds_subcarrier:,} Hz")
                        issues_found.append(f"{receiver.identifier}: Nyquist < RBDS subcarrier")
                    else:
                        print(f"    ✅ Sample rate sufficient: {receiver.sample_rate:,} Hz")
                        print(f"       Nyquist: {nyquist:,} Hz > RBDS subcarrier: {rbds_subcarrier:,} Hz")
                else:
                    print(f"    ℹ️  RBDS not enabled")
                
                print(f"\n  Stereo Configuration:")
                print(f"    Enabled: {'Yes' if receiver.stereo_enabled else 'No'}")
                
                # Check stereo requirements
                if receiver.stereo_enabled:
                    modulation = receiver.modulation_type.upper() if receiver.modulation_type else 'UNKNOWN'
                    
                    if modulation not in ('FM', 'WFM'):
                        print(f"    ⚠️  WARNING: Stereo only works with FM/WFM modulation")
                        print(f"       Current modulation: {modulation}")
                        print(f"       Stereo will be disabled automatically")
                        issues_found.append(f"{receiver.identifier}: Stereo enabled but not FM/WFM")
                    else:
                        # Check sample rate for stereo
                        nyquist = receiver.sample_rate / 2
                        stereo_subcarrier = 38_000
                        pilot_tone = 19_000
                        
                        if receiver.sample_rate < 76_000:
                            print(f"    ❌ ISSUE: Sample rate too low for stereo")
                            print(f"       Current: {receiver.sample_rate:,} Hz")
                            print(f"       Minimum: 76,000 Hz (2× Nyquist of 38 kHz subcarrier)")
                            print(f"       Stereo will be disabled automatically")
                            issues_found.append(f"{receiver.identifier}: Stereo enabled but sample rate too low")
                        elif stereo_subcarrier > nyquist:
                            print(f"    ❌ ISSUE: Nyquist frequency too low for stereo")
                            print(f"       Nyquist: {nyquist:,} Hz")
                            print(f"       Stereo Subcarrier: {stereo_subcarrier:,} Hz")
                            issues_found.append(f"{receiver.identifier}: Nyquist < stereo subcarrier")
                        elif pilot_tone > nyquist:
                            print(f"    ❌ ISSUE: Nyquist frequency too low for pilot")
                            print(f"       Nyquist: {nyquist:,} Hz")
                            print(f"       Pilot Tone: {pilot_tone:,} Hz")
                            issues_found.append(f"{receiver.identifier}: Nyquist < pilot tone")
                        else:
                            print(f"    ✅ Sample rate sufficient: {receiver.sample_rate:,} Hz")
                            print(f"       Nyquist: {nyquist:,} Hz > Stereo subcarrier: {stereo_subcarrier:,} Hz")
                            print(f"       Pilot tone {pilot_tone:,} Hz also within range")
                else:
                    print(f"    ℹ️  Stereo not enabled")
                
                # Check de-emphasis
                print(f"\n  De-emphasis: {receiver.deemphasis_us}μs")
                if receiver.deemphasis_us == 75.0:
                    print(f"    ✅ North America standard (75μs)")
                elif receiver.deemphasis_us == 50.0:
                    print(f"    ✅ Europe standard (50μs)")
                elif receiver.deemphasis_us == 0.0:
                    print(f"    ℹ️  De-emphasis disabled")
                else:
                    print(f"    ⚠️  Non-standard de-emphasis value")
                
                # Export to config
                print(f"\n  Testing config export...")
                try:
                    config = receiver.to_config()
                    print(f"    ✅ to_config() successful")
                    print(f"       stereo_enabled: {config.stereo_enabled}")
                    print(f"       enable_rbds: {config.enable_rbds}")
                    print(f"       deemphasis_us: {config.deemphasis_us}")
                except Exception as e:
                    print(f"    ❌ to_config() failed: {e}")
                    issues_found.append(f"{receiver.identifier}: Config export failed")
                
                print()
            
            # Summary
            print("="*80)
            print(" Validation Summary")
            print("="*80)
            
            if issues_found:
                print(f"\n❌ Found {len(issues_found)} issue(s):\n")
                for issue in issues_found:
                    print(f"  • {issue}")
                print("\nRecommendations:")
                print("  1. Increase sample rate to at least 200 kHz for RBDS")
                print("  2. Increase sample rate to at least 200 kHz for stereo")
                print("  3. Use 2.4-2.5 MHz sample rate for full FM broadcast (RTL-SDR, Airspy)")
                print("  4. Verify modulation type is FM or WFM for stereo")
                return 1
            else:
                print("\n✅ All configurations validated successfully!")
                print("\nRBDS and stereo paths are correctly configured.")
                print("Features will work as expected when receivers are started.")
                return 0
    
    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point."""
    return validate_database_config()


if __name__ == "__main__":
    sys.exit(main())
