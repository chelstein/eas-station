"""US county boundary management for FIPS-based alert geometry.

Provides startup auto-loading and admin helpers for importing Census Bureau
TIGER/Line county boundary shapefiles into the ``us_county_boundaries`` table.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import func, text

from .extensions import db
from .models import USCountyBoundary

logger = logging.getLogger(__name__)

# Where the bundled shapefile lives (relative to project root)
_BUNDLED_SHAPEFILE_DIR = Path("data") / "shapefiles" / "cb_2024_us_county_500k"
_BUNDLED_SHAPEFILE_NAME = "cb_2024_us_county_500k.shp"

# State FIPS-to-abbreviation mapping
STATE_ABBREV_TO_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12",
    "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18",
    "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23",
    "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28",
    "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38",
    "OH": "39", "OK": "40", "OR": "41", "PA": "42", "PR": "72",
    "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48",
    "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54",
    "WI": "55", "WY": "56",
}

STATE_FIPS_TO_ABBREV = {v: k for k, v in STATE_ABBREV_TO_FIPS.items()}


def _find_bundled_shapefile() -> Optional[Path]:
    """Locate the bundled county shapefile relative to the project root."""
    # Try a few common project roots
    for base in [
        Path(os.getcwd()),
        Path(__file__).resolve().parent.parent,
        Path("/opt/eas-station"),
    ]:
        candidate = base / _BUNDLED_SHAPEFILE_DIR / _BUNDLED_SHAPEFILE_NAME
        if candidate.exists():
            return candidate
    return None


def _table_exists() -> bool:
    """Check if the us_county_boundaries table exists."""
    try:
        result = db.session.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                 "WHERE table_name = 'us_county_boundaries')")
        ).scalar()
        return bool(result)
    except Exception:
        return False


def get_county_count(state_filter: Optional[str] = None) -> int:
    """Return number of county boundary records in the database."""
    if not _table_exists():
        return 0
    try:
        q = USCountyBoundary.query
        if state_filter:
            fips = STATE_ABBREV_TO_FIPS.get(state_filter.upper(), state_filter)
            q = q.filter_by(statefp=fips)
        return q.count()
    except Exception:
        return 0


def get_loaded_states() -> List[Dict[str, Any]]:
    """Return a list of states with their county counts."""
    if not _table_exists():
        return []
    try:
        rows = (
            db.session.query(
                USCountyBoundary.statefp,
                USCountyBoundary.stusps,
                USCountyBoundary.state_name,
                func.count(USCountyBoundary.id).label("county_count"),
            )
            .group_by(
                USCountyBoundary.statefp,
                USCountyBoundary.stusps,
                USCountyBoundary.state_name,
            )
            .order_by(USCountyBoundary.state_name)
            .all()
        )
        return [
            {
                "statefp": r.statefp,
                "stusps": r.stusps,
                "state_name": r.state_name,
                "county_count": r.county_count,
            }
            for r in rows
        ]
    except Exception:
        return []


def search_counties(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Search counties by name, GEOID, or state."""
    if not _table_exists():
        return []
    try:
        q = USCountyBoundary.query
        if query:
            pattern = f"%{query}%"
            q = q.filter(
                db.or_(
                    USCountyBoundary.name.ilike(pattern),
                    USCountyBoundary.namelsad.ilike(pattern),
                    USCountyBoundary.geoid.ilike(pattern),
                    USCountyBoundary.stusps.ilike(pattern),
                    USCountyBoundary.state_name.ilike(pattern),
                )
            )
        results = q.order_by(USCountyBoundary.state_name, USCountyBoundary.name).limit(limit).all()
        return [
            {
                "id": c.id,
                "geoid": c.geoid,
                "same_code": c.same_code,
                "name": c.name,
                "namelsad": c.namelsad,
                "stusps": c.stusps,
                "state_name": c.state_name,
            }
            for c in results
        ]
    except Exception:
        return []


