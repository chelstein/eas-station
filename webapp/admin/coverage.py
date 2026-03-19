"""
EAS Station - Emergency Alert System
Copyright (c) 2025-2026 Timothy Kramer (KR8MER)

This file is part of EAS Station.

EAS Station is dual-licensed software:
- GNU Affero General Public License v3 (AGPL-3.0) for open-source use
- Commercial License for proprietary use

You should have received a copy of both licenses with this software.
For more information, see LICENSE and LICENSE-COMMERCIAL files.

IMPORTANT: This software cannot be rebranded or have attribution removed.
See NOTICE file for complete terms.

Repository: https://github.com/KR8MER/eas-station
"""

from __future__ import annotations

"""Coverage calculation helpers for admin routes."""

import json
from typing import Any, Dict, List, Tuple

from flask import current_app
from sqlalchemy import func, text

from app_core.models import Boundary, CAPAlert, Intersection
from app_core.extensions import db


def _us_county_table_ready() -> bool:
    """Return True if the us_county_boundaries table exists and has rows."""
    try:
        row_check = db.session.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables"
                "  WHERE table_name = 'us_county_boundaries'"
                ")"
            )
        ).scalar()
        if not row_check:
            return False
        count = db.session.execute(
            text("SELECT COUNT(*) FROM us_county_boundaries LIMIT 1")
        ).scalar()
        return bool(count and count > 0)
    except Exception:
        return False


def try_build_geometry_from_same_codes(alert_id: int) -> bool:
    """Attempt to build alert geometry from available sources.

    Tries three sources in order:
    1. ``alert.geom`` already set – return immediately.
    2. Polygon embedded in ``raw_json['geometry']`` (NOAA GeoJSON feature body).
    3. SAME geocodes matched against the ``us_county_boundaries`` table.

    Uses a SAVEPOINT so that failures never corrupt the caller's session.
    Call this *before* calculate_coverage_percentages, not inside it.

    Returns True if the alert now has geometry, False otherwise.
    """
    try:
        alert = CAPAlert.query.get(alert_id)
        if not alert or alert.geom:
            return bool(alert and alert.geom)

        raw_json = alert.raw_json if isinstance(alert.raw_json, dict) else {}

        # --- Priority 1: use the polygon embedded in raw_json['geometry'] ---
        raw_geom = raw_json.get('geometry')
        if raw_geom and isinstance(raw_geom, dict) and raw_geom.get('coordinates'):
            nested = db.session.begin_nested()
            try:
                geom_json = json.dumps(raw_geom)
                result = db.session.execute(
                    text("SELECT ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)"),
                    {"g": geom_json},
                ).scalar()
                if result is not None:
                    alert.geom = result
                    nested.commit()
                    db.session.commit()
                    current_app.logger.info(
                        'Built geometry from raw_json[geometry] for alert %s',
                        alert.identifier,
                    )
                    return True
                nested.rollback()
            except Exception as exc:
                current_app.logger.debug(
                    'raw_json[geometry] parse failed for alert %s: %s',
                    alert_id, exc,
                )
                nested.rollback()

        # --- Priority 2: build from SAME geocodes via county boundary table ---
        if not _us_county_table_ready():
            return False

        same_codes = raw_json.get('properties', {}).get('geocode', {}).get('SAME', [])
        if not same_codes:
            return False

        geoids = set()
        statewide_state_fps = set()

        for code in same_codes:
            if not isinstance(code, str) or len(code) < 5:
                continue
            if code.endswith('000'):
                # Statewide: SAME 039000 → state FIPS "39"
                state_fp = code[1:3] if len(code) == 6 else code.lstrip('0')[:2]
                statewide_state_fps.add(state_fp)
                continue
            geoid = code.lstrip('0')
            if len(geoid) >= 4:
                geoids.add(geoid)

        if not geoids and not statewide_state_fps:
            return False

        # Use a SAVEPOINT so that any DB error is contained
        nested = db.session.begin_nested()
        try:
            conditions = []
            params: Dict[str, Any] = {}

            if geoids:
                conditions.append("geoid = ANY(:geoids)")
                params["geoids"] = list(geoids)
            if statewide_state_fps:
                conditions.append("statefp = ANY(:state_fps)")
                params["state_fps"] = list(statewide_state_fps)

            where_clause = " OR ".join(conditions)

            count = db.session.execute(
                text(f"SELECT COUNT(*) FROM us_county_boundaries WHERE ({where_clause}) AND geom IS NOT NULL"),
                params,
            ).scalar()

            if not count:
                nested.rollback()
                return False

            union_geom = db.session.execute(
                text(f"""
                    SELECT ST_SetSRID(ST_Multi(ST_Union(geom)), 4326)
                    FROM us_county_boundaries
                    WHERE ({where_clause}) AND geom IS NOT NULL
                """),
                params,
            ).scalar()

            if union_geom is None:
                nested.rollback()
                return False

            alert.geom = union_geom
            nested.commit()
            db.session.commit()

            current_app.logger.info(
                'Built geometry from %d SAME codes (%d counties) for alert %s',
                len(same_codes), count, alert.identifier,
            )
            return True

        except Exception:
            nested.rollback()
            return False

    except Exception as exc:
        current_app.logger.debug('SAME geometry build skipped for alert %s: %s', alert_id, exc)
        return False


