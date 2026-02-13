"""IPAWS alert enrichment utilities.

Extracts certificate details from IPAWS XML digital signatures,
verifies the XML digital signature, checks certificate validity,
and saves embedded audio resources to disk for archival and playback.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def extract_certificate_info(raw_xml: str) -> Optional[Dict[str, Any]]:
    """Extract X.509 certificate details from an IPAWS CAP alert's XML signature.

    Parses the capsig:Signature / ds:Signature element to pull out the
    embedded certificate and uses ``openssl x509`` (via subprocess) to
    decode subject, issuer, validity, serial number, and key details.
    Falls back to regex extraction from the XML if openssl is unavailable.

    Also checks certificate temporal validity and attempts to verify the
    XML digital signature against the embedded public key.

    Args:
        raw_xml: Raw XML string of the CAP alert.

    Returns:
        Dictionary of certificate details, or None if no certificate found.
        Keys: subject, issuer, serial_number, not_before, not_after,
              key_algorithm, key_size, signature_algorithm,
              xml_signature_method, xml_digest_method,
              is_cert_valid, cert_validity_status,
              signature_verified, signature_status
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

    # --- Certificate validity check ---
    validity = _check_certificate_validity(info)
    info.update(validity)

    # --- XML digital signature verification ---
    sig_result = _verify_xml_signature(raw_xml, cert_b64)
    info.update(sig_result)

    return info if info else None


def _check_certificate_validity(cert_info: Dict[str, Any]) -> Dict[str, Any]:
    """Check whether the certificate is currently valid based on not_before/not_after.

    Returns:
        Dict with is_cert_valid (bool or None) and cert_validity_status (str).
    """
    result: Dict[str, Any] = {
        'is_cert_valid': None,
        'cert_validity_status': 'Unknown',
    }

    not_before_str = cert_info.get('not_before', '')
    not_after_str = cert_info.get('not_after', '')

    if not not_before_str or not not_after_str:
        return result

    not_before = _parse_openssl_date(not_before_str)
    not_after = _parse_openssl_date(not_after_str)

    if not_before is None or not_after is None:
        result['cert_validity_status'] = 'Could not parse dates'
        return result

    now = datetime.now(timezone.utc)

    if now < not_before:
        result['is_cert_valid'] = False
        result['cert_validity_status'] = 'Not yet valid'
    elif now > not_after:
        result['is_cert_valid'] = False
        result['cert_validity_status'] = 'Expired'
    else:
        result['is_cert_valid'] = True
        days_remaining = (not_after - now).days
        if days_remaining < 30:
            result['cert_validity_status'] = f'Valid (expires in {days_remaining} days)'
        else:
            result['cert_validity_status'] = 'Valid'

    return result


