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

"""Email notification sender for EAS alerts."""

import logging
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


def parse_mail_url(mail_url: str) -> Dict[str, Any]:
    """Parse an SMTP URL into connection parameters.

    Supported formats:
      smtp://user:pass@host:port?tls=true   — plain SMTP with STARTTLS
      smtps://user:pass@host:port           — SMTP over SSL/TLS (e.g. port 465)
      smtp://user:pass@host:port?ssl=true   — same as smtps://

    Port defaults: 465 for smtps/ssl, 587 otherwise.

    Returns a dict with keys: host, port, username, password, use_tls, use_ssl.
      use_ssl  — wrap the connection in SSL/TLS from the start (SMTP_SSL)
      use_tls  — upgrade a plain connection via STARTTLS (ignored when use_ssl)
    """
    parsed = urlparse(mail_url)
    qs = parse_qs(parsed.query)

    # ssl=true query param or smtps:// scheme → SMTP_SSL mode
    ssl_raw = qs.get("ssl", ["false"])[0]
    use_ssl = parsed.scheme == "smtps" or ssl_raw.lower() in ("true", "1", "yes")

    tls_raw = qs.get("tls", ["false"])[0]
    use_tls = tls_raw.lower() in ("true", "1", "yes")

    default_port = 465 if use_ssl else 587

    return {
        "host": parsed.hostname or "localhost",
        "port": int(parsed.port) if parsed.port else default_port,
        "username": parsed.username or None,
        "password": parsed.password or None,
        "use_tls": use_tls,
        "use_ssl": use_ssl,
    }


def send_eas_alert_email(
    alert_info: Dict[str, Any],
    recipients: List[str],
    mail_url: str,
    audio_data: Optional[bytes] = None,
    audio_filename: Optional[str] = None,
) -> bool:
    """Send an EAS alert notification email.

    Args:
        alert_info: Dict with alert details (event_code, headline, same_header,
                    location_codes, source, timestamp).
        recipients:  List of destination email addresses.
        mail_url:    SMTP URL (smtp://user:pass@host:port?tls=true).
        audio_data:  Optional WAV bytes to attach to the email.
        audio_filename: Filename for the audio attachment.

    Returns:
        True on success, False on failure.
    """
    if not recipients:
        logger.debug("No alert email recipients configured; skipping")
        return False

    if not mail_url:
        logger.warning("No mail URL configured; skipping alert email")
        return False

    try:
        conn = parse_mail_url(mail_url)
    except Exception as exc:
        logger.error("Invalid mail URL: %s", exc)
        return False

    event_code = alert_info.get("event_code", "UNKNOWN")
    headline = alert_info.get("headline", f"EAS Alert: {event_code}")
    same_header = alert_info.get("same_header", "")
    source = alert_info.get("source", "EAS Station")
    timestamp = alert_info.get("timestamp", "")
    location_codes = alert_info.get("location_codes", [])

    sender = conn["username"] or "alerts@localhost"

    msg = EmailMessage()
    msg["Subject"] = f"EAS Alert: {event_code} - {headline}"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)

    body_lines = [
        "EAS Station Alert Notification",
        "=" * 40,
        f"Event:       {event_code}",
        f"Headline:    {headline}",
    ]
    if same_header:
        body_lines.append(f"SAME Header: {same_header}")
    if location_codes:
        body_lines.append(f"Locations:   {', '.join(location_codes)}")
    if timestamp:
        body_lines.append(f"Time:        {timestamp}")
    body_lines.append(f"Source:      {source}")
    body_lines.append("")
    body_lines.append("This is an automated notification from EAS Station.")

    msg.set_content("\n".join(body_lines))

    if audio_data:
        filename = audio_filename or f"eas_alert_{event_code}.wav"
        msg.add_attachment(
            audio_data,
            maintype="audio",
            subtype="wav",
            filename=filename,
        )

    try:
        if conn["use_ssl"]:
            smtp_cls = smtplib.SMTP_SSL
        else:
            smtp_cls = smtplib.SMTP

        with smtp_cls(conn["host"], conn["port"], timeout=15) as smtp:
            if not conn["use_ssl"] and conn["use_tls"]:
                smtp.starttls()
            if conn["username"] and conn["password"]:
                smtp.login(conn["username"], conn["password"])
            smtp.send_message(msg)

        logger.info(
            "EAS alert email sent to %d recipient(s) for event %s",
            len(recipients),
            event_code,
        )
        return True

    except Exception as exc:
        logger.error(
            "Failed to send EAS alert email for event %s (%s://%s:%d): %s",
            event_code,
            "smtps" if conn["use_ssl"] else "smtp",
            conn["host"],
            conn["port"],
            exc,
        )
        return False


def test_email(mail_url: str, recipient: str) -> Tuple[bool, str]:
    """Send a test email to verify the SMTP configuration.

    Args:
        mail_url:  SMTP URL (smtp://user:pass@host:port?tls=true).
        recipient: Destination email address for the test.

    Returns:
        (success: bool, message: str)
    """
    if not mail_url:
        return False, "No mail URL configured"

    if not recipient:
        return False, "A recipient email address is required for testing"

    try:
        conn = parse_mail_url(mail_url)
    except Exception as exc:
        return False, f"Invalid mail URL: {exc}"

    sender = conn["username"] or "alerts@localhost"

    msg = EmailMessage()
    msg["Subject"] = "EAS Station - Test Email"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        "This is a test email from EAS Station.\n\n"
        "If you received this message, your email notification "
        "configuration is working correctly."
    )

    try:
        if conn["use_ssl"]:
            smtp_cls = smtplib.SMTP_SSL
        else:
            smtp_cls = smtplib.SMTP

        with smtp_cls(conn["host"], conn["port"], timeout=15) as smtp:
            if not conn["use_ssl"] and conn["use_tls"]:
                smtp.starttls()
            if conn["username"] and conn["password"]:
                smtp.login(conn["username"], conn["password"])
            smtp.send_message(msg)

        logger.info("Test email sent to %s via %s:%d", recipient, conn["host"], conn["port"])
        return True, "Test email sent successfully"

    except Exception as exc:
        logger.error(
            "Test email to %s failed (%s://%s:%d): %s",
            recipient,
            "smtps" if conn["use_ssl"] else "smtp",
            conn["host"],
            conn["port"],
            exc,
        )
        return False, f"Failed to send test email: {exc}"


__all__ = ["parse_mail_url", "send_eas_alert_email", "test_email"]
