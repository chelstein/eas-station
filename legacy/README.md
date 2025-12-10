# Legacy Code Archive

This directory contains archived code from previous deployment architectures. These files are **Docker-specific** and **not used in bare-metal deployments**.

## Purpose

This directory preserves Docker-era scripts and tools for:
- Historical reference
- Migration assistance for Docker users
- Understanding past design decisions
- Debugging legacy deployments

## Contents

### Docker-Specific Scripts (Archived December 2025)
- `collect_sdr_diagnostics_docker.sh` - Docker-based SDR diagnostics (use `scripts/collect_sdr_diagnostics.sh` instead)
- `diagnose_cpu_loop.sh` - Docker container CPU diagnostics
- `diagnose_portainer.sh` - Portainer deployment diagnostics
- `diagnose-icecast.sh` - Docker-based Icecast diagnostics
- `troubleshoot_connection.sh` - Docker network troubleshooting
- `restart_audio.sh` - Docker compose service restart
- `fix_database.sh` - Docker-based database fixes
- `validate_architecture.sh` - Docker compose validation

### Audio Issue Fixes (Docker-era)
- `fix-audio-squeal.sh` - Audio squeal fix for Docker deployments
- `fix_all_audio_issues.sh` - Comprehensive audio fix (Docker)
- `fix_all_audio_issues_standalone.sh` - Standalone audio fix (Docker)
- `detect_stream_sample_rates.sh` - Stream rate detection (Docker)

### Other Legacy Tools
- `audio/` - Archived audio processing implementations
- `fixes/` - One-time database and configuration fixes
- `add_fastapi_service.sh` - Docker compose FastAPI integration
- `debug-ipv6-server.sh` - Docker IPv6 configuration check
- `start-pi.sh` - Legacy Raspberry Pi startup script
- `detect-sdr-devices.sh` - Legacy SDR detection

## Important Notes

⚠️ **These scripts will NOT work on bare-metal deployments**

For bare-metal systems, use:
- `scripts/collect_sdr_diagnostics.sh` - Bare-metal SDR diagnostics
- `systemctl` commands - Service management
- `journalctl` commands - Log viewing

## Removal from ISO

This directory is excluded from ISO builds to reduce image size and avoid confusion.

---

**Do not use these scripts in production bare-metal deployments.**
