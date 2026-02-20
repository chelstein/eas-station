"""Add admin_sessions table and password expiration support.

Adds a table to track individual administrator login sessions
(created on login, ended on logout/expiry). Also adds password_changed_at
to admin_users and password_expiration_days to application_settings.

Revision ID: 20260220_add_sessions_and_password_expiry
Revises: 20260220_add_password_policy_settings
Create Date: 2026-02-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260220_add_sessions_and_password_expiry"
down_revision = "20260220_add_password_policy_settings"
branch_labels = None
depends_on = None


def _table_exists(conn, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _column_exists(conn, table: str, column: str) -> bool:
    cols = [c["name"] for c in sa.inspect(conn).get_columns(table)]
    return column in cols


def _index_exists(conn, table: str, index: str) -> bool:
    idxs = [i["name"] for i in sa.inspect(conn).get_indexes(table)]
    return index in idxs


def upgrade() -> None:
    """Add admin_sessions table and password tracking columns."""
    conn = op.get_bind()

    # admin_sessions table (idempotent)
    if not _table_exists(conn, "admin_sessions"):
        op.create_table(
            "admin_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("admin_users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("user_agent", sa.String(length=512), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "last_seen_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.func.now(),
            ),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_reason", sa.String(length=32), nullable=True),
        )

    # Indices (idempotent — no index=True on column to avoid auto-creation)
    if not _index_exists(conn, "admin_sessions", "ix_admin_sessions_user_id"):
        op.create_index("ix_admin_sessions_user_id", "admin_sessions", ["user_id"])
    if not _index_exists(conn, "admin_sessions", "ix_admin_sessions_ended_at"):
        op.create_index("ix_admin_sessions_ended_at", "admin_sessions", ["ended_at"])

    # admin_users: password_changed_at (idempotent)
    if not _column_exists(conn, "admin_users", "password_changed_at"):
        op.add_column(
            "admin_users",
            sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        )

    # application_settings: password_expiration_days (idempotent)
    if not _column_exists(conn, "application_settings", "password_expiration_days"):
        op.add_column(
            "application_settings",
            sa.Column(
                "password_expiration_days",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade() -> None:
    """Remove admin_sessions table and password tracking columns."""
    conn = op.get_bind()

    if _column_exists(conn, "application_settings", "password_expiration_days"):
        op.drop_column("application_settings", "password_expiration_days")
    if _column_exists(conn, "admin_users", "password_changed_at"):
        op.drop_column("admin_users", "password_changed_at")
    if _table_exists(conn, "admin_sessions"):
        if _index_exists(conn, "admin_sessions", "ix_admin_sessions_ended_at"):
            op.drop_index("ix_admin_sessions_ended_at", table_name="admin_sessions")
        if _index_exists(conn, "admin_sessions", "ix_admin_sessions_user_id"):
            op.drop_index("ix_admin_sessions_user_id", table_name="admin_sessions")
        op.drop_table("admin_sessions")
