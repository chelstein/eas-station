"""Add Adafruit Ultimate GPS HAT (#2324) support to hardware settings.

Adds GPS receiver configuration for UART-connected GPS modules with PPS
output for precision timekeeping. Supports the Adafruit Ultimate GPS HAT
(product #2324) and compatible NMEA-0183 serial GPS receivers.

Revision ID: 20260220_add_gps_hat_support
Revises: 20260219_refactor_smtp_to_fields
Create Date: 2026-02-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260220_add_gps_hat_support"
down_revision = "20260219_refactor_smtp_to_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add GPS HAT columns to the hardware_settings table."""
    op.add_column(
        "hardware_settings",
        sa.Column("gps_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "hardware_settings",
        sa.Column(
            "gps_serial_port",
            sa.String(length=100),
            nullable=False,
            server_default="/dev/serial0",
        ),
    )
    op.add_column(
        "hardware_settings",
        sa.Column("gps_baudrate", sa.Integer(), nullable=False, server_default="9600"),
    )
    op.add_column(
        "hardware_settings",
        sa.Column("gps_pps_gpio_pin", sa.Integer(), nullable=False, server_default="4"),
    )
    op.add_column(
        "hardware_settings",
        sa.Column("gps_use_for_location", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "hardware_settings",
        sa.Column("gps_use_for_time", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "hardware_settings",
        sa.Column("gps_min_satellites", sa.Integer(), nullable=False, server_default="4"),
    )


def downgrade() -> None:
    """Remove GPS HAT columns from the hardware_settings table."""
    op.drop_column("hardware_settings", "gps_min_satellites")
    op.drop_column("hardware_settings", "gps_use_for_time")
    op.drop_column("hardware_settings", "gps_use_for_location")
    op.drop_column("hardware_settings", "gps_pps_gpio_pin")
    op.drop_column("hardware_settings", "gps_baudrate")
    op.drop_column("hardware_settings", "gps_serial_port")
    op.drop_column("hardware_settings", "gps_enabled")
