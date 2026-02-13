"""Add uploaded audio columns to manual_eas_activations.

Revision ID: 20260213_add_audio_upload_columns
Revises: 20260210_add_local_authorities
Create Date: 2026-02-13

Adds columns for user-uploaded audio files: narration audio (alternative to
TTS), pre-alert audio (plays before narration), and post-alert audio (plays
after narration, before EOM).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260213_add_audio_upload_columns"
down_revision = "20260210_add_local_authorities"
branch_labels = None
depends_on = None


TABLE_NAME = "manual_eas_activations"


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    try:
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def upgrade() -> None:
    """Add uploaded audio columns."""
    if not _column_exists(TABLE_NAME, "narration_upload_audio_data"):
        op.add_column(TABLE_NAME, sa.Column("narration_upload_audio_data", sa.LargeBinary(), nullable=True))

    if not _column_exists(TABLE_NAME, "pre_alert_audio_data"):
        op.add_column(TABLE_NAME, sa.Column("pre_alert_audio_data", sa.LargeBinary(), nullable=True))

    if not _column_exists(TABLE_NAME, "post_alert_audio_data"):
        op.add_column(TABLE_NAME, sa.Column("post_alert_audio_data", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    """Remove uploaded audio columns."""
    if _column_exists(TABLE_NAME, "post_alert_audio_data"):
        op.drop_column(TABLE_NAME, "post_alert_audio_data")

    if _column_exists(TABLE_NAME, "pre_alert_audio_data"):
        op.drop_column(TABLE_NAME, "pre_alert_audio_data")

    if _column_exists(TABLE_NAME, "narration_upload_audio_data"):
        op.drop_column(TABLE_NAME, "narration_upload_audio_data")
