"""Add password policy columns to application_settings.

Allows administrators to configure minimum password length and
character complexity requirements (uppercase, lowercase, digits,
special characters) from the Application Settings page.

Revision ID: 20260220_add_password_policy_settings
Revises: 20260220_add_gps_hat_support
Create Date: 2026-02-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260220_add_password_policy_settings"
down_revision = "20260220_add_gps_hat_support"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add password policy columns to the application_settings table."""
    op.add_column(
        "application_settings",
        sa.Column("password_min_length", sa.Integer(), nullable=False, server_default="8"),
    )
    op.add_column(
        "application_settings",
        sa.Column("password_require_uppercase", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "application_settings",
        sa.Column("password_require_lowercase", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "application_settings",
        sa.Column("password_require_digits", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "application_settings",
        sa.Column("password_require_special", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Remove password policy columns from the application_settings table."""
    op.drop_column("application_settings", "password_require_special")
    op.drop_column("application_settings", "password_require_digits")
    op.drop_column("application_settings", "password_require_lowercase")
    op.drop_column("application_settings", "password_require_uppercase")
    op.drop_column("application_settings", "password_min_length")
