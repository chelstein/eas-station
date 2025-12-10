# 3-Tier Separated Architecture Implementation Plan

## Overview

This document describes the complete 3-tier separated architecture for EAS Station:

```text
┌──────────────────┐
│  sdr-service     │  ─→ SDR hardware access only
│  (sdr_service.py)│  ─→ Publishes IQ samples to Redis: sdr:samples:{receiver_id}
└────────┬─────────┘
         │ Redis IQ pub/sub
         ▼
┌──────────────────┐
│ audio-service    │  ─→ Audio demodulation only
│(audio_service.py)│  ─→ Subscribes to Redis IQ via RedisSDRSourceAdapter
│                  │  ─→ Demodulates IQ → audio
│                  │  ─→ Publishes audio to Redis: audio:samples:{source}
└────────┬─────────┘
         │ Redis audio pub/sub
         ▼
┌──────────────────┐
│  eas-service     │  ─→ EAS monitoring only
│  (eas_service.py)│  ─→ Subscribes to Redis audio via RedisAudioAdapter
│                  │  ─→ Runs SAME decoder
│                  │  ─→ Stores alerts in database
└──────────────────┘
```

## Components Created

### ✅ Implementation Complete

1. **app_core/audio/redis_sdr_adapter.py** - Subscribes to Redis IQ samples
2. **app_core/audio/redis_audio_adapter.py** - Subscribes to Redis audio samples
3. **app_core/audio/redis_audio_publisher.py** - Publishes audio to Redis
4. **eas_service.py** - Standalone EAS service
5. **audio_service.py** - EAS monitor initialization removed (EAS handled by eas-service)

## ⚠️ Important: Single EAS Monitor Architecture

**Only the `eas-service` container performs EAS monitoring.** The `audio-service` container does NOT run EAS monitoring.

This separation provides:
- **Clear responsibility**: Each service has one job
- **Reliability**: EAS crashes don't affect audio processing
- **Scalability**: Services can be restarted independently
- **Simplicity**: No coordination needed between multiple EAS monitors

## Changes Needed to audio_service.py

### Remove EAS Monitor

Current (lines ~417-480):
```python
def initialize_eas_monitor(app, audio_controller):
    # ... EAS monitor initialization ...
```

Replace with:
```python
def initialize_redis_audio_publisher(app, audio_controller):
    """Initialize Redis audio publisher for eas-service."""
    global _redis_audio_publisher

    from app_core.audio.redis_audio_publisher import RedisAudioPublisher

    broadcast_queue = audio_controller.get_broadcast_queue()

    publisher = RedisAudioPublisher(
        broadcast_queue=broadcast_queue,
        source_name="main",
        sample_rate=44100,
        publish_interval_ms=100
    )

    if publisher.start():
        logger.info("✅ Redis audio publisher started")
        _redis_audio_publisher = publisher
        return publisher
    else:
        raise RuntimeError("Failed to start Redis audio publisher")
```

### Update main() function

Current (line ~740):
```python
_eas_monitor = initialize_eas_monitor(_flask_app, _audio_controller)
```

Replace with:
```python
_redis_audio_publisher = initialize_redis_audio_publisher(_flask_app, _audio_controller)
```

## eas-service services

```yaml
  eas-service:
    image: eas-station:latest
    container_name: eas-eas-service
    init: true
    restart: unless-stopped
    networks:
      - eas-network
    command: ["python", "eas_service.py"]
    volumes:
      - app-config:/app-config
    tmpfs:
      - /tmp:size=${TMPFS_EAS_SERVICE:-64M},mode=1777
    environment:
      # Database connection
      POSTGRES_HOST: ${POSTGRES_HOST:-alerts-db}
      POSTGRES_PORT: ${POSTGRES_PORT:-5432}
      POSTGRES_DB: ${POSTGRES_DB:-alerts}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}

      # Redis connection
      REDIS_HOST: ${REDIS_HOST:-redis}
      REDIS_PORT: ${REDIS_PORT:-6379}
      REDIS_DB: ${REDIS_DB:-0}

      # Application settings
      CONFIG_PATH: /app-config/.env
    extra_hosts:
    security_opt:
      - no-new-privileges:true
    depends_on:
      redis:
        condition: service_healthy
      audio-service:
        condition: service_started
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import redis; r=redis.Redis(host=\"redis\"); r.ping()' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

## Testing Plan

### 1. Syntax Checks
✅ All Python files compile without errors

### 2. Import Checks
```bash
cd /home/user/eas-station
python3 -c "from app_core.audio.redis_sdr_adapter import RedisSDRSourceAdapter; print('✅ RedisSDRSourceAdapter')"
python3 -c "from app_core.audio.redis_audio_adapter import RedisAudioAdapter; print('✅ RedisAudioAdapter')"
python3 -c "from app_core.audio.redis_audio_publisher import RedisAudioPublisher; print('✅ RedisAudioPublisher')"
```

### 3. Integration Test
```bash
# 1. Build containers

# 2. Start services

# 3. Check logs

# 4. Verify Redis channels

# Expected output:
# sdr:samples:*
# audio:samples:*
```

## Benefits of 3-Tier Architecture

1. **Isolation**: Each service can crash/restart independently
2. **Scalability**: Can run multiple EAS monitors on different audio sources
3. **Maintainability**: Clear separation of concerns
4. **Testability**: Each tier can be tested independently
5. **Flexibility**: Easy to add new audio sources or EAS monitors

## Rollback Plan

If issues occur, revert to monolithic mode:
1. Change sdr-service command to `audio_service.py`
2. Disable audio-service and eas-service containers
3. This was the original "fix #2" from the first investigation
