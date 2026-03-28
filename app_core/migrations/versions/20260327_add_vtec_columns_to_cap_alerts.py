"""Add VTEC event identity columns to cap_alerts.

Extracts the five fields that form a stable VTEC event key
(office, phenomenon, significance, ETN, year) plus the action code into
dedicated indexed columns so related alert updates (NEW → CON → EXT → EXP)
can be grouped with a simple equality query instead of scanning raw_json.

Revision ID: 20260327_add_vtec_columns_to_cap_alerts
Revises: 20260327_activation_ip_audit
Create Date: 2026-03-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260327_add_vtec_columns_to_cap_alerts"
down_revision = "20260327_activation_ip_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cap_alerts", sa.Column("vtec_office",       sa.String(4),  nullable=True))
    op.add_column("cap_alerts", sa.Column("vtec_phenomenon",   sa.String(2),  nullable=True))
    op.add_column("cap_alerts", sa.Column("vtec_significance", sa.String(1),  nullable=True))
    op.add_column("cap_alerts", sa.Column("vtec_etn",          sa.Integer(),  nullable=True))
    op.add_column("cap_alerts", sa.Column("vtec_year",         sa.Integer(),  nullable=True))
    op.add_column("cap_alerts", sa.Column("vtec_action",       sa.String(3),  nullable=True))

    # Composite index covering the full event key lookup
    op.create_index(
        "ix_cap_alerts_vtec_event_key",
        "cap_alerts",
        ["vtec_office", "vtec_phenomenon", "vtec_significance", "vtec_etn", "vtec_year"],
    )
    # Individual column indexes (already declared on the model; create here for
    # databases that don't auto-create them from the ORM definition)
    op.create_index("ix_cap_alerts_vtec_office",       "cap_alerts", ["vtec_office"])
    op.create_index("ix_cap_alerts_vtec_phenomenon",   "cap_alerts", ["vtec_phenomenon"])
    op.create_index("ix_cap_alerts_vtec_significance", "cap_alerts", ["vtec_significance"])
    op.create_index("ix_cap_alerts_vtec_etn",          "cap_alerts", ["vtec_etn"])
    op.create_index("ix_cap_alerts_vtec_year",         "cap_alerts", ["vtec_year"])


def downgrade() -> None:
    op.drop_index("ix_cap_alerts_vtec_event_key",      table_name="cap_alerts")
    op.drop_index("ix_cap_alerts_vtec_office",         table_name="cap_alerts")
    op.drop_index("ix_cap_alerts_vtec_phenomenon",     table_name="cap_alerts")
    op.drop_index("ix_cap_alerts_vtec_significance",   table_name="cap_alerts")
    op.drop_index("ix_cap_alerts_vtec_etn",            table_name="cap_alerts")
    op.drop_index("ix_cap_alerts_vtec_year",           table_name="cap_alerts")
    op.drop_column("cap_alerts", "vtec_action")
    op.drop_column("cap_alerts", "vtec_year")
    op.drop_column("cap_alerts", "vtec_etn")
    op.drop_column("cap_alerts", "vtec_significance")
    op.drop_column("cap_alerts", "vtec_phenomenon")
    op.drop_column("cap_alerts", "vtec_office")
