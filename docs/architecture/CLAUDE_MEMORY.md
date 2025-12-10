# Claude Code Memory - EAS Station
**Last Rebuilt**: 2025-12-08
**Branch**: claude/rebuild-memory-01JfSL14HFk5WzjFbLnLB6Kt

---

## Project Overview

**EAS Station** is a professional Emergency Alert System (EAS) platform - a software-defined replacement for commercial EAS encoder/decoder hardware (like DASDEC units costing $5,000-$7,000). Built for Raspberry Pi and commodity x86 hardware.

**Repository**: https://github.com/KR8MER/eas-station
**Author**: Timothy Kramer (KR8MER)
**License**: Dual (AGPL-3.0 / Commercial)
**Status**: Laboratory/research use only - NOT FCC-certified

---

## Core Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Flask 3.0, Flask-SocketIO, Gunicorn + Gevent |
| **Database** | PostgreSQL 17 + PostGIS 3.4, GeoAlchemy2 |
| **Caching** | Redis 7 (pub/sub, state, caching) |
| **ORM** | SQLAlchemy 2.0, Alembic migrations |
| **Frontend** | Bootstrap 5, Socket.IO, Vanilla JS |
| **Audio** | pydub, scipy, numpy, ffmpeg |
| **SDR** | SoapySDR (RTL-SDR v3, Airspy R2) |
| **Hardware** | gpiozero (GPIO), luma.oled (OLED), pyserial (VFD) |
| **TTS** | pyttsx3 (offline), Azure OpenAI/Speech (optional) |
| **Deployment** | Docker + Docker Compose, nginx, Let's Encrypt |

---

## Architecture: Separated 3-Tier Services

```
┌──────────────────┐
│  sdr-service     │  → Exclusive USB/hardware access
│  (sdr_hardware_  │  → Publishes IQ to Redis: sdr:samples:{id}
│   service.py)    │
└────────┬─────────┘
         │ Redis pub/sub
         ▼
┌──────────────────┐
│ audio-service    │  → Subscribes to IQ via RedisSDRSourceAdapter
│(eas_monitoring_  │  → Demodulates IQ → audio
│ service.py)      │  → Runs SAME decoder
└────────┬─────────┘  → Stores alerts in database
         │
         ▼
┌──────────────────┐
│  Web App (Flask) │  → User interface & API
│  (app.py)        │  → Real-time WebSocket updates
└──────────────────┘
```

**Key Principle**: USB SDR access is EXCLUSIVE to sdr-service. All other services receive IQ samples via Redis.

---

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `app_core/` | Core business logic, models, database |
| `app_core/audio/` | Audio processing, SAME decoding, streaming |
| `app_core/radio/` | SDR drivers, demodulation, discovery |
| `app_core/auth/` | Authentication, RBAC, MFA |
| `app_core/config/` | Configuration management |
| `app_core/database/` | Database connectivity, PostGIS |
| `app_core/analytics/` | System analytics |
| `app_utils/` | Standalone utilities (EAS, FIPS, TTS, GPIO) |
| `webapp/` | Flask routes organized by feature |
| `webapp/admin/` | Administration features |
| `webapp/routes/` | Grouped route handlers |
| `poller/` | CAP alert polling service |
| `templates/` | 30+ Jinja2 HTML templates |
| `static/` | CSS, JS, vendor libraries |
| `tests/` | 100+ pytest test files |
| `docs/` | 70+ markdown documentation files |
| `scripts/` | Diagnostic and maintenance scripts |

---

## Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | 1071 | Main Flask application |
| `sdr_hardware_service.py` | 893 | SDR hardware-exclusive service |
| `eas_monitoring_service.py` | 1225 | EAS monitoring service |
| `poller/cap_poller.py` | 2910 | CAP alert polling |
| `app_core/models.py` | 1800+ | SQLAlchemy models |
| `app_core/radio/drivers.py` | 1494 | SDR drivers (SoapySDR) |
| `app_core/radio/demodulation.py` | 652 | FM/AM/NFM demodulation |
| `app_core/audio/redis_sdr_adapter.py` | 322 | Redis IQ bridge |
| `templates/admin.html` | 336KB | Admin dashboard |
| `app_utils/fips_codes.py` | 88KB | FIPS reference database |

---

## Database Models (app_core/models.py)

| Model | Purpose |
|-------|---------|
| `CAPAlert` | Stored CAP alerts from NOAA/IPAWS |
| `EASMessage` | Generated EAS/SAME messages |
| `ManualEASActivation` | Manual broadcast activations |
| `RadioReceiver` | SDR receiver configurations |
| `RadioReceiverStatus` | Receiver runtime status |
| `AudioSourceConfig` | Audio source configurations |
| `Boundary` | Geographic boundaries (PostGIS) |
| `Intersection` | Alert-boundary intersections |
| `LocationSettings` | Station location config |
| `LEDSignStatus` | LED sign status |
| `LEDMessage` | LED message queue |
| `AdminUser` | User authentication |
| `Role` / `Permission` | RBAC system |
| `SystemLog` | System audit logs |
| `SnowEmergency` | Snow emergency declarations |

---

## Redis Channels

| Channel | Content | Publisher |
|---------|---------|-----------|
| `sdr:samples:{id}` | IQ samples (zlib+base64) | sdr-service |
| `sdr:metrics` | Health metrics | sdr-service |
| `sdr:spectrum:{id}` | FFT spectrum | sdr-service |
| `sdr:commands` | Control commands | Web UI |
| `audio:samples:{source}` | Audio samples | audio-service |

