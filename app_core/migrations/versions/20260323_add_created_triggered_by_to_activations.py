"""Add created_by and triggered_by columns to manual_eas_activations.

Records the username of the operator who generated and/or broadcast each
manual EAS activation, providing a persistent audit trail beyond the
application log.

Revision ID: 20260323_activation_user_audit
Revises: 20260320_add_snmp_to_notifications
Create Date: 2026-03-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260323_activation_user_audit"
down_revision = "20260320_add_snmp_to_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add created_by and triggered_by columns to manual_eas_activations."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = inspector.get_table_names()
    if "manual_eas_activations" not in existing_tables:
        return

    existing_cols = {col["name"] for col in inspector.get_columns("manual_eas_activations")}

    if "created_by" not in existing_cols:
        op.add_column(
            "manual_eas_activations",
            sa.Column("created_by", sa.String(length=100), nullable=True),
        )

    if "triggered_by" not in existing_cols:
        op.add_column(
            "manual_eas_activations",
            sa.Column("triggered_by", sa.String(length=100), nullable=True),
        )


def downgrade() -> None:
    """Remove created_by and triggered_by columns from manual_eas_activations."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = inspector.get_table_names()
    if "manual_eas_activations" not in existing_tables:
        return

    existing_cols = {col["name"] for col in inspector.get_columns("manual_eas_activations")}

    if "triggered_by" in existing_cols:
        op.drop_column("manual_eas_activations", "triggered_by")

    if "created_by" in existing_cols:
        op.drop_column("manual_eas_activations", "created_by")
