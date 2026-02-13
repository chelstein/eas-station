#!/usr/bin/env python3
"""Load US county boundaries from Census Bureau TIGER/Line shapefiles.

Downloads (if needed) and imports county boundary polygons into the
``us_county_boundaries`` table so that IPAWS alerts with SAME geocodes
can be rendered on the map even when they carry no inline polygon.

Usage::

    # Load all US counties (creates table if needed)
    python scripts/load_us_county_boundaries.py

    # Load only Ohio counties
    python scripts/load_us_county_boundaries.py --state OH

    # Specify a local shapefile instead of downloading
    python scripts/load_us_county_boundaries.py --shapefile data/shapefiles/cb_2024_us_county_500k/cb_2024_us_county_500k.shp

Data source: US Census Bureau Cartographic Boundary Files (500k resolution)
https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SHAPEFILE_URL = (
    "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip"
)
DEFAULT_SHAPEFILE_DIR = PROJECT_ROOT / "data" / "shapefiles"
DEFAULT_SHAPEFILE_SUBDIR = "cb_2024_us_county_500k"
DEFAULT_SHAPEFILE_NAME = "cb_2024_us_county_500k.shp"

# US state FIPS-to-abbreviation mapping (for --state filter)
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


def _download_shapefile(dest_dir: Path) -> Path:
    """Download and extract the Census county shapefile."""
    import requests

    zip_path = dest_dir / "cb_2024_us_county_500k.zip"
    extract_dir = dest_dir / DEFAULT_SHAPEFILE_SUBDIR

    if (extract_dir / DEFAULT_SHAPEFILE_NAME).exists():
        print(f"Shapefile already exists at {extract_dir / DEFAULT_SHAPEFILE_NAME}")
        return extract_dir / DEFAULT_SHAPEFILE_NAME

    dest_dir.mkdir(parents=True, exist_ok=True)

    if not zip_path.exists():
        print(f"Downloading {SHAPEFILE_URL} ...")
        resp = requests.get(SHAPEFILE_URL, stream=True, timeout=120)
        resp.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                f.write(chunk)
        print(f"  Downloaded {zip_path.stat().st_size / 1024 / 1024:.1f} MB")

    print(f"Extracting to {extract_dir} ...")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)

    return extract_dir / DEFAULT_SHAPEFILE_NAME


def _load_shapefile(
    shp_path: str,
    state_filter: str | None = None,
    replace: bool = False,
) -> int:
    """Read shapefile and insert records into the database.

    Returns the number of records inserted.
    """
    import shapefile as shp
    from sqlalchemy import text

    from app_core.extensions import db
    from app_core.models import USCountyBoundary

    sf = shp.Reader(shp_path)
    fields = [f[0] for f in sf.fields[1:]]
    print(f"Shapefile fields: {fields}")
    print(f"Total records: {len(sf)}")

    # Determine state FIPS filter
    state_fips = None
    if state_filter:
        state_fips = STATE_ABBREV_TO_FIPS.get(state_filter.upper())
        if not state_fips:
            print(f"Unknown state abbreviation: {state_filter}")
            sys.exit(1)
        print(f"Filtering to state {state_filter} (FIPS {state_fips})")

    # Ensure the table exists
    db.create_all()

    if replace:
        if state_fips:
            deleted = USCountyBoundary.query.filter_by(statefp=state_fips).delete()
        else:
            deleted = USCountyBoundary.query.delete()
        db.session.commit()
        print(f"Deleted {deleted} existing records")

    inserted = 0
    skipped = 0

    for shape_rec in sf.iterShapeRecords():
        rec = shape_rec.record.as_dict()
        statefp = rec.get("STATEFP", "")

        if state_fips and statefp != state_fips:
            continue

        geoid = rec.get("GEOID", "")
        if not geoid:
            skipped += 1
            continue

        # Check for existing record
        existing = USCountyBoundary.query.filter_by(geoid=geoid).first()
        if existing and not replace:
            skipped += 1
            continue

        # Convert shape to GeoJSON
        geojson = shape_rec.shape.__geo_interface__
        import json
        geojson_str = json.dumps(geojson)

        if existing:
            # Update geometry
            existing.name = rec.get("NAME", "")
            existing.namelsad = rec.get("NAMELSAD", "")
            existing.stusps = rec.get("STUSPS", "")
            existing.state_name = rec.get("STATE_NAME", "")
            existing.aland = rec.get("ALAND")
            existing.awater = rec.get("AWATER")
            existing.geom = db.session.execute(
                text("SELECT ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))"),
                {"g": geojson_str},
            ).scalar()
        else:
            county = USCountyBoundary(
                statefp=statefp,
                countyfp=rec.get("COUNTYFP", ""),
                geoid=geoid,
                name=rec.get("NAME", ""),
                namelsad=rec.get("NAMELSAD", ""),
                stusps=rec.get("STUSPS", ""),
                state_name=rec.get("STATE_NAME", ""),
                aland=rec.get("ALAND"),
                awater=rec.get("AWATER"),
                geom=db.session.execute(
                    text("SELECT ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))"),
                    {"g": geojson_str},
                ).scalar(),
            )
            db.session.add(county)

        inserted += 1

        # Batch commit every 100 records
        if inserted % 100 == 0:
            db.session.commit()
            print(f"  Inserted {inserted} records...")

    db.session.commit()
    print(f"Done: {inserted} inserted, {skipped} skipped")
    return inserted


def main():
    parser = argparse.ArgumentParser(
        description="Load US county boundaries from Census TIGER/Line shapefiles"
    )
    parser.add_argument(
        "--shapefile",
        help="Path to a local .shp file (skips download)",
    )
    parser.add_argument(
        "--state",
        help="Only load counties for this state (e.g. OH, IN)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing records instead of skipping duplicates",
    )
    args = parser.parse_args()

    # Flask app context is required for database access
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:
        # dotenv not required if env is already configured
        pass

    from app import app
    with app.app_context():
        if args.shapefile:
            shp_path = args.shapefile
        else:
            shp_path = str(_download_shapefile(DEFAULT_SHAPEFILE_DIR))

        print(f"Loading from {shp_path}")
        count = _load_shapefile(shp_path, state_filter=args.state, replace=args.replace)
        print(f"\nLoaded {count} US county boundaries")


if __name__ == "__main__":
    main()
