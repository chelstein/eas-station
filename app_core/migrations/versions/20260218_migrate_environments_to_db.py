"""Migrate environment variables to database settings tables.

Adds missing fields to poller_settings and creates notification_settings
and application_settings tables to replace environment variable management.

Revision ID: 20260218_migrate_environments_to_db
Revises: 20260218_add_neopixel_support
Create Date: 2026-02-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260218_migrate_environments_to_db"
down_revision = "20260218_add_neopixel_support"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Extend poller_settings and create notification_settings / application_settings."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # ------------------------------------------------------------------
    # 1. Extend poller_settings with CAP feed configuration columns
    # ------------------------------------------------------------------
    if 'poller_settings' in existing_tables:
        existing_cols = {col['name'] for col in inspector.get_columns('poller_settings')}

        if 'cap_timeout' not in existing_cols:
            op.add_column('poller_settings',
                sa.Column('cap_timeout', sa.Integer(), nullable=False, server_default='30'))

        if 'noaa_user_agent' not in existing_cols:
            op.add_column('poller_settings',
                sa.Column(
                    'noaa_user_agent',
                    sa.String(500),
                    nullable=False,
                    server_default='EAS Station (+https://github.com/KR8MER/eas-station; support@easstation.com)',
                ))

        if 'cap_endpoints' not in existing_cols:
            op.add_column('poller_settings',
                sa.Column('cap_endpoints', JSONB(), nullable=False, server_default='[]'))

        if 'ipaws_feed_urls' not in existing_cols:
            op.add_column('poller_settings',
                sa.Column('ipaws_feed_urls', JSONB(), nullable=False, server_default='[]'))

        if 'ipaws_default_lookback_hours' not in existing_cols:
            op.add_column('poller_settings',
                sa.Column('ipaws_default_lookback_hours', sa.Integer(), nullable=False, server_default='12'))

    # ------------------------------------------------------------------
    # 2. Create notification_settings table
    # ------------------------------------------------------------------
    if 'notification_settings' not in existing_tables:
        op.create_table(
            'notification_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('mail_url', sa.String(500), nullable=False, server_default=''),
            sa.Column('compliance_alert_emails', JSONB(), nullable=False, server_default='[]'),
            sa.Column('sms_enabled', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('updated_at', sa.DateTime(), nullable=True,
                      server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id'),
        )

    # Seed default row (idempotent)
    op.execute("""
        INSERT INTO notification_settings (id, email_enabled, mail_url, compliance_alert_emails, sms_enabled, updated_at)
        VALUES (1, false, '', '[]', false, CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO NOTHING
    """)

    # ------------------------------------------------------------------
    # 3. Create application_settings table
    # ------------------------------------------------------------------
    if 'application_settings' not in existing_tables:
        op.create_table(
            'application_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('log_level', sa.String(16), nullable=False, server_default='INFO'),
            sa.Column('log_file', sa.String(255), nullable=False,
                      server_default='logs/eas_station.log'),
            sa.Column('upload_folder', sa.String(255), nullable=False,
                      server_default='/opt/eas-station/uploads'),
            sa.Column('updated_at', sa.DateTime(), nullable=True,
                      server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id'),
        )

    # Seed default row (idempotent)
    op.execute("""
        INSERT INTO application_settings (id, log_level, log_file, upload_folder, updated_at)
        VALUES (1, 'INFO', 'logs/eas_station.log', '/opt/eas-station/uploads', CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    """Remove migrated settings tables and poller_settings columns."""
    op.drop_table('application_settings')
    op.drop_table('notification_settings')

    for col in ('ipaws_default_lookback_hours', 'ipaws_feed_urls', 'cap_endpoints',
                'noaa_user_agent', 'cap_timeout'):
        op.drop_column('poller_settings', col)
