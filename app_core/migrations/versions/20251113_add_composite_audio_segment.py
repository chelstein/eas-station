"""Add composite audio segment to EASDecodedAudio

Revision ID: 20251113_add_composite_audio_segment
Revises: 20251113_add_serial_mode_to_led_sign_status
Create Date: 2025-11-13 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20251113_add_composite_audio_segment'
down_revision = '20251113_add_serial_mode_to_led_sign_status'
branch_labels = None
depends_on = None


TABLE_NAME = "eas_decoded_audio"
COLUMN_NAME = "composite_audio_data"


def upgrade():
    """Add composite_audio_data column to eas_decoded_audio table."""
    bind = op.get_bind()
    inspector = inspect(bind)

    # Check if table exists
    if TABLE_NAME not in inspector.get_table_names():
        return

    # Check if column already exists
    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    if COLUMN_NAME in columns:
        return

    op.add_column(TABLE_NAME, sa.Column(COLUMN_NAME, sa.LargeBinary(), nullable=True))


def downgrade():
    """Remove composite_audio_data column from eas_decoded_audio table."""
    bind = op.get_bind()
    inspector = inspect(bind)

    # Check if table exists
    if TABLE_NAME not in inspector.get_table_names():
        return

    # Check if column exists
    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    if COLUMN_NAME not in columns:
        return

    op.drop_column(TABLE_NAME, COLUMN_NAME)
