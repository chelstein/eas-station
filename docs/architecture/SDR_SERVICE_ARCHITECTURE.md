# SDR Service Architecture

## Overview

The EAS Station uses a **dual-service architecture** for SDR (Software Defined Radio) operations to ensure reliable 24/7 operation required for life-safety systems. This document describes the architecture, components, and operational details.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HOST SYSTEM                                        │
│  ┌─────────────────┐                                                        │
│  │  USB SDR Device │  (Airspy R2, RTL-SDR, etc.)                           │
│  │  /dev/bus/usb   │                                                        │
│  └────────┬────────┘                                                        │
└───────────┼─────────────────────────────────────────────────────────────────┘
            │ USB passthrough
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SDR SERVICE CONTAINER                                    │
│                     (sdr_service.py)                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    Dual-Thread Architecture                           │  │
│  │                                                                       │  │
│  │  ┌─────────────────┐        ┌─────────────────┐                      │  │
│  │  │ USB Reader      │        │ Ring Buffer     │                      │  │
│  │  │ Thread          │───────▶│ (1 second)      │                      │  │
│  │  │                 │        │                 │                      │  │
│  │  │ • readStream()  │        │ • Lock-free     │                      │  │
│  │  │ • Never blocks  │        │ • Overflow      │                      │  │
│  │  │ • 100ms timeout │        │   detection     │                      │  │
│  │  └─────────────────┘        └────────┬────────┘                      │  │
│  │                                      │                                │  │
│  │                                      ▼                                │  │
│  │                          ┌─────────────────────┐                      │  │
│  │                          │ Publisher Thread    │                      │  │
│  │                          │                     │                      │  │
│  │                          │ • FFT/Spectrum      │                      │  │
│  │                          │ • Sample encoding   │                      │  │
│  │                          │ • Redis publish     │                      │  │
│  │                          └──────────┬──────────┘                      │  │
│  └──────────────────────────────────────┼───────────────────────────────┘  │
│                                         │                                   │
│  Privileges:                            │                                   │
│  • privileged: true                     │                                   │
│  • USB device access                    │                                   │
│  • Unlimited locked memory              │                                   │
│  • 256MB shared memory                  │                                   │
└─────────────────────────────────────────┼───────────────────────────────────┘
                                          │ Redis pub/sub
                                          │ (zlib compressed, base64 encoded)
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          REDIS                                               │
│                                                                              │
│  Channels:                               Keys:                               │
│  • sdr:samples:{receiver_id}             • sdr:metrics (health data)        │
│                                          • sdr:spectrum:{id} (waterfall)    │
│                                          • sdr:ring_buffer:{id} (stats)     │
│                                          • sdr:heartbeat                     │
│                                          • sdr:commands (control queue)      │
│                                          • sdr:command_result:{id}           │
└─────────────────────────────────────────┬───────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     AUDIO SERVICE CONTAINER                                  │
│                     (audio_service.py)                                      │
│                                                                              │
│  No USB access required - receives samples via Redis                         │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ Demodulation    │  │ EAS/SAME        │  │ Icecast         │             │
│  │ (FM, AM, etc.)  │──│ Decoder         │──│ Streaming       │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. SDR Service (`sdr_service.py`)

**Purpose:** Dedicated service for SDR hardware operations only.

**Responsibilities:**
- SoapySDR device management (open, configure, stream)
- Dual-thread USB reading for jitter absorption
- IQ sample publishing to Redis
- Health metrics publishing
- Control command processing

**Container Requirements:**
```yaml
sdr-service:
  command: ["python", "sdr_service.py"]
  devices:
    - /dev/bus/usb:/dev/bus/usb
  privileged: true
  cap_add:
    - SYS_RAWIO
    - SYS_ADMIN
  ulimits:
    memlock:
      soft: -1
      hard: -1
  shm_size: '256mb'
```

### 2. Ring Buffer (`app_core/radio/ring_buffer.py`)

**Purpose:** Lock-free buffer for USB jitter absorption.

**Features:**
- Single producer, single consumer (SPSC) design
- 1-second buffer capacity (configurable)
- Overflow/underflow detection
- Health statistics

**Configuration:**
```python
# Buffer sizing
MIN_SIZE = 262144   # ~0.1s at 2.5 MHz
MAX_SIZE = 4194304  # ~1.6s at 2.5 MHz

# Default: 1 second of buffer
buffer_size = sample_rate * 1.0
```

### 3. Dual-Thread Architecture (`app_core/radio/dual_thread.py`)

**Purpose:** Separate USB reading from processing.

**Threads:**
1. **USB Reader Thread (Producer)**
   - Only calls `readStream()`
   - Never blocks on processing
   - 100ms read timeout
   - Writes directly to ring buffer

2. **Processing Thread (Consumer)**
   - Reads from ring buffer
   - FFT computation
   - Signal strength calculation
   - Audio sample buffer updates

### 4. Audio Service (`audio_service.py`)

**Purpose:** Audio processing and EAS decoding.

**Responsibilities:**
- Subscribe to SDR sample channels
- Demodulation (FM, AM, etc.)
- EAS/SAME header detection
- Icecast streaming output
- Web audio streaming

**Container Requirements:**
- No USB access needed
- Standard container privileges
- Redis connectivity only

## Redis Data Flow

### Sample Publishing

