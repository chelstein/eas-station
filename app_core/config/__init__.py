"""
Configuration module for EAS Station.

This module provides configuration management including:
- Environment variable parsing
- Database connection URL construction
- Security configuration (SECRET_KEY, CSRF)

Extracted from app.py as part of the refactoring effort to improve maintainability.
"""

from .environment import parse_env_list, parse_int_env
from .database import build_database_url
from .services import (
    SERVICE_PREFIX,
    EAS_SERVICES,
    POLLER_SERVICES,
    INFRASTRUCTURE_SERVICES,
    get_all_log_services,
    get_eas_services,
    get_web_service,
    get_sdr_service,
    get_audio_service,
    get_hardware_service,
    HARDWARE_SERVICE_URL,
    AUDIO_SERVICE_URL,
    SDR_SERVICE_URL,
    REDIS_URL,
)

__all__ = [
    'parse_env_list',
    'parse_int_env',
    'build_database_url',
    'SERVICE_PREFIX',
    'EAS_SERVICES',
    'POLLER_SERVICES',
    'INFRASTRUCTURE_SERVICES',
    'get_all_log_services',
    'get_eas_services',
    'get_web_service',
    'get_sdr_service',
    'get_audio_service',
    'get_hardware_service',
    'HARDWARE_SERVICE_URL',
    'AUDIO_SERVICE_URL',
    'SDR_SERVICE_URL',
    'REDIS_URL',
]
