# app.py Refactoring Plan - Function Extraction

**Date**: December 2025  
**Purpose**: Document the complete refactoring plan to extract all functions from app.py into properly organized modules  
**Current State**: app.py has 1,296 lines with 29 functions - needs professional hierarchical organization

## Current Problems

1. **Monolithic Structure**: 1,296 lines in a single file
2. **Mixed Responsibilities**: Configuration, error handling, database init, file operations, CLI commands all in one file
3. **Poor Maintainability**: Changes require navigating a massive file
4. **Testing Challenges**: Hard to test individual functions in isolation
5. **Unclear Dependencies**: Function relationships are unclear

## Refactoring Principles

1. **Single Responsibility**: Each module handles one aspect of the system
2. **Clear Hierarchy**: Logical organization matching professional standards
3. **Separation of Concerns**: Configuration ≠ Error Handling ≠ Database Init
4. **Testability**: Each module can be tested independently
5. **Maintainability**: Easy to find and modify specific functionality

## Proposed File Structure

```
app_core/
├── config/
│   ├── __init__.py
│   ├── environment.py        # Environment variable parsing
│   ├── database.py           # Database URL construction
│   └── security.py           # SECRET_KEY, CSRF configuration
├── database/
│   ├── __init__.py
│   ├── connectivity.py       # Connection checking and retry logic
│   ├── initialization.py     # Database initialization and migrations
│   └── postgis.py            # PostGIS extension management
├── eas/
│   ├── __init__.py
│   └── file_operations.py    # EAS file loading, caching, deletion
├── flask/
│   ├── __init__.py
│   ├── error_handlers.py     # 404, 500, 403, 400 error handlers
│   ├── request_hooks.py      # before_request, after_request
│   ├── template_filters.py   # shields_escape_filter, etc.
│   ├── context_processors.py # inject_global_vars
│   └── csrf.py               # CSRF token generation and validation
├── cli/
│   ├── __init__.py
│   ├── admin.py              # create_admin_user_cli
│   ├── testing.py            # test_led
│   ├── maintenance.py        # cleanup_expired, init_db
│   └── database.py           # Database CLI commands
└── datetime/
    ├── __init__.py
    └── parsing.py            # parse_nws_datetime wrapper
```

## Detailed Function Mapping

### 1. Configuration Module (`app_core/config/`)

#### `app_core/config/environment.py`
**Purpose**: Parse environment variables into typed values

**Functions to Extract**:
- `_parse_env_list(name: str) -> List[str]` (Line 271)
  - Parses comma-separated environment variable
  - Used for: COMPLIANCE_ALERT_EMAILS, COMPLIANCE_SNMP_TARGETS
  
- `_parse_int_env(name: str, default: int) -> int` (Line 278)
  - Parses integer from environment with fallback
  - Used for: COMPLIANCE_HEALTH_INTERVAL, thresholds

**New Public API**:
```python
from app_core.config.environment import parse_env_list, parse_int_env

emails = parse_env_list('COMPLIANCE_ALERT_EMAILS')
interval = parse_int_env('COMPLIANCE_HEALTH_INTERVAL', 300)
```

**Dependencies**:
- Standard library: `os`
- No app dependencies

**Tests to Create**:
- `tests/unit/config/test_environment.py`
  - Test empty environment variable
  - Test comma-separated list parsing
  - Test integer parsing with valid/invalid values
  - Test default fallback behavior

---

#### `app_core/config/database.py`
**Purpose**: Construct database connection URLs

**Functions to Extract**:
- `_build_database_url() -> str` (Line 372)
  - Builds PostgreSQL URL from POSTGRES_* variables or DATABASE_URL
  - Handles URL encoding of special characters
  - Provides sensible defaults

**New Public API**:
```python
from app_core.config.database import build_database_url

DATABASE_URL = build_database_url()
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
```

**Dependencies**:
- Standard library: `os`, `urllib.parse.quote`
- No app dependencies

**Tests to Create**:
- `tests/unit/config/test_database.py`
  - Test DATABASE_URL takes precedence
  - Test building from POSTGRES_* variables
  - Test special character encoding
  - Test default values

---

#### `app_core/config/security.py`
**Purpose**: Security configuration (SECRET_KEY, CSRF)

**Configuration to Extract**:
- SECRET_KEY validation and generation (Lines 322-336)
- CSRF configuration constants (Lines 315-320)
- PUBLIC_API_GET_PATHS (Lines 299-314)

