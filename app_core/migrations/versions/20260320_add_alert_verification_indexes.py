"""Add indexes to speed up alert verification page queries

Revision ID: 20260320_alert_verify_idx
Revises: 20260319_led_rss
Create Date: 2026-03-20

Adds indexes on the three columns used as WHERE/ORDER-BY filters on the
/admin/alert-verification analytics page, which previously triggered full
table scans on every page load:

  - cap_alerts.sent              (window filter in collect_alert_delivery_records)
  - eas_messages.created_at      (window filter in collect_alert_delivery_records)
  - eas_decoded_audio.created_at (ORDER BY in load_recent_audio_decodes)
"""
from __future__ import annotations

from alembic import op
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "20260320_alert_verify_idx"
down_revision = "20260319_led_rss"
branch_labels = None
depends_on = None

_INDEXES = [
    ("idx_cap_alerts_sent", "cap_alerts", ["sent"]),
    ("idx_eas_messages_created_at", "eas_messages", ["created_at"]),
    ("idx_eas_decoded_audio_created_at", "eas_decoded_audio", ["created_at"]),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)

    for index_name, table_name, columns in _INDEXES:
        existing = {idx["name"] for idx in inspector.get_indexes(table_name)}
        if index_name not in existing:
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade() -> None:
    op.drop_index("idx_eas_decoded_audio_created_at", table_name="eas_decoded_audio")
    op.drop_index("idx_eas_messages_created_at", table_name="eas_messages")
    op.drop_index("idx_cap_alerts_sent", table_name="cap_alerts")
