"""
Database connectivity utilities.

This module provides functions for testing and establishing database connections
with retry logic and error handling.

Functions:
    check_database_connectivity: Test database connection with exponential backoff retry
"""

import time
import logging
from sqlalchemy.exc import OperationalError
from sqlalchemy import text

logger = logging.getLogger(__name__)


def check_database_connectivity(
    app,
    db,
    max_retries: int = 5,
    initial_backoff: float = 1.0
) -> bool:
    """
    Attempt to connect to the database with retry logic.
    
    Uses exponential backoff to retry failed connections, up to a maximum
    backoff of 30 seconds between attempts.
    
    Args:
        app: Flask application instance (for app context)
        db: SQLAlchemy database instance
        max_retries: Maximum number of connection attempts (default: 5)
        initial_backoff: Initial retry delay in seconds (default: 1.0)
    
    Returns:
        True if connection successful, False otherwise
        
    Example:
        >>> from flask import Flask
        >>> from flask_sqlalchemy import SQLAlchemy
        >>> app = Flask(__name__)
        >>> db = SQLAlchemy(app)
        >>> if check_database_connectivity(app, db):
        ...     print("Connected!")
        Connected!
    """
    attempt = 0
    backoff = initial_backoff

    while attempt < max_retries:
        try:
            with app.app_context():
                with db.engine.connect() as connection:
                    connection.execute(text("SELECT 1"))

            if attempt > 0:
                logger.info("✅ Database connection succeeded after %d attempts", attempt + 1)
            return True

        except OperationalError as exc:
            attempt += 1

            if attempt >= max_retries:
                logger.error("❌ Database connection failed after %d attempts: %s", max_retries, exc)
                break

            logger.warning(
                "⚠️  Database connection failed (attempt %d/%d): %s. Retrying in %.1fs...",
                attempt, max_retries, exc, backoff
            )
            time.sleep(backoff)
            backoff = min(backoff * 2, 30.0)  # Exponential backoff, max 30s

        except Exception as exc:  # noqa: BLE001 - broad catch to log unexpected failures
            logger.exception("Unexpected error during database connectivity check: %s", exc)
            break

    return False


__all__ = ['check_database_connectivity']
