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
    from sqlalchemy import inspect
    
    # Get database connection
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if table already exists
    if 'eas_decoder_monitor_settings' not in inspector.get_table_names():
        op.create_table(
            'eas_decoder_monitor_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('stream_name', sa.String(length=255), nullable=False, server_default='eas-decoder-monitor'),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Insert default settings (database-agnostic)
        from sqlalchemy.sql import table, column
        eas_decoder_monitor_settings = table(
            'eas_decoder_monitor_settings',
            column('id', sa.Integer),
            column('enabled', sa.Boolean),
            column('stream_name', sa.String),
            column('updated_at', sa.DateTime)
        )
        
        op.execute(
            eas_decoder_monitor_settings.insert().values(
                id=1,
                enabled=False,
                stream_name='eas-decoder-monitor',
                updated_at=sa.func.now()
            )
        )


def downgrade():
    """Remove EAS decoder monitor settings table."""
    op.drop_table('eas_decoder_monitor_settings')
