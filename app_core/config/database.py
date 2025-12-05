"""
Database configuration utilities.

This module provides functions for constructing database connection URLs
from environment variables.

Functions:
    build_database_url: Construct PostgreSQL connection URL from env vars
"""

import os
from urllib.parse import quote


def build_database_url() -> str:
    """
    Build database URL from environment variables.

    Prioritizes DATABASE_URL if set, otherwise builds from POSTGRES_* variables.
    
    Environment Variables:
        DATABASE_URL: Complete database URL (takes precedence if set)
        POSTGRES_HOST: Database host (default: 'alerts-db')
        POSTGRES_PORT: Database port (default: '5432')
        POSTGRES_DB: Database name (default: 'alerts')
        POSTGRES_USER: Database user (default: 'postgres')
        POSTGRES_PASSWORD: Database password (default: 'postgres')
    
    Returns:
        A PostgreSQL connection URL string in the format:
        postgresql+psycopg2://user:password@host:port/database
        
    Note:
        Special characters in credentials are URL-encoded to handle
        passwords with special characters.
        
    Example:
        >>> os.environ['POSTGRES_HOST'] = 'localhost'
        >>> os.environ['POSTGRES_USER'] = 'myuser'
        >>> os.environ['POSTGRES_PASSWORD'] = 'my@pass'
        >>> build_database_url()
        'postgresql+psycopg2://myuser:my%40pass@localhost:5432/alerts'
    """
    url = os.getenv('DATABASE_URL')
    if url:
        return url

    # Build from individual POSTGRES_* variables
    user = os.getenv('POSTGRES_USER', 'postgres') or 'postgres'
    password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    host = os.getenv('POSTGRES_HOST', 'alerts-db') or 'alerts-db'
    port = os.getenv('POSTGRES_PORT', '5432') or '5432'
    database = os.getenv('POSTGRES_DB', 'alerts') or 'alerts'

    # URL-encode credentials to handle special characters
    user_part = quote(user, safe='')
    password_part = quote(password, safe='') if password else ''

    if password_part:
        auth_segment = f"{user_part}:{password_part}"
    else:
        auth_segment = user_part

    return f"postgresql+psycopg2://{auth_segment}@{host}:{port}/{database}"


__all__ = ['build_database_url']
