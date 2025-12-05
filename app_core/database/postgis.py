"""
PostGIS extension management utilities.

This module provides functions for managing PostgreSQL PostGIS extension.

Functions:
    ensure_postgis_extension: Ensure PostGIS extension is installed
"""

import logging
from sqlalchemy.exc import OperationalError
from sqlalchemy import text

logger = logging.getLogger(__name__)


def ensure_postgis_extension(app, db) -> bool:
    """
    Ensure the PostGIS extension exists for PostgreSQL databases.
    
    Attempts to create the PostGIS extension if it doesn't already exist.
    Skips non-PostgreSQL databases. Handles permission errors gracefully.
    
    Args:
        app: Flask application instance (for config access)
        db: SQLAlchemy database instance
    
    Returns:
        True if extension exists or was created successfully, False on error.
        Returns True for non-PostgreSQL databases (skips check).
        
    Example:
        >>> from flask import Flask
        >>> from flask_sqlalchemy import SQLAlchemy
        >>> app = Flask(__name__)
        >>> db = SQLAlchemy(app)
        >>> if ensure_postgis_extension(app, db):
        ...     print("PostGIS ready")
        PostGIS ready
    """
    database_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '') or ''
    if not database_uri.startswith('postgresql'):
        logger.debug(
            "Skipping PostGIS extension check for non-PostgreSQL database URI: %s",
            database_uri,
        )
        return True

    try:
        with db.engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    except OperationalError as exc:
        logger.error("Failed to ensure PostGIS extension: %s", exc)
        return False
    except Exception as exc:  # noqa: BLE001 - capture unexpected errors for logging
        logger.exception("Unexpected error ensuring PostGIS extension: %s", exc)
        return False

    logger.debug("PostGIS extension ensured for current database.")
    return True


__all__ = ['ensure_postgis_extension']
