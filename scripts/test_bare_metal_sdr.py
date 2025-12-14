#!/usr/bin/env python3
"""
Bare metal SoapySDR test - mimics dump1090/dump978 approach.

This script tests the simplest possible SoapySDR device opening:
1. Enumerate devices with driver filter
2. Open device with minimal args (driver only, no serial)
3. Read some samples

Usage: python3 scripts/test_bare_metal_sdr.py [driver]
       driver: airspy, rtlsdr, etc. (default: airspy)
"""

import sys
import time

def main():
    driver = sys.argv[1] if len(sys.argv) > 1 else "airspy"

    print("=" * 60)
    print("Bare Metal SoapySDR Test")
    print("=" * 60)
    print(f"Target driver: {driver}")
    print()

    # Import SoapySDR
    try:
        import SoapySDR
        print(f"[OK] SoapySDR imported (API: {SoapySDR.getAPIVersion()})")
    except ImportError as e:
        print(f"[FAIL] Cannot import SoapySDR: {e}")
        return 1

    # Method 1: Enumerate with driver filter (like dump1090)
    print()
    print("-" * 60)
    print("Method 1: Enumerate with driver filter")
    print("-" * 60)

    try:
        # dump1090/dump978 style: pass driver as string
        results = SoapySDR.Device.enumerate(f"driver={driver}")
        print(f"[OK] Found {len(results)} device(s) with driver={driver}")
        for i, dev in enumerate(results):
            dev_dict = dict(dev)
            print(f"  Device {i}: {dev_dict}")
    except Exception as e:
        print(f"[FAIL] Enumerate failed: {e}")
        results = []

    if not results:
        print()
        print("No devices found. Try enumerating ALL devices:")
        try:
            all_devices = SoapySDR.Device.enumerate()
            print(f"  All devices: {len(all_devices)}")
            for i, dev in enumerate(all_devices):
                print(f"    Device {i}: {dict(dev)}")
        except Exception as e:
            print(f"  Enumerate all failed: {e}")
        return 1

    # Method 2: Open device with MINIMAL args (just driver)
    print()
    print("-" * 60)
    print("Method 2: Open with driver only (dump1090 style)")
    print("-" * 60)

    device = None
    try:
        # dump1090/dump978 approach: just driver name, no serial
        # This opens the FIRST matching device
        device = SoapySDR.Device({"driver": driver})
        print(f"[OK] Device opened successfully!")

        # Get device info
        hw_info = device.getHardwareInfo()
        print(f"  Hardware info: {dict(hw_info)}")

    except Exception as e:
        print(f"[FAIL] Device.make() failed: {e}")
        print()
        print("Trying string format (like dump978)...")

        try:
            # Alternative: string format
            device = SoapySDR.Device(f"driver={driver}")
            print(f"[OK] String format worked!")
        except Exception as e2:
            print(f"[FAIL] String format also failed: {e2}")
            return 1

    if device is None:
        return 1

    # Method 3: Configure and read samples
    print()
    print("-" * 60)
    print("Method 3: Configure and read samples")
    print("-" * 60)

    try:
        # Get supported sample rates
        rates = device.listSampleRates(SoapySDR.SOAPY_SDR_RX, 0)
        print(f"  Supported sample rates: {list(rates)}")

        # Use first supported rate (or 2.5MHz for Airspy)
        if driver == "airspy" and 2500000.0 in rates:
            sample_rate = 2500000.0
        elif rates:
            sample_rate = rates[0]
        else:
            sample_rate = 2400000.0

        print(f"  Setting sample rate: {sample_rate/1e6:.1f} MHz")
        device.setSampleRate(SoapySDR.SOAPY_SDR_RX, 0, sample_rate)

        # Set frequency (NOAA Weather Radio)
        freq = 162.550e6
        print(f"  Setting frequency: {freq/1e6:.3f} MHz")
        device.setFrequency(SoapySDR.SOAPY_SDR_RX, 0, freq)

        # Setup stream
        print("  Setting up RX stream...")
        rx_stream = device.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CF32)
        device.activateStream(rx_stream)

        # Read samples
        import numpy as np
        buff = np.zeros(1024, dtype=np.complex64)

        print("  Reading samples...")
        sr = device.readStream(rx_stream, [buff], len(buff), timeoutUs=1000000)

        if sr.ret > 0:
            print(f"[OK] Read {sr.ret} samples successfully!")
            print(f"  Sample mean magnitude: {np.mean(np.abs(buff[:sr.ret])):.6f}")
        else:
            print(f"[WARN] Read returned {sr.ret}")

        # Cleanup
        device.deactivateStream(rx_stream)
        device.closeStream(rx_stream)

    except Exception as e:
        print(f"[FAIL] Sample reading failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print()
    print("=" * 60)
    print("[SUCCESS] Bare metal SoapySDR test passed!")
    print("=" * 60)
    print()
    print("The device CAN be opened with minimal args (driver only).")
    print("The problem is likely in the complex abstraction layers.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
