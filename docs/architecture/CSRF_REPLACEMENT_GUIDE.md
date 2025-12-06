# Flask-WTF CSRF Replacement Quick-Start Guide

**Status**: Ready to implement  
**Risk Level**: Medium (authentication-related)  
**Estimated Time**: 4-6 hours  
**Testing Time**: 2-4 hours

## Prerequisites

- ✅ Flask-WTF 1.2.2 added to requirements.txt
- ✅ `app_core/flask/csrf_protect.py` module created
- ⏳ Testing environment ready

## Step-by-Step Implementation

### Step 1: Initialize Flask-WTF (15 minutes)

Add to `app.py` after Flask app creation (around line 440):

```python
# Import Flask-WTF CSRF
from app_core.flask.csrf_protect import setup_csrf_protection, csrf

# Initialize CSRF protection
csrf = setup_csrf_protection(app)
logger.info("✅ Flask-WTF CSRF protection initialized")
```

### Step 2: Keep Custom CSRF as Fallback (30 minutes)

**DO NOT remove custom CSRF yet!** Run both in parallel initially:

In `app.py`, modify the `before_request` handler to use Flask-WTF first, fall back to custom:

```python
@app.before_request
def _check_authentication_and_security():
    # ... existing code ...
    
    # Try Flask-WTF CSRF validation first
    try:
        from flask_wtf.csrf import validate_csrf
        from werkzeug.exceptions import BadRequest
        
        if request.method in CSRF_PROTECTED_METHODS:
            if not (request.endpoint in CSRF_EXEMPT_ENDPOINTS or request.path in CSRF_EXEMPT_PATHS):
                # Let Flask-WTF handle it
                try:
                    validate_csrf(request.headers.get('X-CSRF-Token') or request.form.get('csrf_token'))
                    # Flask-WTF validation succeeded, skip custom
                    logger.debug("✅ Flask-WTF CSRF validation passed")
                except BadRequest:
                    # Flask-WTF validation failed, fall back to custom
                    logger.debug("Flask-WTF CSRF failed, trying custom validation")
                    # ... keep existing custom CSRF code ...
    except Exception as e:
        logger.warning(f"Flask-WTF CSRF error: {e}, using custom validation")
        # Fall back to custom validation
        # ... keep existing custom CSRF code ...
```

### Step 3: Exempt Public Routes (30 minutes)

Add `@csrf.exempt` decorator to routes that should skip CSRF:

```python
# In webapp/admin/auth.py
from flask_wtf.csrf import csrf_exempt

@auth_bp.route('/api/public/health', methods=['GET'])
@csrf_exempt
def public_health():
    return jsonify({'status': 'ok'})
```

Public API routes that need exemption:
- `/api/alerts` (GET only)
- `/api/boundaries` (GET only)
- `/api/system_status` (GET only)
- Any other public endpoints listed in `PUBLIC_API_GET_PATHS`

### Step 4: Update Templates (1 hour)

Replace custom CSRF token generation in templates with Flask-WTF's:

**Before:**
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

**After (same syntax, but now uses Flask-WTF):**
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

Flask-WTF provides the `csrf_token()` function automatically, so templates should work as-is!

### Step 5: Test Thoroughly (2-4 hours)

#### Manual Testing Checklist:
- [ ] Login with correct credentials works
- [ ] Login with wrong credentials rejected
- [ ] Login without CSRF token rejected
- [ ] Login with invalid CSRF token rejected
- [ ] POST to `/api/alerts` with valid token works
- [ ] POST to `/api/alerts` without token fails with 400
- [ ] GET to `/api/alerts` works without token
- [ ] Form submissions work
- [ ] AJAX requests with X-CSRF-Token header work
- [ ] Session refresh doesn't break CSRF token

#### Automated Testing:
```python
def test_csrf_protection():
    with app.test_client() as client:
        # Test that POST without CSRF fails
        response = client.post('/api/alerts', json={'title': 'Test'})
        assert response.status_code == 400
        
        # Test that POST with CSRF succeeds
        with client.session_transaction() as sess:
            csrf_token = generate_csrf_token()
        response = client.post(
            '/api/alerts',
            json={'title': 'Test'},
            headers={'X-CSRF-Token': csrf_token}
        )
        assert response.status_code in [200, 201]
```

### Step 6: Monitor in Production (1 week)

After deployment:
- Monitor logs for CSRF errors
- Check error rates
- Verify no authentication issues
- Look for any unexpected 400 errors

### Step 7: Remove Custom CSRF (2 hours)

**Only after 1 week of successful operation:**

1. Remove custom CSRF validation from `app.py` `before_request` handler
2. Mark `app_core/flask/csrf.py` as deprecated
3. Update any remaining references

## Rollback Procedure

If Flask-WTF CSRF causes issues:

1. **Immediate rollback:**
   ```python
   # In app.py, comment out Flask-WTF initialization
   # csrf = setup_csrf_protection(app)
   ```

2. **Restart the application** - custom CSRF validation is still in place as fallback

3. **Investigate the issue** in development environment

4. **Fix and redeploy** once root cause identified

## Common Issues

### Issue 1: CSRF token not found in session
**Cause**: Session not properly initialized  
**Fix**: Ensure `app.secret_key` is set before CSRF initialization

### Issue 2: AJAX requests failing  
**Cause**: Missing X-CSRF-Token header  
**Fix**: Add header to all AJAX requests:
```javascript
headers: {
    'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content
}
```

### Issue 3: Forms not working
**Cause**: Missing hidden CSRF field  
**Fix**: Add to all forms:
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

## Success Criteria

- ✅ All authentication flows work correctly
- ✅ No increase in 400 errors
- ✅ CSRF attacks properly blocked
- ✅ Legitimate requests not blocked
- ✅ Performance unchanged
- ✅ Logs show successful Flask-WTF validation

## Estimated Code Reduction

- Remove ~30 lines from `app.py` (CSRF validation in before_request)
- Remove ~60 lines from `app_core/flask/csrf.py` (after deprecation period)
- **Total: ~90 lines removed**
- **Maintenance burden: Significantly reduced** (library handles it)

---

**Next**: After CSRF replacement is stable, proceed with Flask-Limiter rate limiting replacement (see LIBRARY_REPLACEMENT_IMPLEMENTATION_PLAN.md)
