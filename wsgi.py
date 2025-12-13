#!/usr/bin/env python3
"""
EAS Station - Emergency Alert System
Copyright (c) 2025 Timothy Kramer (KR8MER)

This file is part of EAS Station.

EAS Station is dual-licensed software:
- GNU Affero General Public License v3 (AGPL-3.0) for open-source use
- Commercial License for proprietary use

You should have received a copy of both licenses with this software.
For more information, see LICENSE and LICENSE-COMMERCIAL files.

IMPORTANT: This software cannot be rebranded or have attribution removed.
See NOTICE file for complete terms.

Repository: https://github.com/KR8MER/eas-station
"""

import os
import sys
import logging

# Configure logging early for wsgi startup diagnostics
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S %z'
)


def _project_root() -> str:
    """Return the project root based on this file's location."""
    return os.path.dirname(os.path.abspath(__file__))


project_dir = _project_root()
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

os.chdir(project_dir)

from app import app as application, socketio, initialize_database  # noqa: E402

# Initialize database eagerly when Gunicorn workers start
# This prevents the first request from hanging while initialization completes
# Skip during migrations to avoid chicken-and-egg problems
if not os.environ.get("SKIP_DB_INIT"):
    logger = logging.getLogger(__name__)
    logger.info("WSGI: Initializing database at worker startup...")
    with application.app_context():
        if not initialize_database():
            # Try to get the actual error from the global variable
            from app import _db_initialization_error
            error_details = str(_db_initialization_error) if _db_initialization_error else "Unknown error"
            logger.critical("WSGI: Database initialization failed! Error: %s", error_details)
            raise RuntimeError(f"Database initialization failed: {error_details}")
    logger.info("WSGI: Database initialization complete")

__all__ = ["application", "socketio"]
