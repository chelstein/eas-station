"""Fix OLED system overview layout: resolve bar/text overlaps and cramped rows.

The previous layout had bars (x=28..99) overlapping with percentage text
(starting at ~x=97) by 3 pixels, and 11pt font rows packed at 12px
intervals left no breathing room.  This revision widens row spacing,
shortens bars to leave a clear gap for the percentage label, and bumps
bar height from 9px to 10px for better visibility on the physical display.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import column, table


revision = "20260213_fix_oled_system_overview_layout"
down_revision = "20251120_refine_oled_system_layout"
branch_labels = None
depends_on = None


display_screens = table(
    "display_screens",
    column("id", sa.Integer),
    column("name", sa.String),
    column("display_type", sa.String),
    column("template_data", JSONB),
    column("updated_at", sa.DateTime),
)


# Layout budget (128 x 64):
#
#   y  0-11  Header banner  (12px filled rect, text at y=1)
#      12    1px gap
#   y 13-23  CPU row         (label y=13, bar y=13 h=10, pct y=13)
#      24    1px gap
#   y 25-35  MEM row         (label y=25, bar y=25 h=10, pct y=25)
#      36    1px gap
#   y 37-47  DSK row         (label y=37, bar y=37 h=10, pct y=37)
#      48    1px gap
#   y 49     Divider line    (1px filled rect)
#      50    1px gap
#   y 51-63  Footer row      (status text + date, 13px for small font)
#
# Bar horizontal layout:
#   label   x=2..24   (~22px for "CPU"/"MEM"/"DSK")
#   bar     x=26..95  (width=70, leaves 2px gap after label)
#   pct     x=125 right-aligned, max_width=28 → starts at ~x=97
#   gap     x=96 (1px clear between bar end and pct start)

SYSTEM_OVERVIEW_TEMPLATE = {
    "clear": True,
    "elements": [
        # ── Header banner ────────────────────────────────────────
        {"type": "rectangle", "x": 0, "y": 0, "width": 128, "height": 12, "filled": True},
        {"type": "text", "text": "SYSTEM STATUS", "x": 2, "y": 1, "font": "small", "invert": True},
        {"type": "text", "text": "{now.time_24}", "x": 125, "y": 1, "font": "small", "invert": True, "align": "right"},

        # ── CPU row ──────────────────────────────────────────────
        {"type": "text", "text": "CPU", "x": 2, "y": 14, "font": "small"},
        {"type": "bar", "value": "{status.system_resources.cpu_usage_percent}", "x": 26, "y": 14, "width": 70, "height": 10},
        {
            "type": "text",
            "text": "{status.system_resources.cpu_usage_percent}%",
            "x": 125,
            "y": 14,
            "font": "small",
            "align": "right",
            "max_width": 28,
            "overflow": "trim",
        },

        # ── Memory row ───────────────────────────────────────────
        {"type": "text", "text": "MEM", "x": 2, "y": 26, "font": "small"},
        {"type": "bar", "value": "{status.system_resources.memory_usage_percent}", "x": 26, "y": 26, "width": 70, "height": 10},
        {
            "type": "text",
            "text": "{status.system_resources.memory_usage_percent}%",
            "x": 125,
            "y": 26,
            "font": "small",
            "align": "right",
            "max_width": 28,
            "overflow": "trim",
        },

        # ── Disk row ─────────────────────────────────────────────
        {"type": "text", "text": "DSK", "x": 2, "y": 38, "font": "small"},
        {"type": "bar", "value": "{status.system_resources.disk_usage_percent}", "x": 26, "y": 38, "width": 70, "height": 10},
        {
            "type": "text",
            "text": "{status.system_resources.disk_usage_percent}%",
            "x": 125,
            "y": 38,
            "font": "small",
            "align": "right",
            "max_width": 28,
            "overflow": "trim",
        },

        # ── Footer divider + summary ─────────────────────────────
        {"type": "rectangle", "x": 0, "y": 49, "width": 128, "height": 1, "filled": True},
        {
            "type": "text",
            "text": "{status.status_summary}",
            "x": 2,
            "y": 52,
            "font": "small",
            "max_width": 66,
            "overflow": "ellipsis",
        },
        {
            "type": "text",
            "text": "{now.date}",
            "x": 125,
            "y": 52,
            "font": "small",
            "align": "right",
            "max_width": 48,
            "overflow": "ellipsis",
        },
    ],
}


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    update_stmt = (
        display_screens.update()
        .where(display_screens.c.name == sa.bindparam("target_screen_name"))
        .where(display_screens.c.display_type == "oled")
    )

    conn.execute(
        update_stmt,
        {
            "template_data": json.loads(json.dumps(SYSTEM_OVERVIEW_TEMPLATE)),
            "updated_at": now,
            "target_screen_name": "oled_system_overview",
        },
    )


def downgrade() -> None:
    # No downgrade to avoid clobbering operator customizations
    pass
