# EAS Station - Proposed Architecture Rewrite

**Version**: 1.0  
**Date**: December 2025  
**Status**: Planning Phase  
**Purpose**: Define clean architecture for systematic codebase rewrite

## Executive Summary

This document proposes a clean, maintainable architecture for EAS Station that addresses current technical debt while preserving all existing functionality. The new architecture emphasizes:

- **Clear separation of concerns**
- **Testability and maintainability**
- **Scalability and performance**
- **Developer experience**
- **Production reliability**

## Current State Assessment

### Strengths to Preserve ✅
- Comprehensive feature set
- Robust testing infrastructure
- Working service separation (SDR, Audio, EAS, Web)
- Strong domain knowledge in code
- Good documentation foundation
- Active development and testing

### Problems to Address ❌
1. **Monolithic app.py** (1,297 lines) - too many responsibilities
2. **Tight coupling** between services
3. **Mixed concerns** - business logic in routes
4. **Configuration sprawl** - settings scattered
5. **Inconsistent patterns** across modules
6. **Limited abstraction** - direct DB access in routes
7. **Testing challenges** - hard to isolate components
8. **Technical debt** - patches and band-aids accumulated

## New Architecture Principles

### 1. Layered Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Presentation Layer                  │
│            (API, Web UI, CLI Commands)              │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│               Application Layer                      │
│        (Use Cases, Business Logic, Services)        │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│                 Domain Layer                         │
│          (Entities, Value Objects, Rules)           │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│             Infrastructure Layer                     │
│    (Database, Redis, Hardware, External APIs)       │
└─────────────────────────────────────────────────────┘
```

### 2. Dependency Injection

**Current Problem:**
```python
# Global state everywhere
_audio_controller = None
_eas_monitor = None
_redis_client = None
```

**Proposed Solution:**
```python
# Explicit dependency injection
class EASService:
    def __init__(
        self,
        alert_repository: AlertRepository,
        notification_service: NotificationService,
        config: EASConfig
    ):
        self.alerts = alert_repository
        self.notifications = notification_service
        self.config = config
```

### 3. Service Boundaries

Clear contracts between services:
```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Web UI    │◄────►│  API Layer  │◄────►│  Services   │
└─────────────┘      └─────────────┘      └──────┬──────┘
                                                  │
                     ┌────────────────────────────┼────────────┐
                     │                            │            │
              ┌──────▼──────┐            ┌───────▼────┐  ┌────▼────┐
              │ Alert       │            │  Audio     │  │  EAS    │
              │ Service     │            │  Service   │  │ Service │
              └──────┬──────┘            └───────┬────┘  └────┬────┘
                     │                           │            │
              ┌──────▼──────────────────────────▼────────────▼────┐
              │              Event Bus (Redis Pub/Sub)           │
              └───────────────────────────────────────────────────┘
