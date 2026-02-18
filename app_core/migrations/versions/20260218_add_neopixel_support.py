"""Add NeoPixel and USB tower light configuration to hardware settings.

Revision ID: 20260218_add_neopixel_support
Revises: 20260218_add_gpio_oled_and_flash
Create Date: 2026-02-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260218_add_neopixel_support"
down_revision = "20260218_add_gpio_oled_and_flash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add NeoPixel and USB tower light columns to the hardware_settings table."""
    # ------------------------------------------------------------------
    # USB Tower Light (Adafruit #5125 / CH34x serial stack light)
    # ------------------------------------------------------------------
    op.add_column(
        "hardware_settings",
        sa.Column("tower_light_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "hardware_settings",
        sa.Column(
            "tower_light_serial_port",
            sa.String(length=100),
            nullable=False,
            server_default="/dev/ttyUSB0",
        ),
    )
    op.add_column(
        "hardware_settings",
        sa.Column("tower_light_baudrate", sa.Integer(), nullable=False, server_default="9600"),
    )
    op.add_column(
        "hardware_settings",
        sa.Column(
            "tower_light_alert_buzzer", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "hardware_settings",
        sa.Column(
            "tower_light_incoming_uses_yellow",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )
    op.add_column(
        "hardware_settings",
        sa.Column(
            "tower_light_blink_on_alert",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )

    # ------------------------------------------------------------------
    # NeoPixel / WS2812B addressable LED strip
    # ------------------------------------------------------------------
    op.add_column(
        "hardware_settings",
        sa.Column("neopixel_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "hardware_settings",
        sa.Column("neopixel_gpio_pin", sa.Integer(), nullable=False, server_default="18"),
    )
    op.add_column(
        "hardware_settings",
        sa.Column("neopixel_num_pixels", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "hardware_settings",
        sa.Column("neopixel_brightness", sa.Integer(), nullable=False, server_default="128"),
    )
    op.add_column(
        "hardware_settings",
        sa.Column(
            "neopixel_led_order",
            sa.String(length=10),
            nullable=False,
            server_default="GRB",
        ),
    )
    op.add_column(
        "hardware_settings",
        sa.Column(
            "neopixel_standby_color",
            JSONB(),
            nullable=False,
            server_default='{"r": 0, "g": 10, "b": 0}',
        ),
    )
    op.add_column(
        "hardware_settings",
        sa.Column(
            "neopixel_alert_color",
            JSONB(),
            nullable=False,
            server_default='{"r": 255, "g": 0, "b": 0}',
        ),
    )
    op.add_column(
        "hardware_settings",
        sa.Column(
            "neopixel_flash_on_alert",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )
    op.add_column(
        "hardware_settings",
        sa.Column(
            "neopixel_flash_interval_ms",
            sa.Integer(),
            nullable=False,
            server_default="500",
        ),
    )


def downgrade() -> None:
    """Remove NeoPixel and tower light columns from the hardware_settings table."""
    # NeoPixel
    op.drop_column("hardware_settings", "neopixel_flash_interval_ms")
    op.drop_column("hardware_settings", "neopixel_flash_on_alert")
    op.drop_column("hardware_settings", "neopixel_alert_color")
    op.drop_column("hardware_settings", "neopixel_standby_color")
    op.drop_column("hardware_settings", "neopixel_led_order")
    op.drop_column("hardware_settings", "neopixel_brightness")
    op.drop_column("hardware_settings", "neopixel_num_pixels")
    op.drop_column("hardware_settings", "neopixel_gpio_pin")
    op.drop_column("hardware_settings", "neopixel_enabled")
    # Tower light
    op.drop_column("hardware_settings", "tower_light_blink_on_alert")
    op.drop_column("hardware_settings", "tower_light_incoming_uses_yellow")
    op.drop_column("hardware_settings", "tower_light_alert_buzzer")
    op.drop_column("hardware_settings", "tower_light_baudrate")
    op.drop_column("hardware_settings", "tower_light_serial_port")
    op.drop_column("hardware_settings", "tower_light_enabled")
