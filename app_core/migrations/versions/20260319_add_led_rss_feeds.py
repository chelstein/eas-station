"""Add LED RSS feed tables

Revision ID: 20260319_led_rss
Revises: 20260224_add_stream_url_to_metadata_log
Create Date: 2026-03-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260319_led_rss"
down_revision = "20260224_add_stream_url_to_metadata_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "led_rss_feeds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("interval_minutes", sa.Integer(), server_default="15"),
        sa.Column("color", sa.String(length=20), server_default="AMBER"),
        sa.Column("effect", sa.String(length=20), server_default="ROLL_LEFT"),
        sa.Column("speed", sa.String(length=20), server_default="SPEED_3"),
        sa.Column("max_items", sa.Integer(), server_default="5"),
        sa.Column("last_fetched", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_send", sa.Boolean(), server_default="false"),
        sa.Column("priority", sa.Integer(), server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "led_rss_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("link", sa.String(length=500), nullable=True),
        sa.Column("published", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_shown", sa.DateTime(timezone=True), nullable=True),
        sa.Column("show_count", sa.Integer(), server_default="0"),
        sa.Column("guid", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["feed_id"],
            ["led_rss_feeds.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("led_rss_items")
    op.drop_table("led_rss_feeds")