```

## Proposed Directory Structure

```
eas-station/
├── src/                          # All source code
│   ├── api/                      # API layer (FastAPI)
│   │   ├── __init__.py
│   │   ├── main.py              # API entry point
│   │   ├── dependencies.py      # DI container setup
│   │   ├── middleware.py        # Auth, CORS, logging
│   │   ├── routes/              # API endpoints
│   │   │   ├── alerts.py
│   │   │   ├── audio.py
│   │   │   ├── boundaries.py
│   │   │   ├── eas.py
│   │   │   ├── health.py
│   │   │   └── users.py
│   │   └── schemas/             # Pydantic models
│   │       ├── alert.py
│   │       ├── audio.py
│   │       └── user.py
│   │
│   ├── domain/                  # Domain models
│   │   ├── __init__.py
│   │   ├── models/              # Core entities
│   │   │   ├── alert.py
│   │   │   ├── boundary.py
│   │   │   ├── eas_message.py
│   │   │   ├── radio_receiver.py
│   │   │   └── user.py
│   │   ├── value_objects/       # Immutable values
│   │   │   ├── fips_code.py
│   │   │   ├── same_header.py
│   │   │   ├── frequency.py
│   │   │   └── timezone.py
│   │   ├── events/              # Domain events
│   │   │   ├── alert_received.py
│   │   │   ├── eas_detected.py
│   │   │   └── broadcast_started.py
│   │   └── exceptions/          # Domain errors
│   │       ├── validation.py
│   │       └── business_rules.py
│   │
│   ├── application/             # Use cases & services
│   │   ├── __init__.py
│   │   ├── services/            # Application services
│   │   │   ├── alert_service.py
│   │   │   ├── audio_service.py
│   │   │   ├── boundary_service.py
│   │   │   ├── eas_service.py
│   │   │   ├── notification_service.py
│   │   │   └── user_service.py
│   │   ├── use_cases/           # Business operations
│   │   │   ├── process_alert.py
│   │   │   ├── activate_eas.py
│   │   │   ├── configure_receiver.py
│   │   │   └── import_boundaries.py
│   │   └── interfaces/          # Port definitions
│   │       ├── repositories.py
│   │       ├── event_bus.py
│   │       └── external_apis.py
│   │
│   ├── infrastructure/          # External implementations
│   │   ├── __init__.py
│   │   ├── database/            # Data persistence
│   │   │   ├── __init__.py
│   │   │   ├── connection.py
│   │   │   ├── migrations/      # Alembic migrations
│   │   │   └── repositories/    # Repository implementations
│   │   │       ├── alert_repo.py
│   │   │       ├── boundary_repo.py
│   │   │       └── user_repo.py
│   │   ├── cache/               # Redis cache
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   └── cache_service.py
│   │   ├── messaging/           # Event bus
│   │   │   ├── __init__.py
│   │   │   ├── redis_bus.py
│   │   │   └── handlers/
│   │   ├── audio/               # Audio hardware
│   │   │   ├── __init__.py
│   │   │   ├── sdr_driver.py
│   │   │   ├── demodulator.py
│   │   │   └── same_decoder.py
│   │   ├── hardware/            # GPIO, displays
│   │   │   ├── __init__.py
│   │   │   ├── gpio_controller.py
│   │   │   ├── led_display.py
│   │   │   └── oled_display.py
│   │   ├── external/            # External APIs
│   │   │   ├── __init__.py
│   │   │   ├── noaa_client.py
│   │   │   ├── ipaws_client.py
│   │   │   └── icecast_client.py
│   │   └── config/              # Configuration
│   │       ├── __init__.py
│   │       ├── settings.py
│   │       └── validation.py
│   │
│   ├── services/                # Standalone services
│   │   ├── __init__.py
│   │   ├── web/                 # Web UI service
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   └── templates/
│   │   ├── audio/               # Audio processing service
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   ├── sdr/                 # SDR hardware service
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   ├── eas/                 # EAS monitoring service
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   └── poller/              # Alert polling service
│   │       ├── __init__.py
│   │       └── main.py
│   │
│   └── shared/                  # Shared utilities
│       ├── __init__.py
│       ├── logging.py
│       ├── datetime.py
│       ├── validation.py
│       └── constants.py
│
├── tests/                       # All tests
│   ├── unit/                    # Unit tests
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── integration/             # Integration tests
│   │   ├── api/
│   │   ├── database/
│   │   └── services/
│   ├── e2e/                     # End-to-end tests
│   │   └── scenarios/
│   ├── fixtures/                # Test data
│   └── conftest.py             # Pytest configuration
│
├── docs/                        # Documentation
│   ├── architecture/
│   ├── api/
│   ├── deployment/
│   └── development/
│
├── docker/                      # Docker files
│   ├── Dockerfile.web
│   ├── Dockerfile.audio
│   ├── Dockerfile.sdr
│   └── docker-compose.yml
│
├── scripts/                     # Utility scripts
│   ├── migrate.sh
│   ├── test.sh
│   └── deploy.sh
│
├── static/                      # Static assets
│   ├── css/
│   ├── js/
│   └── img/
│
├── pyproject.toml              # Python project config
├── poetry.lock                 # Dependency lock file
├── .env.example                # Example environment
└── README.md                   # Main readme
```

## Core Components Design

### 1. Domain Models

**Pure business entities with no framework dependencies:**

```python
# src/domain/models/alert.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from ..value_objects import FIPSCode, AlertStatus