```
Channel: sdr:samples:{receiver_id}
Format: JSON with zlib+base64 encoded samples

{
  "receiver_id": "noaa-1",
  "timestamp": 1701532800.123,
  "sample_count": 32768,
  "sample_rate": 2500000,
  "center_frequency": 162550000,
  "encoding": "zlib+base64",
  "samples": "<base64 encoded zlib compressed interleaved float32>"
}
```

### Spectrum Data (Waterfall)

```
Key: sdr:spectrum:{receiver_id}
TTL: 5 seconds

{
  "identifier": "noaa-1",
  "spectrum": [0.1, 0.2, ...],  // Normalized 0-1
  "fft_size": 2048,
  "sample_rate": 2500000,
  "center_frequency": 162550000,
  "timestamp": 1701532800.123,
  "status": "available"
}
```

### Health Metrics

```
Key: sdr:metrics
TTL: 30 seconds

{
  "service": "sdr_service",
  "timestamp": 1701532800.123,
  "pid": 12345,
  "receivers": {
    "noaa-1": {
      "running": true,
      "locked": true,
      "signal_strength": 0.42,
      "frequency_hz": 162550000,
      "sample_rate": 2500000,
      "ring_buffer": {
        "fill_percentage": 25.5,
        "overflow_count": 0
      }
    }
  }
}
```

### Control Commands

```
Queue: sdr:commands (LPUSH/LPOP)

{
  "action": "restart",  // restart, stop, start
  "receiver_id": "noaa-1",
  "command_id": "cmd-12345"
}

Result: sdr:command_result:{command_id}
TTL: 30 seconds

{
  "command_id": "cmd-12345",
  "success": true,
  "message": "Receiver noaa-1 restarted"
}
```

## Benefits of Separation

### Fault Isolation
- SDR crashes don't affect audio processing
- Audio crashes don't affect SDR streaming
- Either service can be restarted independently

### Security
- USB privileges isolated to SDR container only
- Audio processing runs with minimal privileges
- Reduced attack surface

### Performance
- USB reading never blocked by FFT or encoding
- Ring buffer absorbs USB latency jitter
- Processing can run on different CPU cores

### Scalability
- SDR service can run on dedicated hardware
- Audio processing can be distributed
- Multiple audio consumers can subscribe

## Configuration

### Environment Variables

```bash
# Redis Connection
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Database Connection
POSTGRES_HOST=alerts-db
POSTGRES_PORT=5432
POSTGRES_DB=alerts
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<secure_password>

# SDR Settings
SDR_ARGS=driver=airspy

# Application Config
CONFIG_PATH=/app-config/.env
```

### Docker Compose Files

| File | Description |
|------|-------------|
| `docker-compose.yml` | Standard deployment with external database |
| `docker-compose.embedded-db.yml` | Standalone with embedded PostgreSQL |
| `docker-compose.separated.yml` | Documentation of separated architecture |
| `docker-compose.pi.yml` | Raspberry Pi hardware overlay |

## Troubleshooting

### SDR Service Not Starting

1. Check USB device access:
   ```bash
   docker exec eas-sdr-service lsusb
   ```

2. Check SoapySDR detection:
   ```bash
   docker exec eas-sdr-service SoapySDRUtil --find
   ```

3. Check container logs:
   ```bash
   docker logs eas-sdr-service
   ```

### Buffer Overflows

Symptoms: "Ring buffer overflow" warnings in logs

Causes:
- Processing thread too slow
- Insufficient CPU
- High sample rate without adequate resources

Solutions:
- Reduce sample rate
- Increase ring buffer size
- Use faster hardware
- Check for CPU throttling

### No Spectrum Data

1. Check Redis connectivity:
   ```bash
   docker exec eas-sdr-service python -c "import redis; r=redis.Redis(host='redis'); print(r.ping())"
   ```

2. Check spectrum key:
   ```bash
   docker exec eas-redis redis-cli GET sdr:spectrum:noaa-1
   ```

3. Verify receiver is locked:
   ```bash
   docker exec eas-redis redis-cli HGETALL sdr:metrics
   ```

## Monitoring

### Health Check Endpoints

The SDR service publishes a heartbeat to Redis:

```bash
# Check heartbeat
docker exec eas-redis redis-cli GET sdr:heartbeat

# Expected output:
{"timestamp": 1701532800.123, "pid": 12345, "receiver_count": 1}
```

### Ring Buffer Statistics

```bash
# Check ring buffer health
docker exec eas-redis redis-cli HGETALL sdr:ring_buffer:noaa-1

# Expected fields:
# fill_percentage: 25.5
# overflow_count: 0
# underflow_count: 0
# total_samples_written: 1234567890
```

### Container Health

```bash
# Check all containers
docker-compose ps

# Check SDR service specifically
docker inspect eas-sdr-service --format='{{.State.Health.Status}}'
```

## Performance Tuning

### Buffer Sizes

For Airspy R2 at 2.5 MHz:
```python
# USB read buffer: 50ms of samples
read_buffer = int(2_500_000 * 0.050)  # 125,000 samples

# Ring buffer: 1 second of samples  
ring_buffer = int(2_500_000 * 1.0)    # 2,500,000 samples
```

### CPU Affinity

For multi-core systems, consider pinning threads:
```yaml
# docker-compose.yml
sdr-service:
  cpuset: "0,1"  # Use cores 0 and 1
```

### Memory

```yaml
# docker-compose.yml
sdr-service:
  shm_size: '512mb'  # Increase for higher sample rates
  mem_limit: 1g       # Limit total memory
```
