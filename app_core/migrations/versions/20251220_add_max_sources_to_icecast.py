"""Add max_sources field to Icecast settings

Revision ID: 20251220_add_max_sources_to_icecast
Revises: 20251220_add_zigbee_to_hardware_settings
Create Date: 2025-12-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251220_add_max_sources_to_icecast'
down_revision = '20251220_add_zigbee_to_hardware_settings'
branch_labels = None
depends_on = None


def upgrade():
    """Add max_sources field to icecast_settings table."""
    # Add new column to icecast_settings
    op.add_column('icecast_settings', sa.Column('max_sources', sa.Integer, nullable=True))


def downgrade():
    """Remove max_sources field from icecast_settings table."""
    op.drop_column('icecast_settings', 'max_sources')
