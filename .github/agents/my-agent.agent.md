---
# Fill in the fields below to create a basic custom agent for your repository.
# The Copilot CLI can be used for local testing: https://gh.io/customagents/cli
# To make this agent available, merge this file into the default repository branch.
# For format details, see: https://gh.io/customagents/config

name: EAS-STATION
description: AI agent for the NOAA CAP Emergency Alert System, providing coding standards and guidelines for development
---

# EAS-STATION AI Agent

Quick reference guide for AI agents working on the NOAA CAP Emergency Alert System codebase.

**📚 Full Documentation**: See [docs/development/AGENTS.md](../../docs/development/AGENTS.md) for comprehensive guidelines.

---

## 🎯 Core Principles

1. **Safety First**: Never commit secrets, API keys, or sensitive data
2. **Preserve Existing Patterns**: Follow established code style and architecture
4. **Focused Changes**: Keep fixes targeted to the specific issue
5. **Document Changes**: Update relevant documentation when adding features
6. **Follow Versioning**: Bug fixes increment by 0.0.+1, features by 0.+1.0
7. **File Naming**: Old files get `_old` suffix, never use `_new` for replacements
8. **Repository Organization**: Docs belong in `docs/` directory structure

## 🐛 Bug Tracking

- Check `/bugs` directory for screenshots before investigating
- Reference screenshot filenames in commit messages
- Move to `/bugs/resolved` when fixed

## 🎨 Frontend Requirements

**CRITICAL**: Every backend feature MUST have a frontend UI. Backend-only features are unacceptable.

**Key Requirements**:
- Create both API endpoint AND UI page
- Add to navigation menu in `templates/base.html`
- Use dropdowns/radio buttons for binary choices (never text inputs)
- Document UI access path
- Test end-to-end through the web interface

**Form Input Rule**: For true/false, yes/no, enabled/disabled - use `<select>` dropdowns or radio buttons, NOT text fields.

