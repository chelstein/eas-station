"""
SSL Certificate utilities for EAS Station.
Provides functions to check and examine SSL certificates.
"""

import os
import subprocess
from datetime import datetime
from typing import Dict, Optional


def get_ssl_certificate_info() -> Dict:
    """
    Get information about the installed SSL certificate.
    
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
        'error': None
    }
    
    # Check for Let's Encrypt certificate
    letsencrypt_dir = '/etc/letsencrypt/live'
    if os.path.exists(letsencrypt_dir) and os.path.isdir(letsencrypt_dir):
        # Find the first domain directory
        try:
            domains = [d for d in os.listdir(letsencrypt_dir) 
                      if os.path.isdir(os.path.join(letsencrypt_dir, d)) and d != 'README']
            if domains:
                domain = domains[0]  # Use first domain
                cert_path = os.path.join(letsencrypt_dir, domain, 'fullchain.pem')
                
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
                            
                            # Parse issuer
                            for line in output.split('\n'):
                                if 'Issuer:' in line:
                                    if "Let's Encrypt" in line or 'ISRG' in line:
                                        cert_info['issuer'] = "Let's Encrypt"
                                    else:
                                        cert_info['issuer'] = line.split('Issuer:')[1].strip()
                            
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
