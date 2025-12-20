"""Add Zigbee fields to hardware_settings table

Revision ID: 20251220_add_zigbee_to_hardware_settings
Revises: 20251219_add_eas_settings
Create Date: 2025-12-20

"""
from alembic import op
import sqlalchemy as sa
import os


# revision identifiers, used by Alembic.
revision = '20251220_add_zigbee_to_hardware_settings'
down_revision = '20251219_eas_decoder_monitor'
branch_labels = None
depends_on = None


def _parse_bool(value, default=False):
    """Parse boolean from environment variable."""
    if not value:
        return default
    return str(value).lower() in ('true', '1', 'yes', 'on')


def _parse_int(value, default=0):
    """Parse integer from environment variable."""
    if not value:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def upgrade():
    """Add Zigbee configuration columns to hardware_settings table."""
    from sqlalchemy import inspect

    # Get database connection
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if columns already exist (idempotent migration)
    existing_columns = [col['name'] for col in inspector.get_columns('hardware_settings')]

    if 'zigbee_enabled' not in existing_columns:
        op.add_column('hardware_settings',
            sa.Column('zigbee_enabled', sa.Boolean(), nullable=False, server_default='false'))

    if 'zigbee_port' not in existing_columns:
        op.add_column('hardware_settings',
            sa.Column('zigbee_port', sa.String(length=100), nullable=False, server_default='/dev/ttyAMA0'))

    if 'zigbee_baudrate' not in existing_columns:
        op.add_column('hardware_settings',
            sa.Column('zigbee_baudrate', sa.Integer(), nullable=False, server_default='115200'))

    if 'zigbee_channel' not in existing_columns:
        op.add_column('hardware_settings',
            sa.Column('zigbee_channel', sa.Integer(), nullable=False, server_default='15'))

    if 'zigbee_pan_id' not in existing_columns:
        op.add_column('hardware_settings',
            sa.Column('zigbee_pan_id', sa.String(length=20), nullable=False, server_default='0x1A62'))

    # Populate from environment variables if they exist
    zigbee_enabled = _parse_bool(os.getenv('ZIGBEE_ENABLED'))
    zigbee_port = os.getenv('ZIGBEE_PORT', '/dev/ttyAMA0')
    zigbee_baudrate = _parse_int(os.getenv('ZIGBEE_BAUDRATE'), 115200)
    zigbee_channel = _parse_int(os.getenv('ZIGBEE_CHANNEL'), 15)
    zigbee_pan_id = os.getenv('ZIGBEE_PAN_ID', '0x1A62')

    # Update the existing row with values from environment
    conn.execute(
        sa.text("""
            UPDATE hardware_settings
            SET zigbee_enabled = :zigbee_enabled,
                zigbee_port = :zigbee_port,
                zigbee_baudrate = :zigbee_baudrate,
                zigbee_channel = :zigbee_channel,
                zigbee_pan_id = :zigbee_pan_id
            WHERE id = 1
        """),
        {
            'zigbee_enabled': zigbee_enabled,
            'zigbee_port': zigbee_port,
            'zigbee_baudrate': zigbee_baudrate,
            'zigbee_channel': zigbee_channel,
            'zigbee_pan_id': zigbee_pan_id,
        }
    )


def downgrade():
    """Remove Zigbee columns from hardware_settings table."""
    op.drop_column('hardware_settings', 'zigbee_pan_id')
    op.drop_column('hardware_settings', 'zigbee_channel')
    op.drop_column('hardware_settings', 'zigbee_baudrate')
    op.drop_column('hardware_settings', 'zigbee_port')
    op.drop_column('hardware_settings', 'zigbee_enabled')
