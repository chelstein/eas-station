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
Centralized service configuration for EAS Station.

All service names and URLs are defined here to avoid hardcoding throughout the codebase.
These can be overridden via environment variables for custom deployments.
"""

import os
from typing import List

# Service name prefix (can be overridden for custom installations)
SERVICE_PREFIX = os.environ.get('EAS_SERVICE_PREFIX', 'eas-station')

# Core EAS Station services
EAS_SERVICES = [
    f'{SERVICE_PREFIX}-web.service',
    f'{SERVICE_PREFIX}-sdr.service',
    f'{SERVICE_PREFIX}-audio.service',
    f'{SERVICE_PREFIX}-eas.service',
    f'{SERVICE_PREFIX}-hardware.service',
]

# Poller services (NOAA and IPAWS)
POLLER_SERVICES = [
    f'{SERVICE_PREFIX}-noaa-poller.service',
    f'{SERVICE_PREFIX}-ipaws-poller.service',
]

# Infrastructure services (not prefixed)
INFRASTRUCTURE_SERVICES = [
    'nginx.service',
    'postgresql.service',
    'redis-server.service',
    'certbot.service',
    'certbot.timer',
]

# All services for log viewing
def get_all_log_services() -> List[str]:
    """Get all services that can be viewed in the logs interface."""
    return EAS_SERVICES + POLLER_SERVICES + INFRASTRUCTURE_SERVICES


def get_eas_services() -> List[str]:
    """Get core EAS services (without infrastructure)."""
    return EAS_SERVICES + POLLER_SERVICES


def get_web_service() -> str:
    """Get the web service name."""
    return f'{SERVICE_PREFIX}-web.service'


def get_sdr_service() -> str:
    """Get the SDR service name."""
    return f'{SERVICE_PREFIX}-sdr.service'


def get_audio_service() -> str:
    """Get the audio service name."""
    return f'{SERVICE_PREFIX}-audio.service'


def get_hardware_service() -> str:
    """Get the hardware service name."""
    return f'{SERVICE_PREFIX}-hardware.service'


# Service URLs (all with environment variable overrides)
HARDWARE_SERVICE_URL = os.environ.get('HARDWARE_SERVICE_URL', 'http://127.0.0.1:5001')
AUDIO_SERVICE_URL = os.environ.get('AUDIO_SERVICE_URL', 'http://127.0.0.1:5002')
SDR_SERVICE_URL = os.environ.get('SDR_SERVICE_URL', 'http://127.0.0.1:5003')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
