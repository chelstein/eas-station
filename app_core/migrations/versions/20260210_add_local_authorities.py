"""Add local_authorities table for jurisdiction-scoped EAS access.

Revision ID: 20260210_add_local_authorities
Revises: 20251220_add_max_sources_to_icecast
Create Date: 2026-02-10

This migration adds the local_authorities table which allows local government
officials (county EMA directors, sheriff's offices, etc.) to be granted access
to issue EAS alerts for their political subdivision. Each authority record
links to an AdminUser and defines the 8-character station identifier, originator
code, authorized FIPS codes, and authorized event codes per the EAS plan.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260210_add_local_authorities"
down_revision = "20251220_add_max_sources_to_icecast"
branch_labels = None
depends_on = None


LOCAL_AUTHORITIES_TABLE = "local_authorities"


def _table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    inspector = inspect(conn)
    try:
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def upgrade() -> None:
    """Create local_authorities table."""
    if _table_exists(LOCAL_AUTHORITIES_TABLE):
        return

    op.create_table(
        LOCAL_AUTHORITIES_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("admin_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("short_name", sa.String(length=32), nullable=True),
        sa.Column("station_id", sa.String(length=8), nullable=False),
        sa.Column("originator", sa.String(length=3), nullable=False, server_default="CIV"),
        sa.Column("authorized_fips_codes", JSONB, nullable=False, server_default="[]"),
        sa.Column("authorized_event_codes", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_local_authorities_user_id",
        LOCAL_AUTHORITIES_TABLE,
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop local_authorities table."""
    if _table_exists(LOCAL_AUTHORITIES_TABLE):
        op.drop_index("ix_local_authorities_user_id", table_name=LOCAL_AUTHORITIES_TABLE)
        op.drop_table(LOCAL_AUTHORITIES_TABLE)