**Functions to Extract**:
- Secret key validation logic
- CSRF configuration setup

**New Public API**:
```python
from app_core.config.security import (
    setup_secret_key,
    get_csrf_config,
    PUBLIC_API_GET_PATHS
)

secret_key, setup_mode_active = setup_secret_key()
app.secret_key = secret_key
```

**Dependencies**:
- Standard library: `os`, `secrets`
- No app dependencies

**Tests to Create**:
- `tests/unit/config/test_security.py`
  - Test placeholder key detection
  - Test short key detection
  - Test random key generation
  - Test CSRF configuration

---

### 2. Database Module (`app_core/database/`)

#### `app_core/database/connectivity.py`
**Purpose**: Database connection testing and retry logic

**Functions to Extract**:
- `_check_database_connectivity(max_retries: int, initial_backoff: float) -> bool` (Line 556)
  - Retries connection with exponential backoff
  - Logs connection attempts
  - Returns success/failure

**New Public API**:
```python
from app_core.database.connectivity import check_database_connectivity

if not check_database_connectivity(max_retries=5):
    logger.error("Database connection failed")
```

**Dependencies**:
- `time` module
- `sqlalchemy` engine
- `logging`

**Tests to Create**:
- `tests/unit/database/test_connectivity.py`
  - Test successful connection
  - Test retry logic with mock failures
  - Test exponential backoff timing
  - Test max retries exceeded

---

#### `app_core/database/initialization.py`
**Purpose**: Database initialization and schema setup

**Functions to Extract**:
- `initialize_database()` (Line 1017)
  - Main database initialization orchestrator
  - Calls all ensure_* functions
  - Sets up migrations and extensions
  
- `_initialize_database_with_error_check()` (Line 1147)
  - Wrapper with error handling
  - Used in create_app()

**New Public API**:
```python
from app_core.database.initialization import (
    initialize_database,
    initialize_database_safely
)

# Called during app startup
initialize_database_safely()
```

**Dependencies**:
- `app_core.models`
- All `ensure_*` functions from various modules
- `db` (SQLAlchemy)
- `logger`

**Tests to Create**:
- `tests/integration/database/test_initialization.py`
  - Test full initialization sequence
  - Test error handling
  - Test idempotency (can run multiple times)
  - Test each ensure_* function call

---

#### `app_core/database/postgis.py`
**Purpose**: PostGIS extension management

**Functions to Extract**:
- `ensure_postgis_extension() -> bool` (Line 618)
  - Checks for PostGIS extension
  - Creates extension if missing
  - Handles permissions gracefully

**New Public API**:
```python
from app_core.database.postgis import ensure_postgis_extension

if not ensure_postgis_extension():
    logger.warning("PostGIS not available")
```

**Dependencies**:
- `db` (SQLAlchemy)
- `sqlalchemy.text`
- `logger`

**Tests to Create**:
- `tests/integration/database/test_postgis.py`
  - Test extension exists check
  - Test extension creation
  - Test permission denied handling
  - Test with/without superuser privileges

---

### 3. EAS File Operations Module (`app_core/eas/`)

#### `app_core/eas/file_operations.py`
**Purpose**: EAS file loading, caching, and deletion

**Functions to Extract**:
- `_get_eas_output_root() -> Optional[str]` (Line 407)
  - Gets EAS_OUTPUT_DIR from config
  
- `_get_eas_static_prefix() -> str` (Line 412)
  - Gets web subdirectory for EAS files
  
- `_resolve_eas_disk_path(filename: Optional[str]) -> Optional[str]` (Line 416)
  - Resolves filename to safe absolute path
  - Validates path is within output root
  - Prevents directory traversal attacks
  
- `_load_or_cache_audio_data(message: EASMessage, *, variant: str) -> Optional[bytes]` (Line 442)
  - Loads audio from database or disk
  - Caches in database for performance
  - Handles primary and EOM variants
  
- `_load_or_cache_summary_payload(message: EASMessage) -> Optional[Dict]` (Line 481)
  - Loads text payload from database or disk
  - Caches JSON payloads
  
- `_remove_eas_files(message: EASMessage) -> None` (Line 506)
  - Deletes audio, text, and EOM files
  - Handles missing files gracefully

