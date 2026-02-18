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

"""Application settings admin routes."""

import logging

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from sqlalchemy.exc import SQLAlchemyError

from app_core.extensions import db
from app_core.models import ApplicationSettings
from app_core.auth.decorators import require_auth
from app_core.auth.roles import require_permission

logger = logging.getLogger(__name__)

application_settings_bp = Blueprint('application_settings', __name__, url_prefix='/admin/application')

VALID_LOG_LEVELS = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}


def _get_or_create_settings() -> ApplicationSettings:
    """Get application settings, creating defaults if none exist."""
    settings = ApplicationSettings.query.first()
    if not settings:
        settings = ApplicationSettings(
            id=1,
            log_level='INFO',
            log_file='logs/eas_station.log',
            upload_folder='/opt/eas-station/uploads',
        )
        db.session.add(settings)
        db.session.commit()
        logger.info("Created default application settings")
    return settings


@application_settings_bp.route('/', methods=['GET'])
@require_auth
@require_permission('system.configure')
def application_settings_page():
    """Display application settings page."""
    try:
        settings = _get_or_create_settings()
        return render_template('admin/application_settings.html', settings=settings,
                               valid_log_levels=sorted(VALID_LOG_LEVELS))
    except SQLAlchemyError as e:
        logger.error(f"Database error loading application settings: {str(e)}")
        db.session.rollback()
        flash('Database error loading application settings', 'danger')
        return redirect(url_for('admin_page'))


@application_settings_bp.route('/update', methods=['POST'])
@require_auth
@require_permission('system.configure')
def update_application_settings():
    """Update application settings."""
    try:
        settings = ApplicationSettings.query.first()
        if not settings:
            settings = ApplicationSettings(id=1)
            db.session.add(settings)

        log_level = request.form.get('log_level', 'INFO').strip().upper()
        if log_level not in VALID_LOG_LEVELS:
            return jsonify({'success': False,
                            'error': f'Invalid log level. Must be one of: {", ".join(sorted(VALID_LOG_LEVELS))}'}), 400
        settings.log_level = log_level

        log_file = request.form.get('log_file', '').strip()
        if not log_file:
            return jsonify({'success': False, 'error': 'Log file path is required'}), 400
        settings.log_file = log_file

        upload_folder = request.form.get('upload_folder', '').strip()
        if not upload_folder:
            return jsonify({'success': False, 'error': 'Upload folder path is required'}), 400
        settings.upload_folder = upload_folder

        db.session.commit()

        # Apply log level change immediately to the running process
        import logging as _logging
        numeric_level = getattr(_logging, settings.log_level, _logging.INFO)
        _logging.getLogger().setLevel(numeric_level)
        logger.info("Updated application settings: log_level=%s, log_file=%s, upload_folder=%s",
                    settings.log_level, settings.log_file, settings.upload_folder)

        return jsonify({
            'success': True,
            'message': 'Application settings updated successfully. Log level applied immediately.',
            'settings': settings.to_dict(),
        })

    except SQLAlchemyError as e:
        logger.error(f"Database error updating application settings: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Database error saving application settings'}), 500


@application_settings_bp.route('/status', methods=['GET'])
@require_auth
@require_permission('system.view_config')
def application_status():
    """Get current application settings as JSON."""
    try:
        settings = ApplicationSettings.query.first()
        if not settings:
            return jsonify({'success': False, 'error': 'Application settings not configured'}), 404
        return jsonify({'success': True, 'settings': settings.to_dict()})
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching application status: {str(e)}")
        return jsonify({'success': False, 'error': 'Database error'}), 500
