# EAS Station - Migration Guide

**Version**: 1.0  
**Date**: December 2025  
**Purpose**: Step-by-step instructions for migrating to the new architecture

## Overview

This guide provides detailed instructions for migrating from the current EAS Station codebase to the new clean architecture. It covers:

- Pre-migration preparation
- Phase-by-phase migration steps
- Database migration procedures
- Service switchover process
- Testing and validation
- Rollback procedures

## Prerequisites

### Knowledge Required
- Understanding of current codebase
- Familiarity with proposed architecture
- Python 3.11+ experience
- Docker and docker-compose knowledge
- PostgreSQL and Redis experience
- Git and version control

### Tools Needed
- Python 3.11+
- Poetry 1.7+
- Docker 24+
- PostgreSQL 17+
- Redis 7+
- Git 2.40+

### Documentation to Read
1. `CODEBASE_INVENTORY.md` - Understand current state
2. `REWRITE_ARCHITECTURE.md` - Understand target architecture
3. `REWRITE_ROADMAP.md` - Understand phases and timeline

## Pre-Migration Checklist

### Backup Everything
- [ ] Backup production database
- [ ] Backup Redis data
- [ ] Backup configuration files
- [ ] Backup custom modifications
- [ ] Export current alerts
- [ ] Document current settings

### Prepare Development Environment
- [ ] Clone repository
- [ ] Create feature branch
- [ ] Set up Python virtual environment
- [ ] Install Poetry
- [ ] Configure development tools
- [ ] Set up test databases

### Team Preparation
- [ ] Schedule migration window
- [ ] Notify users of changes
- [ ] Assign responsibilities
- [ ] Prepare rollback plan
- [ ] Set up monitoring
- [ ] Create communication channels

---

## Phase 0: Preparation (Weeks 1-2)

### Week 1: Project Setup

#### Day 1: Create New Structure

**1. Create src/ directory:**
```bash
cd /home/runner/work/eas-station/eas-station
mkdir -p src/{api,domain,application,infrastructure,services,shared}
```

**2. Initialize Poetry:**
```bash
# Create pyproject.toml
poetry init \
  --name eas-station \
  --description "Emergency Alert System Platform" \
  --python "^3.11" \
  --no-interaction

# Add dependencies
poetry add fastapi[all] sqlmodel pydantic pydantic-settings
poetry add redis hiredis orjson uvicorn[standard]
poetry add alembic psycopg2-binary geoalchemy2

# Add dev dependencies
poetry add --group dev pytest pytest-asyncio pytest-cov
poetry add --group dev ruff mypy types-redis
poetry add --group dev httpx

# Install dependencies
poetry install
```

**3. Configure tools:**
```toml
# pyproject.toml additions
[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]

[tool.ruff.isort]
known-first-party = ["src"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

**4. Set up pre-commit:**
```bash
# Install pre-commit
poetry add --group dev pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-redis]
EOF

# Install hooks
poetry run pre-commit install
```

#### Day 2-3: Configuration System

**1. Create settings module:**
```python
# src/infrastructure/config/settings.py
from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseSettings(BaseSettings):
    """Database configuration"""
    model_config = SettingsConfigDict(env_prefix="POSTGRES_")
    
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    user: str = Field(default="postgres")
    password: str = Field(default="postgres")
    db: str = Field(default="alerts", alias="database")
    
    @property
    def url(self) -> str:
        return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

class RedisSettings(BaseSettings):
    """Redis configuration"""
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    password: str | None = Field(default=None)

class EASSettings(BaseSettings):
    """EAS configuration"""
    model_config = SettingsConfigDict(env_prefix="EAS_")
    
    broadcast_enabled: bool = Field(default=False)
    originator: str = Field(default="WXR")
    station_id: str = Field(default="")

class Settings(BaseSettings):
    """Master configuration"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__"
    )
    
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    eas: EASSettings = Field(default_factory=EASSettings)
    
    secret_key: str = Field(..., min_length=32)
    debug: bool = Field(default=False)

# Create singleton
settings = Settings()
```

**2. Test configuration:**
```python
# tests/unit/config/test_settings.py
from src.infrastructure.config.settings import Settings

def test_settings_load():
    """Test configuration loads"""
    settings = Settings(_env_file=".env.test")
    assert settings.database.host is not None
    assert settings.redis.host is not None
```

#### Day 4-5: Database Layer

**1. Set up database connection:**
```python
# src/infrastructure/database/connection.py
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from ..config.settings import settings

# Create async engine
engine: AsyncEngine = create_async_engine(
    settings.database.url.replace("postgresql+psycopg2://", "postgresql+asyncpg://"),
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Create session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db_session() -> AsyncSession:
    """Dependency for database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**2. Initialize Alembic:**
