# SDR Architecture Refactoring Plan

## Current Architecture Problems

### Monolithic Service Design

The current containerized architecture has a **design inconsistency** that creates confusion and maintenance issues:

**Current State:**
- `audio_service.py` is a **monolithic service** that handles:
  1. SDR/Radio hardware (SoapySDR receiver initialization)
  2. Audio ingestion from all sources (SDR, streams, files)
  3. EAS monitoring and SAME decoding
  4. Icecast streaming
  5. Metrics publishing to Redis

**What Should Happen:**
- SDR hardware management should run in `sdr-service` container
- Audio processing should run in a separate `audio-service` container
- Each service should have a single, well-defined responsibility

**Why This Matters:**
1. **Confusion**: Service names don't match their actual function
2. **Resource Allocation**: Can't independently scale SDR vs audio processing
3. **Hardware Access**: The sdr-service needs both USB (for SDR) and potentially audio devices
4. **Debugging**: Logs are mixed, making troubleshooting harder
5. **Deployment**: Can't deploy SDR-only or audio-only services independently

### File Structure Inconsistency

**Two SDR Service Implementations:**
1. `/home/user/eas-station/audio_service.py` - **Currently used** by sdr-service (monolithic)
2. `/home/user/eas-station/sdr_service.py` - Standalone SDR-only service (**not used**)

This creates confusion about which file should be maintained and which architecture is intended.

## Impact of Containerization

### What Changed
After moving to separate containers, several integrations broke:

#### 1. **NVMe Health Monitoring** ❌ BROKEN
- **Problem**: `app` container has no access to `/dev/nvme*` devices
- **Impact**: System health page cannot display NVMe SMART data

#### 2. **VFD Display** ❌ POTENTIALLY BROKEN
- **Problem**: `hardware-service` missing `/dev/ttyUSB0` mount
- **Impact**: VFD display cannot be accessed even if enabled
- **Fix Applied**: Added `/dev/ttyUSB0` and `/dev/ttyAMA0` mounts to hardware-service

#### 3. **SDR Audio Chain** ⚠️ WORKS BUT WRONG
- **Problem**: Everything runs in one container (`sdr-service` → `audio_service.py`)
- **Impact**: No separation of concerns, can't independently manage services
- **Fix Needed**: Refactor to separate SDR and audio concerns

## Proposed Architecture

### Service Separation

```
┌─────────────────────┐
│   sdr-service       │
│  (sdr_service.py)   │
│                     │
│ - SoapySDR Init    │
│ - Hardware Mgmt    │
│ - IQ Sample Acq    │
│ - Publish to Redis │
└──────────┬──────────┘
           │ IQ samples
           │ via Redis
           ▼
┌─────────────────────┐
│  audio-service      │
│ (audio_service.py)  │
│                     │
│ - Read IQ from     │
│   Redis            │
│ - Demodulation     │
│ - Audio Routing    │
│ - EAS Monitoring   │
│ - SAME Decoding    │
│ - Icecast Stream   │
└─────────────────────┘
```

### Container Configuration

#### sdr-service
**Purpose**: SDR hardware management and IQ sample acquisition
**Command**: `python sdr_service.py`
**Hardware Access**:
- `/dev/bus/usb:/dev/bus/usb` (USB SDR devices)
- `privileged: true` (for USB DMA)
- `ulimits: memlock: -1` (USB buffer locking)

**Responsibilities**:
- Initialize SoapySDR receivers
- Configure radio parameters (frequency, gain, sample rate)
- Acquire IQ samples from SDR hardware
- Publish raw IQ samples to Redis streams
- Monitor SDR hardware health
- Handle device reconnection

**Metrics Published**:
- `eas:sdr:receiver:{id}:status` - Receiver status (running, error, etc.)
- `eas:sdr:receiver:{id}:metrics` - Sample rate, frequency, gain
- `eas:sdr:iq:{id}` - Redis stream of IQ samples

#### audio-service
**Purpose**: Audio processing and EAS monitoring
**Command**: `python audio_service.py`
**Hardware Access**: None (accesses audio via Redis)

**Responsibilities**:
- Subscribe to IQ sample Redis streams
- Demodulate RF to audio
- Audio ingestion from all sources (SDR, HTTP streams, files)
- Route audio to outputs (local, Icecast)
- EAS SAME monitoring and decoding
- Alert processing and storage
- Audio metrics publishing

**Metrics Published**:
- `eas:audio:source:{id}:level` - Audio levels
- `eas:audio:source:{id}:status` - Source health
- `eas:broadcast:queue` - Current broadcast queue
- `eas:eas:last_same` - Last SAME message decoded

## Migration Strategy

### Phase 1: Create Separate Services (No Breaking Changes)

**Goal**: Establish infrastructure for separated architecture while maintaining current functionality.

**Tasks**:
1. ✅ Keep `sdr-service` running `audio_service.py` (current state)
3. Have both services running in parallel
4. Update documentation to reflect intended vs actual state

```yaml
audio-service:
  image: eas-station:latest
  container_name: eas-audio-service
  restart: unless-stopped
  networks:
    - eas-network
  command: ["python", "audio_service.py"]
  volumes:
    - app-config:/app-config
  environment:
    # Same as sdr-service but without SDR-specific vars
    POSTGRES_HOST: ${POSTGRES_HOST:-alerts-db}
    REDIS_HOST: ${REDIS_HOST:-redis}
    # ...
  # NO USB device access
  # NO privileged mode
  depends_on:
    redis:
      condition: service_healthy
```

**Status**: Not yet implemented - needs user decision on migration approach

### Phase 2: Refactor sdr_service.py (Breaking Changes)

**Goal**: Implement proper SDR-only service.

