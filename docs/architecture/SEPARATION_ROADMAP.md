# EAS Station - Container Separation Roadmap

**Status**: In Progress
**Last Updated**: 2025-12-02
**Goal**: Eliminate all monolithic patterns and achieve full service separation

---

## Current Architecture Status

### ✅ Already Separated (Working)

| Service | Container | Hardware Access | Status |
|---------|-----------|----------------|--------|
| **SDR Management** | `sdr-service` | `/dev/bus/usb` (USB SDR devices) | ✅ Complete |
| **Audio Processing** | `audio-service` | None (reads from Redis) | ⚠️ Fixed today (was broken) |
| **Hardware Control** | `hardware-service` | GPIO, I2C, Serial ports | ✅ Complete |
| **Web UI** | `app` | None | ✅ Complete |
| **NOAA Polling** | `noaa-poller` | None | ✅ Complete |
| **IPAWS Polling** | `ipaws-poller` | None | ✅ Complete |
| **Audio Streaming** | `icecast` | None | ✅ Complete |
| **Reverse Proxy** | `nginx` | None | ✅ Complete |

### 🔴 CRITICAL ISSUES (Breaking Functionality)

## 1. RadioManager Control from App Container

**Status**: ❌ BROKEN
**Severity**: 🔴 Critical
**Files**: `webapp/routes_settings_radio.py`

**Problem**:
- App container tries to directly access `RadioManager` object
- RadioManager only exists in `sdr-service` container
- 11 references to `get_radio_manager()` in webapp code

**Broken Features**:
- ❌ Restart receiver button (line 727)
- ❌ Live spectrum/waterfall from settings page (line 1246)
- ⚠️ Some operations fail silently with defensive error handling

**Current Workaround**: Status display now uses Redis (✅ fixed)

**Solution Options**:

### Option A: Control API in SDR-Service (Recommended)
Create HTTP API in sdr-service for receiver control:

```python
# sdr_service.py - Add Flask endpoints
@app.route('/api/receiver/<identifier>/restart', methods=['POST'])
def restart_receiver(identifier):
    receiver = radio_manager.get_receiver(identifier)
    if receiver:
        receiver.stop()
        time.sleep(0.5)
        receiver.start()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Not found"}), 404
```

### Option B: Redis Command Queue (Current Partial Implementation)
Already implemented in sdr_service.py:458 (`process_commands`)

```python
# webapp -> Redis
redis.lpush("sdr:commands", json.dumps({
    "action": "restart",
    "receiver_id": identifier,
    "command_id": str(uuid.uuid4())
}))

# Wait for response
result = redis.get(f"sdr:command_result:{command_id}")
```

**Recommendation**: Complete Option B (Redis queue) - already 80% done!

---

## 2. Network Management in App Container

**Status**: ❌ BROKEN
**Severity**: 🔴 Critical
**File**: `webapp/admin/network.py`

**Problem**:
- Runs `nmcli` commands to control host WiFi
- App container has no `network_mode: host`
- App container can't see or control host network interfaces

**Broken Features**:
- ❌ WiFi scanning and connection
- ❌ Network status display
- ❌ Ethernet configuration

**Current State**: All network management UI is non-functional

**Solution**: Move to hardware-service OR create proxy API

### Option A: Move to hardware-service
```yaml
# hardware-service already has network capabilities
hardware-service:
  cap_add:
    - NET_ADMIN  # ✅ Already has this!
```

### Option B: Expose via hardware-service API
```python
# hardware_service.py - Add network endpoints
@app.route('/api/network/wifi/scan', methods=['POST'])
def scan_wifi():
    result = subprocess.run(['nmcli', 'dev', 'wifi', 'rescan'], ...)
    return jsonify({"success": True})

# webapp/admin/network.py - Call API
response = requests.post('http://hardware-service:5001/api/network/wifi/scan')
```

**Recommendation**: Option B - Keep hardware-service as network proxy

---

## 3. Zigbee Management in App Container

**Status**: ❌ BROKEN
**Severity**: 🔴 Critical
**File**: `webapp/admin/zigbee.py`

**Problem**:
- Tries to access `/dev/ttyAMA0` and `/dev/ttyUSB0`
- Serial devices mapped to `hardware-service`, not `app`

**Broken Features**:
- ❌ Zigbee coordinator management
- ❌ Device listing
- ❌ Device pairing

**Solution**: Create Zigbee proxy API in hardware-service

```python
# hardware_service.py - Add Zigbee endpoints
@app.route('/api/zigbee/devices', methods=['GET'])
def list_zigbee_devices():
    # Access serial port from hardware-service
    devices = zigbee_controller.list_devices()
    return jsonify({"devices": devices})
```

**Recommendation**: Implement Zigbee API proxy

---

## 4. Audio-Service Starting Receivers

**Status**: ✅ FIXED TODAY
**Severity**: 🔴 Critical (was causing AirSpy errors)
**File**: `audio_service.py:219`

**Problem**: Both sdr-service AND audio-service tried to open same SDR device

**Fix Applied**:
```python
# OLD CODE (line 219)
radio_manager.start_all()  # ❌ Tried to open hardware!

# NEW CODE
# DO NOT start receivers here - that's sdr-service's responsibility!
logger.info("⚠️  Audio service does NOT start receivers")
```

