"""Add max_activation_seconds to eas_settings.

Adds a configurable hard limit for total EAS activation duration (DASDEC-style
cap). After this many seconds the EOM is forced and playback stops. Defaults
to 300 seconds per DASDEC specification.

Revision ID: 20260402_add_max_activation_seconds_to_eas_settings
Revises: 20260401_add_superseded_by_to_cap_alerts
Create Date: 2026-04-02
"""

from __future__ import annotations

from alembic import op

revision = "20260402_add_max_activation_seconds_to_eas_settings"
down_revision = "20260401_add_superseded_by_to_cap_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE eas_settings"
        " ADD COLUMN IF NOT EXISTS max_activation_seconds INTEGER NOT NULL DEFAULT 300"
    )


def downgrade() -> None:
    op.drop_column("eas_settings", "max_activation_seconds")
