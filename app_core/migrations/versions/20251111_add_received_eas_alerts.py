"""Add received_eas_alerts table to track monitored alerts

Revision ID: 20251111_add_received_eas_alerts
Revises: 20251107_merge_radio_and_audio
Create Date: 2025-11-11

This migration adds the received_eas_alerts table to track EAS alerts
received from audio monitoring sources, including:
- Reception details (source, timestamp)
- SAME header data (event, originator, FIPS codes)
- Forwarding decision (forwarded, ignored, error)
- Link to generated EASMessage if forwarded
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import sqlalchemy.exc
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251111_add_received_eas_alerts'
down_revision = '20251107_merge_radio_and_audio'
branch_labels = None
depends_on = None


TABLE_NAME = 'received_eas_alerts'


def _table_exists() -> bool:
    """Check if the table already exists in the database."""
    conn = op.get_bind()
    inspector = inspect(conn)
    try:
        return TABLE_NAME in inspector.get_table_names()
    except (sa.exc.DatabaseError, sa.exc.OperationalError):
        # Database error (connectivity, permissions) - assume table doesn't exist
        # to allow the migration to attempt creation (which will give a clearer error)
        return False


def _index_exists(index_name: str) -> bool:
    """Check if an index already exists.
    
    Note: Returns False if the table doesn't exist, which is safe because
    index creation will be skipped or fail with a clear error.
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    try:
        indexes = inspector.get_indexes(TABLE_NAME)
        return any(idx['name'] == index_name for idx in indexes)
    except (sa.exc.DatabaseError, sa.exc.OperationalError, sa.exc.NoSuchTableError):
        # Table doesn't exist or database error - assume index doesn't exist
        return False


def upgrade():
    """Create received_eas_alerts table."""
    table_already_exists = _table_exists()

    if not table_already_exists:
        op.create_table(
            'received_eas_alerts',
            sa.Column('id', sa.Integer(), nullable=False),

            # Reception details
            sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('source_name', sa.String(length=100), nullable=False),

            # SAME header data
            sa.Column('raw_same_header', sa.Text(), nullable=True),
            sa.Column('event_code', sa.String(length=8), nullable=True),
            sa.Column('event_name', sa.String(length=255), nullable=True),
            sa.Column('originator_code', sa.String(length=8), nullable=True),
            sa.Column('originator_name', sa.String(length=100), nullable=True),
            sa.Column('fips_codes', sa.JSON(), nullable=True),
            sa.Column('issue_datetime', sa.DateTime(timezone=True), nullable=True),
            sa.Column('purge_datetime', sa.DateTime(timezone=True), nullable=True),
            sa.Column('callsign', sa.String(length=16), nullable=True),

            # Forwarding decision
            sa.Column('forwarding_decision', sa.String(length=20), nullable=False),
            sa.Column('forwarding_reason', sa.Text(), nullable=True),
            sa.Column('matched_fips_codes', sa.JSON(), nullable=True),

            # Link to generated broadcast
            sa.Column('generated_message_id', sa.Integer(), nullable=True),
            sa.Column('forwarded_at', sa.DateTime(timezone=True), nullable=True),

            # Full alert data and quality metrics
            sa.Column('full_alert_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('decode_confidence', sa.Float(), nullable=True),

            # Constraints
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['generated_message_id'], ['eas_messages.id'], ),
        )

    # Create indexes if they don't exist (handles both new table and existing table with missing indexes)
    if not _index_exists('ix_received_eas_alerts_received_at'):
        op.create_index('ix_received_eas_alerts_received_at', 'received_eas_alerts', ['received_at'], unique=False)
    if not _index_exists('ix_received_eas_alerts_source_name'):
        op.create_index('ix_received_eas_alerts_source_name', 'received_eas_alerts', ['source_name'], unique=False)
    if not _index_exists('ix_received_eas_alerts_event_code'):
        op.create_index('ix_received_eas_alerts_event_code', 'received_eas_alerts', ['event_code'], unique=False)
    if not _index_exists('ix_received_eas_alerts_forwarding_decision'):
        op.create_index('ix_received_eas_alerts_forwarding_decision', 'received_eas_alerts', ['forwarding_decision'], unique=False)


def downgrade():
    """Drop received_eas_alerts table."""
    if not _table_exists():
        return

    if _index_exists('ix_received_eas_alerts_forwarding_decision'):
        op.drop_index('ix_received_eas_alerts_forwarding_decision', table_name='received_eas_alerts')
    if _index_exists('ix_received_eas_alerts_event_code'):
        op.drop_index('ix_received_eas_alerts_event_code', table_name='received_eas_alerts')
    if _index_exists('ix_received_eas_alerts_source_name'):
        op.drop_index('ix_received_eas_alerts_source_name', table_name='received_eas_alerts')
    if _index_exists('ix_received_eas_alerts_received_at'):
        op.drop_index('ix_received_eas_alerts_received_at', table_name='received_eas_alerts')
    op.drop_table('received_eas_alerts')