def calculate_coverage_percentages(alert_id, intersections):
    """Calculate coverage metrics for each boundary type and the overall county.

    Important: call ``try_build_geometry_from_same_codes`` before this function
    so that alerts with SAME-derived geometry are handled.
    """

    coverage_data: Dict[str, Dict[str, Any]] = {}

    try:
        alert = CAPAlert.query.get(alert_id)
        if not alert or not alert.geom:
            return coverage_data

        boundary_types: Dict[str, List[Tuple[Intersection, Boundary]]] = {}
        for intersection, boundary in intersections:
            boundary_types.setdefault(boundary.type, []).append((intersection, boundary))

        for boundary_type, boundaries in boundary_types.items():
            if not boundaries:
                continue

            # Count all boundaries of this type for display purposes
            total_count = Boundary.query.filter_by(type=boundary_type).count()
            if not total_count:
                continue

            # Coverage percentage is calculated as:
            #   sum(intersection areas) / sum(full areas of intersecting boundaries)
            # This answers "what percentage of the affected boundary area does the
            # alert actually cover?" rather than dividing by all boundaries system-wide.
            boundary_ids = [boundary.id for _, boundary in boundaries]
            total_area_query = db.session.query(
                func.sum(func.ST_Area(Boundary.geom)).label('total_area')
            ).filter(Boundary.id.in_(boundary_ids)).first()

            total_area = total_area_query.total_area if total_area_query and total_area_query.total_area else 0

            intersected_area = sum(
                intersection.intersection_area or 0 for intersection, _ in boundaries
            )

            coverage_percentage = 0.0
            if total_area > 0:
                coverage_percentage = (intersected_area / total_area) * 100
                coverage_percentage = min(100.0, max(0.0, coverage_percentage))

            coverage_data[boundary_type] = {
                'total_boundaries': total_count,
                'affected_boundaries': len(boundaries),
                'coverage_percentage': round(coverage_percentage, 1),
                'total_area_sqm': total_area,
                'intersected_area_sqm': intersected_area,
            }

        county_boundary = Boundary.query.filter_by(type='county').first()
        if county_boundary and county_boundary.geom:
            county_intersection_query = db.session.query(
                func.ST_Area(
                    func.ST_Intersection(alert.geom, county_boundary.geom)
                ).label('intersection_area'),
                func.ST_Area(county_boundary.geom).label('total_county_area'),
            ).first()

            if county_intersection_query:
                county_coverage = 0.0
                if county_intersection_query.total_county_area:
                    county_coverage = (
                        county_intersection_query.intersection_area
                        / county_intersection_query.total_county_area
                    ) * 100
                    county_coverage = min(100.0, max(0.0, county_coverage))

                coverage_data['county'] = {
                    'coverage_percentage': round(county_coverage, 1),
                    'total_area_sqm': county_intersection_query.total_county_area,
                    'intersected_area_sqm': county_intersection_query.intersection_area,
                }

    except Exception as exc:  # pragma: no cover - defensive logging
        current_app.logger.error('Error calculating coverage percentages: %s', exc)

    return coverage_data


__all__ = ['calculate_coverage_percentages', 'try_build_geometry_from_same_codes']
