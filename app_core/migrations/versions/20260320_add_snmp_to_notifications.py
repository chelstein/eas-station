"""Add SNMP trap notification fields to notification_settings.

Extends the notification_settings table with:
- snmp_enabled: master switch for SNMP trap notifications
- snmp_targets: list of "host:port" trap destination strings
- snmp_community: SNMP v2c community string (default "public")

Revision ID: 20260320_add_snmp_to_notifications
Revises: 20260320_alert_verify_idx
Create Date: 2026-03-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260320_add_snmp_to_notifications"
down_revision = "20260320_alert_verify_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add SNMP notification columns to notification_settings."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = inspector.get_table_names()
    if "notification_settings" not in existing_tables:
        return

    existing_cols = {col["name"] for col in inspector.get_columns("notification_settings")}

    if "snmp_enabled" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column("snmp_enabled", sa.Boolean(), nullable=False, server_default="false"),
        )

    if "snmp_targets" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column("snmp_targets", JSONB(), nullable=False, server_default="[]"),
        )

    if "snmp_community" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column(
                "snmp_community",
                sa.String(length=255),
                nullable=False,
                server_default="public",
            ),
        )


def downgrade() -> None:
    """Remove SNMP notification columns from notification_settings."""
    for col in ("snmp_community", "snmp_targets", "snmp_enabled"):
        op.drop_column("notification_settings", col)
