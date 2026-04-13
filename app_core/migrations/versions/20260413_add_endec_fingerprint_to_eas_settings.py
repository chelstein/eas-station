"""Add endec_fingerprint to eas_settings.

Adds a boolean flag controlling whether the KR8MER EAS Station trill
fingerprint (3 × 0xAA bytes after each SAME burst) is included in
generated audio. Defaults to True.

Revision ID: 20260413_add_endec_fingerprint_to_eas_settings
Revises: 20260402_add_max_activation_seconds_to_eas_settings
Create Date: 2026-04-13
"""

from __future__ import annotations

from alembic import op

revision = "20260413_add_endec_fingerprint_to_eas_settings"
down_revision = "20260402_backfill_vtec_superseded_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE eas_settings"
        " ADD COLUMN IF NOT EXISTS endec_fingerprint BOOLEAN NOT NULL DEFAULT TRUE"
    )


def downgrade() -> None:
    op.drop_column("eas_settings", "endec_fingerprint")
