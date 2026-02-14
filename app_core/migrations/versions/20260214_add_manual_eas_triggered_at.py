"""Add triggered_at column to manual_eas_activations.

Revision ID: 20260214_add_manual_eas_triggered_at
Revises: 20260213_merge_audio_upload_and_oled_fix
Create Date: 2026-02-14

Tracks when a manual EAS activation was actually sent/transmitted
(audio playback + GPIO activation).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260214_add_manual_eas_triggered_at"
down_revision = "20260213_merge_audio_upload_and_oled_fix"
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
    """Add triggered_at column."""
    if not _column_exists(TABLE_NAME, "triggered_at"):
        op.add_column(TABLE_NAME, sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove triggered_at column."""
    if _column_exists(TABLE_NAME, "triggered_at"):
        op.drop_column(TABLE_NAME, "triggered_at")
