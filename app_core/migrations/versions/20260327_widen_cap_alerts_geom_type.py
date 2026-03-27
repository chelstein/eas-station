"""Widen cap_alerts.geom from geometry(POLYGON,4326) to geometry(GEOMETRY,4326).

SAME-code-derived alert geometries are MultiPolygon (union of multiple county
boundaries).  Storing them in a POLYGON-typed column causes a PostGIS type
constraint violation, silently rolling back the savepoint and leaving the alert
with no geometry.  Widening to the generic GEOMETRY type preserves all existing
Polygon data while allowing MultiPolygon (and any other valid geometry type).

Revision ID: 20260327_widen_cap_alerts_geom_type
Revises: 20260326_tts_pronunciation_rules
Create Date: 2026-03-27
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260327_widen_cap_alerts_geom_type"
down_revision = "20260326_tts_pronunciation_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Only applicable to PostgreSQL + PostGIS; skip silently for other backends.
    try:
        dialect = conn.dialect.name
        if dialect != "postgresql":
            return

        # Check the column exists and has the old POLYGON constraint.
        result = conn.execute(
            text(
                "SELECT type FROM geometry_columns "
                "WHERE f_table_name = 'cap_alerts' AND f_geometry_column = 'geom'"
            )
        ).fetchone()

        if result is None:
            # Column doesn't exist yet – nothing to do.
            return

        current_type = (result[0] or "").upper()
        if current_type == "GEOMETRY":
            # Already widened – idempotent.
            return

        # ALTER COLUMN to the generic GEOMETRY type (preserves all existing rows).
        conn.execute(
            text(
                "ALTER TABLE cap_alerts "
                "ALTER COLUMN geom TYPE geometry(GEOMETRY,4326) "
                "USING geom::geometry(GEOMETRY,4326)"
            )
        )
    except Exception:
        # Non-fatal: if PostGIS isn't installed or the table doesn't exist the
        # application will fall back to text storage anyway.
        pass


def downgrade() -> None:
    conn = op.get_bind()

    try:
        dialect = conn.dialect.name
        if dialect != "postgresql":
            return

        # Restore narrow POLYGON type – only safe if all stored geometries are
        # actually Polygons; rows with MultiPolygon geometry would fail the cast.
        conn.execute(
            text(
                "ALTER TABLE cap_alerts "
                "ALTER COLUMN geom TYPE geometry(POLYGON,4326) "
                "USING geom::geometry(POLYGON,4326)"
            )
        )
    except Exception:
        pass