```bash
# Initialize Alembic in new location
poetry run alembic init src/infrastructure/database/migrations

# Update alembic.ini
sed -i 's|script_location = alembic|script_location = src/infrastructure/database/migrations|' alembic.ini
```

**3. Test database connection:**
```python
# tests/integration/database/test_connection.py
import pytest
from sqlalchemy import text
from src.infrastructure.database.connection import get_db_session

@pytest.mark.asyncio
async def test_database_connection():
    """Test database connectivity"""
    async with get_db_session() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
```

---

## Phase 1: Domain Layer (Weeks 3-4)

### Extracting Domain Models

#### Step 1: Analyze Current Models

**Identify entities in current code:**
```bash
# Find all SQLAlchemy models
grep -r "class.*db.Model" app_core/models.py

# Find all domain logic
grep -r "def.*is_.*:" app_core/
```

#### Step 2: Extract Alert Domain

**1. Create domain model:**
```python
# src/domain/models/alert.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from enum import Enum

class AlertStatus(str, Enum):
    """Alert status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class Severity(str, Enum):
    """Alert severity levels"""
    EXTREME = "Extreme"
    SEVERE = "Severe"
    MODERATE = "Moderate"
    MINOR = "Minor"
    UNKNOWN = "Unknown"

@dataclass
class Alert:
    """Pure domain model for weather/emergency alerts"""
    
    # Identity
    id: str
    cap_id: str
    
    # Content
    event_code: str
    headline: str
    description: str
    
    # Classification
    severity: Severity
    urgency: str
    certainty: str
    category: str
    
    # Geographic
    affected_areas: List[str] = field(default_factory=list)
    
    # Temporal
    effective: datetime
    expires: datetime
    onset: datetime | None = None
    
    # Status
    status: AlertStatus = AlertStatus.ACTIVE
    
    # Source
    source: str = "NOAA"
    source_url: str | None = None
    
    def is_active_at(self, check_time: datetime) -> bool:
        """Business rule: Check if alert is active at given time"""
        if self.status != AlertStatus.ACTIVE:
            return False
        
        return self.effective <= check_time < self.expires
    
    def affects_area(self, fips_code: str) -> bool:
        """Business rule: Check if alert affects given area"""
        return fips_code in self.affected_areas
    
    def is_severe(self) -> bool:
        """Business rule: Check if alert is severe"""
        return self.severity in {Severity.EXTREME, Severity.SEVERE}
```

**2. Create value objects:**
```python
# src/domain/value_objects/fips_code.py
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class FIPSCode:
    """FIPS code value object"""
    
    code: str
    
    def __post_init__(self):
        """Validate FIPS code format"""
        if not self._is_valid():
            raise ValueError(f"Invalid FIPS code: {self.code}")
    
    def _is_valid(self) -> bool:
        """Validate FIPS code format (6 digits)"""
        return bool(re.match(r'^\d{6}$', self.code))
    
    @property
    def state(self) -> str:
        """Extract state code (first 2 digits)"""
        return self.code[:2]
    
    @property
    def county(self) -> str:
        """Extract county code (last 3 digits)"""
        return self.code[2:5]
    
    @property
    def subdivision(self) -> str:
        """Extract subdivision (last digit)"""
        return self.code[5]
```

**3. Create domain events:**
```python
# src/domain/events/alert_received.py
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class AlertReceived:
    """Domain event: New alert received"""
    
    alert_id: str
    event_code: str
    severity: str
    timestamp: datetime
    source: str
```

**4. Write unit tests:**
```python
# tests/unit/domain/test_alert.py
from datetime import datetime, timedelta
from src.domain.models.alert import Alert, AlertStatus, Severity

def test_alert_is_active():
    """Test alert active status"""
    now = datetime.now()
    alert = Alert(
        id="test-1",
        cap_id="cap-1",
        event_code="TOR",
        headline="Test",
        description="Test",
        severity=Severity.EXTREME,
        urgency="Immediate",
        certainty="Observed",
        category="Met",
        effective=now - timedelta(hours=1),
        expires=now + timedelta(hours=1)
    )
    
    assert alert.is_active_at(now)
    assert not alert.is_active_at(now + timedelta(hours=2))

def test_alert_affects_area():
    """Test geographic filtering"""
    alert = Alert(
        # ... required fields ...
        affected_areas=["039001", "039003"]
    )
    
    assert alert.affects_area("039001")
    assert not alert.affects_area("039999")
```

