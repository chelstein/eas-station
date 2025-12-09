# Flask to FastAPI Migration Guide

## Overview

This document tracks the migration of EAS Station from Flask to FastAPI. The migration is being done gradually to minimize risk and allow for incremental testing.

## Migration Status

**IMPORTANT**: This is a **gradual migration**. Both Flask and FastAPI are installed and can run simultaneously. The Flask app (port 5000) remains the production app while FastAPI (port 8080) is being developed.

### ✅ Completed

1. **Dependencies Updated** (`requirements.txt`)
   - ✅ **Flask kept** - Flask==3.0.3 + all extensions (WSGI, port 5000)
   - ✅ **FastAPI added** - FastAPI + Uvicorn (ASGI, port 8080)
   - ✅ **Shared libraries** - SQLAlchemy, Jinja2, Redis, python-socketio
   - ✅ **Both servers** - Gunicorn (Flask) + Uvicorn (FastAPI)

2. **Minimal Working FastAPI App** (`fastapi_app_minimal.py`)
   - ✅ Basic FastAPI application structure
   - ✅ Lifespan context for startup/shutdown
   - ✅ CORS middleware
   - ✅ Session middleware
   - ✅ Health check endpoint (`/health`)
   - ✅ System status endpoint (`/api/status`)
   - ✅ Version endpoint (`/api/version`)
   - ✅ Error handlers (404, 500)
   - ✅ Auto-generated API docs (`/docs`, `/redoc`)

3. **Infrastructure**
   - ✅ Startup script (`run_fastapi.sh`)
   - ✅ FastAPI extensions module for database (`app_core/fastapi_extensions.py`)

### 🚧 In Progress

- Database integration with existing models
- Route migration framework

### ⏳ Pending

- Authentication system (session-based + MFA)
- CSRF protection
- WebSocket support (Socket.IO for real-time updates)
- Caching layer (Redis)
- Background workers refactoring
- Template rendering
- Rate limiting
- Route migrations:
  - 0/51 route modules migrated
  - Priority routes: authentication, public APIs, admin dashboard

## Running the Applications

### FastAPI (Port 8080)

```bash
# Development mode with auto-reload
./run_fastapi.sh dev

# Production mode
./run_fastapi.sh prod

# Or directly with uvicorn
uvicorn fastapi_app_minimal:app --reload --port 8080
```

**Endpoints:**
- `http://localhost:8080/` - Landing page
- `http://localhost:8080/health` - Health check
- `http://localhost:8080/api/status` - System status
- `http://localhost:8080/docs` - Interactive API documentation
- `http://localhost:8080/redoc` - ReDoc documentation

**Note:** Port 8000 is reserved for Icecast (audio streaming)

### Flask (Port 5000) - Legacy

```bash
# Still operational for comparison/fallback
gunicorn -w 1 -k gevent --bind 0.0.0.0:5000 wsgi:app
```

## Migration Strategy

### Phase 1: Foundation (✅ Complete)
- Set up minimal FastAPI app
- Create database abstraction layer
- Establish deployment patterns

### Phase 2: Core Features (Current)
- Migrate database models to pure SQLAlchemy
- Implement authentication system
- Add CSRF protection
- Set up caching

### Phase 3: Route Migration (Next)
Priority order for route migration:

1. **Public APIs** (no auth required)
   - `/api/alerts`
   - `/api/boundaries`
   - `/api/system_status`
   - `/api/system_health`

2. **Authentication**
   - `/login`
   - `/logout`
   - `/mfa/enroll`
   - `/mfa/verify`

3. **Admin APIs**
   - User management
   - System configuration
   - Alert management

4. **Real-time Features**
   - WebSocket implementation
   - Audio monitoring
   - System health updates

5. **Remaining Routes**
   - EAS workflow
   - Radio receivers
   - LED/VFD displays
   - Analytics
   - etc. (47 modules remaining)

### Phase 4: Background Workers
- Refactor RWT scheduler
- Update health monitoring
- Migrate screen manager
- Update analytics scheduler

### Phase 5: Production Cutover
- Performance testing
- Load testing
- Security audit
- Gradual traffic migration
- Flask deprecation

## Technical Decisions

