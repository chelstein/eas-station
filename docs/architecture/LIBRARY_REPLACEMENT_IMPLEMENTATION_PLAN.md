# Library Replacement Implementation Plan

**Date**: December 2024  
**Status**: Phase 1 - In Progress  
**Purpose**: Detailed implementation plan for replacing 47 custom implementations with maintained libraries

## Current Progress

### Completed
- ✅ Added Flask-WTF 1.2.2 to requirements.txt
- ✅ Added Flask-Limiter 3.8.0 to requirements.txt  
- ✅ Created `app_core/flask/csrf_protect.py` module for Flask-WTF integration

### In Progress
- 🔄 CSRF Protection replacement (Item #2 from audit)
- 🔄 Rate Limiter replacement (Item #1 from audit)

---

## Phase 1: Critical Security Replacements (Week 1-2)

### 1. Replace Custom CSRF with Flask-WTF

**Files to modify:**
- `app.py` (lines 674-703): Remove custom CSRF validation in `before_request`
- `app_core/flask/csrf.py`: Mark as deprecated, keep for backward compatibility
- `webapp/admin/auth.py`: Exempt login/logout routes from CSRF
- All templates: Update CSRF token generation to use Flask-WTF

**Implementation steps:**
1. Initialize Flask-WTF in app.py: `from app_core.flask.csrf_protect import setup_csrf_protection`
2. Call `setup_csrf_protection(app)` after app creation
3. Remove custom CSRF validation from `before_request` handler
4. Add `@csrf_exempt` decorator to public API routes
5. Update all templates to use `{{ csrf_token() }}` instead of custom function
6. Test authentication flows thoroughly

**Testing required:**
- [ ] Login/logout still works
- [ ] POST/PUT/PATCH/DELETE protected by CSRF
- [ ] GET requests don't require CSRF
- [ ] API routes with `@csrf_exempt` work without tokens
- [ ] Invalid CSRF tokens properly rejected
- [ ] CSRF tokens survive session refresh

**Rollback plan:**
Keep custom CSRF module (`app_core/flask/csrf.py`) as fallback. If Flask-WTF fails, revert `app.py` changes and re-enable custom validation.

**Lines saved:** ~80 lines of custom CSRF code

---

### 2. Replace Custom Rate Limiter with Flask-Limiter

**Files to modify:**
- `app_core/auth/rate_limiter.py`: Mark as deprecated
- `webapp/admin/auth.py`: Replace `get_rate_limiter()` calls with Flask-Limiter decorators
- `app_core/auth/ip_filter.py`: Update flood detection to use Flask-Limiter storage
- `app.py`: Initialize Flask-Limiter

**Implementation steps:**
1. Create `app_core/auth/limiter.py` module for Flask-Limiter setup:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",  # or redis://localhost:6379
    strategy="fixed-window"
)

def setup_rate_limiting(app):
    limiter.init_app(app)
    return limiter
```

2. Add to app.py:
```python
from app_core.auth.limiter import setup_rate_limiting
limiter = setup_rate_limiting(app)
```

3. Update login route:
```python
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per 5 minutes")
def login():
    # No need to manually check rate limits!
    ...
```

4. Update other protected routes:
```python
@app.route('/api/alerts', methods=['POST'])
@limiter.limit("100 per hour")
def create_alert():
    ...
```

5. Remove `app_core/auth/rate_limiter.py` after migration

**Testing required:**
- [ ] Login rate limiting works (5 attempts per 5 minutes)
- [ ] Lockout duration enforced (15 minutes)
- [ ] Rate limits properly reset after success
- [ ] Per-IP tracking works correctly
- [ ] Rate limit headers included in responses
- [ ] Redis backend works (if using Redis)

**Rollback plan:**
Keep `app_core/auth/rate_limiter.py` and revert route changes if Flask-Limiter fails.

**Lines saved:** ~266 lines of custom rate limiting code

---

## Phase 2: Audio & Performance (Week 3-4)

### 3. Replace Custom Audio Ring Buffer

**Target:** `app_core/audio/ringbuffer.py` (400+ lines)  
**Replace with:** `sounddevice` built-in ring buffer or `pyring`  
**Effort:** 2-3 days  
**Risk:** Medium (core audio component)

### 4. Replace Custom Validation with Pydantic

**Target:** `app_core/auth/input_validation.py` + scattered validation  
**Replace with:** Pydantic models  
**Effort:** 1 week  
**Risk:** Low

---

## Phase 3: Remaining Replacements (Week 5+)

The audit document lists 43 more custom implementations to replace. These should be tackled incrementally in separate PRs:

- Custom HTTP clients → httpx (already in requirements!)
- Custom retry logic → tenacity
- Custom caching → use Redis more effectively
- Custom task queue → Celery
- etc.

---

## Risk Management

### High-Risk Changes
- Authentication/CSRF (Phase 1, Item #1-2): Requires extensive testing
- Audio ring buffer (Phase 2, Item #3): Core functionality
- Database migrations: Any schema changes

### Medium-Risk Changes  
- Input validation (Phase 2, Item #4): Good test coverage exists
- HTTP clients: Mostly internal APIs
- Caching: Can fall back to current implementation

### Low-Risk Changes
- Logging improvements
- Documentation
- Type hints
- Code organization

---

## Testing Strategy

### For Each Replacement:
1. **Unit tests**: Test new library integration
2. **Integration tests**: Test with existing code
3. **Manual testing**: Test critical user flows
4. **Performance tests**: Ensure no regression
5. **Security audit**: Verify security properties maintained

### Continuous Validation:
- Run full test suite after each change
- Check for breaking changes
- Monitor logs for unexpected errors
- Review security scan results

---

## Timeline Estimate

| Phase | Duration | Items | Status |
|-------|----------|-------|--------|
| Phase 1 | 2 weeks | CSRF + Rate Limiter | In Progress |
| Phase 2 | 2 weeks | Audio + Validation | Not Started |
| Phase 3 | 4+ weeks | Remaining 43 items | Not Started |
| **Total** | **8+ weeks** | **47 items** | **~10% Complete** |

---

## Notes

- This is **months of careful work**, not a quick refactor
- Each replacement requires testing to avoid breaking production
- Some replacements (like FastAPI) are optional modernizations, not critical
- Priority: Security > Stability > Performance > Code Quality
- Never rush authentication/security changes

---

## Decision Points

Before starting Phase 2+:
- [ ] Phase 1 completed and tested
- [ ] No regressions in production
- [ ] User acceptance of new CSRF/rate limiting
- [ ] Performance metrics baseline established
- [ ] Rollback procedures tested

