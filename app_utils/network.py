"""
EAS Station - Emergency Alert System
Copyright (c) 2025 Timothy Kramer (KR8MER)

Network Management Utilities

Provides network configuration functions using NetworkManager (nmcli):
- WiFi interface detection
- Hostname management
- Error message enhancement for user-friendly feedback
"""

import glob
import logging
import os
import re
import shutil
import subprocess
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

# Hostname validation pattern (RFC 1123)
HOSTNAME_PATTERN = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$')

# Cached nmcli availability
_nmcli_available: Optional[bool] = None


def run_command(
    cmd: List[str],
    check: bool = True,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Execute a shell command safely and return the result.

    Args:
        cmd: Command as list of strings (REQUIRED for security)
        check: If True, include error info for non-zero exit codes
        timeout: Command timeout in seconds

    Returns:
        dict with success, stdout, stderr, returncode, and optional error
    """
    try:
        result = subprocess.run(
            cmd,
            shell=False,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout
        )

        success = result.returncode == 0
        response = {
            'success': success,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'returncode': result.returncode
        }

        if not success and check:
            response['error'] = result.stderr.strip() or f'Command failed with code {result.returncode}'

        return response

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': f'Command timed out after {timeout} seconds',
            'stdout': '',
            'stderr': '',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'stdout': '',
            'stderr': '',
            'returncode': -1
        }


def check_nmcli_available() -> bool:
    """
    Check if nmcli (NetworkManager CLI) is available.

    Uses cached result after first check for performance.

    Returns:
        True if nmcli is available, False otherwise
    """
    global _nmcli_available

    if _nmcli_available is not None:
        return _nmcli_available

    _nmcli_available = shutil.which('nmcli') is not None
    return _nmcli_available


def get_wifi_interface() -> Optional[str]:
    """
    Detect the WiFi interface name (e.g., wlan0, wlp3s0).

    Returns:
        WiFi interface name if found, None otherwise
    """
    try:
        result = run_command(
            ['nmcli', '-t', '-f', 'DEVICE,TYPE', 'device'],
            check=False,
            timeout=10
        )
        if result['success'] and result['stdout']:
            for line in result['stdout'].split('\n'):
                if line.strip():
                    parts = line.split(':')
                    if len(parts) >= 2 and parts[1] == 'wifi':
                        return parts[0]

        # Fallback: Check common WiFi interface names
        for pattern in ['/sys/class/net/wlan*', '/sys/class/net/wlp*']:
            interfaces = glob.glob(pattern)
            if interfaces:
                return os.path.basename(interfaces[0])

        return None
    except Exception as e:
        logger.warning(f"Error detecting WiFi interface: {e}")
        return None


def enhance_error_message(error_msg: str, context: str = '') -> Dict[str, str]:
    """
    Enhance error messages with helpful troubleshooting hints.

    Args:
        error_msg: Raw error message from nmcli or system
        context: Context of the operation (e.g., 'scan', 'connect', 'configure')

    Returns:
        dict with 'message', 'hint', and 'technical' keys
    """
    error_lower = str(error_msg).lower()

    error_patterns = {
        'not found': {
            'message': 'Interface or network not found',
            'hint': 'Check that your WiFi/Ethernet adapter is properly connected and enabled.'
        },
        'no such device': {
            'message': 'Network device not available',
            'hint': 'Ensure your network hardware is connected and drivers are installed.'
        },
        'no wifi interface': {
            'message': 'No WiFi adapter detected',
            'hint': 'Check if your WiFi adapter is connected, powered on, and recognized by the system.'
        },
        'connection activation failed': {
            'message': 'Failed to connect to network',
            'hint': 'Verify the password is correct and the network is in range. Try forgetting and reconnecting.'
        },
        'secrets were required': {
            'message': 'Password required',
            'hint': 'This network requires a password. Please enter the correct WiFi password.'
        },
        'timeout': {
            'message': 'Operation timed out',
            'hint': 'The network operation took too long. Check network signal strength and try again.'
        },
        'no networks in range': {
            'message': 'No networks detected',
            'hint': 'Move closer to a WiFi access point or check if WiFi is enabled on the router.'
        },
        'already exists': {
            'message': 'Connection already configured',
            'hint': 'This network is already saved. Try activating the existing connection instead.'
        },
        'permission denied': {
            'message': 'Permission denied',
            'hint': 'Network configuration requires administrator privileges. Contact your system administrator.'
        },
        'invalid ip': {
            'message': 'Invalid IP address',
            'hint': 'Enter a valid IP address in format: 192.168.1.100'
        },
        'invalid gateway': {
            'message': 'Invalid gateway address',
            'hint': 'Gateway must be in the same subnet as the IP address.'
        },
    }

    for pattern, enhanced in error_patterns.items():
        if pattern in error_lower:
            return {
                'message': enhanced['message'],
                'hint': enhanced['hint'],
                'technical': error_msg
            }

    context_hints = {
        'scan': 'Make sure WiFi is enabled and your adapter is working properly.',
        'connect': 'Check the network password and signal strength.',
        'configure': 'Verify the IP settings are valid for your network.',
        'dns': 'Enter valid DNS server IP addresses (e.g., 8.8.8.8).',
        'hostname': 'Hostname must contain only letters, numbers, and hyphens.',
    }

    return {
        'message': str(error_msg),
        'hint': context_hints.get(context, 'Try refreshing and attempting the operation again.'),
        'technical': error_msg
    }


def get_hostname() -> Dict[str, Any]:
    """
    Get the current system hostname.

    Returns:
        dict with success status and hostname or error message
    """
    try:
        result = run_command(['hostname'], check=False, timeout=5)
        if result['success'] and result['stdout']:
            return {
                'success': True,
                'hostname': result['stdout'].strip()
            }
        else:
            return {
                'success': False,
                'error': 'Failed to get hostname'
            }
    except Exception as e:
        logger.error(f"Error getting hostname: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def set_hostname(new_hostname: str) -> Dict[str, Any]:
    """
    Set the system hostname using hostnamectl.

    Validates hostname format according to RFC 1123 before setting.

    Args:
        new_hostname: New hostname to set

    Returns:
        dict with success status and message or error
    """
    try:
        if not new_hostname:
            enhanced = enhance_error_message('Hostname cannot be empty', 'hostname')
            return {
                'success': False,
                'error': enhanced['message'],
                'hint': enhanced['hint']
            }

        if len(new_hostname) > 63:
            enhanced = enhance_error_message('Hostname too long (max 63 characters)', 'hostname')
            return {
                'success': False,
                'error': enhanced['message'],
                'hint': enhanced['hint']
            }

        if not HOSTNAME_PATTERN.match(new_hostname):
            enhanced = enhance_error_message('Invalid hostname format', 'hostname')
            return {
                'success': False,
                'error': enhanced['message'],
                'hint': 'Hostname must contain only letters, numbers, and hyphens. Cannot start or end with hyphen.'
            }

        result = run_command(['hostnamectl', 'set-hostname', new_hostname], check=False, timeout=10)

        if result['success']:
            logger.info(f"Hostname changed to: {new_hostname}")
            return {
                'success': True,
                'message': f'Hostname set to {new_hostname}',
                'hostname': new_hostname
            }
        else:
            error_msg = result.get('stderr', result.get('error', 'Failed to set hostname'))
            enhanced = enhance_error_message(error_msg, 'hostname')
            logger.error(f"Failed to set hostname: {error_msg}")
            return {
                'success': False,
                'error': enhanced['message'],
                'hint': enhanced.get('hint', ''),
                'technical': error_msg
            }

    except Exception as e:
        logger.error(f"Error setting hostname: {e}", exc_info=True)
        enhanced = enhance_error_message(str(e), 'hostname')
        return {
            'success': False,
            'error': enhanced['message'],
            'hint': enhanced.get('hint', '')
        }