def load_counties_from_shapefile(
    shp_path: str,
    state_filter: Optional[str] = None,
    replace: bool = False,
) -> Dict[str, Any]:
    """Load county boundaries from a shapefile into the database.

    Returns a summary dict with keys: inserted, skipped, errors, total.
    """
    import shapefile as shp

    result = {"inserted": 0, "skipped": 0, "errors": 0, "total": 0}

    try:
        sf = shp.Reader(shp_path)
    except Exception as exc:
        return {**result, "error": f"Could not read shapefile: {exc}"}

    state_fips = None
    if state_filter:
        state_fips = STATE_ABBREV_TO_FIPS.get(state_filter.upper())
        if not state_fips:
            return {**result, "error": f"Unknown state: {state_filter}"}

    # Ensure the table exists
    db.create_all()

    if replace:
        if state_fips:
            USCountyBoundary.query.filter_by(statefp=state_fips).delete()
        else:
            USCountyBoundary.query.delete()
        db.session.commit()

    for shape_rec in sf.iterShapeRecords():
        rec = shape_rec.record.as_dict()
        result["total"] += 1
        statefp = rec.get("STATEFP", "")

        if state_fips and statefp != state_fips:
            continue

        geoid = rec.get("GEOID", "")
        if not geoid:
            result["skipped"] += 1
            continue

        existing = USCountyBoundary.query.filter_by(geoid=geoid).first()
        if existing and not replace:
            result["skipped"] += 1
            continue

        try:
            geojson_str = json.dumps(shape_rec.shape.__geo_interface__)
            geom = db.session.execute(
                text("SELECT ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))"),
                {"g": geojson_str},
            ).scalar()

            if existing:
                existing.name = rec.get("NAME", "")
                existing.namelsad = rec.get("NAMELSAD", "")
                existing.stusps = rec.get("STUSPS", "")
                existing.state_name = rec.get("STATE_NAME", "")
                existing.aland = rec.get("ALAND")
                existing.awater = rec.get("AWATER")
                existing.geom = geom
            else:
                db.session.add(USCountyBoundary(
                    statefp=statefp,
                    countyfp=rec.get("COUNTYFP", ""),
                    geoid=geoid,
                    name=rec.get("NAME", ""),
                    namelsad=rec.get("NAMELSAD", ""),
                    stusps=rec.get("STUSPS", ""),
                    state_name=rec.get("STATE_NAME", ""),
                    aland=rec.get("ALAND"),
                    awater=rec.get("AWATER"),
                    geom=geom,
                ))

            result["inserted"] += 1

            if result["inserted"] % 100 == 0:
                db.session.commit()

        except Exception as exc:
            result["errors"] += 1
            logger.warning("Error loading county %s: %s", geoid, exc)

    db.session.commit()
    return result


def delete_counties(state_filter: Optional[str] = None) -> int:
    """Delete county boundaries, optionally filtered by state. Returns count deleted."""
    if not _table_exists():
        return 0
    q = USCountyBoundary.query
    if state_filter:
        fips = STATE_ABBREV_TO_FIPS.get(state_filter.upper(), state_filter)
        q = q.filter_by(statefp=fips)
    count = q.delete()
    db.session.commit()
    return count


def ensure_us_county_boundaries(app_logger=None) -> bool:
    """Auto-load US county boundaries from bundled shapefile if table is empty.

    Called during app startup.  Only loads if the table has zero rows and
    the bundled shapefile is present on disk.  Returns True on success.
    """
    log = app_logger or logger

    try:
        # Create table if needed
        db.create_all()

        count = get_county_count()
        if count > 0:
            log.info("US county boundaries: %d records already loaded", count)
            return True

        shp_path = _find_bundled_shapefile()
        if not shp_path:
            log.info(
                "US county boundaries: no bundled shapefile found; "
                "load via Admin > County Boundaries or run "
                "scripts/load_us_county_boundaries.py"
            )
            return False

        log.info("Loading US county boundaries from %s ...", shp_path)
        result = load_counties_from_shapefile(str(shp_path))
        log.info(
            "US county boundaries loaded: %d inserted, %d skipped, %d errors",
            result["inserted"], result["skipped"], result["errors"],
        )
        return result["inserted"] > 0

    except Exception as exc:
        log.warning("Could not load US county boundaries: %s", exc)
        return False


__all__ = [
    "ensure_us_county_boundaries",
    "get_county_count",
    "get_loaded_states",
    "search_counties",
    "load_counties_from_shapefile",
    "delete_counties",
    "STATE_ABBREV_TO_FIPS",
    "STATE_FIPS_TO_ABBREV",
]