#### Step 3: Repeat for Other Domains

**Follow same pattern for:**
- EAS Message domain (`src/domain/models/eas_message.py`)
- Boundary domain (`src/domain/models/boundary.py`)
- Radio Receiver domain (`src/domain/models/radio_receiver.py`)
- User domain (`src/domain/models/user.py`)

**Each should have:**
1. Pure domain model (no framework dependencies)
2. Value objects for complex types
3. Business rules as methods
4. Domain events for state changes
5. Comprehensive unit tests

---

## Phase 2: Infrastructure Layer (Weeks 5-6)

### Implementing Repositories

#### Step 1: Create Repository Interface

```python
# src/application/interfaces/repositories.py
from abc import ABC, abstractmethod
from typing import List, Optional
from ...domain.models.alert import Alert

class AlertRepository(ABC):
    """Repository interface for alerts"""
    
    @abstractmethod
    async def save(self, alert: Alert) -> Alert:
        """Save alert to storage"""
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
    async def find_by_area(self, fips_code: str) -> List[Alert]:
        """Find alerts affecting area"""
        pass
```

#### Step 2: Implement Repository

```python
# src/infrastructure/database/repositories/alert_repo.py
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ....application.interfaces.repositories import AlertRepository
from ....domain.models.alert import Alert
from ..models.alert_model import AlertModel

class SQLAlertRepository(AlertRepository):
    """PostgreSQL implementation of AlertRepository"""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, alert: Alert) -> Alert:
        """Save alert to PostgreSQL"""
        # Convert domain model to database model
        db_alert = AlertModel.from_domain(alert)
        
        # Merge or add
        self._session.add(db_alert)
        await self._session.flush()
        await self._session.refresh(db_alert)
        
        # Convert back to domain model
        return db_alert.to_domain()
    
    async def find_by_id(self, alert_id: str) -> Optional[Alert]:
        """Find alert by ID"""
        stmt = select(AlertModel).where(AlertModel.id == alert_id)
        result = await self._session.execute(stmt)
        db_alert = result.scalar_one_or_none()
        
        if db_alert is None:
            return None
        
        return db_alert.to_domain()
    
    async def find_active(self) -> List[Alert]:
        """Find active alerts"""
        stmt = select(AlertModel).where(
            AlertModel.status == "active"
        )
        result = await self._session.execute(stmt)
        db_alerts = result.scalars().all()
        
        return [alert.to_domain() for alert in db_alerts]
```

#### Step 3: Create Database Models

```python
# src/infrastructure/database/models/alert_model.py
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import List
from .base import Base
from ....domain.models.alert import Alert, AlertStatus, Severity

class AlertModel(Base):
    """SQLAlchemy model for alerts"""
    __tablename__ = "cap_alerts"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    cap_id: Mapped[str] = mapped_column(String, unique=True)
    event_code: Mapped[str] = mapped_column(String)
    headline: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    urgency: Mapped[str] = mapped_column(String)
    certainty: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    affected_areas: Mapped[List[str]] = mapped_column(JSON)
    effective: Mapped[datetime] = mapped_column(DateTime)
    expires: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    
    @classmethod
    def from_domain(cls, alert: Alert) -> "AlertModel":
        """Convert domain model to database model"""
        return cls(
            id=alert.id,
            cap_id=alert.cap_id,
            event_code=alert.event_code,
            headline=alert.headline,
            description=alert.description,
            severity=alert.severity.value,
            urgency=alert.urgency,
            certainty=alert.certainty,
            category=alert.category,
            affected_areas=alert.affected_areas,
            effective=alert.effective,
            expires=alert.expires,
            status=alert.status.value,
            source=alert.source,
        )
    
    def to_domain(self) -> Alert:
        """Convert database model to domain model"""
        return Alert(
            id=self.id,
            cap_id=self.cap_id,
            event_code=self.event_code,
            headline=self.headline,
            description=self.description,
            severity=Severity(self.severity),
            urgency=self.urgency,
            certainty=self.certainty,
            category=self.category,
            affected_areas=self.affected_areas,
            effective=self.effective,
            expires=self.expires,
            status=AlertStatus(self.status),
            source=self.source,
        )
```