**New Public API**:
```python
from app_core.eas.file_operations import (
    get_eas_output_root,
    get_eas_static_prefix,
    resolve_eas_disk_path,
    load_or_cache_audio_data,
    load_or_cache_summary_payload,
    remove_eas_files
)

# Load audio for message
audio_data = load_or_cache_audio_data(message, variant='primary')
eom_data = load_or_cache_audio_data(message, variant='eom')

# Clean up files
remove_eas_files(message)
```

**Dependencies**:
- `app_core.models.EASMessage`
- `db` (SQLAlchemy)
- Standard library: `os`, `json`
- `logger`

**Tests to Create**:
- `tests/unit/eas/test_file_operations.py`
  - Test path resolution with valid paths
  - Test path traversal prevention
  - Test caching behavior
  - Test missing file handling
  - Test file deletion

---

### 4. Flask Lifecycle Module (`app_core/flask/`)

#### `app_core/flask/error_handlers.py`
**Purpose**: HTTP error handlers (404, 500, 403, 400)

**Functions to Extract**:
- `not_found_error(error)` (Line 709) - 404 handler
- `internal_error(error)` (Line 717) - 500 handler
- `forbidden_error(error)` (Line 728) - 403 handler
- `bad_request_error(error)` (Line 736) - 400 handler

**New Public API**:
```python
from app_core.flask.error_handlers import (
    handle_not_found,
    handle_internal_error,
    handle_forbidden,
    handle_bad_request,
    register_error_handlers
)

# Register all handlers at once
register_error_handlers(app)
```

**Dependencies**:
- `flask.render_template`, `flask.jsonify`, `flask.request`
- `logger`

**Tests to Create**:
- `tests/unit/flask/test_error_handlers.py`
  - Test JSON response for API requests
  - Test HTML response for browser requests
  - Test error logging
  - Test Accept header detection

---

#### `app_core/flask/request_hooks.py`
**Purpose**: before_request and after_request hooks

**Functions to Extract**:
- `before_request()` (Line 823)
  - Setup mode detection
  - HTTPS enforcement
  - CSRF validation
  - Authentication checks
  - Route-specific logic
  
- `after_request(response)` (Line 961)
  - Security headers (CSP, X-Frame-Options, etc.)
  - CORS handling
  - Cache control headers

**New Public API**:
```python
from app_core.flask.request_hooks import (
    setup_before_request_handler,
    setup_after_request_handler
)

@app.before_request
def before_request():
    return setup_before_request_handler()

@app.after_request
def after_request(response):
    return setup_after_request_handler(response)
```

**Dependencies**:
- `flask` (session, request, redirect, abort, etc.)
- `app.config`
- `logger`

**Tests to Create**:
- `tests/unit/flask/test_request_hooks.py`
  - Test HTTPS redirect logic
  - Test CSRF validation
  - Test security headers
  - Test CORS headers
  - Test authentication checks

---

#### `app_core/flask/context_processors.py`
**Purpose**: Template context injection

**Functions to Extract**:
- `inject_global_vars()` (Line 752)
  - Injects version, timezone, features into templates
  - Provides global template variables

**New Public API**:
```python
from app_core.flask.context_processors import get_template_context

@app.context_processor
def inject_global_vars():
    return get_template_context()
```

**Dependencies**:
- `app.config`
- `app_utils` (timezone functions)

**Tests to Create**:
- `tests/unit/flask/test_context_processors.py`
  - Test all injected variables
  - Test setup mode flag
  - Test feature flags

---

#### `app_core/flask/template_filters.py`
**Purpose**: Custom Jinja2 template filters

**Functions to Extract**:
- `shields_escape_filter(text)` (Line 795)
  - Escapes text for shields.io badges
  - Handles special characters

**New Public API**:
```python
from app_core.flask.template_filters import shields_escape

@app.template_filter('shields_escape')
def shields_escape_filter(text):
    return shields_escape(text)
```

**Dependencies**:
- Standard library: `urllib.parse.quote`

**Tests to Create**:
- `tests/unit/flask/test_template_filters.py`
  - Test special character escaping
  - Test empty/None inputs
  - Test Unicode handling

---

#### `app_core/flask/csrf.py`
**Purpose**: CSRF token generation and validation

**Functions to Extract**:
- `generate_csrf_token() -> str` (Line 351)
  - Generates secure CSRF token
  - Stores in session

**New Public API**:
```python
from app_core.flask.csrf import generate_csrf_token, validate_csrf_token

token = generate_csrf_token()
if not validate_csrf_token(request_token):
    abort(403)
```

