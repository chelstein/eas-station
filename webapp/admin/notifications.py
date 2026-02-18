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

"""Notification settings admin routes."""

import logging

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from sqlalchemy.exc import SQLAlchemyError

from app_core.extensions import db
from app_core.models import NotificationSettings
from app_core.auth.decorators import require_auth
from app_core.auth.roles import require_permission

logger = logging.getLogger(__name__)

notifications_bp = Blueprint('notifications', __name__, url_prefix='/admin/notifications')


def _get_or_create_settings() -> NotificationSettings:
    """Get notification settings, creating defaults if none exist."""
    settings = NotificationSettings.query.first()
    if not settings:
        settings = NotificationSettings(
            id=1,
            email_enabled=False,
            mail_url='',
            compliance_alert_emails=[],
            sms_enabled=False,
        )
        db.session.add(settings)
        db.session.commit()
        logger.info("Created default notification settings")
    return settings


@notifications_bp.route('/', methods=['GET'])
@require_auth
@require_permission('system.configure')
def notification_settings():
    """Display notification configuration settings page."""
    try:
        settings = _get_or_create_settings()
        return render_template('admin/notifications.html', settings=settings)
    except SQLAlchemyError as e:
        logger.error(f"Database error loading notification settings: {str(e)}")
        db.session.rollback()
        flash('Database error loading notification settings', 'danger')
        return redirect(url_for('admin_page'))


@notifications_bp.route('/update', methods=['POST'])
@require_auth
@require_permission('system.configure')
def update_notification_settings():
    """Update notification settings."""
    try:
        settings = NotificationSettings.query.first()
        if not settings:
            settings = NotificationSettings(id=1)
            db.session.add(settings)

        settings.email_enabled = request.form.get('email_enabled', 'false').lower() == 'true'
        settings.mail_url = request.form.get('mail_url', '').strip()
        settings.sms_enabled = request.form.get('sms_enabled', 'false').lower() == 'true'

        # Compliance alert emails: textarea, one address per line
        emails_raw = request.form.get('compliance_alert_emails', '').strip()
        settings.compliance_alert_emails = [
            addr.strip() for addr in emails_raw.splitlines() if addr.strip()
        ]

        db.session.commit()
        logger.info(
            "Updated notification settings: email_enabled=%s, sms_enabled=%s, "
            "compliance_emails=%d",
            settings.email_enabled, settings.sms_enabled,
            len(settings.compliance_alert_emails),
        )

        return jsonify({
            'success': True,
            'message': 'Notification settings updated successfully',
            'settings': settings.to_dict(),
        })

    except SQLAlchemyError as e:
        logger.error(f"Database error updating notification settings: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Database error saving notification settings'}), 500


@notifications_bp.route('/status', methods=['GET'])
@require_auth
@require_permission('system.view_config')
def notification_status():
    """Get current notification settings as JSON."""
    try:
        settings = NotificationSettings.query.first()
        if not settings:
            return jsonify({'success': False, 'error': 'Notification settings not configured'}), 404
        return jsonify({'success': True, 'settings': settings.to_dict()})
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching notification status: {str(e)}")
        return jsonify({'success': False, 'error': 'Database error'}), 500
