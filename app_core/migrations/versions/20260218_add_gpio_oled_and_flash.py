"""Add GPIO status OLED screen and flash pattern configuration.

Revision ID: 20260218_add_gpio_oled_and_flash
Revises: 20260217_add_stream_metadata_log
Create Date: 2026-02-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone


revision = "20260218_add_gpio_oled_and_flash"
down_revision = "20260217_add_stream_metadata_log"
branch_labels = None
depends_on = None


# Define table structures for data manipulation
display_screens = table(
    "display_screens",
    column("id", sa.Integer),
    column("name", sa.String),
    column("description", sa.Text),
    column("display_type", sa.String),
    column("enabled", sa.Boolean),
    column("priority", sa.Integer),
    column("refresh_interval", sa.Integer),
    column("duration", sa.Integer),
    column("template_data", JSONB),
    column("data_sources", JSONB),
    column("conditions", JSONB),
    column("created_at", sa.DateTime),
    column("updated_at", sa.DateTime),
)


def upgrade() -> None:
    """Add GPIO status OLED screen."""
    conn = op.get_bind()
    
    # Check if screen already exists
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM display_screens WHERE name = 'oled_gpio_status'")
    ).scalar()
    
    if result == 0:
        # Insert GPIO status OLED screen
        op.execute(
            display_screens.insert().values(
                name="oled_gpio_status",
                description="GPIO pin status monitor showing active relays and recent activations.",
                display_type="oled",
                enabled=True,
                priority=2,
                refresh_interval=5,  # Refresh every 5 seconds for real-time monitoring
                duration=15,  # Display for 15 seconds in rotation
                template_data={
                    "clear": True,
                    "lines": [
                        {
                            "text": "◢ GPIO STATUS ◣",
                            "font": "medium",
                            "wrap": False,
                            "invert": True,
                            "spacing": 1,
                            "y": 0,
                        },
                        {
                            "text": "Active Pins: {gpio.active_count}",
                            "font": "small",
                            "wrap": False,
                            "y": 15,
                            "max_width": 124,
                        },
                        {
                            "text": "{gpio.active_pins_summary}",
                            "y": 27,
                            "max_width": 124,
                            "allow_empty": True,
                        },
                        {
                            "text": "Last: {gpio.last_activation_summary}",
                            "y": 45,
                            "wrap": False,
                            "max_width": 124,
                            "allow_empty": True,
                        },
                        {
                            "text": "Today: {gpio.activations_today} activations",
                            "y": 56,
                            "wrap": False,
                            "max_width": 124,
                        },
                    ],
                },
                data_sources=[
                    {"endpoint": "/api/gpio/status", "var_name": "gpio"},
                ],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )


def downgrade() -> None:
    """Remove GPIO status OLED screen."""
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM display_screens WHERE name = 'oled_gpio_status'")
    )
