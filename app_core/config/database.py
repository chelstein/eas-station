"""
Database configuration utilities.

This module provides functions for getting database connection URLs
from environment variables.

Functions:
    build_database_url: Get PostgreSQL connection URL from DATABASE_URL env var
"""

import os


def build_database_url() -> str:
    """
    Get database URL from DATABASE_URL environment variable.

    This function requires DATABASE_URL to be set in the environment.
    Individual POSTGRES_* variables are no longer supported.
    
    Environment Variables:
        DATABASE_URL: Complete database URL (required)
    
    Returns:
        A PostgreSQL connection URL string
        
    Raises:
        ValueError: If DATABASE_URL is not set
        
    Example:
        >>> os.environ['DATABASE_URL'] = '******localhost:5432/alerts'
        >>> build_database_url()
        '******localhost:5432/alerts'
    """
    url = os.getenv('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable is required")
    return url


__all__ = ['build_database_url']
