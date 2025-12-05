"""
EAS file operations utilities.

This module provides functions for managing EAS (Emergency Alert System) files,
including loading, caching, and deletion operations.

Functions:
    get_eas_output_root: Get the EAS output directory path
    get_eas_static_prefix: Get the web subdirectory for EAS files
    resolve_eas_disk_path: Safely resolve EAS file path
    load_or_cache_audio_data: Load audio data with caching
    load_or_cache_summary_payload: Load summary payload with caching
    remove_eas_files: Delete EAS files from disk
"""

import os
import logging
from typing import Optional, Dict, Any
from json import loads as json_loads
from json import JSONDecodeError

logger = logging.getLogger(__name__)


def get_eas_output_root(app) -> Optional[str]:
    """
    Get the EAS output directory path from application config.
    
    Args:
        app: Flask application instance
        
    Returns:
        EAS output directory path, or None if not configured
    """
    output_root = str(app.config.get('EAS_OUTPUT_DIR') or '').strip()
    return output_root or None


def get_eas_static_prefix(app) -> str:
    """
    Get the web subdirectory for EAS files from application config.
    
    Args:
        app: Flask application instance
        
    Returns:
        Web subdirectory path (default: 'eas_messages')
    """
    return app.config.get('EAS_OUTPUT_WEB_SUBDIR', 'eas_messages').strip('/')


def resolve_eas_disk_path(app, filename: Optional[str]) -> Optional[str]:
    """
    Safely resolve an EAS filename to an absolute disk path.
    
    Validates that the resolved path is within the EAS output directory
    to prevent directory traversal attacks.
    
    Args:
        app: Flask application instance
        filename: Filename to resolve
        
    Returns:
        Absolute path if valid and exists, None otherwise
        
    Example:
        >>> resolve_eas_disk_path(app, "message.wav")
        '/path/to/eas_output/message.wav'
        >>> resolve_eas_disk_path(app, "../../../etc/passwd")
        None
    """
    output_root = get_eas_output_root(app)
    if not output_root or not filename:
        return None

    safe_fragment = str(filename).strip().lstrip('/\\')
    if not safe_fragment:
        return None

    candidate = os.path.abspath(os.path.join(output_root, safe_fragment))
    root = os.path.abspath(output_root)

    try:
        common = os.path.commonpath([candidate, root])
    except ValueError:
        return None

    if common != root:
        return None

    if os.path.exists(candidate):
        return candidate

    return None


def load_or_cache_audio_data(app, db, message, *, variant: str = 'primary') -> Optional[bytes]:
    """
    Load audio data from database or disk, caching in database.
    
    Attempts to load audio data from the message's cached field first.
    If not found, loads from disk and caches in the database.
    
    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
        message: EASMessage model instance
        variant: Audio variant ('primary' or 'eom')
        
    Returns:
        Audio data as bytes, or None if not found
    """
    if variant == 'eom':
        data = message.eom_audio_data
        filename = (message.metadata_payload or {}).get('eom_filename') if message.metadata_payload else None
    else:
        data = message.audio_data
        filename = message.audio_filename

    if data:
        return data

    disk_path = resolve_eas_disk_path(app, filename)
    if not disk_path:
        return None

    try:
        with open(disk_path, 'rb') as handle:
            data = handle.read()
    except OSError:
        return None

    if not data:
        return None

    if variant == 'eom':
        message.eom_audio_data = data
    else:
        message.audio_data = data

    try:
        db.session.add(message)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to cache audio data for message {message.id}: {e}", exc_info=True)

    return data


def load_or_cache_summary_payload(app, db, message) -> Optional[Dict[str, Any]]:
    """
    Load summary payload from database or disk, caching in database.
    
    Attempts to load the summary payload from the message's cached field first.
    If not found, loads from disk JSON file and caches in the database.
    
    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
        message: EASMessage model instance
        
    Returns:
        Summary payload as dictionary, or None if not found
    """
    if message.text_payload:
        return dict(message.text_payload)

    disk_path = resolve_eas_disk_path(app, message.text_filename)
    if not disk_path:
        return None

    try:
        with open(disk_path, 'r', encoding='utf-8') as handle:
            payload = json_loads(handle.read())
    except (OSError, JSONDecodeError) as exc:
        logger.debug('Unable to load summary payload from %s: %s', disk_path, exc)
        return None

    message.text_payload = payload
    try:
        db.session.add(message)
        db.session.commit()
    except Exception:
        db.session.rollback()

    return dict(payload)


def remove_eas_files(app, message) -> None:
    """
    Remove EAS files from disk for a given message.
    
    Attempts to delete the audio, text, and EOM audio files associated
    with the message. Silently ignores missing files.
    
    Args:
        app: Flask application instance
        message: EASMessage model instance
    """
    filenames = {
        message.audio_filename,
        message.text_filename,
    }
    metadata = message.metadata_payload or {}
    eom_filename = metadata.get('eom_filename') if isinstance(metadata, dict) else None
    filenames.add(eom_filename)

    for filename in filenames:
        disk_path = resolve_eas_disk_path(app, filename)
        if not disk_path:
            continue
        try:
            os.remove(disk_path)
        except OSError:
            continue


__all__ = [
    'get_eas_output_root',
    'get_eas_static_prefix',
    'resolve_eas_disk_path',
    'load_or_cache_audio_data',
    'load_or_cache_summary_payload',
    'remove_eas_files',
]
