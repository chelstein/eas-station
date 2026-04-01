"""Add forwarded_event_codes to eas_settings.

Stores the list of SAME event codes that should be auto-forwarded from
CAP/IPAWS and OTA sources. An empty list means forward all event types
(preserves existing behaviour). A non-empty list acts as an allowlist.

Revision ID: 20260331_add_forwarded_event_codes
Revises: 20260327_add_vtec_columns_to_cap_alerts
Create Date: 2026-03-31
"""

from __future__ import annotations

from alembic import op

revision = "20260331_add_forwarded_event_codes"
down_revision = "20260327_add_vtec_columns_to_cap_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE eas_settings ADD COLUMN IF NOT EXISTS forwarded_event_codes JSONB NOT NULL DEFAULT '[]'::jsonb"
    )


def downgrade() -> None:
    op.drop_column("eas_settings", "forwarded_event_codes")
