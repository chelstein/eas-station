# EAS Station Scripts

This directory contains utility scripts for EAS Station maintenance, diagnostics, and development.

## 🚀 Quick Start

### SDR Troubleshooting
```bash
# Comprehensive SDR diagnostic collection
bash scripts/collect_sdr_diagnostics.sh

# Quick SDR device check
python3 scripts/sdr_diagnostics.py

# Test SDR capture
python3 scripts/sdr_diagnostics.py --test-capture --frequency 162550000
```

### System Diagnostics
```bash
# Web interface connection issues
bash scripts/diagnostics/troubleshoot_connection.sh

# Check SDR receiver status
python3 scripts/diagnostics/check_sdr_status.py

# Icecast streaming diagnostics
bash scripts/diagnostics/diagnose_icecast.sh

# Portainer deployment diagnostics
bash scripts/diagnostics/diagnose_portainer.sh
```

---

## 📋 Script Categories

### Diagnostic Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| **`collect_sdr_diagnostics.sh`** | **Comprehensive SDR diagnostics** | `bash scripts/collect_sdr_diagnostics.sh` |
| **`sdr_diagnostics.py`** | **SDR hardware & driver testing** | `python3 scripts/sdr_diagnostics.py` |
| `diagnostics/check_sdr_status.py` | Check SDR receiver status | `python3 scripts/diagnostics/check_sdr_status.py` |
| `diagnostics/troubleshoot_connection.sh` | Web interface diagnostics | `bash scripts/diagnostics/troubleshoot_connection.sh` |
| `diagnostics/diagnose_icecast.sh` | Icecast streaming diagnostics | `bash scripts/diagnostics/diagnose_icecast.sh` |
| `diagnostics/diagnose_portainer.sh` | Portainer deployment check | `bash scripts/diagnostics/diagnose_portainer.sh` |

See [diagnostics/README.md](diagnostics/README.md) for detailed documentation.

### SDR & Radio Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `sdr_diagnostics.py` | SDR hardware & driver testing | `python3 scripts/sdr_diagnostics.py` |
| `collect_sdr_diagnostics.sh` | Comprehensive SDR diagnostics | `bash scripts/collect_sdr_diagnostics.sh` |



### Performance Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `diagnose_cpu_loop.sh` | Diagnose CPU usage loops | `bash scripts/diagnose_cpu_loop.sh` |

### Build & Development

| Script | Purpose | Usage |
|--------|---------|-------|
| `build_diagram_svgs.sh` | Generate diagram SVGs | `bash scripts/build_diagram_svgs.sh` |

---

## 🎯 Common Tasks

### "My SDR Isn't Working"

**Quick diagnostic:**
```bash
bash scripts/collect_sdr_diagnostics.sh
```

This creates a comprehensive diagnostic report with:
- USB hardware detection
- SoapySDR device enumeration
- Container status and logs
- Database configuration
- Redis connectivity
- System resources

**Output:** Timestamped text file with all diagnostics, ready to attach to GitHub issues.

**Documentation:**
- [SDR Quick Fix Guide](../docs/troubleshooting/SDR_QUICK_FIX_GUIDE.md)
- [SDR Master Troubleshooting Guide](../docs/troubleshooting/SDR_MASTER_TROUBLESHOOTING_GUIDE.md)

---

### "Can't Access Web Interface"

**Quick diagnostic:**
```bash
bash scripts/diagnostics/troubleshoot_connection.sh
```

This checks:
- Container status
- Port mappings
- Network configuration
- Firewall rules

---

### "Icecast Streaming Not Working"

**Quick diagnostic:**
```bash
bash scripts/diagnostics/diagnose_icecast.sh
```

This checks:
- Icecast container status
- Port 8001 availability
- Firewall configuration
- Mount point configuration

---

### "Want to Test SDR Hardware"

**Basic test:**
```bash
python3 scripts/sdr_diagnostics.py
```

