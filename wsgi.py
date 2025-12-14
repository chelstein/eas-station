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
from datetime import datetime
import tempfile

# Configure logging early for wsgi startup diagnostics
# NOTE: Gunicorn will override this with its own logging config, but this ensures
# that errors during import are visible if running outside Gunicorn
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

# DIAGNOSTIC: Print immediately to stderr before importing app
# This proves the worker is reaching this point
print(f"\n{'=' * 80}", file=sys.stderr, flush=True)
print(f"WSGI PRE-IMPORT: Worker PID {os.getpid()} about to import app module...", file=sys.stderr, flush=True)
print(f"{'=' * 80}\n", file=sys.stderr, flush=True)

from app import app as application, socketio, initialize_database  # noqa: E402

# DIAGNOSTIC: Print immediately after import completes
print(f"\n{'=' * 80}", file=sys.stderr, flush=True)
print(f"WSGI POST-IMPORT: Worker PID {os.getpid()} successfully imported app module", file=sys.stderr, flush=True)
print(f"{'=' * 80}\n", file=sys.stderr, flush=True)

# Initialize database eagerly when Gunicorn workers start
# This prevents the first request from hanging while initialization completes
# Skip during migrations to avoid chicken-and-egg problems
# Skip if setup mode is active (database unavailable)
if not os.environ.get("SKIP_DB_INIT") and not application.config.get('SETUP_MODE'):
    logger = logging.getLogger(__name__)
    
    # Force unbuffered stderr for immediate visibility in journalctl
    try:
        # Python 3.7+ reconfigure method
        sys.stderr.reconfigure(line_buffering=True)
    except AttributeError:
        # Fallback for older Python versions
        sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 1)
    
    startup_banner = (
        f"\n{'=' * 80}\n"
        f"WSGI STARTUP: Worker PID {os.getpid()} initializing database...\n"
        f"{'=' * 80}\n"
    )
    print(startup_banner, file=sys.stderr, flush=True)
    logger.info("WSGI: Initializing database at worker startup (PID: %d)...", os.getpid())
    
    try:
        with application.app_context():
            if not initialize_database():
                # Try to get the actual error from the global variable
                from app import _db_initialization_error
                error_details = str(_db_initialization_error) if _db_initialization_error else "Unknown error"
                
                error_msg = (
                    f"\n{'=' * 80}\n"
                    f"FATAL ERROR: Database initialization failed!\n"
                    f"Worker PID: {os.getpid()}\n"
                    f"{'=' * 80}\n"
                    f"Error: {error_details}\n"
                    f"{'=' * 80}\n"
                    f"Common causes:\n"
                    f"  1. PostgreSQL is not running (check: systemctl status postgresql)\n"
                    f"  2. Database credentials in .env are incorrect (check DATABASE_URL)\n"
                    f"  3. Database 'eas_station' does not exist (run: createdb eas_station)\n"
                    f"  4. Network connectivity to database host failed\n"
                    f"  5. PostGIS extension is not installed (run: apt install postgresql-postgis)\n"
                    f"{'=' * 80}\n"
                    f"Troubleshooting commands:\n"
                    f"  sudo journalctl -u eas-station-web.service -n 200 --no-pager\n"
                    f"  sudo systemctl status postgresql\n"
                    f"  psql -U eas_station -d eas_station -c 'SELECT version();'\n"
                    f"{'=' * 80}\n"
                )
                
                # Print to stderr with flush for immediate visibility
                print(error_msg, file=sys.stderr, flush=True)
                logger.critical("WSGI: Database initialization failed! Error: %s", error_details)
                
                # Write to secure temporary file for persistence
                try:
                    with tempfile.NamedTemporaryFile(
                        mode='w',
                        prefix='eas-station-web-startup-error-',
                        suffix='.log',
                        dir='/var/log/eas-station' if os.path.exists('/var/log/eas-station') else None,
                        delete=False
                    ) as f:
                        f.write(error_msg)
                        f.write(f"\nTimestamp: {datetime.now()}\n")
                        error_log_path = f.name
                    logger.critical("Error details written to: %s", error_log_path)
                except Exception as log_error:
                    # Silently ignore if we can't write the file
                    logger.debug("Could not write error log file: %s", log_error)
                
                raise RuntimeError(f"Database initialization failed: {error_details}")
    except Exception as e:
        error_msg = (
            f"\n{'=' * 80}\n"
            f"FATAL ERROR: Exception during database initialization!\n"
            f"Worker PID: {os.getpid()}\n"
            f"{'=' * 80}\n"
            f"Exception Type: {type(e).__name__}\n"
            f"Exception Message: {str(e)}\n"
            f"{'=' * 80}\n"
        )
        print(error_msg, file=sys.stderr, flush=True)
        logger.critical("WSGI: Exception during database initialization: %s", e, exc_info=True)
        
        # Write to secure temporary file for persistence
        try:
            import traceback
            with tempfile.NamedTemporaryFile(
                mode='w',
                prefix='eas-station-web-startup-error-',
                suffix='.log',
                dir='/var/log/eas-station' if os.path.exists('/var/log/eas-station') else None,
                delete=False
            ) as f:
                f.write(error_msg)
                f.write(f"\nFull traceback:\n")
                f.write(traceback.format_exc())
                f.write(f"\nTimestamp: {datetime.now()}\n")
                error_log_path = f.name
            logger.critical("Error details written to: %s", error_log_path)
        except Exception as log_error:
            # Silently ignore if we can't write the file
            logger.debug("Could not write error log file: %s", log_error)
        
        raise
    
    success_banner = (
        f"\n{'=' * 80}\n"
        f"WSGI STARTUP: Worker PID {os.getpid()} database initialization complete ✓\n"
        f"{'=' * 80}\n"
    )
    print(success_banner, file=sys.stderr, flush=True)
    logger.info("WSGI: Database initialization complete (PID: %d)", os.getpid())
elif application.config.get('SETUP_MODE'):
    logger = logging.getLogger(__name__)
    setup_reasons = ', '.join(application.config.get('SETUP_MODE_REASONS', []))
    logger.warning("WSGI: Skipping database initialization - application is in setup mode (%s)", setup_reasons)
    logger.warning("WSGI: Visit /setup to complete configuration")

__all__ = ["application", "socketio"]
