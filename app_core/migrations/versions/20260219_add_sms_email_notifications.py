"""Add full SMS and email alert notification fields to notification_settings.

Extends the notification_settings table with:
- alert_emails: separate recipient list for EAS alert emails (vs compliance emails)
- email_attach_audio: option to attach composite EAS audio to alert emails
- sms_provider: SMS gateway provider (currently 'twilio')
- sms_account_sid: Twilio Account SID
- sms_auth_token: Twilio Auth Token
- sms_from_number: Twilio originating phone number
- sms_recipients: list of destination phone numbers

Revision ID: 20260219_add_sms_email_notifications
Revises: 20260218_migrate_environments_to_db
Create Date: 2026-02-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260219_add_sms_email_notifications"
down_revision = "20260218_migrate_environments_to_db"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add SMS and EAS-alert-email columns to notification_settings."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    existing_cols = {col["name"] for col in inspector.get_columns("notification_settings")}

    # EAS alert email recipients (separate from compliance health alert emails)
    if "alert_emails" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column("alert_emails", JSONB(), nullable=False, server_default="[]"),
        )

    # Option to attach composite EAS audio to alert emails
    if "email_attach_audio" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column(
                "email_attach_audio", sa.Boolean(), nullable=False, server_default="false"
            ),
        )

    # SMS provider (Twilio only for now; future: vonage, etc.)
    if "sms_provider" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column(
                "sms_provider",
                sa.String(length=50),
                nullable=False,
                server_default="twilio",
            ),
        )

    # Twilio / SMS gateway credentials
    if "sms_account_sid" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column(
                "sms_account_sid", sa.String(length=255), nullable=False, server_default=""
            ),
        )

    if "sms_auth_token" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column(
                "sms_auth_token", sa.String(length=255), nullable=False, server_default=""
            ),
        )

    if "sms_from_number" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column(
                "sms_from_number", sa.String(length=50), nullable=False, server_default=""
            ),
        )

    # Destination phone numbers for SMS alerts
    if "sms_recipients" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column("sms_recipients", JSONB(), nullable=False, server_default="[]"),
        )


def downgrade() -> None:
    """Remove SMS and EAS-alert-email columns from notification_settings."""
    for col in (
        "sms_recipients",
        "sms_from_number",
        "sms_auth_token",
        "sms_account_sid",
        "sms_provider",
        "email_attach_audio",
        "alert_emails",
    ):
        op.drop_column("notification_settings", col)
