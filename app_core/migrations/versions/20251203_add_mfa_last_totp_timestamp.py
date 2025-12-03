"""Add mfa_last_totp_at to track last used TOTP timestamp

Revision ID: 20251203_add_mfa_last_totp_timestamp
Revises: 20251111_add_received_eas_alerts
Create Date: 2025-12-03

This migration adds the mfa_last_totp_at field to admin_users table to
prevent TOTP code reuse within the same time window (30 seconds).
This fixes the issue where the same TOTP code could be used multiple times.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20251203_add_mfa_last_totp_timestamp'
down_revision = '20251111_add_received_eas_alerts'
branch_labels = None
depends_on = None


TABLE_NAME = 'admin_users'
COLUMN_NAME = 'mfa_last_totp_at'


def upgrade():
    """Add mfa_last_totp_at column to admin_users table."""
    bind = op.get_bind()
    inspector = inspect(bind)

    # Check if table exists
    if TABLE_NAME not in inspector.get_table_names():
        return

    # Check if column already exists
    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    if COLUMN_NAME in columns:
        return

    op.add_column(TABLE_NAME, sa.Column(COLUMN_NAME, sa.DateTime(timezone=True), nullable=True))


def downgrade():
    """Remove mfa_last_totp_at column from admin_users table."""
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
