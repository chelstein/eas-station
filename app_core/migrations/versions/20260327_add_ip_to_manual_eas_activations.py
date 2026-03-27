"""Add created_by_ip and triggered_by_ip columns to manual_eas_activations.

Records the client IP address of the operator session that generated and/or
broadcast each manual EAS activation, providing a persistent IP-level audit
trail alongside the existing username columns.

Revision ID: 20260327_activation_ip_audit
Revises: 20260327_widen_cap_alerts_geom_type
Create Date: 2026-03-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260327_activation_ip_audit"
down_revision = "20260327_widen_cap_alerts_geom_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add created_by_ip and triggered_by_ip columns to manual_eas_activations."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = inspector.get_table_names()
    if "manual_eas_activations" not in existing_tables:
        return

    existing_cols = {col["name"] for col in inspector.get_columns("manual_eas_activations")}

    if "created_by_ip" not in existing_cols:
        op.add_column(
            "manual_eas_activations",
            sa.Column("created_by_ip", sa.String(length=45), nullable=True),
        )

    if "triggered_by_ip" not in existing_cols:
        op.add_column(
            "manual_eas_activations",
            sa.Column("triggered_by_ip", sa.String(length=45), nullable=True),
        )


def downgrade() -> None:
    """Remove created_by_ip and triggered_by_ip columns from manual_eas_activations."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = inspector.get_table_names()
    if "manual_eas_activations" not in existing_tables:
        return

    existing_cols = {col["name"] for col in inspector.get_columns("manual_eas_activations")}

    if "triggered_by_ip" in existing_cols:
        op.drop_column("manual_eas_activations", "triggered_by_ip")

    if "created_by_ip" in existing_cols:
        op.drop_column("manual_eas_activations", "created_by_ip")
