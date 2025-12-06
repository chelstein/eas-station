# EAS Station Codebase Inventory

**Version**: Current State Analysis  
**Date**: December 2025  
**Purpose**: Complete inventory of all system functions and capabilities for architecture rewrite planning

## Executive Summary

This document provides a comprehensive inventory of the EAS Station codebase as it exists today, cataloging all major functions, modules, and capabilities. This serves as the foundation for planning a systematic rewrite with proper architecture.

**Current Scale:**
- **199 Python files** across all modules
- **5 main service entry points** (app, audio, SDR, EAS, hardware)
- **194 supporting module files** (core, utils, webapp, poller)
- **80+ test files** with comprehensive coverage
- **30+ documentation files** describing various aspects

## 1. Main Services (Entry Points)

### 1.1 Web Application Service (`app.py`)
**Size**: 1,297 lines | 29 functions | Flask-based

**Primary Functions:**
- Web UI serving and routing
- Database initialization and schema management
- User authentication and session management
- API endpoint handling
- WebSocket real-time updates
- CSRF protection
- Template rendering and context injection
- Admin user management
- System health monitoring integration
- Location timezone configuration

**Key Dependencies:**
- Flask 3.0.3 + extensions (SQLAlchemy, Caching, SocketIO)
- PostgreSQL with PostGIS
- Redis for caching and state
- All webapp route modules

**Database Tables Managed:**
- AdminUser, CAPAlert, EASMessage, Boundary
- RadioReceiver, RadioReceiverStatus
- LEDMessage, LEDSignStatus, SystemLog
- LocationSettings, PollHistory, PollDebugRecord
- ManualEASActivation, Intersection, SnowEmergency

### 1.2 Audio Processing Service (`audio_service.py`)
**Size**: 1,131 lines | 13 functions | Standalone service

**Primary Functions:**
- Audio source ingestion (SDR, Icecast streams, HTTP streams)
- Audio demodulation (FM, AM, etc.)
- EAS/SAME header monitoring and decoding
- Icecast streaming output
- Audio metrics publishing to Redis
- Spectrum analysis and visualization
- Audio buffer management
- Broadcast queue management

**Key Components:**
- AudioController - manages audio sources
- EASMonitor - SAME decoder integration
- IcecastStreamer - audio output streaming
- RadioManager - SDR receiver coordination
- RedisAudioPublisher - metrics publishing

**Audio Processing Pipeline:**
1. Source ingestion (SDR IQ samples or HTTP streams)
2. Demodulation to audio
3. EAS monitoring and alert detection
4. Output streaming to Icecast
5. Metrics collection and publishing

### 1.3 SDR Hardware Service (`sdr_service.py`)
**Size**: 688 lines | 9 functions | 1 class | Hardware interface

**Primary Functions:**
- SoapySDR device management
- USB hardware access and control
- IQ sample acquisition
- Dual-thread architecture (USB reader + publisher)
- Ring buffer management for reliable streaming
- SDR health metrics publishing
- Device configuration (frequency, sample rate, gain)

**Hardware Support:**
- RTL-SDR dongles
- Airspy receivers
- Generic SoapySDR-compatible devices

**Architecture Benefits:**
- Isolated USB access (no impact on other services)
- Reliable 24/7 operation with buffering
- Independent restart capability
- Hardware-specific permissions isolated

### 1.4 EAS Monitoring Service (`eas_service.py`)
**Size**: 225 lines | 4 functions | Alert detection

**Primary Functions:**
- Subscribe to Redis audio streams
- Continuous EAS/SAME header detection
- FIPS code filtering and geographic matching
- Alert database storage
- Minimal overhead monitoring

**Design Philosophy:**
- Single responsibility (EAS detection only)
- No audio processing (consumes from audio-service)
- No hardware access (isolated from SDR)
- Easy to scale to multiple audio sources

### 1.5 Hardware Control Service (`hardware_service.py`)
**Size**: 830 lines | 15 functions | GPIO and displays

**Primary Functions:**
- GPIO relay control for broadcast automation
- LED display management (matrix signs)
- OLED display control (SSD1306/SH1106)
- VFD display management (Noritake serial displays)
- Hardware health monitoring
- Display content rotation and scheduling

**Hardware Interfaces:**
- Raspberry Pi GPIO via gpiozero
- I2C for OLED displays
- Serial for VFD displays
- Network for LED signs

## 2. Core Modules (`app_core/`)

**116 Python files** providing core system functionality

