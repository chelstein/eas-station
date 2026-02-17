"""
SSL Certificate utilities for EAS Station.
Provides functions to check and examine SSL certificates.
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Match the certbot data directory used by the web app and systemd service
_CERTBOT_DATA_DIR = Path(__file__).parent.parent / 'certbot_data'


def get_certbot_config() -> Dict:
    """
    Get Certbot configuration from database with fallback to environment variables.
    
    Returns:
        dict: Certbot configuration settings
    """
    config = {
        'enabled': False,
        'domain_name': '',
        'email': '',
        'staging': False,
        'auto_renew_enabled': True,
        'renew_days_before_expiry': 30,
    }
    
    try:
        # Try to import database settings
        from app_core.certbot_settings import get_certbot_settings
        settings = get_certbot_settings()
        config.update(settings.to_dict())
    except Exception:
        # Fallback to environment variables
        config['enabled'] = os.getenv('CERTBOT_ENABLED', 'false').lower() in ('true', '1', 'yes', 'on')
        config['domain_name'] = os.getenv('DOMAIN_NAME', '')
        config['email'] = os.getenv('SSL_EMAIL', '')
        config['staging'] = os.getenv('CERTBOT_STAGING', '0') == '1'
    
    return config


def get_ssl_certificate_info() -> Dict:
    """
    Get information about the installed SSL certificate.
    
    Checks the configured domain from certbot settings and reports on the
    most recently created certificate for that domain.

    Returns:
        dict: Certificate information including type, validity, domain, issuer, etc.
    """
    cert_info = {
        'installed': False,
        'type': 'none',
        'valid': False,
        'domain': None,
        'issuer': None,
        'valid_from': None,
        'valid_until': None,
        'days_remaining': None,
        'self_signed': False,
        'is_staging': False,  # True if cert was issued by Let's Encrypt staging server
        'error': None,
        'needs_installation': False  # True if cert exists but isn't installed
    }
    
    # Get configured domain from certbot settings
    config = get_certbot_config()
    configured_domain = config.get('domain_name', '')

    # Check for Let's Encrypt certificate in multiple locations
    # First check the standard location, then check custom certbot directory
    letsencrypt_dirs = [
        '/etc/letsencrypt/live',  # Standard Let's Encrypt location
        str(_CERTBOT_DATA_DIR / 'config' / 'live'),  # Custom certbot config location
    ]

    letsencrypt_dir = None
    for check_dir in letsencrypt_dirs:
        if os.path.exists(check_dir) and os.path.isdir(check_dir):
            # Check if there are any domain directories
            try:
                domains = [d for d in os.listdir(check_dir)
                          if os.path.isdir(os.path.join(check_dir, d)) and d != 'README']
                if domains:
                    letsencrypt_dir = check_dir
                    # If found in custom location but not in standard, mark as needing installation
                    if check_dir != '/etc/letsencrypt/live':
                        cert_info['needs_installation'] = True
                    break
            except Exception:
                continue

    if letsencrypt_dir:
        # Find domain directories matching configured domain
        # Certbot may create domain-0001, domain-0002, etc. when obtaining
        # multiple certs for the same domain (e.g., switching staging to production)
        try:
            all_domains = [d for d in os.listdir(letsencrypt_dir) 
                          if os.path.isdir(os.path.join(letsencrypt_dir, d)) and d != 'README']
            
            # If a specific domain is configured, find matching directories
            matching_domains = []
            if configured_domain:
                for d in all_domains:
                    # Match exact domain or domain-#### pattern (certbot numbered variants)
                    # Example: example.com or example.com-0001
                    # Do NOT match: example.com.test or example.com-backup
                    if d == configured_domain:
                        matching_domains.append(d)
                    elif d.startswith(f"{configured_domain}-"):
                        # Verify the suffix is a number (certbot style)
                        suffix = d[len(configured_domain)+1:]  # Everything after "domain-"
                        if suffix.isdigit():
                            matching_domains.append(d)
            
            # If no matches or no configured domain, use all domains
            if not matching_domains:
                matching_domains = all_domains
            
            if matching_domains:
                # Use the most recently modified domain directory (latest certificate)
                if len(matching_domains) == 1:
                    # Optimization: Skip stat() calls if only one directory
                    domain = matching_domains[0]
                    cert_path = os.path.join(letsencrypt_dir, domain, 'fullchain.pem')
                else:
                    # Cache modification times to avoid repeated syscalls during sort
                    domain_paths = [
                        (d, os.path.join(letsencrypt_dir, d), os.path.getmtime(os.path.join(letsencrypt_dir, d)))
                        for d in matching_domains
                    ]
                    # Sort by modification time, most recent first
                    domain_paths.sort(key=lambda x: x[2], reverse=True)
                    domain = domain_paths[0][0]  # Use most recent domain
                    cert_path = domain_paths[0][1]  # Use cached path
                
                if os.path.exists(cert_path):
                    cert_info['installed'] = True
                    cert_info['type'] = 'letsencrypt'
                    cert_info['domain'] = domain
                    
                    # Get certificate details using openssl
                    try:
                        result = subprocess.run(
                            ['openssl', 'x509', '-in', cert_path, '-noout', '-text'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        
                        if result.returncode == 0:
                            output = result.stdout
                            
                            # Parse issuer - check for staging before production
                            for line in output.split('\n'):
                                if 'Issuer:' in line:
                                    issuer_text = line.split('Issuer:')[1].strip()
                                    # Detect Let's Encrypt staging certificates
                                    # Staging issuers contain "(STAGING)" e.g.:
                                    #   O = (STAGING) Let's Encrypt, CN = (STAGING) Artificial Apricot R3
                                    # Or older format with "Fake LE" / "Fake Let's Encrypt"
                                    if '(STAGING)' in issuer_text or 'Fake LE' in issuer_text or 'Fake Let\'s Encrypt' in issuer_text:
                                        cert_info['issuer'] = "Let's Encrypt (Staging)"
                                        cert_info['is_staging'] = True
                                    elif "Let's Encrypt" in issuer_text or 'ISRG' in issuer_text:
                                        cert_info['issuer'] = "Let's Encrypt"
                                    else:
                                        cert_info['issuer'] = issuer_text
                            
                            # Get expiration date
                            result = subprocess.run(
                                ['openssl', 'x509', '-in', cert_path, '-noout', '-enddate'],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            
                            if result.returncode == 0:
                                # Parse: notAfter=Dec 12 18:00:00 2025 GMT
                                date_str = result.stdout.strip().split('=')[1]
                                expiry_date = datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
                                cert_info['valid_until'] = expiry_date.isoformat()
                                
                                # Calculate days remaining
                                days_left = (expiry_date - datetime.now()).days
                                cert_info['days_remaining'] = days_left
                                cert_info['valid'] = days_left > 0
                            
                            # Get start date
                            result = subprocess.run(
                                ['openssl', 'x509', '-in', cert_path, '-noout', '-startdate'],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            
                            if result.returncode == 0:
                                date_str = result.stdout.strip().split('=')[1]
                                start_date = datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
                                cert_info['valid_from'] = start_date.isoformat()
                                
                    except Exception as e:
                        cert_info['error'] = f"Failed to parse certificate: {str(e)}"
                        
        except Exception as e:
            cert_info['error'] = f"Failed to read Let's Encrypt directory: {str(e)}"
    
    # Check for self-signed certificate
    if not cert_info['installed']:
        self_signed_cert = '/etc/ssl/certs/eas-station-selfsigned.crt'
        if os.path.exists(self_signed_cert):
            cert_info['installed'] = True
            cert_info['type'] = 'self-signed'
            cert_info['self_signed'] = True
            
            try:
                # Get certificate details
                result = subprocess.run(
                    ['openssl', 'x509', '-in', self_signed_cert, '-noout', '-subject', '-issuer', '-dates'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    output = result.stdout
                    
                    # Parse subject for domain
                    for line in output.split('\n'):
                        if 'subject=' in line or 'Subject:' in line:
                            if 'CN=' in line or 'CN =' in line:
                                # Extract CN (Common Name)
                                cn_part = line.split('CN')[1].strip()
                                if '=' in cn_part:
                                    cert_info['domain'] = cn_part.split('=')[1].split(',')[0].strip()
                        elif 'issuer=' in line or 'Issuer:' in line:
                            cert_info['issuer'] = 'Self-Signed'
                        elif 'notAfter=' in line:
                            date_str = line.split('=')[1].strip()
                            expiry_date = datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
                            cert_info['valid_until'] = expiry_date.isoformat()
                            days_left = (expiry_date - datetime.now()).days
                            cert_info['days_remaining'] = days_left
                            cert_info['valid'] = days_left > 0
                        elif 'notBefore=' in line:
                            date_str = line.split('=')[1].strip()
                            start_date = datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
                            cert_info['valid_from'] = start_date.isoformat()
                    
            except Exception as e:
                cert_info['error'] = f"Failed to parse self-signed certificate: {str(e)}"
    
    return cert_info


def get_certificate_renewal_status() -> Dict:
    """
    Check if certbot renewal timer is active and when it last ran.
    
    Returns:
        dict: Renewal status information
    """
    renewal_status = {
        'timer_enabled': False,
        'timer_active': False,
        'next_run': None,
        'last_run': None,
        'error': None
    }
    
    try:
        # Check if timer is enabled
        result = subprocess.run(
            ['systemctl', 'is-enabled', 'certbot.timer'],
            capture_output=True,
            text=True,
            timeout=5
        )
        renewal_status['timer_enabled'] = (result.returncode == 0)
        
        # Check if timer is active
        result = subprocess.run(
            ['systemctl', 'is-active', 'certbot.timer'],
            capture_output=True,
            text=True,
            timeout=5
        )
        renewal_status['timer_active'] = (result.stdout.strip() == 'active')
        
        # Get timer info
        result = subprocess.run(
            ['systemctl', 'status', 'certbot.timer'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            output = result.stdout
            # Parse for next trigger time
            for line in output.split('\n'):
                if 'Trigger:' in line:
                    # Extract trigger time
                    renewal_status['next_run'] = line.split('Trigger:')[1].strip()
                    
    except Exception as e:
        renewal_status['error'] = f"Failed to check renewal status: {str(e)}"
    
    return renewal_status