---

## Key Features

1. **Multi-Source Alert Ingestion**
   - NOAA Weather API (CAP feeds)
   - IPAWS/FEMA (PUBLIC, EAS, WEA, NWEM feeds)
   - Custom CAP feed support

2. **FCC-Compliant SAME Encoding**
   - 67 event codes supported
   - Proper SAME header generation
   - Attention tone synthesis

3. **Geographic Intelligence**
   - PostGIS spatial filtering
   - County/state/zone/polygon support
   - FIPS code matching

4. **SDR Verification**
   - RTL-SDR v3 and Airspy R2 support
   - FM/AM/NFM demodulation
   - SAME header detection

5. **Hardware Integration**
   - GPIO relay control
   - LED alpha signs (IP-based)
   - OLED display (SSD1306)
   - VFD display (Noritake)

6. **Web Interface**
   - Real-time WebSocket updates
   - Alert history and detail views
   - System health monitoring
   - Administration panel

---

## Design Standards (DESIGN_STANDARDS.md)

**Mandatory for all pages:**
- Standard page header with icon
- CSS variables for colors (no hardcoded)
- Bootstrap 5 grid system
- All buttons must have icons
- 4px spacing scale
- Professional gradients (not flashy)

**Color Palette:**
```css
--primary-color: #1e3a8a;      /* Deep Blue */
--success-color: #10b981;      /* Green */
--danger-color: #ef4444;       /* Red */
--warning-color: #f59e0b;      /* Amber */
```

---

## Testing

**Framework**: pytest 8.3.4 + pytest-asyncio

**Test markers:**
- `@pytest.mark.unit` - Fast, isolated
- `@pytest.mark.integration` - Service interactions
- `@pytest.mark.audio` - Audio processing
- `@pytest.mark.radio` - SDR receivers
- `@pytest.mark.database` - Database operations

**Run tests:**
```bash
pytest tests/
pytest -m unit
pytest -m "not slow"
```

---

## Docker Deployment

**Standard:**
```bash
docker compose up -d --build
```

**Variants:**
- `docker-compose.yml` - Main deployment
- `docker-compose.separated.yml` - Service separation
- `docker-compose.embedded-db.yml` - Embedded PostgreSQL
- `docker-compose.pi.yml` - Raspberry Pi optimized
- `docker-compose.icecast.yml` - Icecast streaming

---

## Environment Variables (.env)

**Critical:**
```bash
SECRET_KEY=<generate-with-secrets>
POSTGRES_PASSWORD=<secure-password>
DOMAIN_NAME=<for-ssl>

# Location
DEFAULT_COUNTY_NAME=Your County
DEFAULT_STATE_CODE=XX
DEFAULT_ZONE_CODES=XXZ001,XXC001

# EAS
EAS_BROADCAST_ENABLED=false
EAS_ORIGINATOR=WXR
EAS_STATION_ID=YOURCALL

# SDR
SDR_MAX_CONSECUTIVE_TIMEOUTS=30

# tmpfs (for RAM optimization)
TMPFS_SDR_SERVICE=64M
TMPFS_AUDIO_SERVICE=128M
```

---

## Common Tasks

### Add SDR Receiver
1. Web UI: `/settings/radio`
2. Set driver (airspy/rtlsdr), frequency, sample rate
3. Airspy R2: ONLY 2.5MHz or 10MHz sample rates

### Check SDR Status
```bash
docker logs eas-sdr-service | grep "Started.*receiver"
docker exec eas-redis redis-cli SUBSCRIBE "sdr:samples:*"
```

### Check Audio
```bash
docker logs eas-audio-service | grep "First audio chunk"
curl http://localhost:5000/api/audio/sources
```

### Database Operations
```bash
# Check receivers
docker exec eas-postgres psql -U postgres -d alerts -c "SELECT * FROM radio_receivers"

# Run migrations
docker exec eas-app flask db upgrade
```

---

## Recent Changes (December 2025)

1. **3-Tier Architecture** - SDR, Audio, EAS separated
2. **14 Critical Fixes** - SDR startup, validation, web audio
3. **67 Event Codes** - Added SQW, ISW, WCW, LSW, LFW, EQE
4. **Web Audio Fix** - HTTPS streaming only (no confusing toggle)
5. **Ring Buffer** - Exponential backoff logging
6. **Airspy Validation** - Only 2.5/10 MHz rates accepted

---

## Troubleshooting Quick Reference

| Problem | Check |
|---------|-------|
| No audio | `docker logs eas-sdr-service | grep "SoapySDR"` |
| Airspy won't start | Sample rate must be 2500000 or 10000000 |
| Web player silent | Browser console (F12), check `/api/audio/stream` |
| Database errors | `docker logs eas-postgres` |
| Redis issues | `docker exec eas-redis redis-cli PING` |

---

## Important Documentation

- **README.md** - Project overview, quick start
- **ARCHITECTURE_3_TIER.md** - Service architecture
- **DESIGN_STANDARDS.md** - UI/UX guidelines
- **SDR_WORKING_MEMORY.md** - SDR troubleshooting
- **docs/INDEX.md** - Full documentation index

---

*This memory file is auto-generated. Update when significant changes occur.*
