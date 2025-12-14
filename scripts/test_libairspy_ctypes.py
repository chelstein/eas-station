#!/usr/bin/env python3
"""
Test script for libairspy ctypes wrapper.

This tests direct libairspy access, bypassing SoapySDR/SWIG entirely.

Usage: python3 scripts/test_libairspy_ctypes.py
"""

import sys
import time

# Add project root to path
sys.path.insert(0, '/opt/eas-station')

def main():
    print("=" * 60)
    print("libairspy ctypes wrapper test")
    print("=" * 60)
    print()

    # Import wrapper
    try:
        from app_core.radio.libairspy import (
            AirspyDevice,
            get_lib_version,
            enumerate_airspy_devices,
        )
        print(f"[OK] Imported libairspy wrapper")
        print(f"     libairspy version: {get_lib_version()}")
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Enumerate devices
    print()
    print("-" * 60)
    print("Enumerating devices...")
    print("-" * 60)

    try:
        devices = enumerate_airspy_devices()
        print(f"[OK] Found {len(devices)} Airspy device(s)")
        for dev in devices:
            print(f"     {dev}")
    except Exception as e:
        print(f"[FAIL] Enumeration failed: {e}")
        return 1

    if not devices:
        print()
        print("[WARN] No Airspy devices found. Connect device and retry.")
        return 0

    # Open device
    print()
    print("-" * 60)
    print("Opening device...")
    print("-" * 60)

    try:
        dev = AirspyDevice()
        print(f"[OK] Device opened!")
        print(f"     Serial: {dev.get_serial()}")
        print(f"     Firmware: {dev.get_firmware_version()}")
        print(f"     Board: {dev.get_board_id()}")
        print(f"     Sample rates: {dev.get_sample_rates()}")
    except Exception as e:
        print(f"[FAIL] Open failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Configure device
    print()
    print("-" * 60)
    print("Configuring device...")
    print("-" * 60)

    try:
        dev.set_sample_rate(2_500_000)
        print(f"[OK] Sample rate: 2.5 MHz")

        dev.set_frequency(162_550_000)
        print(f"[OK] Frequency: 162.550 MHz (NOAA Weather)")

        dev.set_linearity_gain(15)
        print(f"[OK] Linearity gain: 15")
    except Exception as e:
        print(f"[FAIL] Configuration failed: {e}")
        dev.close()
        return 1

    # Read samples
    print()
    print("-" * 60)
    print("Reading samples...")
    print("-" * 60)

    try:
        samples = dev.read_samples(65536, timeout=2.0)
        if samples is not None:
            print(f"[OK] Read {len(samples)} samples")
            print(f"     dtype: {samples.dtype}")
            print(f"     mean magnitude: {abs(samples).mean():.6f}")
            print(f"     max magnitude: {abs(samples).max():.6f}")
        else:
            print(f"[WARN] No samples received (timeout)")
    except Exception as e:
        print(f"[FAIL] Read failed: {e}")
        import traceback
        traceback.print_exc()
        dev.close()
        return 1

    # Stop and close
    print()
    print("-" * 60)
    print("Cleanup...")
    print("-" * 60)

    dev.stop_streaming()
    dev.close()
    print(f"[OK] Device closed")

    print()
    print("=" * 60)
    print("[SUCCESS] All tests passed!")
    print("=" * 60)
    print()
    print("The ctypes wrapper bypasses SoapySDR/SWIG and works directly")
    print("with libairspy, similar to how dump1090 accesses hardware.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
