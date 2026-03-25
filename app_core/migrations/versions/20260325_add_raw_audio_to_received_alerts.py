"""Add raw_audio_data column to received_eas_alerts.

Stores the raw WAV audio captured from the monitoring stream at the moment
an OTA EAS alert is detected, so operators can play back what the system
actually heard.

Revision ID: 20260325_received_alert_audio
Revises: 20260323_activation_user_audit
Create Date: 2026-03-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260325_received_alert_audio"
down_revision = "20260323_activation_user_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "received_eas_alerts",
        sa.Column("raw_audio_data", sa.LargeBinary(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("received_eas_alerts", "raw_audio_data")
