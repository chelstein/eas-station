# Airspy "Unable to open AirSpy device" Fix

✅ **VERIFIED WORKING** - Tested on Debian Trixie ARM64 (2025-12-14)

## Problem

Airspy device fails to open even with root/sudo access:

```
$ sudo SoapySDRUtil --probe="driver=airspy"
Error probing device: Unable to open AirSpy device with serial b58069dc39399513
```

Python error from EAS Station:
```
SoapySDR::Device::make() no match (troubleshooting: For Airspy: ensure SoapyAirspy module is installed and libairspy is available)
```

## Root Cause

The `airspy` package (which contains firmware and host utilities) was not installed. 

While `libairspy0` (library) and `soapysdr-module-airspy` (SoapySDR plugin) were present, the device firmware and initialization tools were missing.

## Solution ✅

### Automatic Fix (Fresh Install)

Run the install script - it now includes the `airspy` package:

```bash
sudo ./install.sh
```

### Manual Fix (Existing Installation)

Install the missing package:

```bash
sudo apt-get update
sudo apt-get install airspy
```

Then restart the SDR service:

```bash
sudo systemctl restart eas-station-sdr.service
```

## Verification ✅

1. **Test with airspy_info** (should now work):
   ```bash
   airspy_info
   ```
   
   Expected output:
   ```
   airspy_info version: 1.x.x
   Board ID Number: X (AIRSPY)
   Firmware Version: AirSpy NOS v1.x.x
   ...
   ```

2. **Test with SoapySDR** (should now work):
   ```bash
   SoapySDRUtil --probe="driver=airspy"
   ```
   
   Expected output (VERIFIED WORKING):
   ```
   Probe device driver=airspy

   ----------------------------------------------------
   -- Device identification
   ----------------------------------------------------
     driver=Airspy
     hardware=Airspy
     serial=b58069dc39399513

   ----------------------------------------------------
   -- Peripheral summary
   ----------------------------------------------------
     Channels: 1 Rx, 0 Tx
     Timestamps: NO
     ...
   ```

3. **Check device permissions**:
   ```bash
   lsusb -d 1d50:60a1 -v
   ```

## Verified Test Results

**System**: Raspberry Pi (Debian Trixie), ARM64  
**Date**: 2025-12-14  
**Package Version**: airspy 1.0.10-3+b3

**Before Fix**:
```
$ SoapySDRUtil --probe="driver=airspy"
Error probing device: Unable to open AirSpy device with serial b58069dc39399513
```

**After Fix** (install airspy + restart service):
```
$ SoapySDRUtil --probe="driver=airspy"
Probe device driver=airspy
  driver=Airspy
  hardware=Airspy
  serial=b58069dc39399513
  Channels: 1 Rx, 0 Tx
  Full gain range: [0, 45] dB
  Full freq range: [24, 1800] MHz
  Sample rates: 10, 2.5 MSps
```

✅ **FIX CONFIRMED WORKING**

## Related Packages

| Package | Purpose | Required |
|---------|---------|----------|
| `airspy` | **Firmware, utilities (airspy_info, etc.)** | ✅ **YES** |
| `libairspy0` | Core library | ✅ YES |
| `soapysdr-module-airspy` | SoapySDR driver plugin | ✅ YES |

## Technical Details

The `airspy` package provides:
- Firmware files for Airspy devices
- `airspy_info` - Device information tool
- `airspy_rx` - Raw sample capture tool  
- `airspy_gpio` - GPIO control utility
- Device initialization scripts

Without the firmware, SoapySDR can enumerate the USB device but cannot initialize it for use.

## See Also

- [SDR Setup Guide](../hardware/SDR_SETUP.md)
- [Airspy Container Fix](AIRSPY_CONTAINER_FIX.md)
- [SDR Master Troubleshooting Guide](SDR_MASTER_TROUBLESHOOTING_GUIDE.md)

---

**Fixed in**: Version 2.27.9  
**Date**: 2025-12-14  
**Verified**: ✅ Working on Raspberry Pi (Debian Trixie ARM64)

