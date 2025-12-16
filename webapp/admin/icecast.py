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

"""Icecast streaming server settings management routes."""

import logging
import re
import requests
from typing import Any, Dict

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.exceptions import BadRequest

from app_core.auth.roles import require_permission
from app_core.extensions import db
from app_core.icecast_settings import (
    get_icecast_settings,
    update_icecast_settings,
    invalidate_icecast_settings_cache,
)

logger = logging.getLogger(__name__)

# Create Blueprint for icecast routes
icecast_bp = Blueprint('icecast', __name__)


@icecast_bp.route('/admin/icecast')
@require_permission('system.configure')
def icecast_settings_page():
    """Display Icecast settings configuration page."""
    try:
        settings = get_icecast_settings()

        return render_template(
            'admin/icecast.html',
            settings=settings,
        )
    except Exception as exc:
        logger.error(f"Failed to load Icecast settings: {exc}")
        flash(f"Error loading Icecast settings: {exc}", "error")
        return redirect(url_for('admin.index'))


@icecast_bp.route('/api/admin/icecast/settings', methods=['GET'])
@require_permission('system.configure')
def get_settings():
    """Get current Icecast settings."""
    try:
        settings = get_icecast_settings()
        return jsonify({
            "success": True,
            "settings": settings.to_dict(),
        })
    except Exception as exc:
        logger.error(f"Failed to get Icecast settings: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@icecast_bp.route('/api/admin/icecast/settings', methods=['PUT'])
@require_permission('system.configure')
def update_settings():
    """Update Icecast settings."""
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()

        # Convert boolean fields
        bool_fields = ['enabled', 'stream_public']
        for field in bool_fields:
            if field in data:
                if isinstance(data[field], str):
                    data[field] = data[field].lower() in ('true', '1', 'yes', 'on')
                else:
                    data[field] = bool(data[field])

        # Convert integer fields
        int_fields = ['port', 'external_port', 'stream_bitrate']
        for field in int_fields:
            if field in data and data[field] is not None:
                if data[field] == '' or data[field] == 'None':
                    data[field] = None
                else:
                    try:
                        data[field] = int(data[field])
                    except (TypeError, ValueError):
                        raise BadRequest(f"Invalid value for {field}: must be an integer")

        # Validate required fields
        if 'server' in data and not data['server']:
            raise BadRequest("Server hostname/IP is required")
        
        # SECURITY: Validate server hostname to prevent SSRF
        if 'server' in data and data['server']:
            if not re.match(r'^[a-zA-Z0-9\.\-]+$', data['server']):
                raise BadRequest("Invalid server hostname. Only alphanumeric characters, dots, and hyphens allowed.")
        
        if 'port' in data:
            port = data['port']
            if port is not None and (port < 1 or port > 65535):
                raise BadRequest("Port must be between 1 and 65535")
        
        if 'external_port' in data and data['external_port'] is not None:
            ext_port = data['external_port']
            if ext_port < 1 or ext_port > 65535:
                raise BadRequest("External port must be between 1 and 65535")
        
        if 'stream_bitrate' in data:
            bitrate = data['stream_bitrate']
            if bitrate is not None and (bitrate < 8 or bitrate > 320):
                raise BadRequest("Stream bitrate must be between 8 and 320 kbps")

        # Update settings
        settings = update_icecast_settings(data)
        invalidate_icecast_settings_cache()

        logger.info(f"Icecast settings updated successfully")

        return jsonify({
            "success": True,
            "message": "Icecast settings updated successfully. Restart audio services for changes to take effect.",
            "settings": settings.to_dict(),
        })

    except BadRequest as exc:
        logger.warning(f"Bad request updating Icecast settings: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 400

    except Exception as exc:
        logger.error(f"Failed to update Icecast settings: {exc}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 500


@icecast_bp.route('/api/admin/icecast/test-connection', methods=['POST'])
@require_permission('system.configure')
def test_connection():
    """Test connection to Icecast server.
    
    SECURITY NOTE: This endpoint makes HTTP requests to user-specified servers.
    To prevent SSRF attacks:
    1. Validates port is in allowed range (1-65535)
    2. Validates server hostname format (alphanumeric, dots, hyphens only)
    3. Restricts to HTTP protocol only (no file://, gopher://, etc.)
    4. Uses short timeout (5s) to prevent hanging
    5. Disables redirects to prevent redirect-based SSRF
    6. Only accessible with system.configure permission
    """
    try:
        data = request.get_json() if request.is_json else {}
        
        # Get settings from request or use current settings
        settings = get_icecast_settings()
        server = data.get('server', settings.server)
        port = data.get('port', settings.port)
        admin_user = data.get('admin_user', settings.admin_user)
        admin_password = data.get('admin_password', settings.admin_password)
        
        # SECURITY: Validate server hostname to prevent SSRF attacks
        # Allow localhost, IP addresses, and domain names only
        # Reject URLs, paths, and suspicious characters
        if not re.match(r'^[a-zA-Z0-9\.\-]+$', server):
            return jsonify({
                "success": False,
                "error": f"Invalid server hostname. Only alphanumeric characters, dots, and hyphens allowed."
            }), 400
        
        # SECURITY: Validate port is in valid range
        if not (1 <= port <= 65535):
            return jsonify({
                "success": False,
                "error": f"Invalid port: {port}. Must be between 1 and 65535."
            }), 400

        # Try to connect to Icecast admin interface
        # SECURITY: Construct URL carefully to prevent injection
        test_url = f"http://{server}:{port}/admin/stats.xml"
        
        logger.info(f"Testing Icecast connection to {server}:{port}")
        
        try:
            # Test basic connectivity
            # SECURITY: Set allow_redirects=False to prevent redirect-based SSRF
            response = requests.get(
                test_url,
                auth=(admin_user, admin_password) if admin_user and admin_password else None,
                timeout=5,
                allow_redirects=False  # SSRF prevention
            )
            
            if response.status_code == 200:
                return jsonify({
                    "success": True,
                    "message": f"Successfully connected to Icecast server at {server}:{port}",
                    "details": {
                        "server": server,
                        "port": port,
                        "authenticated": bool(admin_user and admin_password),
                        "status_code": response.status_code
                    }
                })
            elif response.status_code == 401:
                return jsonify({
                    "success": False,
                    "error": "Authentication failed. Check admin username and password.",
                    "details": {
                        "server": server,
                        "port": port,
                        "status_code": response.status_code
                    }
                }), 401
            else:
                return jsonify({
                    "success": False,
                    "error": f"Icecast server returned status code {response.status_code}",
                    "details": {
                        "server": server,
                        "port": port,
                        "status_code": response.status_code
                    }
                }), 500
                
        except requests.exceptions.Timeout:
            return jsonify({
                "success": False,
                "error": f"Connection timeout. Server may be unreachable at {server}:{port}",
            }), 500
        except requests.exceptions.ConnectionError:
            return jsonify({
                "success": False,
                "error": f"Connection refused. Check if Icecast is running on {server}:{port}",
            }), 500
        except Exception as req_exc:
            return jsonify({
                "success": False,
                "error": f"Connection test failed: {str(req_exc)}",
            }), 500

    except Exception as exc:
        logger.error(f"Failed to test Icecast connection: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@icecast_bp.route('/api/admin/icecast/status', methods=['GET'])
@require_permission('system.configure')
def get_status():
    """Get current Icecast streaming status.
    
    SECURITY NOTE: Makes HTTP requests to configured Icecast server.
    SSRF prevention handled by hostname validation during settings save.
    """
    try:
        settings = get_icecast_settings()
        
        if not settings.enabled:
            return jsonify({
                "success": True,
                "enabled": False,
                "message": "Icecast streaming is disabled",
            })
        
        # SECURITY: Validate server hostname (defense in depth)
        server = settings.server or 'localhost'
        if not re.match(r'^[a-zA-Z0-9\.\-]+$', server):
            logger.error(f"Invalid Icecast server hostname in database: {server}")
            return jsonify({
                "success": False,
                "error": "Invalid server hostname in configuration"
            }), 500

        # Try to get stats from Icecast server
        stats_url = f"http://{server}:{settings.port}/admin/stats.xml"
        
        try:
            # SECURITY: Disable redirects to prevent redirect-based SSRF
            response = requests.get(
                stats_url,
                auth=(settings.admin_user, settings.admin_password) if settings.admin_user and settings.admin_password else None,
                timeout=3,
                allow_redirects=False  # SSRF prevention
            )
            
            if response.status_code == 200:
                # Parse stats from XML response
                content = response.text
                
                try:
                    # SECURITY: Basic validation before regex parsing
                    # Only parse XML-like responses from trusted Icecast server
                    content_stripped = content.strip()
                    if not (content_stripped.startswith('<?xml') or content_stripped.startswith('<icestats')):
                        logger.warning(f"Icecast stats response doesn't look like valid XML: {content_stripped[:100]}")
                        return jsonify({
                            "success": False,
                            "error": "Invalid XML response from Icecast server"
                        })
                    
                    # Use simple regex-based parsing for the two stats we need
                    # This is sufficient and more lightweight than xml.etree.ElementTree
                    # for extracting just 2 simple numeric values from well-formed Icecast XML
                    listeners_match = re.search(r'<listeners>(\d+)</listeners>', content)
                    total_listeners = int(listeners_match.group(1)) if listeners_match else 0
                    
                    sources_match = re.search(r'<sources>(\d+)</sources>', content)
                    total_sources = int(sources_match.group(1)) if sources_match else 0
                    
                    return jsonify({
                        "success": True,
                        "enabled": True,
                        "server_reachable": True,
                        "server": settings.server,
                        "port": settings.port,
                        "stats": {
                            "total_listeners": total_listeners,
                            "total_sources": total_sources,
                        }
                    })
                except (ValueError, AttributeError) as parse_err:
                    logger.warning(f"Failed to parse Icecast stats XML: {parse_err}")
                    return jsonify({
                        "success": True,
                        "enabled": True,
                        "server_reachable": True,
                        "server": settings.server,
                        "port": settings.port,
                        "stats": {
                            "total_listeners": 0,
                            "total_sources": 0,
                        },
                        "warning": "Unable to parse server statistics"
                    })
            else:
                return jsonify({
                    "success": True,
                    "enabled": True,
                    "server_reachable": False,
                    "error": f"Server returned status code {response.status_code}",
                })
                
        except requests.exceptions.RequestException as req_exc:
            return jsonify({
                "success": True,
                "enabled": True,
                "server_reachable": False,
                "error": f"Cannot reach Icecast server: {str(req_exc)}",
            })

    except Exception as exc:
        logger.error(f"Failed to get Icecast status: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


def register_icecast_routes(app, logger):
    """Register Icecast admin routes with the Flask app.
    
    Note: Routes defined with absolute paths (starting with '/') in the blueprint
    are not affected by the url_prefix parameter. This follows the pattern used
    in hardware.py for consistency.
    """
    app.register_blueprint(icecast_bp, url_prefix='/admin')
    logger.info("Icecast admin routes registered")


__all__ = ['icecast_bp', 'register_icecast_routes']