**Result**: Device conflict resolved ✅

---

## 🟡 WARNING ISSUES (Degraded Functionality)

## 5. Localhost Hardcoding

**Severity**: 🟡 Warning
**Files**:
- `webapp/routes_diagnostics.py:278` - `http://localhost/health/dependencies`
- `webapp/routes_backups.py:94` - `--host localhost --port 8080`

**Problem**: Services in different containers, `localhost` doesn't work

**Fix**: Use Docker service names
```python
# WRONG
url = "http://localhost:5000/health"

# RIGHT
url = "http://app:5000/health"
```

---

## 6. Host System Commands in App Container

**Severity**: 🟡 Warning
**Count**: 17 subprocess calls in webapp

**Problem**: Commands run in container, not on host

**Examples**:
```python
# webapp/admin/maintenance.py:184
subprocess.run(["apt-get", "update"])  # Updates container, not host!

# webapp/routes_diagnostics.py
subprocess.run(["systemctl", "status", "docker"])  # No systemd in container!
```

**Impact**: System maintenance features don't work as expected

**Solution**: Create maintenance API in a privileged service or disable these features

---

## 🟢 INFO / FUTURE IMPROVEMENTS

## 7. Metrics Key Mismatch (Minor)

**Files**:
- `sdr_service.py` publishes to `sdr:metrics`
- `audio_service.py` publishes to `eas:metrics`
- `webapp/routes_settings_radio.py` reads from `eas:metrics`

**Current Status**: Works (audio-service is bridge), but confusing

**Recommendation**: Standardize on one key name

---

## SEPARATION PRINCIPLES

### ✅ Good Patterns

```python
# 1. Use Redis for state sharing
redis = get_redis_client()
status = redis.get("sdr:receiver:wxj93:status")

# 2. Use HTTP APIs between services
response = requests.post("http://hardware-service:5001/api/gpio/relay/1/on")

# 3. Use Docker service names
DATABASE_HOST = os.getenv("POSTGRES_HOST", "alerts-db")

# 4. Graceful degradation
try:
    redis_status = get_status_from_redis()
except:
    db_status = get_status_from_database()
```

### ❌ Anti-Patterns

```python
# 1. Direct object access across containers
radio_manager = get_radio_manager()  # Only works in sdr-service!

# 2. Localhost assumptions
url = "http://localhost:8000"  # Won't work between containers

# 3. Host system commands
subprocess.run(["nmcli", "dev", "wifi"])  # Container can't control host

# 4. Device path assumptions
with open("/dev/ttyUSB0") as f:  # Not mapped to this container
```

---

## IMPLEMENTATION PRIORITIES

### Phase 1: Critical Fixes (Week 1)
- [x] Fix audio-service receiver conflict ✅ DONE TODAY
- [ ] Complete Redis command queue for receiver control
- [ ] Create network management proxy API
- [ ] Create Zigbee proxy API in hardware-service

### Phase 2: Warning Issues (Week 2-3)
- [ ] Replace localhost with container names
- [ ] Add container awareness to subprocess commands
- [ ] Improve Redis error handling throughout

### Phase 3: Documentation & Testing (Week 4)
- [ ] Update architecture diagrams
- [ ] Write integration tests
- [ ] Create developer guide for separated architecture
- [ ] Add E2E tests for cross-container communication

---

## TESTING CHECKLIST

After each fix, verify:

- [ ] Feature works from web UI
- [ ] No errors in container logs
- [ ] Cross-container communication working
- [ ] Graceful degradation if service fails
- [ ] No localhost references
- [ ] No direct object access

---

## CONTAINER RESPONSIBILITY MATRIX

| Responsibility | Container | Communication Method |
|----------------|-----------|---------------------|
| SDR Hardware | `sdr-service` | Redis pub/sub |
| Audio Processing | `audio-service` | Redis pub/sub |
| GPIO/Relays | `hardware-service` | HTTP API (port 5001) |
| Network Config | `hardware-service` | HTTP API (port 5001) |
| Zigbee Control | `hardware-service` | HTTP API (port 5001) |
| Database | `alerts-db` | PostgreSQL protocol |
| Cache/IPC | `redis` | Redis protocol |
| Audio Streaming | `icecast` | Icecast protocol |
| Web UI | `app` | HTTP (internal port 5000) |
| HTTPS | `nginx` | Reverse proxy |

---

## SUCCESS CRITERIA

The separation is complete when:

1. ✅ Each container has a single, clear responsibility
2. ✅ No container directly accesses another container's objects
3. ✅ All cross-container communication via Redis or HTTP APIs
4. ✅ No localhost references
5. ✅ Hardware access isolated to specific containers
6. ✅ All features working from web UI
7. ✅ Graceful degradation when services fail
8. ✅ Integration tests passing

---

**Next Actions**:
1. Complete Redis command queue implementation (80% done)
2. Create hardware-service API endpoints for network & Zigbee
3. Update webapp to use APIs instead of direct access
4. Write integration tests

**Estimated Effort**: 2-3 weeks for full completion