**Dependencies**:
- `flask.session`
- Standard library: `secrets`, `hmac`

**Tests to Create**:
- `tests/unit/flask/test_csrf.py`
  - Test token generation
  - Test token persistence
  - Test validation logic

---

### 5. CLI Commands Module (`app_core/cli/`)

#### `app_core/cli/admin.py`
**Purpose**: Admin user management commands

**Functions to Extract**:
- `create_admin_user_cli(username: str, password: str)` (Line 1201)
  - Creates admin user from command line
  - Validates credentials
  - Handles existing users

**New Public API**:
```python
from app_core.cli.admin import create_admin_user

@app.cli.command('create-admin')
@click.argument('username')
@click.argument('password')
def create_admin_cli(username, password):
    create_admin_user(username, password)
```

**Dependencies**:
- `app_core.models.AdminUser`
- `app_core.auth.roles`
- `db`
- `click`

**Tests to Create**:
- `tests/unit/cli/test_admin.py`
  - Test user creation
  - Test duplicate user handling
  - Test password hashing

---

#### `app_core/cli/testing.py`
**Purpose**: Hardware testing commands

**Functions to Extract**:
- `test_led()` (Line 1182)
  - Tests LED display hardware
  - Sends test messages

**New Public API**:
```python
from app_core.cli.testing import test_led_display

@app.cli.command('test-led')
def test_led_cli():
    test_led_display()
```

**Dependencies**:
- `app_core.led`
- `logger`

**Tests to Create**:
- `tests/unit/cli/test_testing.py`
  - Test LED message sending
  - Test error handling

---

#### `app_core/cli/maintenance.py`
**Purpose**: Database maintenance commands

**Functions to Extract**:
- `init_db()` (Line 1173)
  - Reinitializes database
  - Calls initialize_database()
  
- `cleanup_expired()` (Line 1239)
  - Removes expired alerts
  - Cleans up old data

**New Public API**:
```python
from app_core.cli.maintenance import init_database, cleanup_expired_alerts

@app.cli.command('init-db')
def init_db_cli():
    init_database()

@app.cli.command('cleanup-expired')
def cleanup_cli():
    cleanup_expired_alerts()
```

**Dependencies**:
- `app_core.database.initialization`
- `app_core.models`
- `db`
- `logger`

**Tests to Create**:
- `tests/unit/cli/test_maintenance.py`
  - Test database initialization
  - Test expired alert deletion
  - Test cleanup thresholds

---

### 6. Datetime Module (`app_core/datetime/`)

#### `app_core/datetime/parsing.py`
**Purpose**: Datetime parsing utilities

**Functions to Extract**:
- `parse_nws_datetime(dt_string)` (Line 694)
  - Wrapper around app_utils parse function
  - Handles NWS datetime formats

**New Public API**:
```python
from app_core.datetime.parsing import parse_nws_datetime

dt = parse_nws_datetime("2025-12-05T12:00:00-05:00")
```

**Dependencies**:
- `app_utils.parse_nws_datetime`

**Tests to Create**:
- `tests/unit/datetime/test_parsing.py`
  - Test various NWS formats
  - Test invalid inputs
  - Test timezone handling

---

### 7. URL Decorators Module (`app_core/flask/`)

#### `app_core/flask/url_defaults.py`
**Purpose**: URL default values and modifications

**Functions to Extract**:
- `add_static_cache_bust(endpoint: str, values: Dict[str, Any])` (Line 360)
  - Adds version parameter to static URLs
  - Cache busting for assets

**New Public API**:
```python
from app_core.flask.url_defaults import setup_static_cache_bust

app.url_defaults(setup_static_cache_bust)
```

**Dependencies**:
- `app.config`
- `app_utils.versioning`

**Tests to Create**:
- `tests/unit/flask/test_url_defaults.py`
  - Test cache bust parameter addition
  - Test non-static endpoints
  - Test existing version parameter

---

## Migration Strategy

### Phase 1: Create Module Structure (Week 1)
1. Create all directories and `__init__.py` files
2. Document each module's purpose
3. Set up import structure

### Phase 2: Extract Pure Functions (Week 2)
1. Start with functions that have no Flask dependencies
   - `app_core/config/environment.py`
   - `app_core/config/database.py`
   - `app_core/eas/file_operations.py`
2. Write tests for each function
3. Update imports in app.py

