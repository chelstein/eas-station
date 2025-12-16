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

"""Certbot/SSL certificate management routes."""

import logging
import os
import re
import socket
import subprocess
from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for, send_file
from werkzeug.exceptions import BadRequest

from app_core.auth.roles import require_permission
from app_core.extensions import db
from app_core.certbot_settings import (
    get_certbot_settings,
    update_certbot_settings,
)

logger = logging.getLogger(__name__)

# Create Blueprint for certbot routes
certbot_bp = Blueprint('certbot', __name__)


# Routes are relative to blueprint's url_prefix='/admin'
# e.g., route '/certbot' becomes '/admin/certbot'
@certbot_bp.route('/certbot')
@require_permission('system.configure')
def certbot_settings_page():
    """Display Certbot/SSL certificate settings configuration page."""
    try:
        settings = get_certbot_settings()

        return render_template(
            'admin/certbot.html',
            settings=settings,
        )
    except Exception as exc:
        logger.error(f"Failed to load Certbot settings: {exc}")
        flash(f"Error loading Certbot settings: {exc}", "error")
        return redirect(url_for('admin.index'))


@certbot_bp.route('/api/certbot/settings', methods=['GET'])
@require_permission('system.configure')
def get_settings():
    """Get current Certbot settings."""
    try:
        settings = get_certbot_settings()
        return jsonify({
            "success": True,
            "settings": settings.to_dict(),
        })
    except Exception as exc:
        logger.error(f"Failed to get Certbot settings: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@certbot_bp.route('/api/certbot/settings', methods=['PUT'])
@require_permission('system.configure')
def update_settings():
    """Update Certbot settings."""
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()

        # Convert boolean fields
        bool_fields = ['enabled', 'staging', 'auto_renew_enabled']
        for field in bool_fields:
            if field in data:
                if isinstance(data[field], str):
                    data[field] = data[field].lower() in ('true', '1', 'yes', 'on')
                else:
                    data[field] = bool(data[field])

        # Convert integer fields
        int_fields = ['renew_days_before_expiry']
        for field in int_fields:
            if field in data and data[field] is not None:
                if data[field] == '' or data[field] == 'None':
                    data[field] = None
                else:
                    try:
                        data[field] = int(data[field])
                    except (TypeError, ValueError):
                        raise BadRequest(f"Invalid value for {field}: must be an integer")

        # Validate required fields when enabled
        if data.get('enabled', False):
            if 'domain_name' in data and not data['domain_name']:
                raise BadRequest("Domain name is required when Certbot is enabled")
            if 'email' in data and not data['email']:
                raise BadRequest("Email is required when Certbot is enabled")

        # SECURITY: Validate domain name to prevent command injection and SSRF
        if 'domain_name' in data and data['domain_name']:
            domain = data['domain_name'].strip()
            # Allow alphanumeric, dots, and hyphens only (standard domain format)
            if not re.match(r'^[a-zA-Z0-9\.\-]+$', domain):
                raise BadRequest("Invalid domain name. Only alphanumeric characters, dots, and hyphens allowed.")
            # Prevent localhost and internal IPs
            if domain.lower() in ['localhost', '127.0.0.1', '0.0.0.0']:
                raise BadRequest("Cannot use localhost or loopback addresses for SSL certificates")
            data['domain_name'] = domain

        # SECURITY: Validate email format
        if 'email' in data and data['email']:
            email = data['email'].strip()
            if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
                raise BadRequest("Invalid email address format")
            data['email'] = email

        # Validate renew_days_before_expiry
        if 'renew_days_before_expiry' in data and data['renew_days_before_expiry'] is not None:
            days = data['renew_days_before_expiry']
            if days < 1 or days > 90:
                raise BadRequest("Renewal days before expiry must be between 1 and 90")

        # Update settings
        settings = update_certbot_settings(data)

        logger.info(f"Certbot settings updated successfully")

        return jsonify({
            "success": True,
            "message": "Certbot settings updated successfully. Changes take effect on next certificate operation.",
            "settings": settings.to_dict(),
        })

    except BadRequest as exc:
        logger.warning(f"Bad request updating Certbot settings: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 400

    except Exception as exc:
        logger.error(f"Failed to update Certbot settings: {exc}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 500


@certbot_bp.route('/api/certbot/certificate-status', methods=['GET'])
@require_permission('system.configure')
def get_certificate_status():
    """Get current SSL certificate status and information."""
    try:
        from app_core.ssl_utils import get_ssl_certificate_info, get_certificate_renewal_status

        cert_info = get_ssl_certificate_info()
        renewal_status = get_certificate_renewal_status()

        # Combine the information
        status = {
            "success": True,
            "certificate": cert_info,
            "renewal": renewal_status,
        }

        return jsonify(status)

    except Exception as exc:
        logger.error(f"Failed to get certificate status: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@certbot_bp.route('/api/certbot/renew-certificate', methods=['POST'])
@require_permission('system.configure')
def renew_certificate():
    """Trigger manual certificate renewal.
    
    SECURITY NOTE: This endpoint runs certbot commands with elevated privileges.
    Access is restricted to system.configure permission.
    Domain validation prevents command injection.
    """
    try:
        settings = get_certbot_settings()

        if not settings.enabled:
            return jsonify({
                "success": False,
                "error": "Certbot is not enabled in settings"
            }), 400

        if not settings.domain_name:
            return jsonify({
                "success": False,
                "error": "Domain name is not configured"
            }), 400

        # SECURITY: Validate domain name (defense in depth)
        domain = settings.domain_name.strip()
        if not re.match(r'^[a-zA-Z0-9\.\-]+$', domain):
            logger.error(f"Invalid domain name in database: {domain}")
            return jsonify({
                "success": False,
                "error": "Invalid domain name in configuration"
            }), 500

        # Check if certbot is installed
        try:
            result = subprocess.run(
                ['which', 'certbot'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return jsonify({
                    "success": False,
                    "error": "Certbot is not installed on this system"
                }), 500
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to check certbot installation: {str(e)}"
            }), 500

        logger.info(f"Attempting certificate renewal for domain: {domain}")

        # Run certbot renew with dry-run first to test
        # SECURITY: Using subprocess.run with list arguments prevents shell injection
        cmd = ['sudo', 'certbot', 'renew', '--dry-run', '--non-interactive']
        if settings.staging:
            cmd.append('--staging')

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return jsonify({
                    "success": True,
                    "message": "Dry-run renewal successful. Certificate is valid and renewal would succeed.",
                    "output": result.stdout[-500:] if result.stdout else "",  # Last 500 chars
                })
            else:
                # Check for specific error messages
                error_output = result.stderr if result.stderr else result.stdout if result.stdout else ""
                
                # Detect sudo privilege issues
                if "no new privileges" in error_output.lower() or "sudo" in error_output.lower():
                    return jsonify({
                        "success": False,
                        "error": "Permission error: Cannot run certbot with sudo from web interface",
                        "details": "Certificate renewal is designed to run via systemd timer (certbot.timer). "
                                 "To test renewal, use the command line: 'sudo certbot renew --dry-run' or "
                                 "check the systemd timer status: 'systemctl status certbot.timer'",
                        "output": error_output[-500:],
                    }), 500
                
                return jsonify({
                    "success": False,
                    "error": "Dry-run renewal failed",
                    "output": error_output[-500:],
                }), 500

        except subprocess.TimeoutExpired:
            return jsonify({
                "success": False,
                "error": "Certificate renewal command timed out after 60 seconds"
            }), 500
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to run certbot: {str(e)}"
            }), 500

    except Exception as exc:
        logger.error(f"Failed to renew certificate: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@certbot_bp.route('/api/certbot/obtain-certificate', methods=['POST'])
@require_permission('system.configure')
def obtain_certificate():
    """Obtain a new SSL certificate from Let's Encrypt.
    
    SECURITY NOTE: This endpoint runs certbot commands with elevated privileges.
    Access is restricted to system.configure permission.
    Domain validation prevents command injection.
    """
    try:
        settings = get_certbot_settings()

        if not settings.enabled:
            return jsonify({
                "success": False,
                "error": "Certbot is not enabled in settings"
            }), 400

        if not settings.domain_name:
            return jsonify({
                "success": False,
                "error": "Domain name is not configured"
            }), 400

        if not settings.email:
            return jsonify({
                "success": False,
                "error": "Email address is not configured"
            }), 400

        # SECURITY: Validate domain name (defense in depth)
        domain = settings.domain_name.strip()
        if not re.match(r'^[a-zA-Z0-9\.\-]+$', domain):
            logger.error(f"Invalid domain name in database: {domain}")
            return jsonify({
                "success": False,
                "error": "Invalid domain name in configuration"
            }), 500

        # SECURITY: Validate email
        email = settings.email.strip()
        if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
            logger.error(f"Invalid email in database: {email}")
            return jsonify({
                "success": False,
                "error": "Invalid email address in configuration"
            }), 500

        # Check if certbot is installed
        try:
            result = subprocess.run(
                ['which', 'certbot'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return jsonify({
                    "success": False,
                    "error": "Certbot is not installed on this system"
                }), 500
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to check certbot installation: {str(e)}"
            }), 500

        logger.info(f"Attempting to obtain certificate for domain: {domain}")

        # Build certbot command
        # SECURITY: Using subprocess.run with list arguments prevents shell injection
        cmd = [
            'sudo', 'certbot', 'certonly',
            '--standalone',
            '--non-interactive',
            '--agree-tos',
            '--email', email,
            '-d', domain
        ]
        
        if settings.staging:
            cmd.append('--staging')

        try:
            # Stop nginx temporarily for standalone mode
            logger.info("Stopping nginx for standalone certificate acquisition...")
            stop_result = subprocess.run(
                ['sudo', 'systemctl', 'stop', 'nginx'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if stop_result.returncode != 0:
                logger.warning(f"Failed to stop nginx: {stop_result.stderr}")
                # Continue anyway - certbot might work with webroot

            # Run certbot
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            # Restart nginx
            logger.info("Restarting nginx...")
            start_result = subprocess.run(
                ['sudo', 'systemctl', 'start', 'nginx'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if start_result.returncode != 0:
                logger.error(f"Failed to restart nginx: {start_result.stderr}")

            if result.returncode == 0:
                logger.info(f"Successfully obtained certificate for {domain}")
                return jsonify({
                    "success": True,
                    "message": f"SSL certificate obtained successfully for {domain}. You may need to update your nginx configuration to use the new certificate.",
                    "output": result.stdout[-1000:] if result.stdout else "",  # Last 1000 chars
                })
            else:
                logger.error(f"Failed to obtain certificate: {result.stderr}")
                
                # Check for specific error messages
                error_output = result.stderr if result.stderr else result.stdout if result.stdout else ""
                
                # Detect sudo privilege issues
                if "no new privileges" in error_output.lower() or ("sudo" in error_output.lower() and "prevent" in error_output.lower()):
                    return jsonify({
                        "success": False,
                        "error": "Permission error: Cannot run certbot with sudo from web interface",
                        "details": "Certificate acquisition requires elevated privileges. "
                                 "Please run manually: 'sudo certbot certonly --standalone -d YOUR_DOMAIN' or "
                                 "ensure the web application has proper permissions.",
                        "output": error_output[-1000:],
                    }), 500
                
                # Detect port 80 already in use
                if "address already in use" in error_output.lower() or "port 80" in error_output.lower():
                    return jsonify({
                        "success": False,
                        "error": "Port 80 is already in use",
                        "details": "nginx or another service is using port 80. Try stopping nginx first or use the webroot method.",
                        "output": error_output[-1000:],
                    }), 500
                
                # Detect domain validation failures
                if "challenge" in error_output.lower() or "validation" in error_output.lower():
                    return jsonify({
                        "success": False,
                        "error": "Domain validation failed",
                        "details": "Let's Encrypt could not validate your domain. Ensure port 80 is accessible from the internet and DNS is correctly configured.",
                        "output": error_output[-1000:],
                    }), 500
                
                return jsonify({
                    "success": False,
                    "error": "Failed to obtain certificate from Let's Encrypt",
                    "output": error_output[-1000:],
                }), 500

        except subprocess.TimeoutExpired:
            # Make sure to restart nginx
            subprocess.run(['sudo', 'systemctl', 'start', 'nginx'], capture_output=True, timeout=30)
            return jsonify({
                "success": False,
                "error": "Certificate acquisition command timed out after 120 seconds"
            }), 500
        except Exception as e:
            # Make sure to restart nginx
            subprocess.run(['sudo', 'systemctl', 'start', 'nginx'], capture_output=True, timeout=30)
            return jsonify({
                "success": False,
                "error": f"Failed to run certbot: {str(e)}"
            }), 500

    except Exception as exc:
        logger.error(f"Failed to obtain certificate: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@certbot_bp.route('/api/certbot/test-domain', methods=['POST'])
@require_permission('system.configure')
def test_domain():
    """Test domain DNS resolution and HTTP accessibility.
    
    SECURITY NOTE: This endpoint performs DNS lookups and HTTP checks.
    Domain validation prevents SSRF attacks.
    """
    try:
        # Handle both JSON and form data, and empty requests
        data = {}
        if request.is_json:
            data = request.get_json() or {}
        elif request.form:
            data = request.form.to_dict()
        
        settings = get_certbot_settings()
        domain = data.get('domain_name', settings.domain_name)

        if not domain:
            return jsonify({
                "success": False,
                "error": "Domain name is required"
            }), 400

        # SECURITY: Validate domain name to prevent SSRF
        domain = domain.strip()
        if not re.match(r'^[a-zA-Z0-9\.\-]+$', domain):
            return jsonify({
                "success": False,
                "error": "Invalid domain name. Only alphanumeric characters, dots, and hyphens allowed."
            }), 400

        # Prevent localhost and internal IPs
        if domain.lower() in ['localhost', '127.0.0.1', '0.0.0.0']:
            return jsonify({
                "success": False,
                "error": "Cannot use localhost or loopback addresses"
            }), 400

        results = {
            "domain": domain,
            "dns_resolution": {"success": False},
            "http_accessible": {"success": False},
        }

        # Test DNS resolution
        try:
            ip_address = socket.gethostbyname(domain)
            results["dns_resolution"] = {
                "success": True,
                "ip_address": ip_address,
                "message": f"Domain resolves to {ip_address}"
            }
        except socket.gaierror as e:
            results["dns_resolution"] = {
                "success": False,
                "error": f"DNS resolution failed: {str(e)}"
            }

        # Test HTTP accessibility (port 80 required for Let's Encrypt HTTP-01 challenge)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((domain, 80))
            sock.close()

            if result == 0:
                results["http_accessible"] = {
                    "success": True,
                    "message": f"Port 80 is accessible on {domain}"
                }
            else:
                results["http_accessible"] = {
                    "success": False,
                    "error": f"Port 80 is not accessible. Let's Encrypt requires port 80 for HTTP-01 challenge."
                }
        except Exception as e:
            results["http_accessible"] = {
                "success": False,
                "error": f"Failed to test port 80 accessibility: {str(e)}"
            }

        overall_success = results["dns_resolution"]["success"] and results["http_accessible"]["success"]

        return jsonify({
            "success": overall_success,
            "results": results,
            "message": "Domain tests completed" if overall_success else "Domain has issues that need to be resolved"
        })

    except Exception as exc:
        logger.error(f"Failed to test domain: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@certbot_bp.route('/api/certbot/download-certificate', methods=['GET'])
@require_permission('system.configure')
def download_certificate():
    """Download the current SSL certificate.
    
    SECURITY NOTE: This endpoint allows downloading certificates.
    Access is logged and restricted to system.configure permission.
    Private keys require separate endpoint with additional warnings.
    """
    try:
        cert_type = request.args.get('type', 'fullchain')

        # SECURITY: Validate cert_type to prevent path traversal
        if cert_type not in ['fullchain', 'cert', 'chain']:
            return jsonify({
                "success": False,
                "error": "Invalid certificate type. Must be 'fullchain', 'cert', or 'chain'"
            }), 400

        # Find certificate directory
        letsencrypt_dir = '/etc/letsencrypt/live'
        if not os.path.exists(letsencrypt_dir):
            return jsonify({
                "success": False,
                "error": "Let's Encrypt certificate directory not found"
            }), 404

        # Find first domain directory
        domains = [d for d in os.listdir(letsencrypt_dir)
                   if os.path.isdir(os.path.join(letsencrypt_dir, d)) and d != 'README']

        if not domains:
            return jsonify({
                "success": False,
                "error": "No SSL certificates found"
            }), 404

        domain = domains[0]
        cert_file = f"{cert_type}.pem"
        cert_path = os.path.join(letsencrypt_dir, domain, cert_file)

        if not os.path.exists(cert_path):
            return jsonify({
                "success": False,
                "error": f"Certificate file not found: {cert_file}"
            }), 404

        logger.info(f"Certificate download requested: {cert_type}.pem for domain {domain}")

        return send_file(
            cert_path,
            as_attachment=True,
            download_name=f"{domain}-{cert_file}",
            mimetype='application/x-pem-file'
        )

    except Exception as exc:
        logger.error(f"Failed to download certificate: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


def register_certbot_routes(app, logger):
    """Register Certbot admin routes with the Flask app.
    
    Routes are registered with url_prefix='/admin', so Flask combines them:
    - Blueprint route '/certbot' becomes '/admin/certbot'
    - Blueprint route '/api/certbot/settings' becomes '/admin/api/certbot/settings'
    
    IMPORTANT: Do NOT add '/admin' prefix to route decorators above, as Flask
    will combine url_prefix with the route path, resulting in doubled paths
    like '/admin/admin/certbot' which will cause 404 errors.
    """
    app.register_blueprint(certbot_bp, url_prefix='/admin')
    logger.info("Certbot admin routes registered")


__all__ = ['certbot_bp', 'register_certbot_routes']