### 2.1 Audio Processing (`app_core/audio/`)
**Key Files:**
- `audio_controller.py` - Central audio source management
- `audio_source_base.py` - Base class for all audio sources
- `eas_monitor.py` - SAME decoder integration
- `icecast_streamer.py` - Audio streaming output
- `redis_adapters.py` - Redis pub/sub for audio
- `same_decoder.py` - SAME protocol implementation
- `spectrum_analyzer.py` - FFT and waterfall display
- `audio_buffer.py` - Ring buffer management

**Functions:**
- Multi-source audio aggregation
- Real-time SAME decoding
- Audio format conversion
- Stream metadata handling
- Buffer overflow protection

### 2.2 Radio Receivers (`app_core/radio/`)
**Key Files:**
- `radio_manager.py` - SDR receiver lifecycle management
- `radio_source.py` - SDR audio source implementation
- `receiver_config.py` - Receiver configuration
- `models.py` - RadioReceiver database models

**Functions:**
- SDR initialization and configuration
- Multi-receiver coordination
- Audio sample rate conversion
- Receiver health monitoring
- Frequency scanning

### 2.3 Authentication & Authorization (`app_core/auth/`)
**Key Files:**
- `roles.py` - RBAC role management
- `decorators.py` - Permission decorators
- `mfa.py` - Multi-factor authentication (TOTP)

**Functions:**
- User authentication
- Role-based access control
- MFA enrollment and verification
- Session management
- Password security

### 2.4 EAS Storage (`app_core/eas_storage.py`)
**Functions:**
- EAS message database operations
- Audio file management
- Metadata payload handling
- SAME header storage
- Audio caching from disk

### 2.5 Boundaries & Geography (`app_core/boundaries.py`)
**Functions:**
- PostGIS spatial operations
- County/state boundary management
- FIPS code lookup
- Geographic intersection detection
- Boundary display configuration

### 2.6 System Health (`app_core/system_health.py`)
**Functions:**
- CPU/memory/disk monitoring
- Service health checks
- Alert threshold detection
- Background health monitoring worker
- Compliance reporting

### 2.7 LED/OLED/VFD Display Systems
**Files:** `led.py`, `oled.py`, `vfd.py`

**Functions:**
- Display initialization and control
- Content rendering and formatting
- Screen rotation and scheduling
- Status indicator management
- Emergency message display

### 2.8 Database Models (`app_core/models.py`)
**Core Tables:**
- CAPAlert - Weather and emergency alerts
- EASMessage - Encoded EAS messages
- Boundary - Geographic boundaries
- RadioReceiver - SDR configurations
- AdminUser - User accounts
- SystemLog - Audit trail
- LocationSettings - System configuration

### 2.9 Analytics (`app_core/analytics/`)
**Functions:**
- Alert statistics and trends
- System usage metrics
- Performance monitoring
- Report generation

### 2.10 Cache Management (`app_core/cache.py`)
**Functions:**
- Redis-based caching
- Cache key management
- TTL configuration
- Cache invalidation

### 2.11 Poller Debug (`app_core/poller_debug.py`)
**Functions:**
- Poll debugging and logging
- Feed health monitoring
- Error tracking

### 2.12 Zone Catalog (`app_core/zones.py`)
**Functions:**
- NWS zone code management
- Zone-to-county mapping
- Zone boundary lookup

### 2.13 WebSocket Push (`app_core/websocket_push.py`)
**Functions:**
- Real-time browser updates
- Alert notifications
- Status change broadcasting

### 2.14 RWT Scheduler (`app_core/rwt_scheduler.py`)
**Functions:**
- Required Weekly Test scheduling
- Automatic test execution
- Compliance tracking

### 2.15 Location Management (`app_core/location.py`)
**Functions:**
- Geographic location configuration
- Timezone management
- Default zone code setup

## 3. Utility Modules (`app_utils/`)

**25 Python files** providing reusable utilities

### 3.1 EAS Utilities (`app_utils/eas.py`)
**Functions:**
- SAME header encoding/decoding
- Attention tone generation
- Audio segment composition
- Originator code descriptions
- Event code lookups

### 3.2 Event Codes (`app_utils/event_codes.py`)
**Functions:**
- 67 event code definitions
- Code categorization
- Originator mapping
- Plain language descriptions

### 3.3 FIPS Codes (`app_utils/fips_codes.py`)
**Functions:**
- US county FIPS lookup
- State-county tree structure
- SAME code parsing
- Geographic code validation

