"""Add stream_url column to stream_metadata_log.

Revision ID: 20260224_add_stream_url_to_metadata_log
Revises: 20260220_add_sessions_and_password_expiry
Create Date: 2026-02-24

Some ICY StreamTitle fields contain base64-encoded audio/stream URLs that
can be decoded and played back directly.  This column stores the decoded URL
so the web UI can offer a play button for those entries.

Regular ICY metadata may also carry an explicit ``url=""`` attribute; that is
stored here as well.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260224_add_stream_url_to_metadata_log"
down_revision = "20260220_add_sessions_and_password_expiry"
branch_labels = None
depends_on = None

TABLE_NAME = "stream_metadata_log"
COLUMN_NAME = "stream_url"


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    inspector = inspect(conn)
    return any(c["name"] == column_name for c in inspector.get_columns(table_name))


def upgrade() -> None:
    """Add stream_url column to stream_metadata_log."""
    if _column_exists(TABLE_NAME, COLUMN_NAME):
        return
    op.add_column(
        TABLE_NAME,
        sa.Column(COLUMN_NAME, sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove stream_url column from stream_metadata_log."""
    if not _column_exists(TABLE_NAME, COLUMN_NAME):
        return
    op.drop_column(TABLE_NAME, COLUMN_NAME)
