# Complete Hardware Isolation Architecture

## Problem

Previously, hardware access was scattered across multiple services, causing:
- **USB contention** - Multiple processes trying to access the same SDR device
- **Fault propagation** - SDR crashes affecting displays, GPIO crashes affecting audio
- **Unclear ownership** - Multiple services with overlapping hardware access
- **Difficult debugging** - Hardware failures cascading across services

## Solution: Complete Hardware Isolation

### **Three-Layer Hardware Architecture**

```mermaid
graph TB
    subgraph USB["🔌 USB Hardware Layer"]
        SDR[sdr-service<br/>SDR ONLY]
        style SDR fill:#e1f5ff
    end

    subgraph GPIO["⚡ GPIO/Display Hardware Layer"]
        HW[hardware-service<br/>GPIO/OLED/Zigbee]
        style HW fill:#fff3e0
    end

    subgraph APP["🌐 Application Layer"]
        Web[app<br/>Web UI Only]
        Poller1[noaa-poller<br/>HTTP Only]
        Poller2[ipaws-poller<br/>HTTP Only]
        style Web fill:#e8f5e9
        style Poller1 fill:#e8f5e9
        style Poller2 fill:#e8f5e9
    end

    subgraph INFRA["📊 Infrastructure"]
        Redis[(Redis)]
        DB[(PostgreSQL)]
        Icecast[Icecast]
    end

    SDR -->|Audio Stream| Icecast
    SDR -->|Metrics| Redis
    HW -->|Status| Redis
    Web -->|Read Metrics| Redis
    Web -->|Config| DB
    Poller1 -->|Alerts| DB
    Poller2 -->|Alerts| DB

    Hardware1[/dev/bus/usb<br/>AirSpy, RTL-SDR/] -->|Exclusive| SDR
    Hardware2[/dev/gpiomem<br/>/dev/gpiochip0<br/>/dev/i2c-1/] -->|Exclusive| HW
    Hardware3[/dev:ro<br/>SMART Only/] -.->|Read-Only| Web

    style USB fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style GPIO fill:#fff8e1,stroke:#f57c00,stroke-width:2px
    style APP fill:#f1f8e9,stroke:#558b2f,stroke-width:2px
    style INFRA fill:#fce4ec,stroke:#c2185b,stroke-width:2px
```

**Fault Isolation Benefits:**
- 🔴 **SDR fails** → GPIO/displays keep working, web UI stays up
- 🟡 **Displays fail** → SDR keeps monitoring, audio keeps streaming
- 🟢 **Web UI fails** → All hardware continues running independently

---

## Service Responsibilities

### **sdr-service** (SDR + Audio)
**Hardware**: `/dev/bus/usb` only

**Purpose**: SDR hardware management and real-time audio processing

**Runs**: `audio_service.py` (systemd service)

**Handles**:
- SDR device initialization (AirSpy, RTL-SDR)
- IQ sample capture
- FM/NFM demodulation
- EAS/SAME decoding
- RBDS data extraction
- Icecast streaming
- Audio metrics publishing

**Why together**: Audio processing requires microsecond-latency access to SDR samples. Splitting them would add inter-process overhead and increase latency.

**Privileges**: Root access for USB device management

---

### **hardware-service** (GPIO + Displays + Zigbee)
**Hardware**: `/dev/gpiomem`, `/dev/gpiochip0`, `/dev/i2c-1`

**Purpose**: Local hardware control (non-SDR)

**Runs**: `hardware_service.py` (systemd service)

**Handles**:
- GPIO pin control (relays, transmitter PTT)
- OLED display rendering (128x64 SSD1306, etc.)
- LED matrix displays
- VFD displays
- Screen rotation and scheduling
- Zigbee coordinator management (if configured)
- Hardware status metrics

**Environment Variables**:
- `GPIO_ENABLED` - Enable/disable GPIO (default: false)
- `SCREENS_AUTO_START` - Auto-start screen rotation (default: true)

**Privileges**: Root access for GPIO/I2C device access on Pi 5

---

### **app** (Web UI)
**Hardware**: Read-only `/dev` access for SMART monitoring only

**Purpose**: User interface and configuration

**Runs**: Flask application (`app.py`) via systemd