**Tasks**:
1. Update `sdr_service.py` to:
   - Initialize SoapySDR receivers only
   - Publish IQ samples to Redis streams
   - Remove audio processing logic
   - Remove EAS monitoring
   - Remove Icecast streaming

2. Update `audio_service.py` to:
   - Subscribe to Redis IQ streams
   - Add IQ demodulation (currently done inline)
   - Keep all current audio/EAS logic

3. Update `sdr-service` container:
   ```yaml
   sdr-service:
     command: ["python", "sdr_service.py"]  # Change from audio_service.py
   ```

**Status**: Planned - requires Phase 1 completion

### Phase 3: Testing and Validation

**Goal**: Ensure separated architecture works correctly.

**Tests**:
1. SDR hardware initialization and IQ acquisition
2. IQ stream publishing to Redis
3. Audio service IQ subscription and demodulation
4. EAS SAME decoding from demodulated audio
5. Icecast streaming functionality
6. Alert processing and storage
7. Metrics publishing from both services
8. Service restart/recovery behavior

**Status**: Planned - requires Phase 2 completion

### Phase 4: Deprecation

**Goal**: Remove old monolithic code paths.

**Tasks**:
1. Remove audio logic from `sdr_service.py` (if any remains)
2. Remove SDR hardware logic from `audio_service.py`
3. Update all documentation
4. Add migration notes to CHANGELOG

**Status**: Planned - requires Phase 3 validation

## Benefits of Refactoring

### Operational Benefits

1. **Independent Scaling**
   - Scale audio processing separately from SDR acquisition
   - Run multiple audio processors for different outputs
   - Optimize resource allocation per service

2. **Better Debugging**
   - Isolated logs per service
   - Clear responsibility boundaries
   - Easier to identify which service has issues

3. **Flexible Deployment**
   - Run SDR service on hardware with USB devices
   - Run audio service anywhere (cloud, different host)
   - Enable/disable services independently

4. **Hardware Isolation**
   - Only SDR service needs privileged mode
   - Reduced security surface for audio processing
   - Better permission management

### Development Benefits

1. **Code Clarity**
   - File names match service responsibilities
   - Easier onboarding for new developers
   - Clear architectural boundaries

2. **Testing**
   - Mock IQ streams for audio service testing
   - Test SDR without audio processing
   - Independent integration tests

3. **Maintenance**
   - Update audio logic without touching SDR code
   - Upgrade SDR drivers without audio service changes
   - Reduced merge conflicts

## Risk Assessment

### Low Risk
- ✅ NVMe health fix (read-only mount)
- ✅ VFD/Zigbee serial port mounts (hardware-service only)
- ✅ WiFi/Zigbee UI additions (new features, no changes to existing)

### Medium Risk
- ⚠️ Phase 1 (parallel services, doubled resource usage temporarily)
- ⚠️ IQ stream design (buffer size, latency, throughput)

### High Risk
- 🔴 Phase 2 (breaking changes to SDR/audio interface)
- 🔴 IQ demodulation (audio quality, decoding accuracy)
- 🔴 Service coordination (startup order, failure recovery)

## Recommendations

### Immediate Actions (Low Risk)
1. ✅ **DONE**: Fix NVMe health with `/dev:/dev:ro` mount
2. ✅ **DONE**: Fix VFD/Zigbee serial ports
3. ✅ **DONE**: Add WiFi configuration UI
4. ✅ **DONE**: Add Zigbee monitoring UI

### Short Term (Medium Risk)
1. **Document current architecture** ✅ (this document)
2. **Add architecture diagrams** to docs/
3. **Create IQ stream interface design** document
4. **Prototype IQ streaming** with Redis streams
5. **Benchmark IQ throughput** (can Redis handle sample rate?)

### Long Term (High Risk - User Decision Required)
1. **Phase 1**: Run parallel services
2. **Phase 2**: Implement separated SDR/audio services
3. **Phase 3**: Full testing and validation
4. **Phase 4**: Deprecate monolithic approach

## Decision Required

**Question for User**:

Do you want to proceed with the SDR/audio separation refactoring now, or keep it as-is for the moment?

**Option A - Refactor Now**:
- Pros: Clean architecture, better maintainability
- Cons: Breaking changes, testing required, potential bugs
- Timeline: 2-3 development sessions

**Option B - Keep As-Is**:
- Pros: No breaking changes, current functionality preserved
- Cons: Technical debt remains, confusing architecture
- Timeline: Document and revisit later

**Option C - Hybrid**:
- Implement Phase 1 (parallel services) only
- Validate approach before committing to full refactor
- Provides fallback option

## Current Status

**Completed**:
- ✅ WiFi configuration API and UI
- ✅ Zigbee monitoring API and UI
- ✅ Documentation of SDR architecture issues

**Pending User Decision**:
- SDR/audio separation refactoring approach
- Timeline for implementation
- Risk tolerance for breaking changes

**Next Steps After User Decision**:
1. If refactoring approved: Begin Phase 1 implementation
2. If deferred: Document decision and create GitHub issue for future work
3. Either way: Commit current fixes and new features

## References

### Key Files
- `/home/user/eas-station/audio_service.py` - Current monolithic service
- `/home/user/eas-station/sdr_service.py` - Unused SDR-only service
- `/home/user/eas-station/hardware_service.py` - GPIO/Display/Zigbee service

### Related Issues
- Smart display (NVMe) broken after containerization - **FIXED**
- VFD display not accessible - **FIXED**
- WiFi configuration needed - **IMPLEMENTED**
- Zigbee feedback needed - **IMPLEMENTED**
- SDR architecture confusion - **DOCUMENTED, PENDING DECISION**
