"""Add tts_pronunciation_rules table.

Stores user-configurable word-to-phonetic-spelling rules applied to TTS
narration text before synthesis.  Seeded with built-in Ohio place name
corrections (Lima, Cairo, Delphos, etc.) that common TTS engines
consistently mispronounce.

Revision ID: 20260326_tts_pronunciation_rules
Revises: 20260325_add_raw_audio_to_received_alerts
Create Date: 2026-03-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260326_tts_pronunciation_rules"
down_revision = "20260325_received_alert_audio"
branch_labels = None
depends_on = None

_TABLE = "tts_pronunciation_rules"

_BUILTIN_ROWS = [
    ("Lima",         "Lye-mah",            "Lima, OH — county seat of Allen County (NOT like Lima, Peru)"),
    ("Cairo",        "Kay-roh",            "Cairo, OH — village in Allen County (NOT like Cairo, Egypt)"),
    ("Delphos",      "Del-fus",            "Delphos, OH — city in Allen and Van Wert counties"),
    ("Versailles",   "Ver-sales",          "Versailles, OH — village in Darke County (NOT like Versailles, France)"),
    ("Russia",       "Roo-sha",            "Russia, OH — village in Shelby County"),
    ("Milan",        "My-lan",             "Milan, OH — village in Erie County (birthplace of Edison; NOT like Milan, Italy)"),
    ("Bellefontaine","Bell-fountain",      "Bellefontaine, OH — county seat of Logan County"),
    ("Piqua",        "Pik-way",            "Piqua, OH — city in Miami County"),
    ("Tiffin",       "Tif-in",             "Tiffin, OH — county seat of Seneca County"),
    ("Wapakoneta",   "Wop-uh-kuh-nee-tuh","Wapakoneta, OH — county seat of Auglaize County"),
]


def upgrade() -> None:
    """Create tts_pronunciation_rules table and seed built-in entries."""
    from sqlalchemy import inspect, text

    conn = op.get_bind()
    inspector = inspect(conn)

    if _TABLE not in inspector.get_table_names():
        op.create_table(
            _TABLE,
            sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
            sa.Column("original_text", sa.String(length=255), nullable=False),
            sa.Column("replacement_text", sa.String(length=255), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("match_case", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("note", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    # Seed built-in rows (idempotent — skip if already present)
    for original, replacement, note in _BUILTIN_ROWS:
        existing = conn.execute(
            text(f"SELECT id FROM {_TABLE} WHERE original_text = :orig AND is_builtin = true"),
            {"orig": original},
        ).fetchone()
        if not existing:
            conn.execute(
                text(
                    f"INSERT INTO {_TABLE} "
                    "(original_text, replacement_text, enabled, match_case, is_builtin, note, created_at, updated_at) "
                    "VALUES (:orig, :repl, true, false, true, :note, NOW(), NOW())"
                ),
                {"orig": original, "repl": replacement, "note": note},
            )


def downgrade() -> None:
    """Drop tts_pronunciation_rules table."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)

    if _TABLE in inspector.get_table_names():
        op.drop_table(_TABLE)
