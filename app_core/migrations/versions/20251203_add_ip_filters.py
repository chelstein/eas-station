"""Add IP filters table for allowlist/blocklist

Revision ID: 20251203_add_ip_filters
Revises: 
Create Date: 2025-12-03 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251203_add_ip_filters'
down_revision = '20251201_add_snow_emergency_opt_out'
branch_labels = None
depends_on = None


def upgrade():
    """Create ip_filters table."""
    op.create_table(
        'ip_filters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('filter_type', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_ip_filters_ip_address', 'ip_filters', ['ip_address'])
    op.create_index('ix_ip_filters_filter_type', 'ip_filters', ['filter_type'])


def downgrade():
    """Drop ip_filters table."""
    op.drop_index('ix_ip_filters_filter_type', table_name='ip_filters')
    op.drop_index('ix_ip_filters_ip_address', table_name='ip_filters')
    op.drop_table('ip_filters')