**Capture test:**
```bash
python3 scripts/sdr_diagnostics.py --test-capture --driver rtlsdr --frequency 162550000
```

**Check capabilities:**
```bash
python3 scripts/sdr_diagnostics.py --capabilities rtlsdr
```

---

## 📖 Documentation

### Troubleshooting Guides
- **[SDR Quick Fix Guide](../docs/troubleshooting/SDR_QUICK_FIX_GUIDE.md)** - 5-minute checklist
- **[SDR Master Troubleshooting Guide](../docs/troubleshooting/SDR_MASTER_TROUBLESHOOTING_GUIDE.md)** - Complete procedures
- [SDR Troubleshooting Flowchart](../docs/troubleshooting/SDR_TROUBLESHOOTING_FLOWCHART.md) - Visual guide
- [SDR Audio Tuning Issues](../docs/troubleshooting/SDR_AUDIO_TUNING_ISSUES.md) - Audio problems
- [All Troubleshooting Guides](../docs/troubleshooting/)

### Setup Guides
- [SDR Setup Guide](../docs/hardware/SDR_SETUP.md) - Initial SDR configuration
- [Setup Instructions](../docs/guides/SETUP_INSTRUCTIONS.md) - First-run setup
- [Complete Documentation Index](../docs/INDEX.md) - All documentation

---

## 🆘 Getting Help

### Before Asking for Help

1. ✅ Run the appropriate diagnostic script
2. ✅ Check the relevant troubleshooting guide
3. ✅ Review existing GitHub issues

### Reporting Issues

When opening a GitHub issue:

1. **Include diagnostic output:**
   ```bash
   bash scripts/collect_sdr_diagnostics.sh
   # Attach the generated .txt file
   ```

2. **Provide context:**
   - What you were trying to do
   - What you expected to happen
   - What actually happened
   - Steps already tried

3. **Link to relevant docs:**
   - Which troubleshooting guides you followed
   - Which steps worked/didn't work

### Where to Get Help

- **GitHub Issues:** https://github.com/KR8MER/eas-station/issues
- **GitHub Discussions:** https://github.com/KR8MER/eas-station/discussions
- **Documentation:** [docs/INDEX.md](../docs/INDEX.md)

---

## 🔨 Contributing

When adding new scripts:

1. **Follow naming conventions:**
   - Use lowercase with underscores: `my_script.sh`
   - Diagnostic scripts go in `diagnostics/` subdirectory
   - Use `.sh` for bash, `.py` for Python, `.sql` for SQL

2. **Add copyright header:**
   ```bash
   #!/bin/bash
   # EAS Station - Emergency Alert System
   # Copyright (c) 2025 Timothy Kramer (KR8MER)
   ```

3. **Make scripts executable:**
   ```bash
   chmod +x scripts/my_script.sh
   ```

4. **Document in this README:**
   - Add to appropriate category table
   - Include purpose and usage
   - Link to related documentation

5. **Add help text:**
   - Support `--help` flag
   - Include usage examples in script header

See [Contributing Guide](../docs/process/CONTRIBUTING.md) for more details.

---

## 📝 Script Index

### All Scripts (Alphabetical)

- `build_diagram_svgs.sh` - Generate diagram SVGs from source
- `collect_sdr_diagnostics.sh` - **Comprehensive SDR diagnostics collector**
- `diagnose_cpu_loop.sh` - Diagnose CPU usage loops
- `diagnostics/check_sdr_status.py` - Check SDR receiver status
- `diagnostics/diagnose_icecast.sh` - Icecast streaming diagnostics
- `diagnostics/diagnose_portainer.sh` - Portainer deployment diagnostics
- `diagnostics/troubleshoot_connection.sh` - Web interface diagnostics
- `sdr_diagnostics.py` - **SDR hardware & driver testing**

---

**Scripts Documentation Version:** 1.0  
**Last Updated:** December 2025
