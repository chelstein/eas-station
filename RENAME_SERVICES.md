# Service Renaming Guide

## Current Confusing Names

The current service names are historical and confusing:

| Current Name      | What It Actually Does                          | Suggested New Name           |
|-------------------|------------------------------------------------|------------------------------|
| `audio_service.py`| Audio demodulation + EAS monitoring (NO SDR!)  | `eas_monitoring_service.py`  |
| `sdr_service.py`  | SDR hardware access + IQ sample publishing     | `sdr_hardware_service.py`    |

## The Problem

**`audio_service.py` suggests it handles "audio" but:**
- Does NOT access SDR hardware or audio devices
- Does NOT capture raw audio
- ONLY processes IQ samples from Redis
- Primary job is EAS/SAME monitoring

**This causes confusion:**
- Developers assume it accesses SDR hardware (it doesn't)
- USB device conflicts when both services tried to access SDR
- Unclear separation of responsibilities

## Proposed Rename

### Option 1: Functional Names (Recommended)
```
audio_service.py      →  eas_monitoring_service.py
sdr_service.py        →  sdr_hardware_service.py
```

### Option 2: Layer Names
```
audio_service.py      →  audio_processing_service.py
sdr_service.py        →  radio_capture_service.py
```

## Implementation Steps

### 1. Create New Files
```bash
# Copy to new names
cp audio_service.py eas_monitoring_service.py
cp sdr_service.py sdr_hardware_service.py
```

### 2. Update docker-compose.yml
```yaml
# Before
sdr-service:
  command: ["python", "sdr_service.py"]

audio-service:
  command: ["python3", "audio_service.py"]

# After
sdr-hardware-service:  # or keep sdr-service
  command: ["python", "sdr_hardware_service.py"]

eas-monitoring-service:  # clearer!
  command: ["python3", "eas_monitoring_service.py"]
```

### 3. Update Documentation
- Update all references in docs/
- Update README.md
- Update SYSTEM_ARCHITECTURE.md diagrams
- Update container names in deployment guides

### 4. Backward Compatibility
Keep old files as symlinks or wrappers:
```python
#!/usr/bin/env python3
# audio_service.py - DEPRECATED, use eas_monitoring_service.py
import sys
import warnings
warnings.warn(
    "audio_service.py is deprecated. Use eas_monitoring_service.py instead.",
    DeprecationWarning
)
from eas_monitoring_service import main
if __name__ == "__main__":
    sys.exit(main())
```

## Benefits

1. **Clear Responsibilities**: Names match what services actually do
2. **Prevents Confusion**: No more assuming audio_service touches hardware
3. **Better Documentation**: Architecture diagrams make sense
4. **Easier Debugging**: Log files immediately show which layer has issues

## Timeline

- **Phase 1** (Immediate): Update documentation to clarify current names
- **Phase 2** (v2.16.0): Create new filenames, update docker-compose
- **Phase 3** (v2.17.0): Deprecate old names with warnings
- **Phase 4** (v3.0.0): Remove old names entirely

## Current Status

- [x] Documentation updated in audio_service.py header
- [x] USB access verified exclusive to sdr-service
- [x] All SDR hardware code removed from audio_service.py
- [ ] Create rename plan (this document)
- [ ] Implement rename in v2.16.0
