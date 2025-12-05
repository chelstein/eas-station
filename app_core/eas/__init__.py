"""
EAS (Emergency Alert System) module for EAS Station.

This module provides EAS-specific functionality including:
- EAS file operations (loading, caching, deletion)
- Audio data management
- Summary payload handling

Extracted from app.py as part of the refactoring effort to improve maintainability.
"""

from .file_operations import (
    get_eas_output_root,
    get_eas_static_prefix,
    resolve_eas_disk_path,
    load_or_cache_audio_data,
    load_or_cache_summary_payload,
    remove_eas_files,
)

__all__ = [
    'get_eas_output_root',
    'get_eas_static_prefix',
    'resolve_eas_disk_path',
    'load_or_cache_audio_data',
    'load_or_cache_summary_payload',
    'remove_eas_files',
]
