"""
EAS Decoder Monitor Settings Admin Page

Allows configuration of EAS decoder audio monitoring tap.
Users can listen to the actual 16 kHz resampled audio fed to the SAME decoder
to verify correct sample rate and audio quality.
"""

from flask import Blueprint, render_template, request, jsonify
from werkzeug.exceptions import BadRequest
import logging

from app_core import db
from app_core.models import EASDecoderMonitorSettings

logger = logging.getLogger(__name__)

eas_decoder_monitor_bp = Blueprint('eas_decoder_monitor', __name__)


@eas_decoder_monitor_bp.route('/admin/eas_decoder_monitor')
def eas_decoder_monitor_page():
    """Render EAS decoder monitor settings page."""
    return render_template('admin/eas_decoder_monitor.html')


@eas_decoder_monitor_bp.route('/api/admin/eas_decoder_monitor/settings', methods=['GET'])
def get_eas_decoder_monitor_settings():
    """Get current EAS decoder monitor settings."""
    try:
        settings = EASDecoderMonitorSettings.query.first()
        if not settings:
            # Create default settings if none exist
            settings = EASDecoderMonitorSettings(
                enabled=False,
                stream_name='eas-decoder-monitor'
            )
            db.session.add(settings)
            db.session.commit()
        
        return jsonify(settings.to_dict())
    except Exception as exc:
        logger.error(f'Error getting EAS decoder monitor settings: {exc}')
        return jsonify({'error': str(exc)}), 500


@eas_decoder_monitor_bp.route('/api/admin/eas_decoder_monitor/settings', methods=['PUT'])
def update_eas_decoder_monitor_settings():
    """Update EAS decoder monitor settings."""
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            raise BadRequest('Invalid JSON payload')
        
        settings = EASDecoderMonitorSettings.query.first()
        if not settings:
            settings = EASDecoderMonitorSettings()
            db.session.add(settings)
        
        # Update enabled status
        if 'enabled' in data:
            settings.enabled = bool(data['enabled'])
        
        # Update stream name
        if 'stream_name' in data:
            stream_name = str(data['stream_name']).strip()
            if not stream_name:
                raise BadRequest('Stream name cannot be empty')
            settings.stream_name = stream_name
        
        db.session.commit()
        
        return jsonify({
            'message': 'EAS decoder monitor settings updated',
            'settings': settings.to_dict()
        })
    except Exception as exc:
        db.session.rollback()
        logger.error(f'Error updating EAS decoder monitor settings: {exc}')
        return jsonify({'error': str(exc)}), 500


def register_blueprint(app):
    """Register the blueprint with the Flask app."""
    app.register_blueprint(eas_decoder_monitor_bp)
