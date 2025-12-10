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

from flask import Blueprint, render_template, jsonify, request
import subprocess
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

logs_bp = Blueprint('logs', __name__)


def get_systemd_logs(service: str, lines: int = 100, priority: str = None, since: str = None) -> Dict[str, Any]:
    """
    Fetch logs from systemd journalctl for a specific service.
    
    Args:
        service: Service name (e.g., 'eas-station-web.service')
        lines: Number of log lines to retrieve
        priority: Log priority filter (err, warning, info, debug)
        since: Time filter (e.g., 'today', '1 hour ago', '2025-12-10')
    
    Returns:
        Dictionary with logs and metadata
    """
    try:
        cmd = ['journalctl', '-u', service, '-n', str(lines), '--no-pager', '--output=json']
        
        if priority:
            cmd.extend(['-p', priority])
        
        if since:
            cmd.extend(['--since', since])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            import json
            logs = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        log_entry = json.loads(line)
                        logs.append({
                            'timestamp': log_entry.get('__REALTIME_TIMESTAMP', ''),
                            'priority': log_entry.get('PRIORITY', '6'),
                            'message': log_entry.get('MESSAGE', ''),
                            'unit': log_entry.get('_SYSTEMD_UNIT', service)
                        })
                    except json.JSONDecodeError:
                        continue
            
            return {
                'success': True,
                'service': service,
                'logs': logs,
                'count': len(logs)
            }
        else:
            return {
                'success': False,
                'error': result.stderr or 'Failed to fetch logs',
                'service': service
            }
    
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Timeout fetching logs',
            'service': service
        }
    except Exception as e:
        logger.error(f"Error fetching logs for {service}: {e}")
        return {
            'success': False,
            'error': str(e),
            'service': service
        }


@logs_bp.route('/system-logs')
def system_logs_page():
    """Render the systemd logs viewer page."""
    services = [
        'eas-station-web.service',
        'eas-station-sdr.service',
        'eas-station-audio.service',
        'eas-station-eas.service',
        'eas-station-hardware.service',
        'eas-station-noaa-poller.service',
        'eas-station-ipaws-poller.service',
        'nginx.service',
        'postgresql.service',
        'redis-server.service'
    ]
    return render_template('system_logs.html', services=services)


@logs_bp.route('/api/logs/<service>')
def get_logs(service: str):
    """
    API endpoint to fetch logs for a specific service.
    
    Query parameters:
        - lines: Number of lines (default: 100, max: 1000)
        - priority: Log priority (err, warning, info, debug)
        - since: Time filter (today, 1 hour ago, etc.)
    """
    # Validate service name to prevent command injection
    allowed_services = [
        'eas-station-web.service',
        'eas-station-sdr.service',
        'eas-station-audio.service',
        'eas-station-eas.service',
        'eas-station-hardware.service',
        'eas-station-noaa-poller.service',
        'eas-station-ipaws-poller.service',
        'nginx.service',
        'postgresql.service',
        'redis-server.service'
    ]
    
    if service not in allowed_services:
        return jsonify({'error': 'Invalid service name'}), 400
    
    lines = min(int(request.args.get('lines', 100)), 1000)
    priority = request.args.get('priority')
    since = request.args.get('since')
    
    # Validate priority
    if priority and priority not in ['emerg', 'alert', 'crit', 'err', 'warning', 'notice', 'info', 'debug']:
        return jsonify({'error': 'Invalid priority'}), 400
    
    result = get_systemd_logs(service, lines, priority, since)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500


@logs_bp.route('/api/logs/all')
def get_all_logs():
    """
    Fetch logs from all EAS Station services.
    
    Query parameters:
        - lines: Number of lines per service (default: 50, max: 500)
        - priority: Log priority filter
        - since: Time filter
    """
    lines = min(int(request.args.get('lines', 50)), 500)
    priority = request.args.get('priority')
    since = request.args.get('since')
    
    services = [
        'eas-station-web.service',
        'eas-station-sdr.service',
        'eas-station-audio.service',
        'eas-station-eas.service',
        'eas-station-hardware.service',
        'eas-station-noaa-poller.service',
        'eas-station-ipaws-poller.service'
    ]
    
    results = {}
    for service in services:
        results[service] = get_systemd_logs(service, lines, priority, since)
    
    return jsonify(results)


def register(app):
    """Register logs blueprint with the Flask app."""
    app.register_blueprint(logs_bp)
    logger.info("Logs routes registered")