### 3.4 Datetime Utilities (`app_utils/__init__.py`)
**Functions:**
- Timezone-aware datetime handling
- NWS datetime parsing
- UTC/local time conversion
- Timezone configuration

### 3.5 Assets Management (`app_utils/assets.py`)
**Functions:**
- Logo and image handling
- Shield badge generation
- Asset path resolution

### 3.6 Optimized Parsing (`app_utils/optimized_parsing.py`)
**Functions:**
- Fast JSON parsing (orjson/ujson)
- XML processing (lxml)
- Performance optimizations

### 3.7 Versioning (`app_utils/versioning.py`)
**Functions:**
- Git commit tracking
- Version string generation
- Build metadata

## 4. Web Application (`webapp/`)

**51 Python files** implementing the web interface

### 4.1 Route Modules (`webapp/routes/`)
**Files:**
- `index.py` - Dashboard and main pages
- `alerts.py` - Alert browsing and management
- `admin.py` - Administration interface
- `api.py` - REST API endpoints
- `auth.py` - Login/logout
- `tools.py` - Diagnostic tools

### 4.2 Admin Functions (`webapp/admin/`)
**Major Areas:**
- **audio/** - Audio source configuration
- **boundaries/** - Geographic boundary management
- **maintenance/** - System maintenance
- Alert imports and exports
- User management
- Configuration editing

**Key Files:**
- `audio_manager.py` - Audio source CRUD
- `boundaries.py` - Boundary import/export
- `maintenance.py` - Manual alert imports
- `environment.py` - Environment variable management

### 4.3 EAS Functions (`webapp/eas/`)
**Functions:**
- Manual EAS activation
- Alert verification tools
- SAME header testing
- Audio preview

## 5. Alert Polling System (`poller/`)

**2 Python files** - Alert feed ingestion

### 5.1 NOAA Poller (`poller/noaa_poller.py`)
**Functions:**
- Weather.gov API integration
- CAP XML parsing
- Alert deduplication
- Geographic filtering
- Continuous polling

### 5.2 IPAWS Poller (`poller/ipaws_poller.py`)
**Functions:**
- FEMA IPAWS feed integration
- Federal alert ingestion
- Multi-source coordination

## 6. Test Infrastructure (`tests/`)

**80+ test files** with comprehensive coverage

### Test Categories:
- **Unit tests** - Individual component testing
- **Integration tests** - Multi-component workflows
- **Audio tests** - SAME decoding, audio processing
- **Radio tests** - SDR receiver functionality
- **API tests** - REST endpoint validation
- **UI tests** - Web interface testing
- **Database tests** - Model and query testing

### Key Test Files:
- `test_eas_decode.py` - SAME decoder validation
- `test_audio_pipeline_integration.py` - End-to-end audio
- `test_radio_manager.py` - SDR management
- `test_3tier_architecture.py` - Service separation
- `test_alert_self_test_harness.py` - Alert replay testing

## 7. Configuration & Deployment

### Docker Compose Services:
1. **nginx** - HTTPS reverse proxy
2. **certbot** - SSL certificate management
3. **redis** - State and caching
4. **sdr-service** - SDR hardware isolation
5. **audio-service** - Audio processing
6. **eas-service** - Alert monitoring
7. **app** - Web UI
8. **alerts-db** - PostgreSQL + PostGIS
9. **icecast** - Optional audio streaming

### Environment Configuration:
- `.env` - Primary configuration
- `stack.env` - Docker compose variables
- `ipaws.env` - IPAWS credentials
- `noaa.env` - NOAA feed configuration

## 8. External Dependencies

### Python Packages (108 total):
**Web Framework:**
- Flask 3.0.3 + extensions
- Werkzeug 3.0.6

**Database:**
- SQLAlchemy 2.0.44
- psycopg2-binary 2.9.10
- GeoAlchemy2 0.15.2
- Alembic 1.14.0

**Audio Processing:**
- numpy 2.2.1
- scipy 1.14.1
- pydub 0.25.1

**Networking:**
- requests 2.32.3
- httpx 0.27.2
- redis 5.0.8

**Hardware:**
- gpiozero 2.0.1
- pyserial 3.5
- luma.oled 3.14.0

**Utilities:**
- python-dotenv 1.0.1
- pytz 2024.2
- python-dateutil 2.9.0

### System Dependencies:
- PostgreSQL 17 with PostGIS 3.4
- Redis 7
- ffmpeg (audio codec support)
- SoapySDR (SDR hardware)
- libusb (USB device access)

## 9. Documentation Structure

### Existing Documentation (30+ files):
**Guides:** Setup, help, configuration, debugging  
**Architecture:** System design, data flow, service isolation  
**Reference:** Changelog, API docs, FCC compliance  
**Hardware:** SDR setup, GPIO configuration, display systems  
**Development:** Contributing, agents, testing  
**Deployment:** Docker, Portainer, cloud hosting  

## 10. Key System Capabilities

### Alert Processing:
✅ Multi-source CAP ingestion (NOAA, IPAWS, custom)  
✅ Geographic filtering (PostGIS spatial queries)  
✅ Alert deduplication and correlation  
✅ Historical alert storage and browsing  
✅ Alert export (JSON, CSV, Excel)

### EAS Encoding:
✅ FCC-compliant SAME header generation  
✅ Dual-tone attention signal (1050/853 Hz)  
✅ FSK encoding (520.83 baud)  
✅ Three-header burst transmission  
✅ EOM (End of Message) signal generation  
✅ Text-to-speech integration (Azure, pyttsx3)

### Audio Monitoring:
✅ Real-time SAME decoder  
✅ Multi-receiver coordination  
✅ FIPS code filtering  
✅ Automatic alert detection  
✅ Audio spectrum visualization

### Broadcasting:
✅ Icecast streaming output  
✅ Multi-format support (MP3, AAC, OGG)  
✅ Stream metadata injection  
✅ Automatic EAS insertion  
✅ Broadcast queue management

### Hardware Integration:
✅ GPIO relay control  
✅ LED matrix display support  
✅ OLED display (I2C)  
✅ VFD display (serial)  
✅ Multi-relay coordination

### Web Interface:
✅ Real-time dashboard  
✅ Alert browsing and filtering  
✅ Manual EAS activation  
✅ Audio source management  
✅ Boundary configuration  
✅ System health monitoring  
✅ User management with RBAC  
✅ Multi-factor authentication  
✅ 19 UI themes

### API:
✅ REST endpoints for all functions  
✅ WebSocket real-time updates  
✅ API key authentication  
✅ CORS support  
✅ Rate limiting  
✅ Comprehensive error handling

## 11. Known Architecture Issues

### Current Problems:
1. **Monolithic app.py** - Too many responsibilities in one file
2. **Tight coupling** - Services depend on each other directly
3. **Mixed concerns** - Business logic mixed with routing
4. **Configuration sprawl** - Settings scattered across multiple files
5. **Inconsistent patterns** - Different coding styles across modules
6. **Limited abstraction** - Direct database access in routes
7. **Testing challenges** - Hard to test components in isolation
8. **Documentation gaps** - Some modules lack clear documentation

### Technical Debt:
- Database migrations mixed with core code
- Global state in service files
- Circular import risks
- Inconsistent error handling
- Mixed sync/async patterns
- Hard-coded configuration values
- Limited dependency injection

## 12. Rewrite Opportunities

### High-Priority Improvements:
1. **Clean separation of concerns** - Service layer, business logic, data access
2. **Dependency injection** - Remove global state, improve testability
3. **Configuration management** - Centralized, validated configuration
4. **API-first design** - Consistent REST/GraphQL API
5. **Event-driven architecture** - Pub/sub for service communication
6. **Microservices boundaries** - Clear service contracts
7. **Comprehensive testing** - Unit, integration, E2E tests
8. **Documentation as code** - API specs, architecture diagrams

### Technology Upgrades:
- FastAPI instead of Flask (async, auto-docs)
- SQLModel instead of SQLAlchemy (type safety)
- Pydantic for validation (data contracts)
- MQTT for event bus (service decoupling)
- OpenTelemetry for observability (distributed tracing)
- Docker Swarm/K8s for orchestration (production scaling)

## Summary Statistics

```
Total Lines of Code: ~50,000+ (estimated)
Python Files: 199
Test Files: 80+
Documentation Files: 30+
Docker Services: 9
Database Tables: 20+
API Endpoints: 100+
Supported Event Codes: 67
UI Themes: 19
External Dependencies: 108
```

## Next Steps

This inventory serves as the foundation for:
1. Creating detailed module documentation
2. Identifying rewrite phases
3. Designing new architecture
4. Planning migration strategy
5. Establishing coding standards

See companion documents:
- `REWRITE_ARCHITECTURE.md` - Proposed new architecture
- `REWRITE_ROADMAP.md` - Phase-by-phase implementation plan
- `MIGRATION_GUIDE.md` - Step-by-step migration instructions
