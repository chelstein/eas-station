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

"""Helper functions for Certbot settings management."""

from typing import Dict, Any
from flask import current_app

from .extensions import db
from .models import CertbotSettings


def get_certbot_settings() -> CertbotSettings:
    """Get Certbot settings from database.

    Returns the single CertbotSettings row (id=1), creating it with defaults if needed.
    """
    settings = CertbotSettings.query.get(1)
    if settings is None:
        settings = CertbotSettings(id=1)
        db.session.add(settings)
        db.session.commit()
    return settings


def update_certbot_settings(data: Dict[str, Any]) -> CertbotSettings:
    """Update Certbot settings in database.

    Args:
        data: Dictionary of settings to update

    Returns:
        Updated CertbotSettings object
    """
    settings = get_certbot_settings()

    # Update fields if provided
    if 'enabled' in data:
        settings.enabled = bool(data['enabled'])
    if 'domain_name' in data:
        settings.domain_name = str(data['domain_name']).strip()
    if 'email' in data:
        settings.email = str(data['email']).strip()
    if 'staging' in data:
        settings.staging = bool(data['staging'])
    if 'auto_renew_enabled' in data:
        settings.auto_renew_enabled = bool(data['auto_renew_enabled'])
    if 'renew_days_before_expiry' in data:
        settings.renew_days_before_expiry = int(data['renew_days_before_expiry'])

    db.session.commit()
    return settings


def get_certbot_config_dict() -> Dict[str, Any]:
    """Get Certbot settings as a dictionary.

    Returns:
        Dictionary of Certbot settings
    """
    settings = get_certbot_settings()
    return settings.to_dict()


__all__ = [
    'get_certbot_settings',
    'update_certbot_settings',
    'get_certbot_config_dict',
]
