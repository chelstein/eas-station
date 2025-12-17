"""Add server info fields to Icecast settings

Revision ID: 20251217_add_icecast_server_info
Revises: 20251217_add_tts_settings
Create Date: 2025-12-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251217_add_icecast_server_info'
down_revision = '20251217_add_tts_settings'
branch_labels = None
depends_on = None


def upgrade():
    """Add server_hostname, server_location, and admin_contact fields to icecast_settings table."""
    # Add new columns to icecast_settings
    op.add_column('icecast_settings', sa.Column('server_hostname', sa.String(255), nullable=True))
    op.add_column('icecast_settings', sa.Column('server_location', sa.String(255), nullable=True))
    op.add_column('icecast_settings', sa.Column('admin_contact', sa.String(255), nullable=True))


def downgrade():
    """Remove server_hostname, server_location, and admin_contact fields from icecast_settings table."""
    op.drop_column('icecast_settings', 'admin_contact')
    op.drop_column('icecast_settings', 'server_location')
    op.drop_column('icecast_settings', 'server_hostname')
