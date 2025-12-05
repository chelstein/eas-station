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

"""
Standalone EAS Service

This service handles ONLY EAS monitoring and alert detection:
- Subscribes to Redis audio streams from audio-service
- Runs continuous EAS/SAME header detection
- Stores detected alerts in database
- NO audio processing, NO SDR hardware access

Architecture:
                    ┌─────────────────┐
                    │   audio-service │
                    │ (Audio from SDR)│
                    └────────┬────────┘
                             │ Redis audio pub/sub
                             ▼
            ┌────────────────────────────────┐
            │         eas_service.py         │
            │   (This file - EAS only)       │
            │                                │
            │  - Subscribe to Redis audio   │
            │  - SAME header detection       │
            │  - FIPS code filtering         │
            │  - Alert database storage      │
            └────────────────────────────────┘

Benefits:
- EAS crashes don't affect audio processing
- EAS service can be restarted independently
- Clear separation of concerns
- Easy to scale EAS monitoring across multiple audio sources
"""

import os
import sys
import time
import signal
import logging
from typing import Optional, Any
from dotenv import load_dotenv

# Configure logging early
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables from persistent config volume
_config_path = os.environ.get('CONFIG_PATH')
if _config_path:
    if os.path.exists(_config_path):
        load_dotenv(_config_path, override=True)
        logger.info(f"✅ Loaded environment from: {_config_path}")
    else:
        logger.warning(f"⚠️  CONFIG_PATH set but file not found: {_config_path}")
        load_dotenv(override=True)
else:
    load_dotenv(override=True)
    logger.info("Loaded environment from .env file")

# Global state
_flask_app: Optional[Any] = None
_eas_monitor: Optional[Any] = None
_running = True


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global _running
    logger.info(f"Received signal {signum}, shutting down...")
    _running = False


def create_app():
    """Create minimal Flask app for database access."""
    from flask import Flask
    from app_core.extensions import db

    app = Flask(__name__)

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql://{os.environ.get('POSTGRES_USER', 'postgres')}:"
        f"{os.environ.get('POSTGRES_PASSWORD', 'postgres')}@"
        f"{os.environ.get('POSTGRES_HOST', 'localhost')}:"
        f"{os.environ.get('POSTGRES_PORT', '5432')}/"
        f"{os.environ.get('POSTGRES_DB', 'alerts')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 5,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }

    # Initialize extensions
    db.init_app(app)

    logger.info("✅ Flask app created for database access")
    return app


def initialize_eas_monitor(app):
    """Initialize EAS monitor that subscribes to Redis audio."""
    global _eas_monitor

    with app.app_context():
        from app_core.audio.eas_monitor import ContinuousEASMonitor
        from app_core.audio.redis_audio_adapter import RedisAudioAdapter
        from app_core.audio.startup_integration import (
            load_fips_codes_from_config,
            create_fips_filtering_callback
        )

        logger.info("Initializing EAS monitor...")

        # Load FIPS codes from configuration
        configured_fips = load_fips_codes_from_config()
        logger.info(f"Loaded {len(configured_fips)} FIPS codes for monitoring")

        # Create FIPS filtering callback
        fips_callback = create_fips_filtering_callback(
            configured_fips_codes=configured_fips,
            flask_app=app
        )

        # Create Redis audio adapter
        # Subscribes to audio:samples:* channels published by audio-service
        audio_adapter = RedisAudioAdapter(
            subscriber_id="eas-monitor",
            sample_rate=16000,  # EAS monitor expects 16kHz
            read_timeout=0.5
        )

        # Create EAS monitor
        _eas_monitor = ContinuousEASMonitor(
            audio_manager=audio_adapter,
            sample_rate=16000,
            alert_callback=fips_callback,
            save_audio_files=True
        )

        # Start monitoring
        if _eas_monitor.start():
            logger.info("✅ EAS monitor started successfully")
        else:
            raise RuntimeError("Failed to start EAS monitor")

        return _eas_monitor


def main():
    """Main entry point for EAS service."""
    global _flask_app, _eas_monitor, _running

    logger.info("=" * 80)
    logger.info("EAS Station - Standalone EAS Service")
    logger.info("Handles EAS/SAME detection and alert storage ONLY")
    logger.info("=" * 80)

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Create Flask app for database access
        _flask_app = create_app()

        # Initialize EAS monitor
        _eas_monitor = initialize_eas_monitor(_flask_app)

        logger.info("✅ EAS service started successfully")
        logger.info("Monitoring for EAS alerts...")

        # Main loop - just keep service alive
        while _running:
            time.sleep(1.0)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error in EAS service: {e}", exc_info=True)
        return 1
    finally:
        # Cleanup
        if _eas_monitor:
            try:
                _eas_monitor.stop()
                logger.info("✅ EAS monitor stopped")
            except Exception as e:
                logger.exception("Error stopping EAS monitor")

        logger.info("EAS service shutdown complete")

    return 0


if __name__ == "__main__":
    sys.exit(main())
