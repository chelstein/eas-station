"""Add superseded_by_id to cap_alerts for VTEC event chain decluttering.

When NWS issues a follow-on product for the same VTEC event (e.g. EXT, CAN,
UPG) the poller marks the prior product's row with the ID of the newer alert.
The UI hides superseded rows by default so operators only see the current
state of each event, while a "View chain" link lets them inspect the full
update history.

Revision ID: 20260401_add_superseded_by_to_cap_alerts
Revises: 20260401_add_alert_source_to_received_alerts
Create Date: 2026-04-01
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260401_add_superseded_by_to_cap_alerts"
down_revision = "20260401_add_alert_source_to_received_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cap_alerts",
        sa.Column(
            "superseded_by_id",
            sa.Integer(),
            sa.ForeignKey("cap_alerts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_cap_alerts_superseded_by_id",
        "cap_alerts",
        ["superseded_by_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cap_alerts_superseded_by_id", table_name="cap_alerts")
    op.drop_column("cap_alerts", "superseded_by_id")
