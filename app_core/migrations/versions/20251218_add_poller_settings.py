"""Add poller settings

Revision ID: 20251218_add_poller_settings
Revises: 20251217_add_tts_settings
Create Date: 2025-12-18

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '20251218_add_poller_settings'
down_revision = '20251217_add_tts_settings'
branch_labels = None
depends_on = None


def upgrade():
    """Add poller_settings table with enabled and poll_interval_sec fields."""
    # Create poller_settings table
    op.create_table(
        'poller_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('poll_interval_sec', sa.Integer(), nullable=False, server_default='120'),
        sa.Column('log_fetched_alerts', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Insert default settings
    op.execute("""
        INSERT INTO poller_settings (id, enabled, poll_interval_sec, log_fetched_alerts, updated_at)
        VALUES (1, true, 120, false, CURRENT_TIMESTAMP)
    """)


def downgrade():
    """Remove poller_settings table."""
    op.drop_table('poller_settings')
