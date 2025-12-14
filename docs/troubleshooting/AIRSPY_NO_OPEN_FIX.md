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
Device.make() returned 'no match' for wxj93 (attempt 1/3)
```

## Root Causes

### Issue 1: Missing Airspy Package (v2.27.9)
The `airspy` package (which contains firmware and host utilities) was not installed. 

While `libairspy0` (library) and `soapysdr-module-airspy` (SoapySDR plugin) were present, the device firmware and initialization tools were missing.

### Issue 2: Label Parameter Not Supported (v2.27.10) ⭐ **CRITICAL**
**Airspy's SoapySDR module does NOT support the `label` parameter** and returns "no match" when it's present in the device args.

The EAS Station code was adding a `label` parameter to help identify devices, but this breaks Airspy:
- ✅ RTL-SDR: Supports `label` parameter
- ❌ Airspy: Rejects `label` parameter with "no match"

This is why `SoapySDRUtil --probe="driver=airspy"` worked (no label), but the Python code failed (label included).

## Solution ✅

### Automatic Fix (Fresh Install)

Run the install script - it now includes both fixes:

```bash
sudo ./install.sh
```

### Manual Fix (Existing Installation)

**Step 1**: Install the missing package:

```bash
sudo apt-get update
sudo apt-get install airspy
```

**Step 2**: Update to version 2.27.10+ with the label fix:

```bash
cd /opt/eas-station
git pull
```

**Step 3**: Restart the SDR service:

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

3. **Check service logs** (should now open device):
   ```bash
   sudo journalctl -u eas-station-sdr.service -n 50 | grep -E "(Found|opened|Locked)"
   ```
   
   Expected output:
   ```
   ✅ Found 1 SoapySDR device(s): ['AirSpy One [b58069dc39399513]']
   ✅ Successfully opened device
   ✅ Receiver wxj93: Locked
   ```

## Verified Test Results

**System**: Raspberry Pi (Debian Trixie), ARM64  
**Date**: 2025-12-14  
**Package Version**: airspy 1.0.10-3+b3
**Code Version**: 2.27.10

**Before Fix** (v2.27.9 with airspy package but label parameter):
```
Device.make() returned 'no match' for wxj93 (attempt 1/3)
```

**After Fix** (v2.27.10 without label parameter for Airspy):
```
✅ Successfully opened device
✅ Receiver started and locked
```

## Technical Details

### Why Label Parameter Breaks Airspy

When opening a SoapySDR device, parameters are passed as a key-value dictionary:

```python
# This works for RTL-SDR
args = {"driver": "rtlsdr", "serial": "12345", "label": "my_receiver"}
device = SoapySDR.Device(args)

# This FAILS for Airspy (label not supported)
args = {"driver": "airspy", "serial": "b58069dc39399513", "label": "wxj93"}
device = SoapySDR.Device(args)  # Returns "no match"
```

The Airspy SoapySDR module (libSoapySDRSupport-airspy.so) doesn't recognize the `label` key and treats it as an invalid argument, returning "no match" even though the device exists.

### Code Fix

```python
# Before (v2.27.9 and earlier)
if self.config.identifier:
    args.setdefault("label", self.config.identifier)

# After (v2.27.10+)
# Airspy driver does NOT support the 'label' parameter
if self.config.identifier and self.driver_hint != "airspy":
    args.setdefault("label", self.config.identifier)
```

## Related Packages

| Package | Purpose | Required |
|---------|---------|----------|
| `airspy` | **Firmware, utilities (airspy_info, etc.)** | ✅ **YES** |
| `libairspy0` | Core library | ✅ YES |
| `soapysdr-module-airspy` | SoapySDR driver plugin | ✅ YES |

## See Also

- [SDR Setup Guide](../hardware/SDR_SETUP.md)
- [Airspy Container Fix](AIRSPY_CONTAINER_FIX.md)
- [Frontend Error After Fix](FRONTEND_AIRSPY_ERROR_AFTER_FIX.md)
- [SDR Master Troubleshooting Guide](SDR_MASTER_TROUBLESHOOTING_GUIDE.md)

---

**Fixed in**: Version 2.27.9 (package) + 2.27.10 (label parameter)  
**Date**: 2025-12-14  
**Verified**: ✅ Working on Raspberry Pi (Debian Trixie ARM64)