#### Step 4: Test Repository

```python
# tests/integration/database/test_alert_repo.py
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.models.alert import Alert, AlertStatus, Severity
from src.infrastructure.database.repositories.alert_repo import SQLAlertRepository

@pytest.mark.asyncio
async def test_save_alert(db_session: AsyncSession):
    """Test saving alert"""
    repo = SQLAlertRepository(db_session)
    
    alert = Alert(
        id="test-1",
        cap_id="cap-1",
        event_code="TOR",
        headline="Test Tornado",
        description="Test description",
        severity=Severity.EXTREME,
        urgency="Immediate",
        certainty="Observed",
        category="Met",
        effective=datetime.now(),
        expires=datetime.now() + timedelta(hours=1)
    )
    
    saved = await repo.save(alert)
    assert saved.id == alert.id

@pytest.mark.asyncio
async def test_find_alert(db_session: AsyncSession):
    """Test finding alert"""
    repo = SQLAlertRepository(db_session)
    
    # Save first
    alert = Alert(...)  # Create test alert
    await repo.save(alert)
    
    # Find
    found = await repo.find_by_id(alert.id)
    assert found is not None
    assert found.id == alert.id
```

---

## Phase 3: Application Layer (Weeks 7-8)

### Building Application Services

#### Step 1: Create Service Interface

```python
# src/application/services/alert_service.py
from typing import List
from ..interfaces.repositories import AlertRepository
from ..interfaces.event_bus import EventBus
from ...domain.models.alert import Alert
from ...domain.events.alert_received import AlertReceived

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
        # 1. Create domain model from raw data
        alert = self._create_alert_from_data(alert_data)
        
        # 2. Validate business rules
        if not self._is_valid_alert(alert):
            raise ValueError("Invalid alert")
        
        # 3. Save to repository
        saved_alert = await self._repo.save(alert)
        
        # 4. Publish domain event
        await self._events.publish(
            AlertReceived(
                alert_id=saved_alert.id,
                event_code=saved_alert.event_code,
                severity=saved_alert.severity.value,
                timestamp=saved_alert.effective,
                source=saved_alert.source
            )
        )
        
        return saved_alert
    
    async def get_active_alerts_for_area(
        self,
        fips_code: str
    ) -> List[Alert]:
        """Get active alerts affecting an area"""
        # Get all active alerts
        active_alerts = await self._repo.find_active()
        
        # Filter by area
        return [
            alert for alert in active_alerts
            if alert.affects_area(fips_code)
        ]
```

#### Step 2: Implement Use Cases

```python
# src/application/use_cases/activate_eas.py
from dataclasses import dataclass
from ..services.alert_service import AlertService
from ..services.eas_service import EASService

@dataclass
class ActivateEASRequest:
    """Request to activate EAS"""
    alert_id: str
    originator: str
    event_code: str
    areas: list[str]
    duration: int

class ActivateEASUseCase:
    """Use case for activating EAS broadcast"""
    
    def __init__(
        self,
        alert_service: AlertService,
        eas_service: EASService
    ):
        self._alerts = alert_service
        self._eas = eas_service
    
    async def execute(self, request: ActivateEASRequest):
        """Execute EAS activation"""
        # 1. Validate alert exists
        alert = await self._alerts.get_alert(request.alert_id)
        if alert is None:
            raise ValueError(f"Alert not found: {request.alert_id}")
        
        # 2. Generate SAME header
        same_header = await self._eas.generate_same_header(
            originator=request.originator,
            event_code=request.event_code,
            areas=request.areas,
            duration=request.duration
        )
        
        # 3. Generate audio
        audio = await self._eas.generate_audio(
            same_header=same_header,
            alert_text=alert.description
        )
        
        # 4. Queue for broadcast
        await self._eas.queue_broadcast(audio)
        
        return {
            "success": True,
            "same_header": same_header,
            "broadcast_queued": True
        }
```

---

## Phase 4: API Layer (Weeks 9-10)

### Creating FastAPI Application

#### Step 1: Set Up FastAPI

```python
# src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .middleware import auth_middleware, logging_middleware
from .routes import alerts, eas, audio, boundaries, users

# Create FastAPI app
app = FastAPI(
    title="EAS Station API",
    description="Emergency Alert System Platform API",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(logging_middleware)
app.middleware("http")(auth_middleware)

# Include routers
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(eas.router, prefix="/api/eas", tags=["eas"])
app.include_router(audio.router, prefix="/api/audio", tags=["audio"])
app.include_router(boundaries.router, prefix="/api/boundaries", tags=["boundaries"])
app.include_router(users.router, prefix="/api/users", tags=["users"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
```

