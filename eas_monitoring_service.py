#!/usr/bin/env python3
"""
EAS Station - Emergency Alert System
Copyright (c) 2025-2026 Timothy Kramer (KR8MER)

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
EAS Monitoring Service

This service handles EAS/SAME monitoring and audio processing (NO SDR hardware access).

This service handles:
- Audio demodulation from IQ samples (received via Redis from sdr-service)
- EAS/SAME header monitoring and decoding
- HTTP/Icecast stream ingestion
- Icecast streaming output
- Metrics publishing to Redis

Architecture (Separated):
┌────────────────────────┐      Redis       ┌──────────────────────────┐
│ sdr_hardware_service.py│ ──> IQ samples ──>│ eas_monitoring_service.py│
│ (USB access)           │   (pub/sub)      │ (NO USB access)          │
│ - SDR hardware         │                  │ - Demodulation           │
│ - IQ sampling          │                  │ - EAS monitoring         │
└────────────────────────┘                  │ - Icecast streaming      │
                                            └──────────────────────────┘
  
The web application reads metrics from Redis and serves the UI.
"""

import os
import sys
import math
import time
import signal
import logging
import threading
import redis
import json
from typing import Optional, Any, Dict
from dotenv import load_dotenv

# Configure logging early
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG to show diagnostic logs
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Constants
FFT_MIN_MAGNITUDE = 1e-10  # Minimum magnitude to avoid log(0) in dB conversion
MIN_AUDIO_SAMPLE_RATE = 8000  # Minimum valid audio sample rate (Hz)

# Load environment variables from persistent config volume
# This must happen before initializing audio sources
_config_path = os.environ.get('CONFIG_PATH')
if _config_path:
    if os.path.exists(_config_path):
        load_dotenv(_config_path, override=True)
        logger.info(f"✅ Loaded environment from: {_config_path}")
    else:
        logger.warning(f"⚠️  CONFIG_PATH set but file not found: {_config_path}")
        load_dotenv(override=True)  # Fall back to default .env
else:
    load_dotenv(override=True)  # Use default .env location

# Global state with thread-safe access
_state_lock = threading.Lock()
_running = True
_redis_client: Optional[redis.Redis] = None
_audio_controller = None
_eas_monitor = None
_auto_streaming_service = None
# NOTE: _radio_manager removed - audio-service does NOT access SDR hardware
# SDR hardware is managed exclusively by sdr-service.py container

# Registry of running AudioArchiver instances: source_name -> AudioArchiver
_archivers: dict = {}

# Registry of RedisAudioPublisher instances for the eas-service: source_name -> publisher
_redis_eas_publishers: dict = {}


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _running
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    _running = False


