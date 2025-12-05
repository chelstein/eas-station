"""
CSRF (Cross-Site Request Forgery) protection utilities.

This module provides CSRF token generation and validation for Flask applications.

Functions:
    generate_csrf_token: Generate or retrieve CSRF token from session
    
Constants:
    CSRF_SESSION_KEY: Session key for storing CSRF token
    CSRF_HEADER_NAME: HTTP header name for CSRF token
    CSRF_PROTECTED_METHODS: HTTP methods that require CSRF protection
    CSRF_EXEMPT_ENDPOINTS: Flask endpoints exempt from CSRF protection
    CSRF_EXEMPT_PATHS: URL paths exempt from CSRF protection
"""

import secrets
from flask import session

# CSRF Configuration Constants
CSRF_SESSION_KEY = '_csrf_token'
CSRF_HEADER_NAME = 'X-CSRF-Token'
CSRF_PROTECTED_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
CSRF_EXEMPT_ENDPOINTS = {'login', 'logout', 'auth.login', 'auth.logout', 'static'}
CSRF_EXEMPT_PATHS = {'/login', '/logout'}


def generate_csrf_token() -> str:
    """
    Generate or retrieve a CSRF token for the current session.
    
    If a token already exists in the session, it is returned. Otherwise,
    a new cryptographically secure token is generated and stored in the session.
    
    Returns:
        A URL-safe CSRF token string
        
    Example:
        >>> from flask import Flask, session
        >>> app = Flask(__name__)
        >>> app.secret_key = 'test'
        >>> with app.test_request_context():
        ...     token = generate_csrf_token()
        ...     len(token) > 0
        True
    """
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


__all__ = [
    'generate_csrf_token',
    'CSRF_SESSION_KEY',
    'CSRF_HEADER_NAME',
    'CSRF_PROTECTED_METHODS',
    'CSRF_EXEMPT_ENDPOINTS',
    'CSRF_EXEMPT_PATHS',
]
