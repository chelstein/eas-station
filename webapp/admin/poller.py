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

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from sqlalchemy.exc import SQLAlchemyError
import logging

from app_core.extensions import db
from app_core.models import PollerSettings
from app_core.auth.decorators import require_auth
from app_core.auth.roles import require_permission

logger = logging.getLogger(__name__)

poller_bp = Blueprint('poller', __name__, url_prefix='/admin/poller')


@poller_bp.route('/', methods=['GET'])
@require_auth
@require_permission('system.configure')
def poller_settings():
    """Display poller configuration settings page."""
    try:
        # Get or create poller settings (single row)
        settings = PollerSettings.query.first()
        if not settings:
            # Create default settings if none exist
            settings = PollerSettings(
                enabled=True,
                poll_interval_sec=120,
                log_fetched_alerts=False
            )
            db.session.add(settings)
            db.session.commit()
            logger.info("Created default poller settings")
        
        return render_template('admin/poller.html', settings=settings)
    
    except SQLAlchemyError as e:
        logger.error(f"Database error loading poller settings: {str(e)}")
        db.session.rollback()
        flash('Database error loading poller settings', 'danger')
        return redirect(url_for('admin_page'))


@poller_bp.route('/update', methods=['POST'])
@require_auth
@require_permission('system.configure')
def update_poller_settings():
    """Update poller configuration settings."""
    try:
        settings = PollerSettings.query.first()
        if not settings:
            settings = PollerSettings()
            db.session.add(settings)
        
        # Get form data
        enabled = request.form.get('enabled', 'false').lower() == 'true'
        poll_interval_sec = int(request.form.get('poll_interval_sec', 120))
        log_fetched_alerts = request.form.get('log_fetched_alerts', 'false').lower() == 'true'
        
        # Validate poll interval (minimum 30 seconds)
        if poll_interval_sec < 30:
            return jsonify({
                'success': False,
                'error': 'Poll interval must be at least 30 seconds'
            }), 400
        
        # Update settings
        settings.enabled = enabled
        settings.poll_interval_sec = poll_interval_sec
        settings.log_fetched_alerts = log_fetched_alerts
        
        db.session.commit()
        
        logger.info(f"Updated poller settings: enabled={enabled}, interval={poll_interval_sec}s, log_fetched={log_fetched_alerts}")
        
        return jsonify({
            'success': True,
            'message': 'Poller settings updated successfully',
            'settings': settings.to_dict()
        })
    
    except ValueError as e:
        logger.error(f"Invalid value in poller settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Invalid value: {str(e)}'
        }), 400
    
    except SQLAlchemyError as e:
        logger.error(f"Database error updating poller settings: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Database error saving poller settings'
        }), 500


@poller_bp.route('/status', methods=['GET'])
@require_auth
@require_permission('system.view_config')
def poller_status():
    """Get current poller settings as JSON."""
    try:
        settings = PollerSettings.query.first()
        if not settings:
            return jsonify({
                'success': False,
                'error': 'Poller settings not configured'
            }), 404
        
        return jsonify({
            'success': True,
            'settings': settings.to_dict()
        })
    
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching poller status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Database error'
        }), 500
