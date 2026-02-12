"""IPAWS alert enrichment utilities.

Extracts certificate details from IPAWS XML digital signatures and
saves embedded audio resources to disk for archival and playback.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import logging
import os
import re
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def extract_certificate_info(raw_xml: str) -> Optional[Dict[str, Any]]:
    """Extract X.509 certificate details from an IPAWS CAP alert's XML signature.

    Parses the capsig:Signature / ds:Signature element to pull out the
    embedded certificate and uses ``openssl x509`` (via subprocess) to
    decode subject, issuer, validity, serial number, and key details.
    Falls back to regex extraction from the XML if openssl is unavailable.

    Args:
        raw_xml: Raw XML string of the CAP alert.

    Returns:
        Dictionary of certificate details, or None if no certificate found.
        Keys: subject, issuer, serial_number, not_before, not_after,
              key_algorithm, key_size, signature_algorithm,
              xml_signature_method, xml_digest_method
    """
    if not raw_xml:
        return None

    # Extract certificate PEM from XML (handles both capsig: and ds: namespaces)
    cert_match = re.search(
        r'(?:capsig|ds):?X509Certificate>([^<]+)</(?:capsig|ds):?X509Certificate>',
        raw_xml,
    )
    if not cert_match:
        # Try without namespace prefix
        cert_match = re.search(r'X509Certificate>([^<]+)</.*?X509Certificate>', raw_xml)
    if not cert_match:
        return None

    cert_b64 = cert_match.group(1).strip()

    info: Dict[str, Any] = {}

    # Extract XML-level signature algorithms
    sig_method = re.search(r'SignatureMethod\s+Algorithm="([^"]+)"', raw_xml)
    if sig_method:
        info['xml_signature_method'] = sig_method.group(1)

    digest_method = re.search(r'DigestMethod\s+Algorithm="([^"]+)"', raw_xml)
    if digest_method:
        info['xml_digest_method'] = digest_method.group(1)

    # Extract subject name from XML (always available)
    subj_match = re.search(r'X509SubjectName>([^<]+)<', raw_xml)
    if subj_match:
        info['subject'] = subj_match.group(1).strip()

    # Try to decode full certificate details via openssl
    cert_details = _decode_certificate_openssl(cert_b64)
    if cert_details:
        info.update(cert_details)
    else:
        # Fallback: parse what we can from the subject name
        if info.get('subject'):
            info.setdefault('issuer', _extract_from_subject(info['subject'], 'issuer'))

    return info if info else None


def _decode_certificate_openssl(cert_b64: str) -> Optional[Dict[str, str]]:
    """Decode X.509 certificate using openssl CLI.

    Args:
        cert_b64: Base64-encoded DER certificate (no PEM headers).

    Returns:
        Dict with subject, issuer, serial_number, not_before, not_after,
        key_algorithm, key_size, signature_algorithm. None on failure.
    """
    import subprocess

    # Build PEM format
    pem_lines = ['-----BEGIN CERTIFICATE-----']
    for i in range(0, len(cert_b64), 64):
        pem_lines.append(cert_b64[i:i + 64])
    pem_lines.append('-----END CERTIFICATE-----')
    pem_text = '\n'.join(pem_lines) + '\n'

    try:
        result = subprocess.run(
            [
                'openssl', 'x509', '-noout',
                '-subject', '-issuer', '-serial',
                '-startdate', '-enddate',
                '-text',
            ],
            input=pem_text,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.debug('openssl x509 failed: %s', result.stderr.strip())
            return None

        output = result.stdout
        info: Dict[str, str] = {}

        # Parse structured fields from the -subject/-issuer/-serial output
        for line in output.splitlines():
            line = line.strip()
            if line.startswith('subject='):
                info['subject'] = line.split('=', 1)[1].strip()
            elif line.startswith('issuer='):
                info['issuer'] = line.split('=', 1)[1].strip()
            elif line.startswith('serial='):
                info['serial_number'] = line.split('=', 1)[1].strip()
            elif line.startswith('notBefore='):
                info['not_before'] = line.split('=', 1)[1].strip()
            elif line.startswith('notAfter='):
                info['not_after'] = line.split('=', 1)[1].strip()

        # Parse key algorithm and size from -text output
        key_match = re.search(r'Public Key Algorithm:\s*(\S+)', output)
        if key_match:
            info['key_algorithm'] = key_match.group(1)

        key_size_match = re.search(r'Public-Key:\s*\((\d+)\s*bit\)', output)
        if key_size_match:
            info['key_size'] = key_size_match.group(1)

        sig_alg_match = re.search(r'Signature Algorithm:\s*(\S+)', output)
        if sig_alg_match:
            info['signature_algorithm'] = sig_alg_match.group(1)

        return info if info else None

    except FileNotFoundError:
        logger.debug('openssl not found on PATH')
        return None
    except subprocess.TimeoutExpired:
        logger.warning('openssl x509 timed out')
        return None
    except Exception as exc:
        logger.debug('Certificate decode failed: %s', exc)
        return None


def _extract_from_subject(subject: str, field: str) -> Optional[str]:
    """Placeholder — cannot derive issuer from subject alone."""
    return None


def save_ipaws_audio(
    raw_json: Dict[str, Any],
    identifier: str,
    output_dir: str,
) -> Optional[str]:
    """Save embedded IPAWS audio resource to disk.

    Looks for audio resources in the alert's properties.resources list,
    decodes the base64 derefUri content, and writes it to disk.
    Validates size limits to prevent DoS attacks.

    Args:
        raw_json: The full alert raw_json dict (contains properties.resources).
        identifier: Alert identifier for the filename.
        output_dir: Directory to write the audio file into.

    Returns:
        Relative filename of the saved audio, or None if no audio found.
    """
    properties = raw_json.get('properties', {})
    resources = properties.get('resources', [])
    if not resources:
        return None

    # Default max size: 10 MB
    try:
        max_bytes = int(os.getenv('IPAWS_AUDIO_MAX_BYTES', '10485760'))
    except (ValueError, TypeError):
        logger.warning('Invalid IPAWS_AUDIO_MAX_BYTES value, using default 10 MB')
        max_bytes = 10485760

    for resource in resources:
        mime_type = (resource.get('mimeType') or '').lower()
        resource_desc = (resource.get('resourceDesc') or '').lower()
        deref_uri = resource.get('derefUri', '')

        is_audio = 'audio' in mime_type or 'eas broadcast' in resource_desc
        if not (is_audio and deref_uri):
            continue

        # Check size hint if available
        size_hint = resource.get('size')
        if size_hint is not None:
            try:
                if int(size_hint) > max_bytes:
                    logger.warning(
                        'Skipping IPAWS audio for %s: size hint %s exceeds %d bytes',
                        identifier, size_hint, max_bytes,
                    )
                    continue
            except (TypeError, ValueError):
                pass

        # Estimate decoded size (base64 expands by ~4/3, so decoded is ~3/4 of encoded)
        estimated_size = (len(deref_uri) * 3) // 4
        if estimated_size > max_bytes:
            logger.warning(
                'Skipping IPAWS audio for %s: estimated size %d exceeds %d bytes',
                identifier, estimated_size, max_bytes,
            )
            continue

        # Determine file extension from MIME type
        if 'mp3' in mime_type or 'mpeg' in mime_type:
            ext = '.mp3'
        elif 'wav' in mime_type:
            ext = '.wav'
        elif 'ogg' in mime_type:
            ext = '.ogg'
        else:
            ext = '.mp3'  # IPAWS typically uses MP3

        try:
            audio_bytes = base64.b64decode(deref_uri, validate=True)
        except (binascii.Error, ValueError) as exc:
            logger.warning('Failed to decode IPAWS audio for %s: %s', identifier, exc)
            continue

        # Verify actual decoded size
        if len(audio_bytes) > max_bytes:
            logger.warning(
                'Skipping IPAWS audio for %s: decoded size %d exceeds %d bytes',
                identifier, len(audio_bytes), max_bytes,
            )
            continue

        # Sanitize identifier for filename
        safe_id = re.sub(r'[^\w\-.]', '_', identifier)
        filename = f'{safe_id}_ipaws_original{ext}'
        filepath = os.path.join(output_dir, filename)

        try:
            os.makedirs(output_dir, exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(audio_bytes)
            logger.info(
                'Saved IPAWS audio for %s: %s (%d bytes)',
                identifier, filename, len(audio_bytes),
            )
            return filename
        except OSError as exc:
            logger.error('Failed to write IPAWS audio file %s: %s', filepath, exc)
            return None

    return None