@dataclass(frozen=True)
class Alert:
    """Pure domain model for an alert"""
    id: str
    event_code: str
    headline: str
    description: str
    severity: str
    urgency: str
    certainty: str
    affected_areas: list[FIPSCode]
    effective: datetime
    expires: datetime
    status: AlertStatus
    source: str
    
    def is_active(self, at_time: datetime) -> bool:
        """Business rule: alert is active"""
        return (
            self.effective <= at_time < self.expires
            and self.status == AlertStatus.ACTIVE
        )
    
    def affects_area(self, fips_code: FIPSCode) -> bool:
        """Business rule: check if alert affects area"""
        return fips_code in self.affected_areas
```

### 2. Application Services

**Orchestrate business operations:**

```python
# src/application/services/alert_service.py
from typing import List
from ..interfaces.repositories import AlertRepository
from ..interfaces.event_bus import EventBus
from ...domain.models import Alert
from ...domain.events import AlertReceived

class AlertService:
    """Application service for alert operations"""
    
    def __init__(
        self,
        alert_repo: AlertRepository,
        event_bus: EventBus
    ):
        self._repo = alert_repo
        self._events = event_bus
    
    async def process_incoming_alert(
        self,
        alert_data: dict
    ) -> Alert:
        """Process new alert from external source"""
        # 1. Validate and create domain model
        alert = Alert.from_dict(alert_data)
        
        # 2. Apply business rules
        if not alert.is_valid():
            raise ValidationError("Invalid alert data")
        
        # 3. Persist to repository
        saved_alert = await self._repo.save(alert)
        
        # 4. Publish domain event
        await self._events.publish(
            AlertReceived(alert_id=saved_alert.id)
        )
        
        return saved_alert
    
    async def get_active_alerts(
        self,
        area: FIPSCode
    ) -> List[Alert]:
        """Get active alerts for area"""
        alerts = await self._repo.find_active()
        return [
            a for a in alerts
            if a.affects_area(area)
        ]
```

### 3. Repository Pattern

**Abstract data access:**

```python
# src/application/interfaces/repositories.py
from abc import ABC, abstractmethod
from typing import List, Optional
from ...domain.models import Alert

class AlertRepository(ABC):
    """Repository interface for alerts"""
    
    @abstractmethod
    async def save(self, alert: Alert) -> Alert:
        """Save alert"""
        pass
    
    @abstractmethod
    async def find_by_id(self, alert_id: str) -> Optional[Alert]:
        """Find alert by ID"""
        pass
    
    @abstractmethod
    async def find_active(self) -> List[Alert]:
        """Find all active alerts"""
        pass
    
    @abstractmethod
    async def delete(self, alert_id: str) -> None:
        """Delete alert"""
        pass

# src/infrastructure/database/repositories/alert_repo.py
from sqlalchemy.ext.asyncio import AsyncSession
from ....application.interfaces.repositories import AlertRepository
from ....domain.models import Alert
from ..models import AlertModel  # SQLAlchemy model

class SQLAlertRepository(AlertRepository):
    """PostgreSQL implementation"""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, alert: Alert) -> Alert:
        """Save to PostgreSQL"""
        model = AlertModel.from_domain(alert)
        self._session.add(model)
        await self._session.commit()
        return model.to_domain()
```

### 4. Dependency Injection

**Central DI container:**

```python
# src/api/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db_session
from .cache import get_redis_client
from ..application.services import AlertService
from ..infrastructure.database.repositories import SQLAlertRepository
from ..infrastructure.messaging import RedisEventBus

