"""add eas decoder monitor settings

Revision ID: 20251219_eas_decoder_monitor
Revises: 20251219_add_eas_settings
Create Date: 2025-12-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251219_eas_decoder_monitor'
down_revision = '20251219_add_eas_settings'
branch_labels = None
depends_on = None


def upgrade():
    """Add EAS decoder monitor settings table for audio monitoring tap."""
    op.create_table(
        'eas_decoder_monitor_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('stream_name', sa.String(length=255), nullable=False, server_default='eas-decoder-monitor'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Insert default settings
    op.execute("""
        INSERT INTO eas_decoder_monitor_settings (id, enabled, stream_name, updated_at)
        VALUES (1, false, 'eas-decoder-monitor', NOW())
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade():
    """Remove EAS decoder monitor settings table."""
    op.drop_table('eas_decoder_monitor_settings')
