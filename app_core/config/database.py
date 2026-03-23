"""
Database configuration utilities.

This module provides functions for getting database connection URLs
from environment variables.

Functions:
    build_database_url: Get PostgreSQL connection URL from environment variables
"""

import os
from urllib.parse import quote_plus


def build_database_url() -> str:
    """
    Get database URL from environment variables.

    Checks DATABASE_URL first; if not set, builds a URL from individual
    POSTGRES_* variables using the following defaults:

        POSTGRES_HOST     → alerts-db
        POSTGRES_PORT     → 5432
        POSTGRES_DB       → alerts
        POSTGRES_USER     → postgres
        POSTGRES_PASSWORD → postgres

    Environment Variables:
        DATABASE_URL:      Complete database URL (takes precedence when set)
        POSTGRES_HOST:     PostgreSQL server hostname
        POSTGRES_PORT:     PostgreSQL server port
        POSTGRES_DB:       Database name
        POSTGRES_USER:     Database username
        POSTGRES_PASSWORD: Database password

    Returns:
        A PostgreSQL connection URL string

    Example:
        >>> os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost:5432/alerts'
        >>> build_database_url()
        'postgresql://user:pass@localhost:5432/alerts'
    """
    url = os.getenv('DATABASE_URL')
    if url:
        return url

    host = os.getenv('POSTGRES_HOST', 'alerts-db')
    port = os.getenv('POSTGRES_PORT', '5432')
    db = os.getenv('POSTGRES_DB', 'alerts')
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', 'postgres')

    encoded_user = quote_plus(user)
    encoded_db = quote_plus(db)

    if password:
        encoded_password = quote_plus(password)
        return f"postgresql+psycopg2://{encoded_user}:{encoded_password}@{host}:{port}/{encoded_db}"
    return f"postgresql+psycopg2://{encoded_user}@{host}:{port}/{encoded_db}"


__all__ = ['build_database_url']