#### Step 2: Create API Routes

```python
# src/api/routes/alerts.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..dependencies import get_alert_service
from ..schemas.alert import AlertResponse, AlertCreate
from ...application.services.alert_service import AlertService

router = APIRouter()

@router.get("/", response_model=List[AlertResponse])
async def list_alerts(
    service: AlertService = Depends(get_alert_service)
):
    """List all active alerts"""
    alerts = await service.get_active_alerts()
    return alerts

@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    service: AlertService = Depends(get_alert_service)
):
    """Get alert by ID"""
    alert = await service.get_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@router.post("/", response_model=AlertResponse, status_code=201)
async def create_alert(
    alert_data: AlertCreate,
    service: AlertService = Depends(get_alert_service)
):
    """Create new alert"""
    alert = await service.process_incoming_alert(alert_data.dict())
    return alert
```

#### Step 3: Define Pydantic Schemas

```python
# src/api/schemas/alert.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List

class AlertBase(BaseModel):
    """Base alert schema"""
    event_code: str = Field(..., min_length=3, max_length=3)
    headline: str = Field(..., min_length=1)
    description: str
    severity: str
    urgency: str
    certainty: str

class AlertCreate(AlertBase):
    """Schema for creating alerts"""
    affected_areas: List[str] = Field(default_factory=list)
    effective: datetime
    expires: datetime

class AlertResponse(AlertBase):
    """Schema for alert responses"""
    id: str
    cap_id: str
    affected_areas: List[str]
    effective: datetime
    expires: datetime
    status: str
    source: str
    
    class Config:
        from_attributes = True
```

---

## Testing Migration

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test categories
poetry run pytest -m unit
poetry run pytest -m integration
poetry run pytest -m e2e
```

### Continuous Integration

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgis/postgis:17-3.4
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: alerts_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install Poetry
        run: pipx install poetry
      
      - name: Install dependencies
        run: poetry install
      
      - name: Run linting
        run: poetry run ruff check src tests
      
      - name: Run type checking
        run: poetry run mypy src
      
      - name: Run tests
        run: poetry run pytest --cov=src
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/alerts_test
          REDIS_HOST: localhost
```

---

## Deployment

### Docker Build

```dockerfile
# Dockerfile.new
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.7.1

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-root

# Copy source code
COPY src ./src
COPY alembic.ini ./

# Run migrations and start app
CMD ["sh", "-c", "poetry run alembic upgrade head && poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000"]
```

### Docker Compose Update

```yaml
# docker-compose.new.yml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.new
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/alerts
      REDIS_HOST: redis
      SECRET_KEY: ${SECRET_KEY}
    depends_on:
      - db
      - redis
    
  # ... other services
```

---

## Rollback Procedures

### If Issues Occur

**1. Immediate Rollback:**
```bash
# Stop new services
docker-compose -f docker-compose.new.yml down

# Restart old services
docker-compose up -d
```

**2. Database Rollback:**
```bash
# Revert to previous migration
poetry run alembic downgrade -1

# Or restore from backup
psql -U postgres alerts < backup.sql
```

**3. Redis Rollback:**
```bash
# Clear Redis and restart
docker exec eas-redis redis-cli FLUSHDB
docker-compose restart redis
```

---

## Success Criteria

### Migration Complete When:
- [ ] All tests pass (>80% coverage)
- [ ] No data loss verified
- [ ] All features working
- [ ] Performance acceptable
- [ ] Documentation complete
- [ ] Team trained
- [ ] Monitoring configured
- [ ] Rollback tested

---

## Support & Resources

### Getting Help
- Documentation: `docs/architecture/`
- GitHub Issues: Report problems
- Team Chat: Real-time support
- Wiki: Additional guides

### Training
- Architecture overview session
- Code walkthrough
- Hands-on workshop
- Q&A sessions

---

## Conclusion

This migration guide provides a comprehensive path to the new architecture. Follow each phase carefully, test thoroughly, and don't hesitate to ask for help.

**Remember:**
- Take it slow and steady
- Test everything
- Document as you go
- Communicate with team
- Be prepared to rollback

Good luck with the migration!
