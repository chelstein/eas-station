"""Merge audio upload columns and OLED system overview layout fix

Revision ID: 20260213_merge_audio_upload_and_oled_fix
Revises: 20260213_add_audio_upload_columns, 20260213_fix_oled_system_overview_layout
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260213_merge_audio_upload_and_oled_fix'
down_revision = ('20260213_add_audio_upload_columns', '20260213_fix_oled_system_overview_layout')
branch_labels = None
depends_on = None


def upgrade():
    """Merge migration - no changes needed."""
    pass


def downgrade():
    """Merge migration - no changes needed."""
    pass