### Why FastAPI?

1. **Performance**: ASGI-based, async/await support
2. **Modern Python**: Type hints, Pydantic validation
3. **Auto Documentation**: OpenAPI/Swagger built-in
4. **WebSocket**: Native async WebSocket support
5. **Ecosystem**: Large and growing community

### Architecture Changes

| Aspect | Flask | FastAPI |
|--------|-------|---------|
| Protocol | WSGI (sync) | ASGI (async) |
| Server | Gunicorn + gevent | Uvicorn |
| Sessions | Flask sessions | Starlette SessionMiddleware |
| Database | Flask-SQLAlchemy | Pure SQLAlchemy 2.0 |
| WebSocket | Flask-SocketIO + gevent | Native async WebSocket + Socket.IO |
| Request Context | Flask's `g`, `session`, `current_app` | FastAPI's `Request`, `Depends()` |
| CSRF | Custom Flask middleware | Custom FastAPI middleware |
| Rate Limiting | Flask-Limiter | Slowapi |
| Caching | Flask-Caching | Custom async cache |

### Compatibility Layer

To minimize code changes, we're creating compatibility wrappers:

- **Database**: `app_core/fastapi_extensions.py` provides similar API to Flask-SQLAlchemy
- **Sessions**: Starlette's SessionMiddleware maintains session compatibility
- **Authentication**: Custom dependency injection for user context

## Testing Strategy

### Unit Tests
- Test individual endpoints
- Test database operations
- Test authentication logic

### Integration Tests
- Test route workflows
- Test WebSocket connections
- Test background workers

### Performance Tests
- Compare Flask vs FastAPI response times
- Load testing with realistic traffic
- WebSocket performance

### Migration Validation
- Run both Flask and FastAPI in parallel
- Compare responses for identical requests
- Verify data consistency

## Rollback Plan

If issues arise during migration:

1. **Immediate**: Reverse proxy routes back to Flask
2. **Short-term**: Revert FastAPI changes, continue with Flask
3. **Long-term**: Address issues incrementally in FastAPI

## Key Files

### New Files
- `fastapi_app_minimal.py` - Minimal working FastAPI app
- `fastapi_app.py` - Full FastAPI app (WIP, has Flask dependencies)
- `app_core/fastapi_extensions.py` - Database layer for FastAPI
- `run_fastapi.sh` - Startup script
- `MIGRATION.md` - This file

### Modified Files
- `requirements.txt` - Added FastAPI dependencies
- Future: Route modules will be migrated incrementally

### Unchanged Files
- All existing Flask code remains operational
- `app.py` - Original Flask application
- `wsgi.py` - Flask WSGI entry point
- All route modules in `webapp/`
- All models in `app_core/models.py`

## Development Workflow

1. **Start FastAPI**: `./run_fastapi.sh dev`
2. **Make changes**: Edit `fastapi_app_minimal.py` or route modules
3. **Auto-reload**: Uvicorn detects changes and reloads
4. **Test**: Visit `http://localhost:8000/docs` for interactive API testing
5. **Commit**: Git commit your changes
6. **Deploy**: Push to branch `claude/flask-to-fastapi-migration-*`

## Common Tasks

### Adding a New Endpoint

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["example"])

@router.get("/example")
async def example_endpoint():
    return {"message": "Hello from FastAPI!"}

# In fastapi_app_minimal.py
app.include_router(router)
```

### Database Access

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app_core.fastapi_extensions import get_db

@app.get("/api/users")
async def get_users(db: Session = Depends(get_db)):
    # Use db session here
    users = db.query(AdminUser).all()
    return {"users": users}
```

### Authentication Dependency

```python
from fastapi import Depends, HTTPException

async def get_current_user(request: Request):
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Load user from database
    return user

@app.get("/api/protected")
async def protected_route(user = Depends(get_current_user)):
    return {"user": user.username}
```

## Performance Benchmarks

TODO: Add benchmarks comparing Flask vs FastAPI

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Starlette Documentation](https://www.starlette.io/)

## Questions or Issues?

Contact the development team or open an issue on GitHub.

---

**Last Updated**: 2025-12-09
**Migration Progress**: ~5% (3/51 route modules + core infrastructure)
