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
3. **Test Before Commit**: Always verify changes work in Docker before committing
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
1. NEVER commit `.env` file (contains secrets)
2. NEVER hardcode credentials (use environment variables)
3. ALWAYS validate user input (especially file uploads)
4. ALWAYS use parameterized queries (prevent SQL injection)

**See**: [Security Guidelines](../../docs/development/AGENTS.md#security-guidelines) | [Security Docs](../../docs/security/SECURITY.md)

## 🐳 Docker & Deployment

**Testing**: Always test in Docker before committing
```bash
sudo docker compose build
sudo docker compose up -d
sudo docker compose logs -f app
```

**Persistent Environment**: Config stored in `/app-config/.env` volume, survives container rebuilds and Git pulls

**Adding Environment Variables** - Update ALL these files:
1. `.env.example` - Documentation and defaults
2. `stack.env` - Docker deployment defaults
3. `docker-entrypoint.sh` - Container startup initialization
4. `webapp/admin/environment.py` - **REQUIRED** for web UI access
5. `app_utils/setup_wizard.py` - If part of initial setup

**Variable Types**: Use `select` with `['false', 'true']` for boolean values, NOT text inputs. This prevents user input errors.

**Docker Compose**: Always update BOTH `docker-compose.yml` AND `docker-compose.embedded-db.yml`

**See**: [Docker Guidelines](../../docs/development/AGENTS.md#docker-deployment) | [Deployment Guide](../../docs/deployment/PORTAINER_DEPLOYMENT.md)

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
- ❌ Hardcoded paths (use environment variables)
- ❌ Committed commented-out code (delete instead)
- ❌ Mutable default arguments (use `None` and check)

**See**: [Common Patterns](../../docs/development/AGENTS.md#common-patterns)

## 🧪 Testing

**Pre-Commit Checklist**:
- Syntax check, Docker build, health check
- UI tested in light & dark modes
- Consider edge cases: null data, invalid input, DB failures

## 📦 Dependencies

**Adding Dependencies**:
1. Add to `requirements.txt` with version pin
2. Test in Docker
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
- [ ] PEP 8 style (4 spaces, snake_case)
- [ ] Uses existing logger only
- [ ] Specific exception handling with rollback
- [ ] No secrets or `.env` file committed
- [ ] Templates extend `base.html` with theme support
- [ ] Tested in Docker locally
- [ ] Commit message follows format

**Remember**: Check existing patterns first. Consistency > perfection.

## 🔍 Debugging Philosophy

**CRITICAL**: When users report bugs, INVESTIGATE CODE FIRST - don't assume deployment/cache issues.

**Debugging Approach**:
1. Trust the user - if they say it doesn't work, investigate
2. Search for hardcoded values, element ID mismatches, function execution order issues
3. Check for code that overrides earlier fixes
4. Only suggest cache clearing if code inspection confirms no bugs

**Common Patterns**: JavaScript ID mismatches, hardcoded backend values, event listener issues, CSS specificity conflicts

**See**: [Debugging Patterns](../../docs/development/AGENTS.md#debugging-patterns-user-interaction)

---

**For complete guidelines, see**: [docs/development/AGENTS.md](../../docs/development/AGENTS.md)