**Handles**:
- Web routes and API endpoints
- User authentication
- Configuration management
- System dashboards
- SMART disk monitoring (read-only)
- Metrics aggregation from Redis

**NO direct hardware write access**

**Privileges**: Unprivileged service, runs as dedicated user

---

### **noaa-poller** / **ipaws-poller** (Alert Polling)
**Hardware**: None

**Purpose**: CAP XML feed polling

**Handles**:
- HTTP polling of NOAA/IPAWS feeds
- CAP XML parsing
- Alert database storage
- NO hardware access needed

**Privileges**: Unprivileged services

---

## Hardware Device Access

Works on all platforms (x86, ARM, Pi, etc.):

**sdr-service** - Configured via systemd unit file:
- Device access: `/dev/bus/usb` (USB SDR devices)
- Udev rules ensure proper permissions

**hardware-service** - Configured via systemd unit file:
- No hardware access in base config
- Works on all platforms with hardware features disabled

**app** - Configured via systemd unit file:
- No device access in base config

On Raspberry Pi, additional hardware is enabled:

**app**:
- Read-only `/dev` access for SMART monitoring

**hardware-service**:
- `/dev/gpiomem` - GPIO memory access
- `/dev/gpiochip0` - GPIO chip interface
- `/dev/i2c-1` - I2C bus for displays
- Environment: `GPIO_ENABLED=true`, `SCREENS_AUTO_START=true`

---

## Fault Isolation Benefits

### **SDR Failure Scenarios**
If `sdr-service` crashes or SDR device disconnects:
- ✅ GPIO relays continue working
- ✅ OLED displays continue updating
- ✅ Web UI remains accessible
- ✅ Alert polling continues
- 🔄 Systemd automatically restarts the service

### **Display Failure Scenarios**
If `hardware-service` crashes or display fails:
- ✅ SDR continues monitoring
- ✅ Audio continues streaming
- ✅ EAS decoding continues
- ✅ Web UI remains accessible
- 🔄 Systemd automatically restarts the service

### **Web UI Failure Scenarios**
If `app` service crashes:
- ✅ SDR continues monitoring
- ✅ Displays continue updating
- ✅ GPIO continues functioning
- ✅ Alert polling continues
- 🔄 Systemd automatically restarts the service

---

## Communication Architecture

### **Inter-Service Communication**

```mermaid
sequenceDiagram
    participant SDR as sdr-service
    participant HW as hardware-service
    participant Redis as Redis
    participant DB as PostgreSQL
    participant App as app (Web UI)
    participant Poller as CAP Pollers

    rect rgb(225, 245, 255)
    Note over SDR: SDR Metrics Publishing
    SDR->>Redis: Publish SDR metrics<br/>(sdr:metrics)
    SDR->>Redis: Signal strength, lock status
    end

    rect rgb(255, 243, 224)
    Note over HW: Hardware Status Publishing
    HW->>Redis: Publish hardware metrics<br/>(hardware:metrics)
    HW->>Redis: GPIO status, screen info
    end

    rect rgb(232, 245, 233)
    Note over App: Dashboard Updates
    App->>Redis: Read all metrics
    Redis-->>App: Combined status
    App->>DB: Read configuration
    end

    rect rgb(255, 243, 224)
    Note over App,HW: GPIO Control Flow
    App->>HW: HTTP API: Activate GPIO
    HW->>HW: Toggle relay
    HW->>Redis: Publish status update
    App->>Redis: Read updated status
    end

    rect rgb(252, 228, 236)
    Note over Poller: Alert Processing
    Poller->>Poller: Poll CAP XML
    Poller->>DB: Store alerts
    App->>DB: Read alerts
    end
```

### **Metrics Flow**
1. `sdr-service` publishes SDR metrics to Redis (`sdr:metrics`)
2. `hardware-service` publishes hardware metrics to Redis (`hardware:metrics`)
3. `app` reads all metrics from Redis for dashboards

### **Control Flow**
1. User clicks GPIO button in web UI
2. `app` sends HTTP request to `hardware-service` API
3. `hardware-service` activates GPIO pin
4. Status published back via Redis

---

## Migration Guide

### From Old Architecture

