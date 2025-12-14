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

"""Hardware settings management routes."""

import logging
from typing import Any, Dict

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.exceptions import BadRequest

from app_core.auth.roles import require_permission
from app_core.extensions import db
from app_core.hardware_settings import (
    get_hardware_settings,
    update_hardware_settings,
    invalidate_hardware_settings_cache,
)
from app_utils.pi_pinout import ARGON_OLED_RESERVED_BCM

logger = logging.getLogger(__name__)

# Create Blueprint for hardware routes
hardware_bp = Blueprint('hardware', __name__)


@hardware_bp.route('/admin/hardware')
@require_permission('admin')
def hardware_settings_page():
    """Display hardware settings configuration page."""
    try:
        settings = get_hardware_settings()

        return render_template(
            'admin/hardware_settings.html',
            settings=settings,
            reserved_gpio_pins=sorted(ARGON_OLED_RESERVED_BCM),
        )
    except Exception as exc:
        logger.error(f"Failed to load hardware settings: {exc}")
        flash(f"Error loading hardware settings: {exc}", "error")
        return redirect(url_for('admin.index'))


@hardware_bp.route('/admin/hardware/update', methods=['POST'])
@require_permission('admin')
def update_hardware():
    """Update hardware settings from form submission."""
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()

        # Parse JSON fields
        if 'gpio_pin_map' in data and isinstance(data['gpio_pin_map'], str):
            import json
            try:
                data['gpio_pin_map'] = json.loads(data['gpio_pin_map']) if data['gpio_pin_map'].strip() else {}
            except json.JSONDecodeError as exc:
                raise BadRequest(f"Invalid GPIO pin map JSON: {exc}")

        if 'gpio_behavior_matrix' in data and isinstance(data['gpio_behavior_matrix'], str):
            import json
            try:
                data['gpio_behavior_matrix'] = json.loads(data['gpio_behavior_matrix']) if data['gpio_behavior_matrix'].strip() else {}
            except json.JSONDecodeError as exc:
                raise BadRequest(f"Invalid GPIO behavior matrix JSON: {exc}")

        # Convert boolean fields
        bool_fields = [
            'gpio_enabled', 'oled_enabled', 'oled_default_invert',
            'oled_button_active_high', 'screens_auto_start',
            'led_enabled', 'vfd_enabled',
        ]
        for field in bool_fields:
            if field in data:
                if isinstance(data[field], str):
                    data[field] = data[field].lower() in ('true', '1', 'yes', 'on')
                else:
                    data[field] = bool(data[field])

        # Convert integer fields
        int_fields = [
            'oled_i2c_bus', 'oled_i2c_address', 'oled_width', 'oled_height',
            'oled_rotate', 'oled_contrast', 'oled_button_gpio',
            'oled_scroll_speed', 'oled_scroll_fps',
            'led_port', 'led_baudrate', 'vfd_baudrate',
        ]
        for field in int_fields:
            if field in data and data[field] is not None:
                if data[field] == '' or data[field] == 'None':
                    data[field] = None
                else:
                    try:
                        data[field] = int(data[field])
                    except (TypeError, ValueError):
                        pass

        # Convert float fields
        float_fields = ['oled_button_hold_seconds']
        for field in float_fields:
            if field in data and data[field] is not None:
                try:
                    data[field] = float(data[field])
                except (TypeError, ValueError):
                    pass

        # Update settings
        settings = update_hardware_settings(data)
        invalidate_hardware_settings_cache()

        flash("Hardware settings updated successfully! Restart services for changes to take effect.", "success")

        if request.is_json:
            return jsonify({
                "success": True,
                "message": "Hardware settings updated",
                "settings": settings.to_dict(),
            })
        else:
            return redirect(url_for('hardware.hardware_settings_page'))

    except BadRequest as exc:
        logger.warning(f"Bad request updating hardware settings: {exc}")
        if request.is_json:
            return jsonify({"success": False, "error": str(exc)}), 400
        else:
            flash(str(exc), "error")
            return redirect(url_for('hardware.hardware_settings_page'))

    except Exception as exc:
        logger.error(f"Failed to update hardware settings: {exc}")
        db.session.rollback()
        if request.is_json:
            return jsonify({"success": False, "error": str(exc)}), 500
        else:
            flash(f"Error updating hardware settings: {exc}", "error")
            return redirect(url_for('hardware.hardware_settings_page'))


@hardware_bp.route('/admin/hardware/restart-services', methods=['POST'])
@require_permission('admin')
def restart_hardware_services():
    """Restart hardware-related services to apply new settings."""
    try:
        import subprocess

        # Restart the target which will restart all services
        result = subprocess.run(
            ['systemctl', 'restart', 'eas-station.target'],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            flash("Services restarted successfully! Hardware changes are now active.", "success")
            return jsonify({"success": True, "message": "Services restarted"})
        else:
            error_msg = result.stderr or "Unknown error"
            flash(f"Failed to restart services: {error_msg}", "error")
            return jsonify({"success": False, "error": error_msg}), 500

    except subprocess.TimeoutExpired:
        flash("Service restart timed out - check status manually", "warning")
        return jsonify({"success": False, "error": "Timeout"}), 500
    except Exception as exc:
        logger.error(f"Failed to restart services: {exc}")
        flash(f"Error restarting services: {exc}", "error")
        return jsonify({"success": False, "error": str(exc)}), 500
