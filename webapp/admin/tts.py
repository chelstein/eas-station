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

from __future__ import annotations

"""Text-to-Speech settings management routes."""

import logging
from typing import Any, Dict

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.exceptions import BadRequest

from app_core.auth.roles import require_permission
from app_core.extensions import db
from app_core.tts_settings import (
    get_tts_settings,
    update_tts_settings,
)

logger = logging.getLogger(__name__)

# Create Blueprint for TTS routes
tts_bp = Blueprint('tts', __name__)


# Routes are relative to blueprint's url_prefix='/admin'
# e.g., route '/tts' becomes '/admin/tts'
@tts_bp.route('/tts')
@require_permission('system.configure')
def tts_settings_page():
    """Display TTS configuration page."""
    try:
        settings = get_tts_settings()

        return render_template(
            'admin/tts.html',
            settings=settings,
        )
    except Exception as exc:
        logger.error(f"Failed to load TTS settings: {exc}")
        flash(f"Error loading TTS settings: {exc}", "error")
        return redirect(url_for('admin.index'))


@tts_bp.route('/api/tts/settings', methods=['GET'])
@require_permission('system.configure')
def get_settings():
    """Get current TTS settings."""
    try:
        settings = get_tts_settings()
        return jsonify({
            "success": True,
            "settings": settings.to_dict(),
        })
    except Exception as exc:
        logger.error(f"Failed to get TTS settings: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@tts_bp.route('/api/tts/settings', methods=['PUT'])
@require_permission('system.configure')
def update_settings():
    """Update TTS settings."""
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()

        # Convert boolean fields
        bool_fields = ['enabled']
        for field in bool_fields:
            if field in data:
                if isinstance(data[field], str):
                    data[field] = data[field].lower() in ('true', '1', 'yes', 'on')
                else:
                    data[field] = bool(data[field])

        # Convert float fields
        if 'azure_openai_speed' in data and data['azure_openai_speed'] is not None:
            if data['azure_openai_speed'] == '' or data['azure_openai_speed'] == 'None':
                data['azure_openai_speed'] = 1.0
            else:
                try:
                    speed = float(data['azure_openai_speed'])
                    if speed < 0.25 or speed > 4.0:
                        raise BadRequest("Speed must be between 0.25 and 4.0")
                    data['azure_openai_speed'] = speed
                except (TypeError, ValueError):
                    raise BadRequest("Invalid value for speed: must be a number")

        # Validate provider
        if 'provider' in data:
            valid_providers = ['', 'azure_openai', 'azure', 'pyttsx3']
            if data['provider'] not in valid_providers:
                raise BadRequest(f"Invalid provider. Must be one of: {', '.join(valid_providers)}")

        # Update settings
        settings = update_tts_settings(data)

        logger.info(f"TTS settings updated successfully")

        return jsonify({
            "success": True,
            "message": "TTS settings updated successfully. Changes take effect immediately.",
            "settings": settings.to_dict(),
        })

    except BadRequest as exc:
        logger.warning(f"Bad request updating TTS settings: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 400

    except Exception as exc:
        logger.error(f"Failed to update TTS settings: {exc}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 500


def register_tts_routes(app, logger):
    """Register TTS admin routes with the Flask app.
    
    Routes are registered with url_prefix='/admin', so Flask combines them:
    - Blueprint route '/tts' becomes '/admin/tts'
    - Blueprint route '/api/tts/settings' becomes '/admin/api/tts/settings'
    
    IMPORTANT: Do NOT add '/admin' prefix to route decorators above, as Flask
    will combine url_prefix with the route path, resulting in doubled paths
    like '/admin/admin/tts' which will cause 404 errors.
    """
    app.register_blueprint(tts_bp, url_prefix='/admin')
    logger.info("TTS admin routes registered")


__all__ = ['tts_bp', 'register_tts_routes']
