"""Add EAS settings

Revision ID: 20251219_add_eas_settings
Revises: 20251218_merge_icecast_and_poller
Create Date: 2025-12-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '20251219_add_eas_settings'
down_revision = '20251218_merge_icecast_and_poller'
branch_labels = None
depends_on = None


def upgrade():
    """Add eas_settings table for EAS broadcast configuration.

    This migration moves EAS configuration from environment variables to the database.
    """
    from sqlalchemy import inspect

    # Get database connection
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if table already exists
    table_exists = 'eas_settings' in inspector.get_table_names()

    if not table_exists:
        # Create eas_settings table
        op.create_table(
            'eas_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            # Enable/Disable
            sa.Column('broadcast_enabled', sa.Boolean(), nullable=False, server_default='false'),
            # Station Identity
            sa.Column('originator', sa.String(8), nullable=False, server_default='WXR'),
            sa.Column('station_id', sa.String(8), nullable=False, server_default='EASNODES'),
            # Audio Generation
            sa.Column('output_dir', sa.String(255), nullable=False, server_default='static/eas_messages'),
            sa.Column('attention_tone_seconds', sa.Integer(), nullable=False, server_default='8'),
            sa.Column('sample_rate', sa.Integer(), nullable=False, server_default='22050'),
            sa.Column('audio_player', sa.String(255), nullable=False, server_default='aplay'),
            # Authorized Broadcast Areas
            sa.Column('authorized_fips_codes', JSONB(), nullable=False, server_default='[]'),
            sa.Column('authorized_event_codes', JSONB(), nullable=False, server_default='[]'),
            # Metadata
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        # Table exists, check and add missing columns
        columns = {col['name'] for col in inspector.get_columns('eas_settings')}

        if 'broadcast_enabled' not in columns:
            op.add_column('eas_settings',
                sa.Column('broadcast_enabled', sa.Boolean(), nullable=False, server_default='false'))

        if 'originator' not in columns:
            op.add_column('eas_settings',
                sa.Column('originator', sa.String(8), nullable=False, server_default='WXR'))

        if 'station_id' not in columns:
            op.add_column('eas_settings',
                sa.Column('station_id', sa.String(8), nullable=False, server_default='EASNODES'))

        if 'output_dir' not in columns:
            op.add_column('eas_settings',
                sa.Column('output_dir', sa.String(255), nullable=False, server_default='static/eas_messages'))

        if 'attention_tone_seconds' not in columns:
            op.add_column('eas_settings',
                sa.Column('attention_tone_seconds', sa.Integer(), nullable=False, server_default='8'))

        if 'sample_rate' not in columns:
            op.add_column('eas_settings',
                sa.Column('sample_rate', sa.Integer(), nullable=False, server_default='22050'))

        if 'audio_player' not in columns:
            op.add_column('eas_settings',
                sa.Column('audio_player', sa.String(255), nullable=False, server_default='aplay'))

        if 'authorized_fips_codes' not in columns:
            op.add_column('eas_settings',
                sa.Column('authorized_fips_codes', JSONB(), nullable=False, server_default='[]'))

        if 'authorized_event_codes' not in columns:
            op.add_column('eas_settings',
                sa.Column('authorized_event_codes', JSONB(), nullable=False, server_default='[]'))

        if 'updated_at' not in columns:
            op.add_column('eas_settings',
                sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))

    # Ensure default settings row exists (idempotent insert)
    op.execute("""
        INSERT INTO eas_settings (id, broadcast_enabled, originator, station_id, output_dir,
                                  attention_tone_seconds, sample_rate, audio_player,
                                  authorized_fips_codes, authorized_event_codes, updated_at)
        VALUES (1, false, 'WXR', 'EASNODES', 'static/eas_messages',
                8, 22050, 'aplay', '[]', '[]', CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade():
    """Remove eas_settings table."""
    op.drop_table('eas_settings')