**See**: [Full Frontend Guidelines](../../docs/development/AGENTS.md#frontend-ui-for-every-backend-feature)

## 📝 Code Style Quick Reference

**Python**: 4 spaces, snake_case functions, PascalCase classes, UPPER_SNAKE constants

**Logging**: Use existing logger only. Never create new instances with `logging.getLogger(__name__)`

**Error Handling**: Catch specific exceptions, include context, rollback DB transactions

```python
# Good pattern
try:
    alert = CAPAlert.query.get_or_404(alert_id)
    db.session.commit()
except OperationalError as e:
    db.session.rollback()
    logger.error(f"Database error: {str(e)}")
    return jsonify({'error': 'Database failed'}), 500
```

**See**: [Full Code Style Standards](../../docs/development/AGENTS.md#code-style-standards)

## 🗄️ Database Quick Reference

**SQLAlchemy**: Always commit or rollback. Use `.filter()` and `.first()` appropriately.

**PostGIS**: Check for NULL geometry before spatial operations. Use `ST_Intersects`, `ST_Area`, `ST_GeomFromGeoJSON`.

**See**: [Full Database Guidelines](../../docs/development/AGENTS.md#database-guidelines)

## 🎨 Templates & Themes

**Templates**: Extend `base.html`, use CSS variables (`var(--primary-color)`, `var(--text-color)`, `var(--bg-color)`), test in light & dark themes

**Active Files**:
- Base: `templates/base.html`
- Navbar: `templates/components/navbar.html` (NOT navbar_old.html)
- Footer: Inline in `base.html`

**JavaScript**: Use existing functions (`showToast()`, `setTheme()`, `toggleTheme()`). Avoid jQuery.

**Themes**: 11 built-in (Cosmo, Dark, Coffee, Spring, Red, Green, Blue, Purple, Pink, Orange, Yellow)

**See**: [Theme System](../../docs/development/AGENTS.md#theme-system-architecture) | [UI Guide](../../docs/frontend/USER_INTERFACE_GUIDE.md)

## 🔒 Security

**Critical Rules**:
1. NEVER commit secrets or API keys
2. NEVER hardcode credentials (store in database settings models)
3. ALWAYS validate user input (especially file uploads)
4. ALWAYS use parameterized queries (prevent SQL injection)

**See**: [Security Guidelines](../../docs/development/AGENTS.md#security-guidelines) | [Security Docs](../../docs/security/SECURITY.md)

## ⚙️ Configuration System

**CRITICAL**: ALL configuration is now database-based. Environment variables have been REMOVED.

### Database-Based Settings (ONLY Way to Configure)

**Settings Models in `app_core/models.py`**:
- `LocationSettings` - Geographic configuration
- `HardwareSettings` - GPIO, OLED, LED, VFD settings
- `IcecastSettings` - Audio streaming configuration
- `CertbotSettings` - SSL certificate management
- `TTSSettings` - Text-to-speech configuration
- `PollerSettings` - Alert poller configuration

**Pattern for New Configurable Features**:
1. **Create Database Model** in `app_core/models.py`:
   ```python
   class MySettings(db.Model):
       __tablename__ = "my_settings"
       id = db.Column(db.Integer, primary_key=True)
       enabled = db.Column(db.Boolean, nullable=False, default=False)
       updated_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)
       
       def to_dict(self):
           return {
               "enabled": self.enabled, 
               "updated_at": self.updated_at.isoformat() if self.updated_at else None
           }
   ```

2. **Create Admin UI** in `webapp/admin/my_feature.py`:
   - GET route to display settings form
   - POST route to save settings to database
   - Use dropdowns/radio buttons for boolean values (NOT text inputs)

3. **Add Navigation** in `templates/base.html`:
   - Add link to appropriate dropdown menu (Settings, Admin, etc.)

4. **Create Database Migration**:
   ```bash
   cd /opt/eas-station
   source venv/bin/activate
   alembic revision --autogenerate -m "Add my_settings table"
   alembic upgrade head
   ```

5. **Read Settings in Code**:
   ```python
   from app_core.models import MySettings
   
   settings = MySettings.query.first()
   if not settings:
       # Create default settings if none exist
       settings = MySettings(enabled=False)
       db.session.add(settings)
       db.session.commit()
   
   if settings.enabled:
       logger.info("Feature enabled")
   ```

**Form Input Standards**:
- ✅ Boolean fields: Use `<select>` dropdown or radio buttons
- ❌ NEVER use text input for true/false/yes/no/enabled/disabled
- ✅ Example:
  ```html
  <select name="enabled" class="form-select">
      <option value="true" {% if settings.enabled %}selected{% endif %}>Enabled</option>
      <option value="false" {% if not settings.enabled %}selected{% endif %}>Disabled</option>
  </select>
  ```

### Sudoers Configuration (System Administration)

**CRITICAL**: `update.sh` runs as root and executes commands as `eas-station` user without password prompts.

**Issue**: `sudo -u eas-station <command>` asks for password (which often doesn't exist).

**Solution**: `/etc/sudoers.d/eas-station` must include:
```bash
# Allow root to run any command as eas-station user without password
root ALL=(eas-station) NOPASSWD: ALL
```

**Syntax Rules**:
- ✅ Escape colons: `chown root\:root` (not `root:root`)
- ✅ Validate: `visudo -c -f /etc/sudoers.d/eas-station`
- ✅ Permissions: `chmod 0440 /etc/sudoers.d/eas-station`
- ❌ Never deploy without syntax validation!

**When to Update**:
- Source: `config/sudoers-eas-station`
- `install.sh` copies during initial install
- `update.sh` updates early (before any `sudo -u` commands)


## 📚 Documentation

**Location**: All docs in `/docs` directory, organized by category (development, guides, reference, security, architecture, etc.)

**When to Update**:
- Feature changes: Update `templates/help.html`, `templates/about.html`, and relevant `docs/` files
- New patterns: Update `docs/development/AGENTS.md`
- Complex logic: Add docstrings and inline comments

**See**: [Documentation Standards](../../docs/development/AGENTS.md#documentation-standards)

## 🔧 Common Patterns & Anti-Patterns

**Flask Route Pattern**: Validate input → Do work → Log success → Return JSON response

**Database Pattern**: Query with joins → Process results → Commit with error handling

**Anti-Patterns to AVOID**:
- ❌ Bare `except:` statements (catch specific exceptions)
- ❌ Creating new loggers with `logging.getLogger(__name__)`
- ❌ Hardcoded paths or credentials (use database settings)
- ❌ Committed commented-out code (delete instead)
- ❌ Mutable default arguments (use `None` and check)

**See**: [Common Patterns](../../docs/development/AGENTS.md#common-patterns)

## 🧪 Testing

**Pre-Commit Checklist**:
- UI tested in light & dark modes
- Consider edge cases: null data, invalid input, DB failures

## 📦 Dependencies

**Adding Dependencies**:
1. Add to `requirements.txt` with version pin
3. Update documentation (required for legal compliance)
4. Document if affects users

**See**: [Dependency Management](../../docs/development/AGENTS.md#dependency-management)

## 🔄 Git Workflow

**Versioning** (update `/VERSION` before every commit):
- Bug fixes: `0.0.+1` (e.g., 2.3.12 → 2.3.13)
- Features: `0.+1.0` (e.g., 2.3.12 → 2.4.0)
- Major: `+1.0.0` (e.g., 2.3.12 → 3.0.0) - rare

**Also Update**: `docs/reference/CHANGELOG.md` under `[Unreleased]` section

**Commit Messages**: 50 char summary, imperative mood, reference issues

**Branch Naming**: `feature/name`, `fix/description`, `docs/topic`, `refactor/component`

**See**: [Git Workflow](../../docs/development/AGENTS.md#git-workflow)

## 📖 Code Navigation

**Architecture**: See [System Architecture](../../docs/architecture/SYSTEM_ARCHITECTURE.md) and [Theory of Operation](../../docs/architecture/THEORY_OF_OPERATION.md)

**Reference**: [CHANGELOG](../../docs/reference/CHANGELOG.md) | [About](../../docs/reference/ABOUT.md) | [Diagrams](../../docs/reference/DIAGRAMS.md)

## ✅ Pre-Commit Checklist

- [ ] **Version incremented** – `/VERSION` file updated (+0.0.1 for bugs, +0.1.0 for features)
- [ ] **CHANGELOG updated** – Add entry to `docs/reference/CHANGELOG.md` under `[Unreleased]`
- [ ] **Documentation updated** – `templates/help.html`, `templates/about.html` if features changed
- [ ] **Bug screenshots checked** – Reference `/bugs` directory if fixing a bug
- [ ] **Template syntax validated** – If `.html` files changed, verify balanced Jinja2 blocks (if/endif, for/endfor, block/endblock, with/endwith)
- [ ] PEP 8 style (4 spaces, snake_case)
- [ ] Uses existing logger only
- [ ] Specific exception handling with rollback
- [ ] No secrets or credentials committed
- [ ] Templates extend `base.html` with theme support
- [ ] Commit message follows format

**Template Validation Command** (run if templates changed):
```python
python3 << 'EOF'
import re
from pathlib import Path

def check_template(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    blocks = {
        'if': (r'{%\s*if\s+', r'{%\s*endif\s*%}'),
        'for': (r'{%\s*for\s+', r'{%\s*endfor\s*%}'),
        'block': (r'{%\s*block\s+', r'{%\s*endblock\s*%}'),
        'with': (r'{%\s*with\s+', r'{%\s*endwith\s*%}'),
    }
    
    for name, (start_pattern, end_pattern) in blocks.items():
        starts = len(re.findall(start_pattern, content))
        ends = len(re.findall(end_pattern, content))
        if starts != ends:
            print(f"❌ {filepath}: {name} blocks unbalanced ({starts} starts, {ends} ends)")
            return False
    return True

changed_ok = True
for template in Path('templates').rglob('*.html'):
    if not check_template(template):
        changed_ok = False

if changed_ok:
    print("✅ All templates have balanced Jinja2 blocks")
else:
    print("\n⚠️  Fix template syntax errors before committing!")
    exit(1)
EOF
```

**Remember**: Check existing patterns first. Consistency > perfection.

## 🔍 Debugging Philosophy

**CRITICAL**: When users report bugs, INVESTIGATE CODE FIRST - don't assume deployment/cache issues.

**Debugging Approach**:
1. **Trace error messages directly to source** - Don't make assumptions or get lost in architecture
2. Trust the user - if they say it doesn't work, investigate
3. Search for hardcoded values, element ID mismatches, function execution order issues
4. Check for code that overrides earlier fixes
5. Only suggest cache clearing if code inspection confirms no bugs

**Example**: Error says "No metrics available from audio-service" → Check Redis metrics key → Verify which service publishes to that key

**Common Patterns**: JavaScript ID mismatches, hardcoded backend values, event listener issues, CSS specificity conflicts

**See**: [Debugging Patterns](../../docs/development/AGENTS.md#debugging-patterns-user-interaction)

---

**For complete guidelines, see**: [docs/development/AGENTS.md](../../docs/development/AGENTS.md)
