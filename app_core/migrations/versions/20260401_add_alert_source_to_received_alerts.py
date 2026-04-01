"""Add alert_source column to received_eas_alerts.

Stores the canonical ingest path for each received EAS alert so operators
can distinguish between alerts captured over RF (SDR, ALSA, PulseAudio)
versus those received from an internet audio stream.

Values match the ALERT_SOURCE_EAS_RF / ALERT_SOURCE_EAS_STREAM constants
defined in app_utils.alert_sources.

Revision ID: 20260401_add_alert_source_to_received_alerts
Revises: 20260331_add_forwarded_event_codes
Create Date: 2026-04-01
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260401_add_alert_source_to_received_alerts"
down_revision = "20260331_add_forwarded_event_codes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "received_eas_alerts",
        sa.Column("alert_source", sa.String(32), nullable=True, index=True),
    )
    op.create_index(
        "ix_received_eas_alerts_alert_source",
        "received_eas_alerts",
        ["alert_source"],
    )


def downgrade() -> None:
    op.drop_index("ix_received_eas_alerts_alert_source", table_name="received_eas_alerts")
    op.drop_column("received_eas_alerts", "alert_source")
