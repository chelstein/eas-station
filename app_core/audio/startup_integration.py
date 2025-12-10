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

"""
EAS Monitoring Startup Integration

Wires together the complete data flow:
Audio Sources → Controller → Adapter → Monitor → Decoder → Database

This module should be called during Flask app initialization to enable
continuous SAME monitoring.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def initialize_eas_monitoring_system() -> bool:
    """
    Initialize and start the complete EAS monitoring system.

    This function:
    1. Checks if audio processing should run in this service
    2. Tries to acquire master worker lock (multi-worker coordination)
    3. Gets the global AudioIngestController (master only)
    4. Creates an alert callback for processing detections
    5. Initializes the EAS monitor with adapter
    6. Auto-starts continuous monitoring

    Service Architecture:
    - Separated: Audio service runs audio processing, web app reads from Redis
    - Integrated: Web app runs everything (with master/slave worker coordination)

    Returns:
        True if successfully initialized and started

    Should be called during Flask app startup (in initialize_database or similar).
    """
    # Separated architecture: Audio processing handled by dedicated audio-service process
    # This web application process only serves the web UI and reads metrics from Redis
    logger.info("🌐 Web application running in UI-only mode")
    logger.info("   Audio processing handled by dedicated audio-service process")
    logger.info("   Metrics read from Redis (published by audio-service)")
    return True  # Success - separated architecture


def load_fips_codes_from_config() -> list:
    """
    Load configured FIPS codes from application settings.

    Returns list of FIPS codes to monitor. If empty list is returned (none configured
    or error loading), the FIPS filtering callback will accept ALL alerts without filtering.
    """
    try:
        from app_core.location import get_location_settings

        settings = get_location_settings()
        fips_codes = settings.get('fips_codes', [])

        # Ensure it's a list
        if isinstance(fips_codes, str):
            # Handle comma-separated string
            fips_codes = [code.strip() for code in fips_codes.split(',') if code.strip()]

        return fips_codes

    except Exception as e:
        logger.warning(f"Could not load FIPS codes from config: {e}")
        # Return empty list - with no FIPS filtering, ALL alerts will be accepted
        return []


def create_fips_filtering_callback(
    configured_fips_codes: list,
    flask_app,
    logger_instance: Optional[logging.Logger] = None
):
    """
    Create a FIPS-filtering callback for EAS monitor integration with Flask app.

    This is a convenience wrapper around the core create_fips_filtering_callback
    from eas_monitor.py. It creates a forward callback that stores alerts in the
    database and then delegates to the actual FIPS filtering logic.

    Args:
        configured_fips_codes: List of FIPS codes to monitor
        flask_app: Flask application instance for database access
        logger_instance: Optional logger instance

    Returns:
        Callback function suitable for ContinuousEASMonitor
    """
    from app_core.audio.eas_monitor import (
        create_fips_filtering_callback as _create_fips_filtering_callback,
        EASAlert
    )

    log = logger_instance or logger

    def forward_to_database(alert: EASAlert) -> Optional[int]:
        """
        Forward callback that stores alert in database.

        This function is called when an alert matches configured FIPS codes.
        It stores the alert in the database for broadcasting/forwarding.

        Returns:
            Message ID if successfully stored, None otherwise
        """
        try:
            # Import here to avoid circular dependencies
            from app_core.models import EASMessage, db
            from flask import has_app_context

            # Ensure we're in Flask app context
            if not has_app_context():
                with flask_app.app_context():
                    return _store_alert_in_context(alert, log)
            else:
                return _store_alert_in_context(alert, log)

        except Exception as e:
            log.error(f"Failed to store alert in database: {e}", exc_info=True)
            return None

    def _store_alert_in_context(alert: EASAlert, log):
        """Helper to store alert within Flask app context."""
        from app_core.models import EASMessage, db

        # Extract SAME header from first header
        same_header = "UNKNOWN"
        if alert.headers and len(alert.headers) > 0:
            first_header = alert.headers[0]
            same_header = first_header.get('raw_text', 'UNKNOWN')

        # Create EAS message record
        # Note: This creates a minimal record. The actual audio generation
        # and broadcasting should be handled by dedicated EAS broadcast logic.
        eas_message = EASMessage(
            same_header=same_header,
            audio_filename=f"auto_{int(time.time())}.wav",
            text_filename=f"auto_{int(time.time())}.txt"
        )

        db.session.add(eas_message)
        db.session.commit()

        log.info(f"Stored EAS alert in database: ID={eas_message.id}, SAME={same_header[:50]}...")
        return eas_message.id

    # Now create the actual FIPS filtering callback using the core function
    return _create_fips_filtering_callback(
        configured_fips_codes=configured_fips_codes,
        forward_callback=forward_to_database,
        logger_instance=log
    )
