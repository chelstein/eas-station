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

"""EAS Station notification subsystem (email + SMS)."""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def send_alert_notifications(
    record_id: Optional[int],
    alert_info: Dict[str, Any],
    db_session,
    logger_instance: Optional[logging.Logger] = None,
) -> None:
    """Send email and/or SMS notifications for a broadcast EAS alert.

    Called after a successful EAS broadcast. Fires email to configured
    alert_emails and/or SMS to configured sms_recipients based on the
    current NotificationSettings row.

    Args:
        record_id: EASMessage primary key (used to fetch audio for attachment).
                   May be None if the record ID is unavailable.
        alert_info: Dict describing the alert. Expected keys:
                    event_code, headline, same_header, location_codes,
                    source, timestamp.
        db_session: Active SQLAlchemy session.
        logger_instance: Optional logger override.
    """
    log = logger_instance or logger

    try:
        from flask import has_app_context
        if not has_app_context():
            log.warning("No Flask app context; alert notifications will not be sent")
            return
    except ImportError:
        return

    try:
        from app_core.models import NotificationSettings, EASMessage

        settings = NotificationSettings.query.first()
        if not settings:
            log.warning("No notification settings row found; skipping alert notifications")
            return

        # ------------------------------------------------------------------
        # Fetch composite audio if needed for email attachment
        # ------------------------------------------------------------------
        audio_data: Optional[bytes] = None
        audio_filename: Optional[str] = None

        if record_id and settings.email_enabled and settings.email_attach_audio:
            try:
                eas_msg = db_session.get(EASMessage, record_id)
                if eas_msg and eas_msg.audio_data:
                    audio_data = bytes(eas_msg.audio_data)
                    audio_filename = eas_msg.audio_filename or "eas_alert.wav"
            except Exception as exc:
                log.warning(
                    "Could not fetch EASMessage audio for notification attachment: %s", exc
                )

        # ------------------------------------------------------------------
        # Email
        # ------------------------------------------------------------------
        if not settings.email_enabled:
            log.debug("Email notifications disabled; skipping")
        elif not settings.mail_url:
            log.warning("Email notifications enabled but no mail URL configured; skipping")
        else:
            recipients = list(settings.alert_emails or [])
            if not recipients:
                log.warning("Email notifications enabled but no alert recipients configured; skipping")
            if recipients:
                try:
                    from app_core.notifications.email import send_eas_alert_email

                    send_eas_alert_email(
                        alert_info=alert_info,
                        recipients=recipients,
                        mail_url=settings.mail_url,
                        audio_data=audio_data if settings.email_attach_audio else None,
                        audio_filename=audio_filename,
                    )
                except Exception as exc:
                    log.error("Alert email notification failed: %s", exc)

        # ------------------------------------------------------------------
        # SMS
        # ------------------------------------------------------------------
        if (
            settings.sms_enabled
            and settings.sms_account_sid
            and settings.sms_auth_token
            and settings.sms_from_number
        ):
            recipients = list(settings.sms_recipients or [])
            if recipients:
                try:
                    from app_core.notifications.sms import send_eas_alert_sms

                    send_eas_alert_sms(
                        alert_info=alert_info,
                        recipients=recipients,
                        account_sid=settings.sms_account_sid,
                        auth_token=settings.sms_auth_token,
                        from_number=settings.sms_from_number,
                    )
                except Exception as exc:
                    log.error("Alert SMS notification failed: %s", exc)

    except Exception as exc:
        log.error("Alert notification dispatch failed: %s", exc)


__all__ = ["send_alert_notifications"]
