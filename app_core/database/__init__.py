"""
Database module for EAS Station.

This module provides database-related functionality including:
- Database connectivity checking and retry logic
- Database initialization and migrations
- PostGIS extension management

Extracted from app.py as part of the refactoring effort to improve maintainability.
"""

from .connectivity import check_database_connectivity
from .postgis import ensure_postgis_extension

__all__ = ['check_database_connectivity', 'ensure_postgis_extension']
