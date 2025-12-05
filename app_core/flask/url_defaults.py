"""
URL default value utilities for Flask.

This module provides functions for modifying Flask URL defaults,
such as cache-busting parameters for static assets.

Functions:
    add_static_cache_bust: Add version parameter to static asset URLs
"""

from typing import Any, Dict


def add_static_cache_bust(app, endpoint: str, values: Dict[str, Any]) -> None:
    """
    Append a cache-busting query parameter to all static asset URLs.
    
    This function is designed to be used as a Flask url_defaults handler.
    It adds a version parameter to static asset URLs to ensure browsers
    reload assets when the application version changes.
    
    Args:
        app: Flask application instance (for config access)
        endpoint: The Flask endpoint name
        values: Dictionary of URL values (modified in place)
    
    Returns:
        None (modifies values dictionary in place)
        
    Example:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> app.config['STATIC_ASSET_VERSION'] = '2.7.2'
        >>> @app.url_defaults
        ... def cache_bust(endpoint, values):
        ...     add_static_cache_bust(app, endpoint, values)
    """
    if endpoint != 'static' or values is None:
        return

    if 'v' in values:
        return

    # Import here to avoid circular dependency:
    # app_utils.versioning imports app_core modules for database access,
    # so importing at module level would create a circular dependency chain.
    from app_utils.versioning import get_current_version
    
    values['v'] = app.config.get('STATIC_ASSET_VERSION', get_current_version())


__all__ = ['add_static_cache_bust']