async def get_alert_service(
    session: AsyncSession = Depends(get_db_session),
    redis = Depends(get_redis_client)
) -> AlertService:
    """Create alert service with dependencies"""
    repo = SQLAlertRepository(session)
    event_bus = RedisEventBus(redis)
    return AlertService(repo, event_bus)

# Usage in routes:
@router.post("/alerts")
async def create_alert(
    data: AlertCreate,
    service: AlertService = Depends(get_alert_service)
):
    alert = await service.process_incoming_alert(data.dict())
    return alert
```

### 5. Configuration Management

**Type-safe, validated configuration:**

```python
# src/infrastructure/config/settings.py
from pydantic import BaseSettings, Field, PostgresDsn

class DatabaseSettings(BaseSettings):
    """Database configuration"""
    url: PostgresDsn = Field(..., env="DATABASE_URL")
    pool_size: int = Field(10, env="DB_POOL_SIZE")
    echo: bool = Field(False, env="DB_ECHO")

class RedisSettings(BaseSettings):
    """Redis configuration"""
    host: str = Field("localhost", env="REDIS_HOST")
    port: int = Field(6379, env="REDIS_PORT")
    db: int = Field(0, env="REDIS_DB")

class EASSettings(BaseSettings):
    """EAS configuration"""
    enabled: bool = Field(False, env="EAS_BROADCAST_ENABLED")
    originator: str = Field("WXR", env="EAS_ORIGINATOR")
    station_id: str = Field("", env="EAS_STATION_ID")
    
    class Config:
        validate_assignment = True

class Settings(BaseSettings):
    """Master settings"""
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    eas: EASSettings = EASSettings()
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"

# Usage:
settings = Settings()
print(settings.database.url)
```

### 6. Event-Driven Communication

**Loose coupling between services:**

```python
# src/domain/events/alert_received.py
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class AlertReceived:
    """Domain event: new alert received"""
    alert_id: str
    timestamp: datetime
    source: str

# src/infrastructure/messaging/redis_bus.py
class RedisEventBus:
    """Redis pub/sub event bus"""
    
    async def publish(self, event: DomainEvent):
        """Publish domain event"""
        channel = f"events:{event.__class__.__name__}"
        await self._redis.publish(
            channel,
            event.to_json()
        )
    
    async def subscribe(self, event_type: type, handler):
        """Subscribe to event type"""
        channel = f"events:{event_type.__name__}"
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        
        async for message in pubsub.listen():
            event = event_type.from_json(message['data'])
            await handler(event)

# Handler example:
async def handle_alert_received(event: AlertReceived):
    """Handle new alert event"""
    # Trigger EAS encoding
    # Update LED displays
    # Send notifications
    pass
```

## Technology Stack Updates

### Current → Proposed

| Component | Current | Proposed | Reason |
|-----------|---------|----------|--------|
| Web Framework | Flask 3.0 | **FastAPI 0.109** | Async, auto-docs, type safety |
| ORM | SQLAlchemy | **SQLModel** | Type safety, Pydantic integration |
| Validation | Manual | **Pydantic V2** | Auto-validation, serialization |
| Testing | pytest | **pytest + httpx** | Async test client |
| API Docs | Manual | **OpenAPI (auto)** | Generated from code |
| Configuration | python-dotenv | **Pydantic Settings** | Type-safe, validated |
| Dependency Mgmt | requirements.txt | **Poetry** | Lock file, better resolution |
| Code Quality | Manual | **Ruff + mypy** | Fast linting, type checking |

**Rationale for FastAPI:**
- Native async support (better for I/O-bound operations)
- Automatic OpenAPI documentation
- Type checking and validation
- Better performance (Starlette + Pydantic)
- Modern Python features (3.11+ type hints)
- Active development and community

## Migration Strategy

### Phase-Based Approach

**Phase 0: Preparation** (Week 1-2)
- Set up new project structure
- Configure tooling (Poetry, Ruff, mypy)
- Create base infrastructure (DB, Redis, config)

**Phase 1: Domain Layer** (Week 3-4)
- Extract domain models
- Define value objects
- Create domain events
- Write unit tests

**Phase 2: Infrastructure Layer** (Week 5-6)
- Implement repositories
- Set up event bus
- Configure database
- Create external API clients

**Phase 3: Application Layer** (Week 7-8)
- Build application services
- Implement use cases
- Add business logic
- Write integration tests

**Phase 4: API Layer** (Week 9-10)
- Create FastAPI routes
- Add authentication
- Implement middleware
- Generate API docs

**Phase 5: Services** (Week 11-12)
- Refactor audio service
- Refactor SDR service
- Refactor EAS service
- Update docker-compose

**Phase 6: Web UI** (Week 13-14)
- Update templates
- Refactor JavaScript
- Update asset pipeline
- Improve UX

**Phase 7: Testing & Documentation** (Week 15-16)
- Complete test coverage
- Write API documentation
- Create deployment guides
- Performance testing

## Testing Strategy

### Test Pyramid

```
         ┌───────────────┐
         │  E2E Tests    │  10% - Full scenarios
         │   (Slow)      │
         ├───────────────┤
         │ Integration   │  30% - Service integration
         │    Tests      │
         ├───────────────┤
         │  Unit Tests   │  60% - Fast, isolated
         │   (Fast)      │
         └───────────────┘
