"""Add certbot_settings table

Revision ID: 20251216_add_certbot_settings
Revises: 20251214_add_icecast_settings
Create Date: 2025-12-16

"""
from alembic import op
import sqlalchemy as sa
import os


# revision identifiers, used by Alembic.
revision = '20251216_add_certbot_settings'
down_revision = '20251214_add_icecast_settings'
branch_labels = None
depends_on = None


def _parse_bool(value, default=False):
    """Parse boolean from environment variable."""
    if not value:
        return default
    return str(value).lower() in ('true', '1', 'yes', 'on', 'enabled')


def _parse_int(value, default=0):
    """Parse integer from environment variable."""
    if not value:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def upgrade():
    # Check if table already exists (idempotent migration)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if 'certbot_settings' in inspector.get_table_names():
        print("certbot_settings table already exists, skipping creation")
        return
    
    # Create certbot_settings table
    op.create_table(
        'certbot_settings',
        sa.Column('id', sa.Integer(), nullable=False),

        # General Settings
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('domain_name', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('email', sa.String(length=255), nullable=False, server_default=''),

        # Certificate Settings
        sa.Column('staging', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_renew_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('renew_days_before_expiry', sa.Integer(), nullable=False, server_default='30'),

        # Metadata
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id')
    )

    # Populate from environment variables
    connection = op.get_bind()

    # Read current environment variables (if any exist)
    # Note: HTTPS_ENABLED is separate and not directly related to Certbot
    domain_name = os.getenv('DOMAIN_NAME', '')
    email = os.getenv('SSL_EMAIL', '')
    staging = _parse_bool(os.getenv('CERTBOT_STAGING'), False)

    # Insert single settings row with id=1
    connection.execute(
        sa.text("""
            INSERT INTO certbot_settings (
                id,
                enabled, domain_name, email,
                staging, auto_renew_enabled, renew_days_before_expiry
            ) VALUES (
                1,
                :enabled, :domain_name, :email,
                :staging, :auto_renew_enabled, :renew_days_before_expiry
            )
        """),
        {
            'enabled': False,  # Default to disabled, users must explicitly enable
            'domain_name': domain_name,
            'email': email,
            'staging': staging,
            'auto_renew_enabled': True,
            'renew_days_before_expiry': 30,
        }
    )


def downgrade():
    op.drop_table('certbot_settings')
