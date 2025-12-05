"""
Flask-WTF CSRF Protection setup.

This module replaces the custom CSRF implementation with Flask-WTF's
CSRFProtect, which is more secure, battle-tested, and maintainable.

Functions:
    setup_csrf_protection: Initialize CSRF protection for Flask app
"""

from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()


def setup_csrf_protection(app):
    """
    Initialize CSRF protection for the Flask application.
    
    This replaces the custom CSRF implementation with Flask-WTF's CSRFProtect,
    which automatically:
    - Generates CSRF tokens
    - Validates tokens on protected methods (POST, PUT, PATCH, DELETE)
    - Handles token rotation
    - Supports both form and header tokens
    - Provides exemption mechanisms
    
    Args:
        app: Flask application instance
        
    Returns:
        CSRFProtect instance
        
    Example:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> app.secret_key = 'test-key'
        >>> csrf = setup_csrf_protection(app)
    """
    # Configure CSRF settings
    app.config.setdefault('WTF_CSRF_ENABLED', True)
    app.config.setdefault('WTF_CSRF_CHECK_DEFAULT', True)
    app.config.setdefault('WTF_CSRF_TIME_LIMIT', None)  # No expiration
    app.config.setdefault('WTF_CSRF_SSL_STRICT', False)  # Allow non-HTTPS for development
    
    # Header names that Flask-WTF will check for CSRF tokens
    app.config.setdefault('WTF_CSRF_HEADERS', ['X-CSRF-Token', 'X-CSRFToken'])
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    return csrf


def exempt_route(func):
    """
    Decorator to exempt a route from CSRF protection.
    
    Usage:
        @app.route('/api/public')
        @exempt_route
        def public_endpoint():
            return {'status': 'ok'}
    """
    from flask_wtf.csrf import csrf_exempt
    return csrf_exempt(func)


__all__ = [
    'csrf',
    'setup_csrf_protection',
    'exempt_route',
]
