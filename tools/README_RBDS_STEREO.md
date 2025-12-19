# RBDS and Stereo Verification Tools

This directory contains tools for verifying and analyzing the RBDS (Radio Broadcast Data System) and FM stereo decoding paths in EAS Station.

## Tools Overview

### 1. `analyze_rbds_stereo_code.py` - Static Code Analyzer

**Purpose**: Analyze source code without running it to verify correct implementation.

**Features**:
- ✅ Verifies all required components exist (filters, decoders, status propagation)
- ✅ Checks filter sample rate usage (must use config.sample_rate, not intermediate_rate)
- ✅ Validates carrier generation timing
- ✅ Traces metadata propagation path
- ✅ Detects common implementation pitfalls
- ✅ No dependencies required (pure Python)

**Usage**:
```bash
python3 tools/analyze_rbds_stereo_code.py
```

**Output**: Detailed analysis report with ✅/❌ indicators for each component.

---

### 2. `trace_rbds_stereo_path.py` - Runtime Signal Tracer

**Purpose**: Generate test signals and trace them through the demodulator at runtime.

**Features**:
- 🧪 Tests multiple sample rates (2.5M, 2.4M, 240K, 200K, 114K, 76K Hz)
- 🧪 Generates synthetic FM multiplex signals with pilot, stereo, and RBDS
- 🧪 Verifies filter responses and demodulation
- 🧪 Checks minimum sample rate requirements
- 🧪 Tests both RBDS and stereo paths independently

**Requirements**:
```bash
pip install numpy scipy  # Required for signal generation
```

**Usage**:
```bash
python3 tools/trace_rbds_stereo_path.py
```

**Output**: Comprehensive test report showing signal processing at each stage.

---

### 3. `validate_rbds_stereo_config.py` - Configuration Validator

**Purpose**: Validate RBDS and stereo settings in the database.

**Features**:
- 📊 Reads RadioReceiver configuration from database
- 📊 Checks sample rate sufficiency for RBDS (≥114 kHz) and stereo (≥76 kHz)
- 📊 Validates modulation type compatibility (FM/WFM for stereo)
- 📊 Tests to_config() method export
- 📊 Provides actionable recommendations for fixing issues

**Requirements**:
- Database connection (uses Flask app context)
- EAS Station must be installed

**Usage**:
```bash
cd /opt/eas-station
source venv/bin/activate
python3 tools/validate_rbds_stereo_config.py
```

**Output**: Per-receiver validation with ✅/❌/⚠️ indicators and recommendations.

---

## Quick Start

### Basic Verification (No Setup Required)

Run the static code analyzer to verify implementation:

```bash
cd /opt/eas-station
python3 tools/analyze_rbds_stereo_code.py
```

Expected output: All checks should show ✅ with "No obvious issues detected"

### Configuration Check (Requires Database)

Verify your receiver settings:

```bash
cd /opt/eas-station
source venv/bin/activate
python3 tools/validate_rbds_stereo_config.py
```

This will show:
- Which receivers have RBDS enabled
- Which receivers have stereo enabled  
- Whether sample rates are sufficient
- Any configuration issues

### Full Signal Path Test (Requires NumPy)

If you want to test signal processing at runtime:

```bash
cd /opt/eas-station
source venv/bin/activate
pip install numpy scipy  # One-time install
python3 tools/trace_rbds_stereo_path.py
```

This generates test signals and processes them through the demodulator to verify all paths work correctly.

---

## Understanding RBDS and Stereo

### FM Multiplex Signal Structure

```
0-15 kHz: L+R (Mono audio)
19 kHz:   Pilot tone (stereo indicator)
23-53 kHz: L-R (Stereo difference signal, DSB-SC at 38 kHz)
57 kHz:   RBDS data subcarrier (1187.5 baud BPSK)
```

### Minimum Sample Rate Requirements

| Feature | Subcarrier | Nyquist | Minimum Rate | Recommended |
|---------|------------|---------|--------------|-------------|
| Mono    | 15 kHz     | 30 kHz  | 32 kHz       | 44.1 kHz    |
| Pilot   | 19 kHz     | 38 kHz  | 38 kHz       | 50 kHz      |
| Stereo  | 38 kHz     | 76 kHz  | 76 kHz       | 200 kHz     |
| RBDS    | 57 kHz     | 114 kHz | 114 kHz      | 200 kHz     |

**Real-world examples**:
- RTL-SDR (2.4 MHz): ✅ Supports all features
- Airspy R2 (2.5 MHz): ✅ Supports all features
- Audio line-in (48 kHz): ❌ Stereo and RBDS not available

---

## Common Issues and Solutions

### Issue: RBDS not decoding

**Check**:
1. Sample rate ≥ 114 kHz? (`validate_rbds_stereo_config.py`)
2. `enable_rbds=True` in database?
3. Receiving actual FM broadcast signal (not file playback)?
4. Strong enough signal (RBDS needs good SNR)?

**Fix**: Increase sample rate to at least 200 kHz or use higher (2.4-2.5 MHz).

### Issue: Stereo not working

**Check**:
1. Sample rate ≥ 76 kHz? (`validate_rbds_stereo_config.py`)
2. `stereo_enabled=True` in database?
3. Modulation type is FM or WFM?
4. Station broadcasting stereo (19 kHz pilot present)?

**Fix**: 
- Increase sample rate to at least 200 kHz
- Set modulation to FM or WFM
- Verify station is broadcasting stereo

### Issue: Audio sounds wrong

**Check**:
1. De-emphasis setting (75μs for North America, 50μs for Europe)
2. Sample rate is exact (not approximate decimation)
3. No aliasing (sample rate sufficient for all subcarriers)

**Fix**: Run `analyze_rbds_stereo_code.py` to verify implementation.

---

## Documentation

For complete technical details, see:
- `docs/audio/RBDS_STEREO_PATH_VERIFICATION.md` - Comprehensive path documentation
- `app_core/radio/demodulation.py` - Source code with inline comments
- `app_core/audio/redis_sdr_adapter.py` - Integration code

---

## Support

If these tools report issues:

1. **Static analyzer fails**: Code may have been modified incorrectly
2. **Config validator fails**: Adjust receiver settings in Settings > Radio Settings
3. **Runtime tracer fails**: Check numpy/scipy installation or library versions

For help, check:
- System logs: `journalctl -u eas-service -f`
- SDR logs: `journalctl -u sdr-service -f`
- Application logs in `/opt/eas-station/logs/`

---

**Last Updated**: December 19, 2024  
**Version**: 2.42.2