def _parse_openssl_date(date_str: str) -> Optional[datetime]:
    """Parse an openssl date string like 'Jan 14 09:48:00 2026 GMT'."""
    formats = [
        '%b %d %H:%M:%S %Y %Z',    # "Jan 14 09:48:00 2026 GMT"
        '%b  %d %H:%M:%S %Y %Z',   # "Jan  6 09:48:00 2026 GMT" (double space)
        '%Y-%m-%dT%H:%M:%S%z',     # ISO format
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _verify_xml_signature(raw_xml: str, cert_b64: str) -> Dict[str, Any]:
    """Verify the XML digital signature using the embedded certificate.

    Attempts verification in order:
    1. ``cryptography`` Python library (fast, in-process)
    2. ``openssl`` CLI (fallback)
    3. Reports presence of signature elements if verification unavailable

    Returns:
        Dict with signature_verified (bool or None) and signature_status (str).
    """
    result: Dict[str, Any] = {
        'signature_verified': None,
        'signature_status': 'Not checked',
    }

    # Extract SignatureValue from XML
    sig_value_match = re.search(
        r'SignatureValue[^>]*>([^<]+)</.*?SignatureValue>',
        raw_xml,
        re.DOTALL,
    )
    if not sig_value_match:
        result['signature_status'] = 'No SignatureValue found in XML'
        return result

    # Extract DigestValue from XML
    digest_value_match = re.search(
        r'DigestValue[^>]*>([^<]+)</.*?DigestValue>',
        raw_xml,
        re.DOTALL,
    )
    if not digest_value_match:
        result['signature_status'] = 'No DigestValue found in XML'
        return result

    # Extract SignedInfo block for signature verification
    signed_info_match = re.search(
        r'(<(?:\w+:)?SignedInfo[\s>].*?</(?:\w+:)?SignedInfo>)',
        raw_xml,
        re.DOTALL,
    )
    if not signed_info_match:
        result['signature_status'] = 'No SignedInfo block found'
        return result

    # Try verification via cryptography library first
    crypto_result = _verify_with_cryptography(cert_b64, sig_value_match, signed_info_match, raw_xml)
    if crypto_result is not None:
        return crypto_result

    # Fall back to openssl CLI verification
    openssl_result = _verify_with_openssl(cert_b64, sig_value_match, signed_info_match, raw_xml)
    if openssl_result is not None:
        return openssl_result

    # If all else fails, note the signature was present but unverifiable
    result['signature_status'] = 'Signature present but verification libraries unavailable'
    return result


def _verify_with_cryptography(cert_b64, sig_value_match, signed_info_match, raw_xml):
    """Try signature verification using the cryptography library."""
    try:
        from cryptography.x509 import load_der_x509_certificate
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec
    except BaseException:
        return None

    result: Dict[str, Any] = {
        'signature_verified': None,
        'signature_status': 'Not checked',
    }

    try:
        cert_der = base64.b64decode(cert_b64)
        cert = load_der_x509_certificate(cert_der)
        public_key = cert.public_key()

        sig_b64 = sig_value_match.group(1).strip()
        sig_bytes = base64.b64decode(sig_b64)

        sig_method_match = re.search(r'SignatureMethod\s+Algorithm="([^"]+)"', raw_xml)
        hash_algo = _resolve_hash_algorithm(
            sig_method_match.group(1) if sig_method_match else ''
        )

        signed_info_bytes = signed_info_match.group(1).encode('utf-8')

        if isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(sig_bytes, signed_info_bytes, padding.PKCS1v15(), hash_algo)
            result['signature_verified'] = True
            result['signature_status'] = 'Valid (RSA signature verified)'
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(sig_bytes, signed_info_bytes, ec.ECDSA(hash_algo))
            result['signature_verified'] = True
            result['signature_status'] = 'Valid (ECDSA signature verified)'
        else:
            result['signature_status'] = f'Unsupported key type: {type(public_key).__name__}'

    except (binascii.Error, ValueError) as exc:
        result['signature_verified'] = False
        result['signature_status'] = f'Base64 decode error: {exc}'
    except Exception as exc:
        exc_name = type(exc).__name__
        result['signature_verified'] = False
        result['signature_status'] = 'Could not verify (C14N canonicalization required)'
        logger.debug('XML signature verification (cryptography) failed: %s: %s', exc_name, exc)

    return result


def _verify_with_openssl(cert_b64, sig_value_match, signed_info_match, raw_xml):
    """Try signature verification using the openssl CLI.

    Uses ``openssl dgst -verify`` to check the signature on the SignedInfo
    block against the public key extracted from the certificate.
    """
    import subprocess
    import tempfile

    result: Dict[str, Any] = {
        'signature_verified': None,
        'signature_status': 'Not checked',
    }

    # Build PEM certificate
    pem_lines = ['-----BEGIN CERTIFICATE-----']
    for i in range(0, len(cert_b64), 64):
        pem_lines.append(cert_b64[i:i + 64])
    pem_lines.append('-----END CERTIFICATE-----')
    pem_text = '\n'.join(pem_lines) + '\n'

    # Determine hash algorithm
    sig_method_match = re.search(r'SignatureMethod\s+Algorithm="([^"]+)"', raw_xml)
    hash_name = _resolve_hash_name(sig_method_match.group(1) if sig_method_match else '')

    sig_b64 = sig_value_match.group(1).strip()
    signed_info_bytes = signed_info_match.group(1).encode('utf-8')

    try:
        sig_bytes = base64.b64decode(sig_b64)
    except (binascii.Error, ValueError) as exc:
        result['signature_verified'] = False
        result['signature_status'] = f'Base64 decode error: {exc}'
        return result

    try:
        with tempfile.NamedTemporaryFile(suffix='.pem', delete=False, mode='w') as cert_f:
            cert_f.write(pem_text)
            cert_path = cert_f.name

        with tempfile.NamedTemporaryFile(suffix='.pub', delete=False, mode='w') as pub_f:
            pub_path = pub_f.name

        with tempfile.NamedTemporaryFile(suffix='.sig', delete=False, mode='wb') as sig_f:
            sig_f.write(sig_bytes)
            sig_path = sig_f.name

        with tempfile.NamedTemporaryFile(suffix='.dat', delete=False, mode='wb') as data_f:
            data_f.write(signed_info_bytes)
            data_path = data_f.name

        # Extract public key from certificate
        extract_result = subprocess.run(
            ['openssl', 'x509', '-pubkey', '-noout', '-in', cert_path],
            capture_output=True, text=True, timeout=10,
        )
        if extract_result.returncode != 0:
            result['signature_status'] = 'Could not extract public key'
            return result

        with open(pub_path, 'w') as pub_f:
            pub_f.write(extract_result.stdout)

        # Verify signature
        verify_result = subprocess.run(
            ['openssl', 'dgst', f'-{hash_name}', '-verify', pub_path,
             '-signature', sig_path, data_path],
            capture_output=True, text=True, timeout=10,
        )

        if 'Verified OK' in verify_result.stdout:
            result['signature_verified'] = True
            result['signature_status'] = 'Valid (verified via openssl)'
        else:
            # Signature mismatch — likely due to missing XML C14N canonicalization.
            # Without lxml, we verify against the raw SignedInfo bytes which may
            # differ from the canonical form the signature was computed over.
            result['signature_verified'] = False
            result['signature_status'] = 'Could not verify (C14N canonicalization required)'

    except FileNotFoundError:
        logger.debug('openssl not found for signature verification')
        return None
    except subprocess.TimeoutExpired:
        result['signature_status'] = 'Verification timed out'
    except Exception as exc:
        result['signature_verified'] = False
        result['signature_status'] = f'Verification error ({type(exc).__name__})'
        logger.debug('openssl signature verification failed: %s', exc)
    finally:
        for path in [cert_path, pub_path, sig_path, data_path]:
            try:
                os.unlink(path)
            except OSError:
                pass

    return result


def _resolve_hash_algorithm(algorithm_uri: str):
    """Map an XML Signature algorithm URI to a cryptography hash instance."""
    from cryptography.hazmat.primitives import hashes

    uri = algorithm_uri.lower()
    if 'sha512' in uri:
        return hashes.SHA512()
    if 'sha384' in uri:
        return hashes.SHA384()
    if 'sha256' in uri:
        return hashes.SHA256()
    if 'sha1' in uri:
        return hashes.SHA1()
    return hashes.SHA256()


def _resolve_hash_name(algorithm_uri: str) -> str:
    """Map an XML Signature algorithm URI to an openssl digest name."""
    uri = algorithm_uri.lower()
    if 'sha512' in uri:
        return 'sha512'
    if 'sha384' in uri:
        return 'sha384'
    if 'sha256' in uri:
        return 'sha256'
    if 'sha1' in uri:
        return 'sha1'
    return 'sha256'


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
