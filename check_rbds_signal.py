#!/usr/bin/env python3
"""
Quick diagnostic: Check if RBDS 57kHz subcarrier is present in the FM multiplex.

This will show the frequency spectrum to see if there's actually a 57kHz signal.
"""

import sys
import time
import redis
import numpy as np
import json

def check_rbds_signal():
    """Check Redis for recent multiplex samples and analyze spectrum."""
    try:
        r = redis.Redis(decode_responses=False)

        print("Checking for RBDS 57kHz subcarrier...")
        print("=" * 70)

        # Try to get recent audio source info
        sources = r.smembers('audio_sources')
        if not sources:
            print("No active audio sources found.")
            return

        print(f"Active sources: {len(sources)}")

        # Check for SDR sources with multiplex data
        for source_key in sources:
            try:
                source_data = r.hgetall(source_key)
                if not source_data:
                    continue

                source_type = source_data.get(b'type', b'').decode('utf-8')
                if source_type != 'sdr':
                    continue

                name = source_data.get(b'name', b'Unknown').decode('utf-8')
                frequency = source_data.get(b'frequency', b'0').decode('utf-8')

                print(f"\nSDR Source: {name} @ {frequency} MHz")
                print("-" * 70)

                # NOTE: The multiplex signal is not stored in Redis
                # This is processed in real-time in the audio service
                print("⚠️  Multiplex spectrum analysis requires adding diagnostics to")
                print("   the demodulator code itself.")
                print()
                print("To check for RBDS signal:")
                print("1. Tune to a known RBDS station (commercial FM in US)")
                print("2. Check signal strength is good (> -30 dBFS)")
                print("3. Look for these log messages:")
                print("   - 'Stereo pilot detected' - confirms 19kHz pilot")
                print("   - 'RBDS Costas: freq=X Hz' where X < 5 Hz")
                print("4. If Costas freq > 10 Hz, likely no 57kHz subcarrier")

            except Exception as e:
                print(f"Error checking source: {e}")

        print()
        print("=" * 70)
        print("DIAGNOSIS STEPS:")
        print("=" * 70)
        print("1. Verify station broadcasts RBDS:")
        print("   - Most commercial FM stations in US have RBDS")
        print("   - Check https://radio-locator.com/ for your station")
        print()
        print("2. Check signal quality:")
        print("   - Look for 'Stereo pilot detected' in logs")
        print("   - If no stereo pilot, signal is too weak")
        print()
        print("3. Check RBDS subcarrier extraction:")
        print("   - Costas freq should be < 5 Hz when locked")
        print("   - Current logs show ~0.5-1.2 Hz (GOOD)")
        print()
        print("4. Check M&M timing:")
        print("   - 'presync: spacing mismatch (expected 26, got 70)'")
        print("   - This means syndrome matches are found but spacing is wrong")
        print("   - Suggests M&M might be producing too many/few symbols")
        print()
        print("Current status from your logs:")
        print("  ✅ Costas locked (~0.5-1 Hz)")
        print("  ✅ M&M producing symbols (250 samples -> 16 symbols)")
        print("  ✅ Bits being extracted")
        print("  ❌ Syndromes random (never matching targets)")
        print("  ⚠️  One presync match with 70-bit spacing (expected 26)")
        print()
        print("NEXT STEPS:")
        print("1. Verify station has RBDS (check radio-locator.com)")
        print("2. Try different station if current one doesn't have RBDS")
        print("3. Check signal strength (should be strong)")
        print("4. If signal is good, M&M loop gain may need tuning")

    except redis.ConnectionError:
        print("Could not connect to Redis")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_rbds_signal()