### Phase 3: Extract Flask Handlers (Week 3)
1. Extract error handlers
2. Extract request hooks
3. Extract context processors and filters
4. Write integration tests

### Phase 4: Extract CLI Commands (Week 4)
1. Extract all CLI commands
2. Update Flask CLI registration
3. Test command execution

### Phase 5: Clean Up app.py (Week 5)
1. Remove extracted functions
2. Update all imports
3. Simplify app.py to only:
   - Import configuration
   - Register handlers
   - Register routes
   - Create app factory

### Phase 6: Update create_app() (Week 6)
1. Refactor create_app() to use new modules
2. Make it a proper application factory
3. Move to `app_core/application.py`

---

## Expected Final app.py Structure

After refactoring, app.py should be ~200 lines:

```python
#!/usr/bin/env python3
"""EAS Station - Main Application"""

from flask import Flask
from app_core.config import setup_configuration
from app_core.database import initialize_database_safely
from app_core.flask import register_error_handlers, register_request_hooks
from app_core.cli import register_cli_commands
from webapp import register_routes

def create_app(config=None):
    """Application factory"""
    app = Flask(__name__)
    
    # Configuration
    setup_configuration(app, config)
    
    # Database
    initialize_database_safely(app)
    
    # Flask hooks and handlers
    register_error_handlers(app)
    register_request_hooks(app)
    
    # Routes
    register_routes(app)
    
    # CLI commands
    register_cli_commands(app)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
```

---

## Benefits of This Refactoring

1. **Maintainability**: Easy to find and modify specific functionality
2. **Testability**: Each module can be tested independently
3. **Clarity**: Clear separation of concerns
4. **Scalability**: Easy to add new features
5. **Professional**: Follows industry best practices
6. **Documentation**: Self-documenting through structure
7. **Team Development**: Multiple developers can work simultaneously

---

## Testing Requirements

### Test Coverage Goals
- **Unit Tests**: 90%+ coverage for each extracted module
- **Integration Tests**: Verify modules work together
- **E2E Tests**: Ensure app still works after refactoring

### Test Categories
1. **Config Tests**: Environment parsing, database URL construction
2. **Database Tests**: Connectivity, initialization, PostGIS
3. **EAS Tests**: File operations, caching, path security
4. **Flask Tests**: Error handlers, hooks, filters, CSRF
5. **CLI Tests**: All command functionality

---

## Implementation Checklist

### Prerequisites
- [ ] Get stakeholder approval
- [ ] Schedule development time (6 weeks)
- [ ] Create feature branch
- [ ] Set up test infrastructure

### Phase 1: Structure
- [ ] Create all module directories
- [ ] Create `__init__.py` files
- [ ] Document module purposes
- [ ] Set up import patterns

### Phase 2-4: Extraction (Per Module)
- [ ] Extract functions
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Update imports
- [ ] Verify functionality

### Phase 5: Cleanup
- [ ] Remove extracted code from app.py
- [ ] Update all imports
- [ ] Simplify app.py
- [ ] Run full test suite

### Phase 6: Factory Pattern
- [ ] Refactor create_app()
- [ ] Move to application module
- [ ] Update deployment
- [ ] Final testing

---

## Risk Mitigation

### Risks
1. **Breaking Changes**: Import changes could break existing code
2. **Circular Imports**: Poor organization could create import cycles
3. **Test Coverage**: Missed edge cases in tests
4. **Deployment**: Changes to app structure could affect deployment

### Mitigations
1. **Incremental Approach**: Extract one module at a time
2. **Comprehensive Testing**: Test each extraction thoroughly
3. **Import Analysis**: Use tools to detect circular imports
4. **Parallel Branch**: Keep old code working until ready
5. **Staged Rollout**: Deploy to staging first

---

## Success Criteria

- [ ] app.py reduced from 1,296 lines to <200 lines
- [ ] All 29 functions extracted to appropriate modules
- [ ] 90%+ test coverage on new modules
- [ ] No functionality lost
- [ ] All existing tests pass
- [ ] Documentation complete
- [ ] Team trained on new structure

---

## Related Documents

- `REWRITE_ARCHITECTURE.md` - Long-term architecture vision
- `REWRITE_ROADMAP.md` - 16-week full rewrite plan
- `MIGRATION_GUIDE.md` - Step-by-step migration instructions

---

**This plan provides immediate, actionable refactoring to make the codebase professional and maintainable.**