```

### Test Categories:

**Unit Tests** (60%)
- Domain models
- Value objects
- Business rules
- Pure functions
- No external dependencies

**Integration Tests** (30%)
- Repository implementations
- API endpoints
- Service interactions
- Database operations
- External API mocking

**E2E Tests** (10%)
- Complete user scenarios
- Alert processing pipeline
- EAS activation workflow
- Multi-service coordination

### Example Test Structure:

```python
# tests/unit/domain/test_alert.py
def test_alert_is_active():
    """Test alert active business rule"""
    alert = Alert(
        effective=datetime(2025, 1, 1, 12, 0),
        expires=datetime(2025, 1, 1, 18, 0),
        status=AlertStatus.ACTIVE
    )
    
    # Before effective time
    assert not alert.is_active(datetime(2025, 1, 1, 11, 0))
    
    # During active period
    assert alert.is_active(datetime(2025, 1, 1, 15, 0))
    
    # After expiration
    assert not alert.is_active(datetime(2025, 1, 1, 19, 0))

# tests/integration/api/test_alerts.py
async def test_create_alert(client: AsyncClient):
    """Test alert creation via API"""
    response = await client.post(
        "/api/alerts",
        json={
            "event_code": "TOR",
            "headline": "Tornado Warning",
            "severity": "Extreme"
        }
    )
    assert response.status_code == 201
    assert response.json()["event_code"] == "TOR"
```

## Benefits of New Architecture

### Developer Experience
✅ Clear project structure  
✅ Type safety throughout  
✅ Easy to test components  
✅ Predictable patterns  
✅ Auto-generated API docs  
✅ Fast feedback loop  

### Maintainability
✅ Single responsibility per module  
✅ Loosely coupled components  
✅ Easy to refactor  
✅ Clear dependencies  
✅ Self-documenting code  

### Scalability
✅ Service boundaries defined  
✅ Event-driven communication  
✅ Database connection pooling  
✅ Redis caching layer  
✅ Horizontal scaling ready  

### Reliability
✅ Comprehensive test coverage  
✅ Type checking catches errors  
✅ Validation at boundaries  
✅ Graceful error handling  
✅ Health checks built-in  

## Next Steps

1. **Review and approve** this architecture proposal
2. **Create Phase 0** implementation plan
3. **Set up new project structure** in parallel branch
4. **Begin domain model extraction**
5. **Iterate and refine** based on learnings

## Related Documents

- `CODEBASE_INVENTORY.md` - Current state analysis
- `REWRITE_ROADMAP.md` - Detailed phase-by-phase plan
- `MIGRATION_GUIDE.md` - Step-by-step migration instructions
- `CODING_STANDARDS.md` - Code style and conventions