```mermaid
graph LR
    subgraph OLD["❌ Old Architecture (Hardware Conflicts)"]
        direction TB
        A1[audio-service<br/>USB + GPIO + Screens]
        A2[noaa-poller<br/>USB + GPIO]
        A3[ipaws-poller<br/>USB + GPIO]
        A4[app<br/>GPIO]

        style A1 fill:#ffcdd2
        style A2 fill:#ffcdd2
        style A3 fill:#ffcdd2
        style A4 fill:#ffcdd2
    end

    subgraph NEW["✅ New Architecture (Isolated)"]
        direction TB
        B1[sdr-service<br/>USB ONLY]
        B2[hardware-service<br/>GPIO/Displays ONLY]
        B3[app<br/>Web UI Only]
        B4[pollers<br/>NO hardware]

        style B1 fill:#c8e6c9
        style B2 fill:#fff9c4
        style B3 fill:#b3e5fc
        style B4 fill:#b3e5fc
    end

    OLD -.->|Migration| NEW

    style OLD fill:#ffebee,stroke:#c62828,stroke-width:2px
    style NEW fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
```

**Before**: Multiple services fighting over USB and GPIO → **Device contention**
**After**: Each service has exclusive hardware access → **Zero contention**

### Deployment Steps

1. **Pull latest code**:
```bash
git pull origin main
```

2. **Stop all services**:
```bash
sudo systemctl stop eas-station.target
```

3. **Deploy with new architecture**:
```bash
# Run the installation script
sudo ./install.sh
```

4. **Verify isolation**:
```bash
# Check sdr-service has USB access
sudo systemctl status sdr-service

# Check hardware-service has GPIO (Pi only)
sudo systemctl status hardware-service

# Check app service status
sudo systemctl status eas-app
```

---

## Troubleshooting

### SDR Not Working
**Check**: Only `sdr-service` should have `/dev/bus/usb` access

```bash
# Check service status
sudo systemctl status sdr-service

# View service logs
sudo journalctl -u sdr-service -n 50
```

### GPIO/Displays Not Working
**Check**: Only `hardware-service` should have GPIO access

```bash
# Check service status (Pi only)
sudo systemctl status hardware-service

# View service logs
sudo journalctl -u hardware-service -n 50
```

### SMART Monitoring Not Working
**Check**: `app` service needs read-only `/dev` access

```bash
# Check service status
sudo systemctl status eas-app

# View service logs
sudo journalctl -u eas-app -n 50
```

---

## Security Benefits

### Principle of Least Privilege
- **sdr-service**: Only USB access, no GPIO
- **hardware-service**: Only GPIO/I2C, no USB
- **app**: Read-only device access, no write access
- **pollers**: Zero hardware access

### Attack Surface Reduction
- USB exploits contained to `sdr-service`
- GPIO exploits contained to `hardware-service`
- Web vulnerabilities can't access hardware directly
- Each service runs independently with systemd isolation
- Services can be restarted without affecting others

### Audit Trail
- Clear hardware ownership per service
- Isolated logs per service via journalctl
- Easy to trace hardware operations
- Systemd provides process tracking and resource limits

---

## Files Changed

- `hardware_service.py` - New dedicated hardware service
- `sdr_service.py` - Optional standalone SDR entrypoint
- `docs/architecture/SDR_SERVICE_ISOLATION.md` - SDR-specific documentation
- `docs/architecture/HARDWARE_ISOLATION.md` - This document

---

## Related Documentation

- [SDR Service Isolation](SDR_SERVICE_ISOLATION.md) - USB/SDR-specific isolation
- [System Architecture](SYSTEM_ARCHITECTURE.md) - Overall system design
- [SDR Setup Guide](../hardware/SDR_SETUP.md) - SDR hardware configuration
- [GPIO Configuration](../hardware/GPIO_SETUP.md) - GPIO setup guide

---

## Summary

**Complete hardware isolation achieved via systemd services:**
- ✅ SDR isolated to `sdr-service`
- ✅ GPIO/displays isolated to `hardware-service`
- ✅ Web UI has zero hardware write access
- ✅ Pollers have zero hardware access
- ✅ Each service can fail independently
- ✅ Clear fault boundaries
- ✅ Better security posture
- ✅ Easier debugging with journalctl
- ✅ Systemd provides automatic restart and resource management
