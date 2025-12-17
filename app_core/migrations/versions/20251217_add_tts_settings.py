"""Add TTS settings table

Revision ID: 20251217_add_tts_settings
Revises: 20251214_add_icecast_settings
Create Date: 2025-12-17 12:56:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '20251217_add_tts_settings'
down_revision = '20251216_add_certbot_settings'
branch_labels = None
depends_on = None


def upgrade():
    # Create tts_settings table
    op.create_table(
        'tts_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('provider', sa.String(length=50), nullable=False, server_default=''),
        sa.Column('azure_openai_endpoint', sa.String(length=500), nullable=True),
        sa.Column('azure_openai_key', sa.String(length=500), nullable=True),
        sa.Column('azure_openai_model', sa.String(length=100), nullable=False, server_default='tts-1'),
        sa.Column('azure_openai_voice', sa.String(length=50), nullable=False, server_default='alloy'),
        sa.Column('azure_openai_speed', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Insert default settings row
    op.execute(
        """
        INSERT INTO tts_settings (id, enabled, provider, azure_openai_model, azure_openai_voice, azure_openai_speed, updated_at)
        VALUES (1, false, '', 'tts-1', 'alloy', 1.0, NULL)
        """
    )


def downgrade():
    op.drop_table('tts_settings')
