"""Merge icecast server info and poller settings migrations

Revision ID: 20251218_merge_icecast_and_poller
Revises: 20251217_add_icecast_server_info, 20251218_add_poller_settings
Create Date: 2025-12-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251218_merge_icecast_and_poller'
down_revision = ('20251217_add_icecast_server_info', '20251218_add_poller_settings')
branch_labels = None
depends_on = None


def upgrade():
    """Merge migration - no changes needed."""
    pass


def downgrade():
    """Merge migration - no changes needed."""
    pass
