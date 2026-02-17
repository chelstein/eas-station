"""Add stream_metadata_log table for ICY now-playing history.

Revision ID: 20260217_add_stream_metadata_log
Revises: 20260216_improve_oled_screens
Create Date: 2026-02-17

Each time a streaming audio source receives a new StreamTitle via ICY
metadata the parsed fields (title, artist, album, artwork_url, length,
display string, raw) are written to this table so the song-play history
is available in the web UI.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260217_add_stream_metadata_log"
down_revision = "20260216_improve_oled_screens"
branch_labels = None
depends_on = None


TABLE_NAME = "stream_metadata_log"


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    """Create stream_metadata_log table."""
    if _table_exists(TABLE_NAME):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("artist", sa.Text(), nullable=True),
        sa.Column("album", sa.Text(), nullable=True),
        sa.Column("artwork_url", sa.Text(), nullable=True),
        sa.Column("length", sa.String(20), nullable=True),
        sa.Column("display", sa.Text(), nullable=True),
        sa.Column("raw", sa.Text(), nullable=True),
    )

    op.create_index(
        f"ix_{TABLE_NAME}_source_name",
        TABLE_NAME,
        ["source_name"],
    )
    op.create_index(
        f"ix_{TABLE_NAME}_timestamp",
        TABLE_NAME,
        ["timestamp"],
    )


def downgrade() -> None:
    """Drop stream_metadata_log table."""
    if not _table_exists(TABLE_NAME):
        return
    op.drop_index(f"ix_{TABLE_NAME}_timestamp", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_source_name", table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
