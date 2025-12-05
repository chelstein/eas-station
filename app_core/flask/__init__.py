"""
Flask integration module for EAS Station.

This module provides Flask-specific functionality including:
- Error handlers (404, 500, 403, 400)
- Request hooks (before_request, after_request)
- Template filters and context processors
- CSRF protection
- URL defaults

Extracted from app.py as part of the refactoring effort to improve maintainability.
"""

from .csrf import (
    generate_csrf_token,
    CSRF_SESSION_KEY,
    CSRF_HEADER_NAME,
    CSRF_PROTECTED_METHODS,
    CSRF_EXEMPT_ENDPOINTS,
    CSRF_EXEMPT_PATHS,
)
from .url_defaults import add_static_cache_bust
from .template_filters import shields_escape
from .context_processors import inject_global_vars

__all__ = [
    'generate_csrf_token',
    'CSRF_SESSION_KEY',
    'CSRF_HEADER_NAME',
    'CSRF_PROTECTED_METHODS',
    'CSRF_EXEMPT_ENDPOINTS',
    'CSRF_EXEMPT_PATHS',
    'add_static_cache_bust',
    'shields_escape',
    'inject_global_vars',
]
