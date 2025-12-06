"""Add IP filters table for allowlist/blocklist

Revision ID: 20251203_add_ip_filters
Revises: 
Create Date: 2025-12-03 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251203_add_ip_filters'
down_revision = '20251201_add_snow_emergency_opt_out'
branch_labels = None
depends_on = None

TABLE_NAME = 'ip_filters'


def _table_exists() -> bool:
    """Check if ip_filters table exists."""
    conn = op.get_bind()
    inspector = inspect(conn)
    try:
        return TABLE_NAME in inspector.get_table_names()
    except Exception:
        return False


def _index_exists(index_name: str) -> bool:
    """Check if an index exists."""
    conn = op.get_bind()
    inspector = inspect(conn)
    try:
        indexes = inspector.get_indexes(TABLE_NAME)
        return any(idx['name'] == index_name for idx in indexes)
    except Exception:
        return False


def upgrade():
    """Create ip_filters table."""
    if _table_exists():
        return  # Table already exists, skip creation
    
    op.create_table(
        TABLE_NAME,
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
    if not _index_exists('ix_ip_filters_ip_address'):
        op.create_index('ix_ip_filters_ip_address', TABLE_NAME, ['ip_address'])
    if not _index_exists('ix_ip_filters_filter_type'):
        op.create_index('ix_ip_filters_filter_type', TABLE_NAME, ['filter_type'])


def downgrade():
    """Drop ip_filters table."""
    if not _table_exists():
        return  # Table doesn't exist, nothing to drop
    
    if _index_exists('ix_ip_filters_filter_type'):
        op.drop_index('ix_ip_filters_filter_type', table_name=TABLE_NAME)
    if _index_exists('ix_ip_filters_ip_address'):
        op.drop_index('ix_ip_filters_ip_address', table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