def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client with retry logic.

    Uses app_core.redis_client for robust connection handling with
    exponential backoff and circuit breaker pattern.
    """
    global _redis_client

    # Use robust Redis client with retry logic
    from app_core.redis_client import get_redis_client as get_robust_client

    try:
        _redis_client = get_robust_client(
            max_retries=5,
            initial_backoff=1.0,
            max_backoff=30.0
        )
        return _redis_client
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis: {e}")
        raise


def _sanitize_value(value: Any) -> Any:
    """Convert runtime values to JSON-serializable primitives.

    Handles numpy types and Python float inf/nan values that would
    otherwise cause json.dumps() to raise ValueError.
    """
    try:
        import numpy as np  # type: ignore

        if isinstance(value, (np.floating, np.integer)):
            v = float(value)
            if math.isinf(v):
                return -120.0 if v < 0 else 120.0
            if math.isnan(v):
                return -120.0
            return v
        if isinstance(value, np.bool_):
            return bool(value)
    except Exception:
        # numpy is optional in some deployments; ignore if unavailable
        pass

    if isinstance(value, bool):
        return value

    if isinstance(value, float):
        if math.isinf(value):
            return -120.0 if value < 0 else 120.0
        if math.isnan(value):
            return -120.0
        return value

    if isinstance(value, (str, int)):
        return value

    if isinstance(value, dict):
        return {str(k): _sanitize_value(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_sanitize_value(v) for v in value]

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    try:
        return float(value)
    except Exception:
        return str(value)


def initialize_database():
    """Initialize database connection for configuration."""
    from app_core.extensions import db
    from flask import Flask

    # Create minimal Flask app for database access
    app = Flask(__name__)

    # Database configuration
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    return app


def initialize_radio_receivers(app):
    """DEPRECATED: Do not use in separated architecture.
    
    In separated architecture, sdr-service.py handles all SDR hardware access.
    This function is kept for backward compatibility but should NOT be called
    from audio-service.py as it conflicts with sdr-service.
    
    If you need SDR functionality in audio-service, ensure:
    1. sdr-service.py is running and publishing to Redis
    2. AudioSourceConfigDB entries exist with managed_by='radio'
    3. RedisSDRSourceAdapter will automatically subscribe to sdr:samples:{receiver_id}
    
    The sync_radio_receiver_audio_sources() function handles step 2 automatically.
    """
    logger.warning(
        "initialize_radio_receivers() called but DEPRECATED in separated architecture. "
        "SDR hardware should be managed by sdr-service.py container. "
        "Use sync_radio_receiver_audio_sources() + RedisSDRSourceAdapter instead."
    )
    return  # Do nothing - prevents conflict with sdr-service


def sync_radio_receiver_audio_sources(app):
    """Ensure audio sources exist for all enabled radio receivers with audio_output=True.
    
    This is critical for the separated architecture where sdr-service publishes IQ samples
    to Redis and audio-service needs AudioSourceConfigDB entries to know which channels
    to subscribe to via RedisSDRSourceAdapter.
    """
    with app.app_context():
        from app_core.models import RadioReceiver, AudioSourceConfigDB, db
        from app_core.audio.ingest import AudioSourceType
        
        logger.info("Syncing audio sources for radio receivers...")
        
        # Get all radio receivers that should have audio sources
        receivers = RadioReceiver.query.filter_by(enabled=True, audio_output=True).all()
        
        if not receivers:
            logger.info("No radio receivers with audio output enabled")
            return
        
        created = 0
        updated = 0
        
        for receiver in receivers:
            source_name = f"sdr-{receiver.identifier}"
            
            # Determine audio sample rate - use explicit setting or auto-detect from modulation
            modulation = (receiver.modulation_type or 'IQ').upper()
            
            # Use explicit audio_sample_rate if configured, otherwise auto-detect
            if receiver.audio_sample_rate and receiver.audio_sample_rate >= MIN_AUDIO_SAMPLE_RATE:
                sample_rate = receiver.audio_sample_rate
                # Channels based on stereo setting
                channels = 2 if (modulation in ('FM', 'WFM', 'WBFM') and receiver.stereo_enabled) else 1
                logger.debug(f"Using configured audio_sample_rate for {receiver.identifier}: {sample_rate} Hz")
            else:
                # Auto-detect based on modulation type
                if modulation in ('FM', 'WFM', 'WBFM') and receiver.stereo_enabled:
                    channels = 2
                    sample_rate = 48000
                elif modulation in ('FM', 'WFM', 'WBFM'):
                    channels = 1
                    sample_rate = 32000
                elif modulation in ('NFM', 'AM'):
                    channels = 1
                    sample_rate = 24000
                else:
                    channels = 1
                    sample_rate = 44100
                logger.debug(f"Auto-detected audio settings for {receiver.identifier}: {sample_rate} Hz, {channels} ch")
            
            buffer_size = 4096 if channels == 1 else 8192
            silence_threshold = float(receiver.squelch_threshold_db or -60.0)
            silence_duration = max(float(receiver.squelch_close_ms or 750) / 1000.0, 0.1)
            
            device_params = {
                'receiver_id': receiver.identifier,
                'receiver_display_name': receiver.display_name,
                'receiver_driver': receiver.driver,
                'receiver_frequency_hz': float(receiver.frequency_hz or 0.0),
                'receiver_modulation': modulation,
                'iq_sample_rate': receiver.sample_rate,
                'demod_mode': receiver.modulation_type or 'FM',
                # RBDS and demodulation settings - use both key names for compatibility
                'enable_rbds': bool(receiver.enable_rbds),
                'rbds_enabled': bool(receiver.enable_rbds),
                'stereo_enabled': bool(receiver.stereo_enabled),
                'deemphasis_us': float(receiver.deemphasis_us or 75.0),  # 75μs for North America
                'squelch_enabled': bool(receiver.squelch_enabled),
                'squelch_threshold_db': silence_threshold,
                'squelch_open_ms': int(receiver.squelch_open_ms or 150),
                'squelch_close_ms': int(receiver.squelch_close_ms or 750),
                'carrier_alarm_enabled': bool(receiver.squelch_alarm),
            }
            
            config_params = {
                'sample_rate': sample_rate,
                'channels': channels,
                'buffer_size': buffer_size,
                'silence_threshold_db': silence_threshold,
                'silence_duration_seconds': silence_duration,
                'device_params': device_params,
                'managed_by': 'radio',  # CRITICAL: This flag tells audio-service to use RedisSDRSourceAdapter
                'squelch_enabled': bool(receiver.squelch_enabled),
                'squelch_threshold_db': silence_threshold,
                'squelch_open_ms': int(receiver.squelch_open_ms or 150),
                'squelch_close_ms': int(receiver.squelch_close_ms or 750),
                'carrier_alarm_enabled': bool(receiver.squelch_alarm),
            }
            
            freq_display = f"{receiver.frequency_hz/1e6:.3f} MHz" if receiver.frequency_hz else "Unknown"
            description = f"SDR monitor for {receiver.display_name} · {freq_display}"
            
            # DEBUG: Log RBDS setting being synced
            logger.info(f"Syncing receiver '{receiver.identifier}': enable_rbds={receiver.enable_rbds}")

            # Check if audio source exists
            db_config = AudioSourceConfigDB.query.filter_by(name=source_name).first()

            if db_config is None:
                # Create new audio source
                logger.info(f"Creating audio source for receiver '{receiver.identifier}': {source_name}")
                db_config = AudioSourceConfigDB(
                    name=source_name,
                    source_type=AudioSourceType.SDR.value,
                    config_params=config_params,
                    priority=10,
                    enabled=True,
                    auto_start=receiver.auto_start,
                    description=description,
                )
                db.session.add(db_config)
                created += 1
            else:
                # Update existing audio source if config changed
                existing_params = db_config.config_params or {}
                existing_rbds = existing_params.get('device_params', {}).get('enable_rbds', 'NOT_SET')
                new_rbds = config_params.get('device_params', {}).get('enable_rbds', 'NOT_SET')
                logger.debug(f"Comparing configs for '{receiver.identifier}': existing_rbds={existing_rbds}, new_rbds={new_rbds}")

                if existing_params != config_params:
                    logger.info(f"Updating audio source for receiver '{receiver.identifier}': {source_name} (rbds: {existing_rbds} -> {new_rbds})")
                    db_config.config_params = config_params
                    db_config.enabled = True
                    db_config.auto_start = receiver.auto_start
                    db_config.description = description
                    updated += 1
                else:
                    logger.debug(f"No config change for '{receiver.identifier}' (rbds={new_rbds})")
        
        if created > 0 or updated > 0:
            db.session.commit()
            logger.info(f"✅ Synced audio sources: {created} created, {updated} updated")
        else:
            logger.info("✅ All audio sources already in sync")


def initialize_audio_controller(app):
    """Initialize audio ingestion controller."""
    global _audio_controller

    with app.app_context():
        from app_core.audio.ingest import AudioIngestController, AudioSourceConfig, AudioSourceType
        from app_core.audio.sources import create_audio_source
        from app_core.models import AudioSourceConfigDB

        logger.info("Initializing audio controller...")
        
        # Sync audio sources for radio receivers before loading from database.
        # This ensures that audio sources exist for all enabled receivers with
        # audio_output=True.  Run inside a try/except so that a bad receiver
        # config (e.g. a DB commit error) degrades gracefully rather than
        # crashing the entire audio service.
        try:
            sync_radio_receiver_audio_sources(app)
        except Exception as sync_exc:
            logger.error(
                "sync_radio_receiver_audio_sources failed (continuing without SDR sync): %s",
                sync_exc, exc_info=True,
            )

        # Create controller — use 30s stall threshold so HTTP streams have enough
        # time for DNS + TCP + HTTP + FFmpeg -analyzeduration before the health
        # monitor fires a false "stalled capture" and restarts them.  The default
        # of 5 s is far too short for network radio streams.
        _audio_controller = AudioIngestController(stall_seconds=30)

        # Load audio sources from database
        saved_configs = AudioSourceConfigDB.query.all()
        logger.info(f"Loading {len(saved_configs)} audio source configurations from database")

        for db_config in saved_configs:
            try:
                # Parse source type
                source_type_str = db_config.source_type
                
                # CRITICAL: In separated architecture, convert 'sdr' to redis_sdr
                # Database stores 'sdr' for radio-managed sources, but audio-service
                # must use RedisSDRSourceAdapter to subscribe to IQ samples from sdr-service
                if source_type_str == 'sdr':
                    # Check if this is a radio-managed source (from RadioReceiver)
                    config_params = db_config.config_params or {}
                    if config_params.get('managed_by') == 'radio':
                        # This is an SDR receiver - use Redis adapter in separated architecture
                        from app_core.audio.redis_sdr_adapter import RedisSDRSourceAdapter
                        
                        runtime_config = AudioSourceConfig(
                            source_type=AudioSourceType.STREAM,  # Use STREAM as placeholder
                            name=db_config.name,
                            enabled=db_config.enabled,
                            priority=db_config.priority,
                            sample_rate=config_params.get('sample_rate', 44100),
                            channels=config_params.get('channels', 1),
                            buffer_size=config_params.get('buffer_size', 4096),
                            silence_threshold_db=config_params.get('silence_threshold_db', -60.0),
                            silence_duration_seconds=config_params.get('silence_duration_seconds', 5.0),
                            device_params=config_params.get('device_params', {}),
                        )
                        
                        # Create Redis SDR adapter directly (subscribes to IQ samples)
                        adapter = RedisSDRSourceAdapter(runtime_config)
                        _audio_controller.add_source(adapter)
                        
                        # Log with receiver details for debugging
                        device_params = config_params.get('device_params', {})
                        receiver_id = device_params.get('receiver_id', 'unknown')
                        receiver_name = device_params.get('receiver_display_name', 'unknown')
                        receiver_freq = device_params.get('receiver_frequency_hz', 0)
                        freq_display = f"{receiver_freq/1e6:.3f} MHz" if receiver_freq else "unknown"
                        
                        logger.info(
                            f"✅ Loaded Redis SDR source: {db_config.name} "
                            f"(receiver: {receiver_name} @ {freq_display}, "
                            f"subscribes to sdr:samples:{receiver_id})"
                        )
                        continue
                
                # Normal source type handling
                source_type = AudioSourceType(source_type_str)

                # Create runtime configuration from database config
                config_params = db_config.config_params or {}
                runtime_config = AudioSourceConfig(
                    source_type=source_type,
                    name=db_config.name,
                    enabled=db_config.enabled,
                    priority=db_config.priority,
                    sample_rate=config_params.get('sample_rate', 44100),
                    channels=config_params.get('channels', 1),
                    buffer_size=config_params.get('buffer_size', 4096),
                    silence_threshold_db=config_params.get('silence_threshold_db', -60.0),
                    silence_duration_seconds=config_params.get('silence_duration_seconds', 5.0),
                    device_params=config_params.get('device_params', {}),
                )

                # Create and add adapter
                adapter = create_audio_source(runtime_config)
                _audio_controller.add_source(adapter)
                logger.info(f"Loaded audio source: {db_config.name} ({db_config.source_type})")

            except Exception as e:
                logger.error(f"Error loading source '{db_config.name}': {e}", exc_info=True)

        logger.info(f"Loaded {len(_audio_controller.get_all_sources())} audio source configurations")

        # Start auto-start sources
        auto_start_sources = [db_config for db_config in saved_configs if db_config.enabled and db_config.auto_start]
        if auto_start_sources:
            logger.info(f"Auto-starting {len(auto_start_sources)} enabled source(s)...")
            for db_config in auto_start_sources:
                try:
                    # Extract receiver info for SDR sources
                    if db_config.source_type == 'sdr':
                        config_params = db_config.config_params or {}
                        device_params = config_params.get('device_params', {})
                        receiver_id = device_params.get('receiver_id', 'unknown')
                        receiver_name = device_params.get('receiver_display_name', 'unknown')
                        logger.info(
                            f"Auto-starting source: '{db_config.name}' "
                            f"(type: {db_config.source_type}, receiver: {receiver_name}, id: {receiver_id})"
                        )
                    else:
                        logger.info(f"Auto-starting source: '{db_config.name}' (type: {db_config.source_type})")
                    
                    result = _audio_controller.start_source(db_config.name)
                    if result:
                        logger.info(f"✅ Successfully started '{db_config.name}'")
                    else:
                        logger.warning(f"⚠️ Failed to start '{db_config.name}' (start returned False)")
                except Exception as e:
                    logger.error(f"❌ Exception auto-starting '{db_config.name}': {e}", exc_info=True)
        else:
            logger.info("No sources configured for auto-start")

        logger.info("✅ Audio controller initialized")
        return _audio_controller


def initialize_auto_streaming(app, audio_controller):
    """Initialize Icecast auto-streaming service."""
    global _auto_streaming_service

    try:
        with app.app_context():
            from app_core.audio.icecast_auto_config import get_icecast_auto_config
            from app_core.audio.auto_streaming import AutoStreamingService
            from app_core.audio.stream_profiles import StreamFormat

            auto_config = get_icecast_auto_config()

            if not auto_config.is_enabled():
                logger.info("Icecast auto-streaming is disabled (ICECAST_ENABLED=false)")
                return None

            logger.info(f"Initializing Icecast auto-streaming: {auto_config.server}:{auto_config.port}")

            # Map format string to enum
            stream_format = StreamFormat.MP3 if auto_config.stream_format.lower() == 'mp3' else StreamFormat.OGG

            _auto_streaming_service = AutoStreamingService(
                icecast_server=auto_config.server,
                icecast_port=auto_config.port,
                icecast_password=auto_config.source_password,
                icecast_admin_user=auto_config.admin_user,
                icecast_admin_password=auto_config.admin_password,
                default_bitrate=auto_config.stream_bitrate,  # Use configured bitrate from database/env
                default_format=stream_format,  # Use configured format from database/env
                enabled=True,
                audio_controller=audio_controller
            )

            # Start the service
            if _auto_streaming_service.start():
                logger.info("✅ Icecast auto-streaming service started successfully")
            else:
                logger.warning("Icecast auto-streaming service failed to start")

            return _auto_streaming_service

    except Exception as exc:
        logger.error(f"Failed to initialize Icecast auto-streaming: {exc}", exc_info=True)
        return None


def _make_metadata_log_callback(flask_app):
    """Return a thread-safe callback that persists ICY metadata changes to the DB."""
    import threading

    def _callback(source_name: str, updates: dict) -> None:
        def _write() -> None:
            try:
                with flask_app.app_context():
                    from app_core.extensions import db
                    from app_core.models import StreamMetadataLog

                    now_playing = updates.get('now_playing', {})
                    record = StreamMetadataLog(
                        source_name=source_name,
                        # updates['title'] / updates['artist'] are only set when a clean
                        # value was actually parsed out of the ICY StreamTitle.
                        # now_playing['title'] can be the full raw ICY blob (it is
                        # initialised from stream_title before any pattern matching),
                        # so we must NOT fall back to it for the title column.
                        # now_playing['artist'] is safe because it starts as None and is
                        # only populated when a real artist string was extracted.
                        title=updates.get('title'),
                        artist=updates.get('artist') or now_playing.get('artist'),
                        album=updates.get('album'),
                        artwork_url=updates.get('artwork_url'),
                        length=updates.get('length'),
                        display=updates.get('song'),
                        raw=updates.get('song_raw'),
                        stream_url=updates.get('stream_url'),
                    )
                    db.session.add(record)
                    db.session.commit()
            except Exception as exc:
                logger.warning("Failed to log stream metadata for '%s': %s", source_name, exc)

        threading.Thread(target=_write, daemon=True).start()

    return _callback


def _make_audio_alert_log_callback(flask_app):
    """Return a thread-safe callback that persists audio source events to the AudioAlert DB table.

    The callback signature is ``(source_name: str, event_type: str, message: str)``.
    ``event_type`` is one of: ``'stall'``, ``'error'``, ``'disconnected'``.
    """
    import threading

    # Map event types to alert levels recognised by the DB model
    _LEVEL_MAP = {
        'stall': 'warning',
        'error': 'error',
        'disconnected': 'warning',
    }

    # Deduplicate rapid-fire alerts: only write one record per source per
    # event type within a short window to avoid flooding the table.
    _last_written: dict = {}  # key: (source_name, event_type) → timestamp
    _dedup_seconds = 30.0
    _lock = threading.Lock()

    def _callback(source_name: str, event_type: str, message: str) -> None:
        import time as _time
        now = _time.time()
        key = (source_name, event_type)
        with _lock:
            if now - _last_written.get(key, 0) < _dedup_seconds:
                return
            _last_written[key] = now

        def _write() -> None:
            try:
                with flask_app.app_context():
                    from app_core.extensions import db
                    from app_core.models import AudioAlert

                    record = AudioAlert(
                        source_name=source_name,
                        alert_level=_LEVEL_MAP.get(event_type, 'warning'),
                        alert_type=event_type,
                        message=message,
                    )
                    db.session.add(record)
                    db.session.commit()
            except Exception as exc:
                logger.warning("Failed to log audio alert for '%s' (%s): %s", source_name, event_type, exc)

        threading.Thread(target=_write, daemon=True).start()

    return _callback


def initialize_archivers(app, audio_controller):
    """Start AudioArchivers for sources that have archiving enabled in their config_params.

    Each AudioSourceConfigDB record may carry an ``"archive"`` key inside
    ``config_params``.  When ``archive.enabled`` is true, an AudioArchiver is
    created and started, then stored in ``_archivers``.
    """
    global _archivers

    try:
        from app_core.audio.archiver import AudioArchiver, AudioArchiverConfig
        from app_core.audio.ingest import AudioSourceStatus
        from app_core.models import AudioSourceConfigDB

        with app.app_context():
            db_configs = AudioSourceConfigDB.query.all()

        started = 0
        for db_config in db_configs:
            config_params = db_config.config_params or {}
            archive_cfg = config_params.get('archive', {})
            if not archive_cfg.get('enabled', False):
                continue

            source_name = db_config.name
            adapter = audio_controller._sources.get(source_name)
            if adapter is None:
                logger.debug("initialize_archivers: source '%s' not loaded yet – skipping", source_name)
                continue

            if adapter.status != AudioSourceStatus.RUNNING:
                logger.debug(
                    "initialize_archivers: source '%s' not running (status=%s) – skipping",
                    source_name, adapter.status,
                )
                continue

            try:
                broadcast_queue = adapter.get_broadcast_queue()
            except AttributeError:
                broadcast_queue = None
            if broadcast_queue is None:
                logger.warning("initialize_archivers: source '%s' has no broadcast queue", source_name)
                continue

            try:
                cfg = AudioArchiverConfig(
                    output_dir=archive_cfg.get('output_dir', 'archives'),
                    segment_duration_seconds=int(archive_cfg.get('segment_duration_seconds', 3600)),
                    retention_days=int(archive_cfg.get('retention_days', 7)),
                    max_disk_bytes=int(archive_cfg.get('max_disk_bytes', 0)),
                    format=archive_cfg.get('format', 'wav'),
                    bitrate=int(archive_cfg.get('bitrate', 128)),
                )
                archiver = AudioArchiver(
                    source_name=source_name,
                    config=cfg,
                    broadcast_queue=broadcast_queue,
                    sample_rate=getattr(adapter.config, 'sample_rate', 44100),
                    channels=getattr(adapter.config, 'channels', 1),
                )
                if archiver.start():
                    _archivers[source_name] = archiver
                    started += 1
                    logger.info("✅ Archiver started for source '%s'", source_name)
                else:
                    logger.warning("⚠️ Archiver failed to start for source '%s'", source_name)
            except Exception as exc:
                logger.error("❌ Error starting archiver for '%s': %s", source_name, exc, exc_info=True)

        logger.info("initialize_archivers: started %d archiver(s)", started)
        return _archivers

    except Exception as exc:
        logger.error("Failed to initialize archivers: %s", exc, exc_info=True)
        return _archivers


def _redis_publisher_monitor_loop(audio_controller, stop_event) -> None:
    """Background thread: publish 16 kHz EAS audio to Redis for eas-service.

    eas-service.py subscribes to ``audio:samples:<source_name>`` Redis
    channels to receive pre-resampled 16 kHz audio.  This thread keeps
    a :class:`~app_core.audio.redis_audio_publisher.RedisAudioPublisher`
    alive for every RUNNING source, starting/stopping publishers as
    sources come and go.
    """
    global _redis_eas_publishers

    from app_core.audio.redis_audio_publisher import RedisAudioPublisher
    from app_core.audio.ingest import AudioSourceStatus

    logger.info("Redis EAS audio publisher monitor started")

    while not stop_event.is_set():
        try:
            all_sources = audio_controller.get_all_sources()

            # Start publishers for newly-running sources
            for source_name, adapter in all_sources.items():
                if (
                    adapter.status == AudioSourceStatus.RUNNING
                    and source_name not in _redis_eas_publishers
                ):
                    try:
                        eas_queue = adapter.get_eas_broadcast_queue()
                        publisher = RedisAudioPublisher(
                            broadcast_queue=eas_queue,
                            source_name=source_name,
                            sample_rate=16000,
                        )
                        if publisher.start():
                            _redis_eas_publishers[source_name] = publisher
                            logger.info(
                                "✅ Redis EAS audio publisher started for source '%s'",
                                source_name,
                            )
                    except Exception as exc:
                        logger.debug(
                            "Failed to start Redis EAS publisher for '%s': %s",
                            source_name, exc,
                        )

            # Stop publishers for sources that are no longer running
            for source_name in list(_redis_eas_publishers.keys()):
                adapter = all_sources.get(source_name)
                if not adapter or adapter.status != AudioSourceStatus.RUNNING:
                    publisher = _redis_eas_publishers.pop(source_name, None)
                    if publisher:
                        try:
                            publisher.stop()
                        except Exception:
                            pass
                        logger.info(
                            "Stopped Redis EAS audio publisher for source '%s'",
                            source_name,
                        )

        except Exception as exc:
            logger.error("Redis EAS publisher monitor error: %s", exc, exc_info=True)

        stop_event.wait(10.0)

    # Clean up all publishers on exit
    for source_name, publisher in list(_redis_eas_publishers.items()):
        try:
            publisher.stop()
        except Exception:
            pass
    _redis_eas_publishers.clear()
    logger.info("Redis EAS audio publisher monitor stopped")


def initialize_eas_monitor(app, audio_controller):
    """Initialize EAS monitoring system with unified monitor service.
    
    V3 ARCHITECTURE: Single-threaded unified monitor that replaces the previous
    multi-monitor architecture. Benefits:
    - 1 thread instead of N threads (reduced CPU/memory)
    - Auto-discovery of sources (no manual add/remove)
    - Centralized health tracking
    - No status aggregation overhead
    
    The UnifiedEASMonitorService automatically discovers and monitors all running
    audio sources in a single monitoring thread.
    """
    global _eas_monitor

    with app.app_context():
        from app_core.audio.eas_monitor_v3 import UnifiedEASMonitorService
        from app_core.audio.eas_monitor import create_fips_filtering_callback
        from app_core.audio.startup_integration import load_fips_codes_from_config

        logger.info("Initializing unified EAS monitor service (V3 architecture)...")

        # Load FIPS codes
        configured_fips = load_fips_codes_from_config()
        logger.info(f"Loaded {len(configured_fips)} FIPS codes for alert filtering")

        # Create alert callback with filtering.
        # forward_alert_handler runs inside the EAS monitor thread which has no
        # Flask application context.  Pushing an app context here (as the
        # _make_metadata_log_callback helper does) lets forward_alert_to_api
        # reach Flask-SQLAlchemy and the air-chain broadcast pipeline.
        def forward_alert_handler(alert):
            """Forward matched alerts to API and air chain broadcast."""
            from app_core.audio.alert_forwarding import forward_alert_to_api
            source_name = alert.get('source_name', 'unknown')
            event_code = alert.get('event_code', 'UNKNOWN')
            location_codes = alert.get('location_codes', [])
            logger.info(
                f"Forwarding alert from source '{source_name}': "
                f"{event_code} for {location_codes}"
            )
            return forward_alert_to_api(alert)

        # The FIPS-filtering callback calls forward_alert_handler AND then
        # _store_received_alert, both of which need Flask context.  Wrap the
        # whole callback so _store_received_alert also runs inside a context.
        _alert_callback_inner = create_fips_filtering_callback(
            configured_fips_codes=configured_fips,
            forward_callback=forward_alert_handler,
            logger_instance=logger
        )

        def alert_callback(alert):
            with app.app_context():
                return _alert_callback_inner(alert)


        # Create unified monitor service (replaces MultiMonitorManager)
        _eas_monitor = UnifiedEASMonitorService(
            audio_controller=audio_controller,
            alert_callback=alert_callback,
            configured_fips_codes=configured_fips,
            discovery_interval_seconds=5.0,  # Check for new/removed sources every 5s
            chunk_duration_ms=100  # 100ms chunks at 16kHz
        )

        # Start unified monitor (auto-discovers sources)
        if _eas_monitor.start():
            logger.info("✅ UnifiedEASMonitorService started successfully")
        else:
            logger.error("❌ UnifiedEASMonitorService failed to start")

        return _eas_monitor


def process_commands():
    """DEPRECATED: SDR commands handled by sdr-service.py.
    
    In separated architecture, all SDR hardware commands go to sdr-service.py.
    This function is kept for backward compatibility but does nothing.
    
    Commands should be sent to sdr-service via Redis, not audio-service.
    """
    # Do nothing - all SDR hardware access is in sdr-service.py
    return


def collect_metrics():
    """Collect metrics from audio controller, radio manager, and EAS monitor."""
    metrics = {
        "audio_controller": None,
        "eas_monitor": None,
        "broadcast_queue": None,
        "radio_manager": None,  # Add radio manager metrics for web application process
        "timestamp": time.time()
    }

    try:
        # Radio manager stats are now collected by sdr-service.py
        # audio-service.py does NOT access SDR hardware
        metrics["radio_manager"] = None  # Will be published by sdr-service if needed
        
        # Get audio controller stats
        if _audio_controller:
            controller_stats: Dict[str, Any] = {
                "sources": {},
                "active_source": _audio_controller._active_source,
            }

            streaming_status: Optional[Dict[str, Any]] = None
            active_streams: Dict[str, Any] = {}

            # Include Icecast streaming stats so the UI can show bitrate, mount, metadata, etc.
            if _auto_streaming_service:
                try:
                    streaming_status = _auto_streaming_service.get_status()
                    active_streams = streaming_status.get("active_streams", {}) if streaming_status else {}
                    controller_stats["streaming"] = _sanitize_value(streaming_status)
                except Exception as e:
                    logger.error(f"Error getting streaming stats: {e}")

            for name, source in _audio_controller.get_all_sources().items():
                try:
                    metrics_obj = getattr(source, "metrics", None)
                    source_stats: Dict[str, Any] = {
                        "status": source.status.value if hasattr(source.status, "value") else str(source.status),
                        "sample_rate": _sanitize_value(getattr(metrics_obj, "sample_rate", getattr(source, "sample_rate", None))),
                        "channels": _sanitize_value(getattr(metrics_obj, "channels", getattr(source, "channels", None))),
                        "frames_captured": _sanitize_value(getattr(metrics_obj, "frames_captured", None)),
                        "peak_level_db": _sanitize_value(getattr(metrics_obj, "peak_level_db", None)),
                        "rms_level_db": _sanitize_value(getattr(metrics_obj, "rms_level_db", None)),
                        "buffer_utilization": _sanitize_value(getattr(metrics_obj, "buffer_utilization", None)),
                        "silence_detected": bool(getattr(metrics_obj, "silence_detected", False)),
                        "timestamp": _sanitize_value(getattr(metrics_obj, "timestamp", None)),
                        "metadata": _sanitize_value(getattr(metrics_obj, "metadata", None)),
                        "error_message": _sanitize_value(getattr(source, "error_message", None)),
                    }

                    if hasattr(source, "config"):
                        source_stats["config"] = _sanitize_value({
                            "sample_rate": getattr(source.config, "sample_rate", None),
                            "channels": getattr(source.config, "channels", None),
                            "buffer_size": getattr(source.config, "buffer_size", None),
                        })

                    if active_streams and name in active_streams:
                        # Provide per-source streaming stats (includes bitrate, mount, metadata)
                        source_stats["streaming"] = {"icecast": _sanitize_value(active_streams[name])}

                    controller_stats["sources"][name] = source_stats
                except Exception as e:
                    logger.error(f"Error getting source stats for '{name}': {e}")

            metrics["audio_controller"] = controller_stats

            # Get broadcast queue stats from all sources
            # Note: Each source has its own broadcast queue (architecture change)
            try:
                broadcast_queues = {}
                for name, source in _audio_controller.get_all_sources().items():
                    if hasattr(source, 'get_broadcast_queue'):
                        bq = source.get_broadcast_queue()
                        if bq:
                            broadcast_queues[name] = _sanitize_value(bq.get_stats())
                
                if broadcast_queues:
                    metrics["broadcast_queue"] = broadcast_queues
            except Exception as e:
                logger.error(f"Error getting broadcast queue stats: {e}")

        # Get EAS monitor stats (supports both single and multi-monitor)
        if _eas_monitor:
            try:
                metrics["eas_monitor"] = _sanitize_value(_eas_monitor.get_status())
            except Exception as e:
                logger.error(f"Error getting EAS monitor stats: {e}")
                metrics["eas_monitor"] = {"running": False, "error": str(e)}

    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")

    return metrics


def publish_metrics_to_redis(metrics):
    """Publish metrics to Redis for web application.

    Uses HSET (merge) instead of DELETE+HSET so the key is never momentarily
    absent between the two pipeline steps.  Deep-sanitizes every value before
    JSON serialisation so that inf/nan/numpy types never cause a silent failure
    that would leave the key absent and the web-app thinking the service is
    down.
    """
    try:
        r = get_redis_client()

        # Add heartbeat timestamp and process ID (required by web application)
        metrics["_heartbeat"] = time.time()
        metrics["_master_pid"] = os.getpid()

        # Deep-sanitize the whole metrics tree so json.dumps() can never throw.
        # _sanitize_value() handles inf, nan, numpy scalars and nested dicts/lists.
        sanitized = _sanitize_value(metrics)

        # Flatten one level: nested dicts/lists → JSON strings, scalars → str.
        flat_metrics = {}
        for key, value in sanitized.items():
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                try:
                    flat_metrics[key] = json.dumps(value)
                except Exception as json_err:
                    logger.debug("Skipping metric '%s' – not JSON serialisable: %s", key, json_err)
            else:
                flat_metrics[key] = str(value)

        if not flat_metrics:
            logger.warning("publish_metrics_to_redis: nothing to publish after sanitisation")
            return

        # Use HSET merge (no DELETE) so the key is never temporarily absent.
        # Reset TTL on each write; 120 s gives headroom for transient hiccups.
        pipe = r.pipeline()
        pipe.hset("eas:metrics", mapping=flat_metrics)
        pipe.expire("eas:metrics", 120)
        pipe.execute()

        # Notify real-time subscribers
        r.publish("eas:metrics:update", "1")

    except Exception as e:
        logger.error(f"Error publishing metrics to Redis: {e}")


def main():
    """Main service loop."""
    global _running, _audio_controller

    logger.info("=" * 80)
    logger.info("EAS Station - Standalone Audio Processing Service")
    logger.info("=" * 80)

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Initialize Redis
        logger.info("Connecting to Redis...")
        r = get_redis_client()

        # Initialize database
        logger.info("Initializing database connection...")
        app = initialize_database()

        # CRITICAL: Do NOT initialize RadioManager here!
        # In separated architecture, sdr-service.py handles SDR hardware access.
        # This service (audio-service) only subscribes to Redis channels for IQ samples.
        # The sync_radio_receiver_audio_sources() function will create AudioSourceConfigDB
        # entries that trigger RedisSDRSourceAdapter creation (which subscribes to Redis).
        logger.info("Skipping RadioManager initialization - using separated architecture")
        logger.info("SDR hardware is managed by SDR hardware service process")
        logger.info("This service will subscribe to Redis channels for IQ samples")

        # Initialize audio controller
        logger.info("Initializing audio controller...")
        try:
            audio_controller = initialize_audio_controller(app)
        except Exception as ctrl_exc:
            logger.error("initialize_audio_controller raised an exception: %s", ctrl_exc, exc_info=True)
            audio_controller = None
        _audio_controller = audio_controller  # Store globally for command subscriber

        if not audio_controller:
            logger.error("Failed to initialize audio controller — cannot continue")
            return 1

        # Initialize Icecast auto-streaming
        logger.info("Initializing Icecast auto-streaming...")
        auto_streaming = initialize_auto_streaming(app, audio_controller)

        # Add all RUNNING audio sources to Icecast streaming
        if auto_streaming and audio_controller:
            from app_core.audio.ingest import AudioSourceStatus

            logger.info("Checking audio sources for Icecast streaming...")

            # Log status of all sources for diagnostics
            total_sources = len(audio_controller.get_all_sources())
            logger.info(f"Total configured sources: {total_sources}")

            for source_name, source_adapter in audio_controller.get_all_sources().items():
                status_str = source_adapter.status.name if hasattr(source_adapter.status, 'name') else str(source_adapter.status)
                logger.info(f"Source '{source_name}' status: {status_str}")

                if source_adapter.status == AudioSourceStatus.ERROR:
                    error_msg = source_adapter.error_message or "Unknown error"
                    logger.error(f"❌ Source '{source_name}' failed to start: {error_msg}")
                    continue

                # Only add sources that are actually running
                if source_adapter.status != AudioSourceStatus.RUNNING:
                    logger.warning(f"⚠️ Skipping '{source_name}' - not running (status: {status_str})")
                    continue

                try:
                    if auto_streaming.add_source(source_name, source_adapter):
                        logger.info(f"✅ Added source '{source_name}' to Icecast streaming")
                    else:
                        logger.warning(f"⚠️ Failed to add '{source_name}' to Icecast streaming")
                except Exception as e:
                    logger.error(f"❌ Error adding '{source_name}' to Icecast: {e}", exc_info=True)

        # Initialize audio archivers for sources that have archiving enabled
        logger.info("Initializing audio archivers...")
        initialize_archivers(app, audio_controller)

        # Attach metadata-logging callback to every source (current and future)
        # so now-playing changes are persisted to stream_metadata_log
        metadata_log_callback = _make_metadata_log_callback(app)
        audio_controller.set_metadata_change_callback(metadata_log_callback)
        logger.info("Stream metadata logging callbacks registered")

        # Attach audio-alert callback so stall/error/disconnect events are
        # persisted to the audio_alerts table (shown in Logs → Audio tab)
        audio_alert_callback = _make_audio_alert_log_callback(app)
        audio_controller.set_source_alert_callback(audio_alert_callback)
        logger.info("Audio alert logging callbacks registered")

        # Initialize EAS monitor
        logger.info("Initializing EAS monitor...")
        try:
            eas_monitor = initialize_eas_monitor(app, audio_controller)
        except Exception as eas_exc:
            logger.error("initialize_eas_monitor raised an exception: %s", eas_exc, exc_info=True)
            eas_monitor = None

        if not eas_monitor:
            logger.error("Failed to initialize EAS monitor")
            return 1

        # Start Redis EAS audio publisher thread so eas-service.py can
        # receive the pre-resampled 16 kHz audio it needs for decoding.
        logger.info("Starting Redis EAS audio publisher monitor...")
        _redis_pub_stop = threading.Event()
        _redis_pub_thread = threading.Thread(
            target=_redis_publisher_monitor_loop,
            args=(audio_controller, _redis_pub_stop),
            daemon=True,
            name="RedisEASPublisherMonitor",
        )
        _redis_pub_thread.start()
        logger.info("✅ Redis EAS audio publisher monitor started")

        # Initialize Redis Pub/Sub command subscriber
        logger.info("Starting Redis command subscriber...")
        command_subscriber = None
        subscriber_thread = None
        try:
            from app_core.audio.redis_commands import AudioCommandSubscriber
            import threading

            command_subscriber = AudioCommandSubscriber(
                audio_controller, auto_streaming, eas_monitor,
                archiver_registry=_archivers,
            )

            # Start subscriber in background thread
            subscriber_thread = threading.Thread(
                target=command_subscriber.start,
                daemon=True,
                name="RedisCommandSubscriber"
            )
            subscriber_thread.start()
            logger.info("✅ Redis command subscriber started")
        except Exception as e:
            logger.warning(f"Failed to start command subscriber: {e}")
            logger.warning("   Audio control commands from app will not work")
            # Continue - metrics publishing still works

        # Start HTTP streaming server for VU meter support
        logger.info("Starting HTTP streaming server...")
        streaming_server_thread = None
        try:
            from flask import Flask, Response, stream_with_context, jsonify
            import threading
            from werkzeug.serving import make_server
            
            # Create Flask app for streaming endpoints
            stream_app = Flask(__name__)
            
            @stream_app.route('/api/audio/stream/<source_name>')
            def stream_audio(source_name):
                """Stream live audio for web browser playback using uncompressed WAV.
                
                Streams uncompressed WAV at native sample rate (~705 kbps for 44.1kHz mono).
                WAV format is used for maximum compatibility and reliability.
                
                Args:
                    source_name: Name of the audio source to stream
                
                Returns:
                    Response: Streaming WAV audio
                """
                import struct
                import io
                import numpy as np
                import queue as queue_module
                from app_core.audio.ingest import AudioSourceStatus
                
                def generate_wav_stream(adapter, source_name):
                    """Generator that yields WAV chunks at native sample rate.

                    Uses BroadcastQueue subscription to avoid competing with other audio consumers
                    (Icecast, EAS monitor, etc). Each subscriber gets independent copy of all audio chunks.
                    
                    No resampling is performed - audio is passed through at native rate to ensure
                    accurate pitch and playback speed.
                    """
                    # For StreamSourceAdapter with preserve_native_rate=True, FFmpeg runs
                    # without -ar and outputs at the stream's actual sample rate.  The
                    # actual rate is detected from FFmpeg's stderr output in a background
                    # thread (_stderr_pump) which then updates config.sample_rate and
                    # metrics.sample_rate.  That detection happens *before* the first
                    # audio packet reaches _read_audio_chunk, so waiting until
                    # _last_connection_time is set (i.e. the first audio packet has
                    # arrived) guarantees the rate is already correct.
                    #
                    # Without this wait, a freshly-started source (e.g. configured as
                    # 44100 Hz but actually streaming at 48000 Hz) would cause the WAV
                    # header to be written with the wrong rate.  The browser would then
                    # play 48000 Hz audio as if it were 44100 Hz — about 91.9% speed —
                    # making 10 minutes of audio take ~11 minutes.
                    if hasattr(adapter, '_last_connection_time'):  # StreamSourceAdapter
                        deadline = time.time() + 5.0
                        while time.time() < deadline and adapter._last_connection_time is None:
                            time.sleep(0.05)

                    # Source configuration — prefer metrics.sample_rate which is
                    # updated asynchronously when the stream's native rate is
                    # detected by FFmpeg.  config.sample_rate is also updated but
                    # checking both provides a safety net.
                    source_sample_rate = adapter.config.sample_rate
                    if hasattr(adapter, 'metrics') and getattr(adapter.metrics, 'sample_rate', 0) > 0:
                        source_sample_rate = adapter.metrics.sample_rate
                    stream_sample_rate = source_sample_rate  # Use native source rate
                    stream_channels = 1  # Mono saves 50% bandwidth
                    bits_per_sample = 16

                    # Validate source sample rate
                    if source_sample_rate <= 0:
                        logger.error(f"Invalid source sample rate: {source_sample_rate} Hz. Using 44100 Hz as fallback.")
                        source_sample_rate = 44100
                        stream_sample_rate = 44100
                    
                    logger.debug(
                        f"Web stream for {source_name}: {stream_sample_rate}Hz (native rate, no resampling)"
                    )

                    # Subscribe to BroadcastQueue for non-competitive audio access
                    subscriber_id = f"web-stream-{source_name}-{threading.current_thread().ident}"
                    if not (hasattr(adapter, 'get_broadcast_queue') and callable(getattr(adapter, 'get_broadcast_queue', None))):
                        logger.error(f"Audio source '{source_name}' does not support broadcast queue")
                        raise RuntimeError(f'Audio source "{source_name}" does not support streaming')
                    
                    broadcast_queue = adapter.get_broadcast_queue()
                    subscription_queue = broadcast_queue.subscribe(subscriber_id)

                    try:
                        # Send WAV header
                        wav_header = io.BytesIO()
                        wav_header.write(b'RIFF')
                        wav_header.write(struct.pack('<I', 0xFFFFFFFF))
                        wav_header.write(b'WAVE')
                        wav_header.write(b'fmt ')
                        wav_header.write(struct.pack('<I', 16))
                        wav_header.write(struct.pack('<H', 1))  # PCM
                        wav_header.write(struct.pack('<H', stream_channels))
                        wav_header.write(struct.pack('<I', stream_sample_rate))
                        wav_header.write(struct.pack('<I', stream_sample_rate * stream_channels * bits_per_sample // 8))
                        wav_header.write(struct.pack('<H', stream_channels * bits_per_sample // 8))
                        wav_header.write(struct.pack('<H', bits_per_sample))
                        wav_header.write(b'data')
                        wav_header.write(struct.pack('<I', 0xFFFFFFFF))
                        yield wav_header.getvalue()

                        # Stream audio chunks
                        silence_duration = 0.05
                        silence_samples = int(stream_sample_rate * stream_channels * silence_duration)

                        logger.debug(f"Web stream '{subscriber_id}' started, subscribed to broadcast queue")

                        while _running:
                            try:
                                # Read from subscription queue (non-competitive)
                                audio_chunk = subscription_queue.get(timeout=0.2)
                                if audio_chunk is None:
                                    # Yield silence to keep stream alive
                                    silence_chunk = np.zeros(silence_samples, dtype=np.int16)
                                    yield silence_chunk.tobytes()
                                    time.sleep(silence_duration)  # Sleep for the silence duration (~50ms)
                                    continue

                                if not isinstance(audio_chunk, np.ndarray):
                                    audio_chunk = np.array(audio_chunk, dtype=np.float32)

                                # Detect actual audio format (mono 1D array vs stereo 2D array)
                                if audio_chunk.ndim == 2 and stream_channels == 1:
                                    # True stereo (Nx2 array) - mix to mono
                                    audio_chunk = np.mean(audio_chunk, axis=1)
                                elif audio_chunk.ndim == 1:
                                    # Already mono - no conversion needed
                                    pass
                                else:
                                    # Unexpected format - flatten to mono
                                    audio_chunk = audio_chunk.flatten()

                                # Convert to int16 PCM (no resampling - use native sample rate)
                                pcm_data = (np.clip(audio_chunk, -1.0, 1.0) * 32767).astype(np.int16)
                                yield pcm_data.tobytes()

                            except queue_module.Empty:
                                # No audio available — the queue.get timeout (200ms) already
                                # throttled this path, just yield silence and continue.
                                silence_chunk = np.zeros(silence_samples, dtype=np.int16)
                                yield silence_chunk.tobytes()
                            except Exception as e:
                                logger.debug(f"Error in stream generator: {e}")
                                silence_chunk = np.zeros(silence_samples, dtype=np.int16)
                                yield silence_chunk.tobytes()
                                time.sleep(0.05)
                    finally:
                        # Unsubscribe when client disconnects
                        broadcast_queue.unsubscribe(subscriber_id)
                        logger.debug(f"Web stream '{subscriber_id}' ended, unsubscribed from broadcast queue")
                
                try:
                    if not _audio_controller:
                        return jsonify({'error': 'Audio controller not initialized'}), 503
                    
                    adapter = _audio_controller.get_source(source_name)
                    if not adapter:
                        return jsonify({'error': f'Audio source "{source_name}" not found'}), 404
                    
                    if adapter.status != AudioSourceStatus.RUNNING:
                        return jsonify({
                            'error': f'Audio source "{source_name}" is not running',
                            'status': adapter.status.value
                        }), 503
                    
                    return Response(
                        stream_with_context(generate_wav_stream(adapter, source_name)),
                        mimetype='audio/wav',
                        headers={
                            'Content-Disposition': f'inline; filename="{source_name}.wav"',
                            'Cache-Control': 'no-cache, no-store, must-revalidate',
                            'Pragma': 'no-cache',
                            'Expires': '0',
                            'X-Content-Type-Options': 'nosniff',
                            'Access-Control-Allow-Origin': '*',
                            'Accept-Ranges': 'none',
                            'Connection': 'keep-alive',
                        }
                    )
                except Exception as exc:
                    logger.error(f'Error setting up audio stream for {source_name}: {exc}')
                    return jsonify({'error': str(exc)}), 500
            
            @stream_app.route('/api/eas/decoder-stream')
            def stream_eas_decoder():
                """Stream the actual 16kHz audio being fed to the EAS decoder.

                This endpoint allows users to listen to exactly what the EAS decoder processes,
                which is critical for debugging detection issues. The audio is resampled to 16kHz
                for decoder CPU efficiency.

                Returns:
                    Response: Streaming MP3 audio at 16kHz (what the decoder actually sees)
                """
                import queue as queue_module
                import io
                import struct
                import numpy as np

                if not _audio_controller:
                    logger.error("Audio controller not initialized")
                    return jsonify({'error': 'Audio controller not initialized'}), 503

                # Resolve which source to stream from.
                # Primary path: use the source that the EAS monitor is actively watching.
                # Fallback path: find any RUNNING source directly from the audio controller.
                # The fallback handles two common scenarios:
                #   1. EAS monitor started but hasn't run its first discovery cycle yet
                #      (discovery runs every 5 seconds; sources may already be running).
                #   2. EAS monitor is initializing while sources stream live audio.
                source_name = None
                if _eas_monitor:
                    status = _eas_monitor.get_status()
                    if status and status.get('monitors'):
                        monitor_info = next(iter(status['monitors'].values()), None)
                        if monitor_info and 'source_name' in monitor_info:
                            source_name = monitor_info['source_name']

                if not source_name:
                    from app_core.audio.ingest import AudioSourceStatus
                    for _name, _adapter in _audio_controller.get_all_sources().items():
                        if (
                            _adapter.status == AudioSourceStatus.RUNNING
                            and hasattr(_adapter, 'get_eas_broadcast_queue')
                        ):
                            source_name = _name
                            logger.info(
                                f"EAS decoder stream: EAS monitor has no active watchers yet; "
                                f"falling back to first running source '{source_name}'"
                            )
                            break

                if not source_name:
                    logger.error("No running audio sources available for EAS decoder stream")
                    return jsonify({
                        'error': (
                            'No running audio sources available. '
                            'Start an audio source to enable the EAS decoder stream.'
                        )
                    }), 503

                adapter = _audio_controller.get_source(source_name)
                if not adapter:
                    logger.error(f"Audio source '{source_name}' not found")
                    return jsonify({'error': f"Audio source '{source_name}' not found"}), 503

                # Use the 16kHz EAS broadcast queue - this is the actual audio the decoder processes
                if not (hasattr(adapter, 'get_eas_broadcast_queue') and callable(getattr(adapter, 'get_eas_broadcast_queue', None))):
                    logger.error(f"Audio source '{source_name}' does not support EAS broadcast queue")
                    return jsonify({'error': f"Audio source '{source_name}' does not support EAS broadcast queue"}), 503

                broadcast_queue = adapter.get_eas_broadcast_queue()

                def generate_eas_decoder_wav():
                    """Stream the EAS decoder's 16kHz mono audio as a WAV.

                    Mirrors the working WAV stream generator used for regular audio
                    sources.  The WAV header is yielded immediately so the browser
                    recognises the format before any PCM data arrives, eliminating
                    the startup latency that caused the previous MP3/FFmpeg
                    implementation to fail.  No external process is required.
                    """
                    stream_sample_rate = 16000  # EAS decoder always uses 16kHz
                    stream_channels = 1
                    bits_per_sample = 16

                    subscriber_id = f"eas-decoder-stream-{threading.current_thread().ident}"

                    try:
                        subscription_queue = broadcast_queue.subscribe(subscriber_id)
                        logger.info(
                            f"EAS decoder stream started (16kHz WAV from {source_name})"
                        )

                        # Yield WAV header immediately — browser needs this to
                        # recognise audio/wav before any PCM samples arrive.
                        wav_header = io.BytesIO()
                        wav_header.write(b'RIFF')
                        wav_header.write(struct.pack('<I', 0xFFFFFFFF))  # streaming: unknown size
                        wav_header.write(b'WAVE')
                        wav_header.write(b'fmt ')
                        wav_header.write(struct.pack('<I', 16))
                        wav_header.write(struct.pack('<H', 1))  # PCM
                        wav_header.write(struct.pack('<H', stream_channels))
                        wav_header.write(struct.pack('<I', stream_sample_rate))
                        wav_header.write(
                            struct.pack('<I', stream_sample_rate * stream_channels * bits_per_sample // 8)
                        )
                        wav_header.write(struct.pack('<H', stream_channels * bits_per_sample // 8))
                        wav_header.write(struct.pack('<H', bits_per_sample))
                        wav_header.write(b'data')
                        wav_header.write(struct.pack('<I', 0xFFFFFFFF))  # streaming: unknown size
                        yield wav_header.getvalue()

                        silence_duration = 0.05
                        silence_samples = int(
                            stream_sample_rate * stream_channels * silence_duration
                        )

                        while _running:
                            try:
                                audio_chunk = subscription_queue.get(timeout=0.2)

                                if audio_chunk is None:
                                    # Sentinel from source — yield silence to keep stream alive
                                    yield np.zeros(silence_samples, dtype=np.int16).tobytes()
                                    time.sleep(silence_duration)
                                    continue

                                if not isinstance(audio_chunk, np.ndarray):
                                    audio_chunk = np.array(audio_chunk, dtype=np.float32)

                                if audio_chunk.ndim == 2 and stream_channels == 1:
                                    audio_chunk = np.mean(audio_chunk, axis=1)
                                elif audio_chunk.ndim == 1:
                                    pass
                                else:
                                    audio_chunk = audio_chunk.flatten()

                                yield (
                                    np.clip(audio_chunk, -1.0, 1.0) * 32767
                                ).astype(np.int16).tobytes()

                            except queue_module.Empty:
                                # No audio yet — yield silence so the browser
                                # keeps the connection open.
                                yield np.zeros(silence_samples, dtype=np.int16).tobytes()
                            except Exception as e:
                                logger.error(f"Error in EAS decoder stream: {e}")
                                yield np.zeros(silence_samples, dtype=np.int16).tobytes()
                                time.sleep(0.05)
                    finally:
                        broadcast_queue.unsubscribe(subscriber_id)
                        logger.info("EAS decoder stream ended")

                return Response(
                    stream_with_context(generate_eas_decoder_wav()),
                    mimetype='audio/wav',
                    headers={
                        'Content-Disposition': 'inline; filename="eas-decoder-16khz.wav"',
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0',
                        'X-Content-Type-Options': 'nosniff',
                        'Access-Control-Allow-Origin': '*',
                        'Accept-Ranges': 'none',
                        'Connection': 'keep-alive',
                    }
                )
            
            # Start Flask server in background thread
            # Use AUDIO_STREAMING_PORT env var (default 5002)
            streaming_port = int(os.environ.get('AUDIO_STREAMING_PORT', '5002'))
            server = make_server('0.0.0.0', streaming_port, stream_app, threaded=True)
            streaming_server_thread = threading.Thread(
                target=server.serve_forever,
                daemon=True,
                name="StreamingHTTPServer"
            )
            streaming_server_thread.start()
            logger.info(f"✅ HTTP streaming server started on port {streaming_port}")
        except Exception as e:
            logger.warning(f"Failed to start HTTP streaming server: {e}")
            logger.warning("   VU meter real-time streaming will not be available")

        logger.info("=" * 80)
        logger.info("✅ Audio service started successfully")
        logger.info("   - Audio ingestion: ACTIVE")
        logger.info(f"   - Icecast streaming: {'ACTIVE' if auto_streaming else 'DISABLED'}")
        
        # Show EAS monitoring status
        if eas_monitor:
            try:
                status = eas_monitor.get_status()
                monitor_count = status.get('monitor_count', 1)
                if monitor_count > 1 and 'monitors' in status:
                    monitor_names = ', '.join(status['monitors'].keys())
                    logger.info(f"   - EAS monitoring: ACTIVE ({monitor_count} sources: {monitor_names})")
                else:
                    logger.info("   - EAS monitoring: ACTIVE (single source)")
            except Exception:
                logger.info("   - EAS monitoring: ACTIVE")
        else:
            logger.info("   - EAS monitoring: FAILED")
        
        logger.info("   - Metrics publishing: ACTIVE")
        logger.info(f"   - Command subscriber: {'ACTIVE' if command_subscriber else 'DISABLED'}")
        streaming_port = int(os.environ.get('AUDIO_STREAMING_PORT', '5002'))
        logger.info(f"   - HTTP streaming: {'ACTIVE' if streaming_server_thread else 'DISABLED'} (port {streaming_port})")
        logger.info("=" * 80)

        # Main loop: publish metrics every 1 second so VU meters stay live
        last_metrics_time = 0
        last_source_watchdog_time = 0
        metrics_interval = 1.0
        source_watchdog_interval = 30.0  # Check source health every 30 seconds

        while _running:
            try:
                current_time = time.time()

                # Process pending commands from webapp (non-blocking)
                process_commands()

                # Source watchdog: restart ERROR sources and auto-start STOPPED sources.
                # Network streams drop after consecutive errors; SDR sources lose lock.
                # This watchdog ensures everything that *should* be running stays running
                # without any operator intervention.
                if current_time - last_source_watchdog_time >= source_watchdog_interval:
                    if audio_controller:
                        from app_core.audio.ingest import AudioSourceStatus
                        from app_core.models import AudioSourceConfigDB
                        try:
                            auto_start_names = {
                                cfg.name
                                for cfg in AudioSourceConfigDB.query.all()
                                if cfg.enabled and cfg.auto_start
                            }
                        except Exception:
                            auto_start_names = set()

                        for source_name, source_adapter in audio_controller.get_all_sources().items():
                            if source_adapter.status == AudioSourceStatus.ERROR:
                                logger.warning(
                                    f"Source watchdog: '{source_name}' is in ERROR state – "
                                    f"attempting automatic restart"
                                )
                                try:
                                    source_adapter.stop()
                                    time.sleep(0.5)
                                    result = audio_controller.start_source(source_name)
                                    if result:
                                        logger.info(
                                            f"Source watchdog: ✅ restarted '{source_name}' successfully"
                                        )
                                    else:
                                        logger.warning(
                                            f"Source watchdog: ⚠️ restart of '{source_name}' returned False"
                                        )
                                except Exception as exc:
                                    logger.error(
                                        f"Source watchdog: ❌ exception restarting '{source_name}': {exc}",
                                        exc_info=True,
                                    )
                            elif (
                                source_adapter.status == AudioSourceStatus.STOPPED
                                and source_name in auto_start_names
                            ):
                                logger.warning(
                                    f"Source watchdog: '{source_name}' is STOPPED but has "
                                    f"auto_start=True – restarting"
                                )
                                try:
                                    result = audio_controller.start_source(source_name)
                                    if result:
                                        logger.info(
                                            f"Source watchdog: ✅ auto-restarted '{source_name}'"
                                        )
                                    else:
                                        logger.warning(
                                            f"Source watchdog: ⚠️ auto-restart of '{source_name}' returned False"
                                        )
                                except Exception as exc:
                                    logger.error(
                                        f"Source watchdog: ❌ exception auto-restarting '{source_name}': {exc}",
                                        exc_info=True,
                                    )
                    last_source_watchdog_time = current_time

                # Publish metrics periodically
                if current_time - last_metrics_time >= metrics_interval:
                    metrics = collect_metrics()
                    publish_metrics_to_redis(metrics)
                    last_metrics_time = current_time

                    # Log health status
                    if metrics.get("eas_monitor"):
                        eas_metrics = metrics["eas_monitor"]
                        if "monitors" in eas_metrics:
                            # Multi-monitor mode
                            monitor_count = eas_metrics.get("monitor_count", 0)
                            total_samples = eas_metrics.get("samples_processed", 0)
                            logger.debug(
                                f"EAS Monitors: {monitor_count} active, "
                                f"total samples processed={total_samples}"
                            )
                        else:
                            # Legacy single monitor
                            samples = eas_metrics.get("samples_processed", 0)
                            running = eas_metrics.get("running", False)
                            logger.debug(f"EAS Monitor: running={running}, samples={samples}")

                # Sleep briefly (check for commands every 500ms)
                time.sleep(0.5)

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(5)

        logger.info("Shutting down audio service...")

        # Stop command subscriber
        if command_subscriber:
            logger.info("Stopping command subscriber...")
            try:
                command_subscriber.stop()
            except Exception as e:
                logger.warning(f"Error stopping command subscriber: {e}")

        # Stop EAS monitor(s) - works for both single and multi-monitor
        if _eas_monitor:
            logger.info("Stopping EAS monitor(s)...")
            _eas_monitor.stop()

        # Stop audio controller
        if _audio_controller:
            logger.info("Stopping audio controller...")
            # Audio controller doesn't have explicit stop, sources will be cleaned up

        # Close Redis connection
        if _redis_client:
            logger.info("Closing Redis connection...")
            _redis_client.close()

        logger.info("✅ Audio service shut down gracefully")
        return 0

    except Exception as e:
        logger.error(f"Fatal error in audio service: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
