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

from typing import Any, Dict, List, Tuple

from flask import current_app
from sqlalchemy import func

from app_core.models import Boundary, CAPAlert, Intersection
from app_core.extensions import db


def _us_county_table_exists() -> bool:
    """Return True if the us_county_boundaries table has been created and has rows."""
    from sqlalchemy import text
    try:
        result = db.session.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'us_county_boundaries')")
        ).scalar()
        return bool(result)
    except Exception:
        return False


def _build_geometry_from_same_codes(alert) -> bool:
    """Build alert geometry from SAME geocodes via US county boundary lookup.

    When an IPAWS alert has no inline polygon but carries SAME geocodes,
    this function looks up matching county boundaries in ``us_county_boundaries``
    and stores a union geometry on the alert.  Handles statewide codes
    (ending in '000') by looking up all counties for that state.

    Returns True if geometry was set, False otherwise.
    """
    if not _us_county_table_exists():
        return False

    raw_json = alert.raw_json if isinstance(alert.raw_json, dict) else {}
    same_codes = raw_json.get('properties', {}).get('geocode', {}).get('SAME', [])
    if not same_codes:
        return False

    try:
        from sqlalchemy import text

        # Convert 6-digit SAME codes to 5-digit GEOIDs and collect state FIPS
        # for statewide codes
        geoids = set()
        statewide_state_fps = set()

        for code in same_codes:
            if not isinstance(code, str) or len(code) < 5:
                continue
            # Statewide codes end in 000 → look up all counties for that state
            if code.endswith('000'):
                # SAME 039000 → state FIPS "39"
                state_fp = code.lstrip('0')[:2] if len(code.lstrip('0')) >= 3 else code[1:3]
                # Ensure 2-digit state FIPS
                if len(code) == 6:
                    state_fp = code[1:3]
                statewide_state_fps.add(state_fp)
                continue
            # County codes: 039137 → GEOID 39137
            geoid = code.lstrip('0')
            if len(geoid) < 4:
                continue
            geoids.add(geoid)

        if not geoids and not statewide_state_fps:
            return False

        # Build WHERE clause for matching counties
        conditions = []
        params = {}

        if geoids:
            conditions.append("geoid = ANY(:geoids)")
            params["geoids"] = list(geoids)

        if statewide_state_fps:
            conditions.append("statefp = ANY(:state_fps)")
            params["state_fps"] = list(statewide_state_fps)

        where_clause = " OR ".join(conditions)

        # Count matches first
        count = db.session.execute(
            text(f"SELECT COUNT(*) FROM us_county_boundaries WHERE ({where_clause}) AND geom IS NOT NULL"),
            params,
        ).scalar()

        if not count:
            return False

        # Build union geometry
        union_result = db.session.execute(
            text(f"""
                SELECT ST_SetSRID(ST_Multi(ST_Union(geom)), 4326)
                FROM us_county_boundaries
                WHERE ({where_clause})
                  AND geom IS NOT NULL
            """),
            params,
        ).scalar()

        if union_result is None:
            return False

        alert.geom = union_result
        db.session.commit()
        current_app.logger.info(
            'Built geometry from %d SAME codes (%d counties matched) for alert %s',
            len(same_codes), count, alert.identifier,
        )
        return True

    except Exception as exc:
        current_app.logger.debug(
            'SAME geometry lookup failed for %s: %s', alert.identifier, exc,
        )
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


def calculate_coverage_percentages(alert_id, intersections):
    """Calculate coverage metrics for each boundary type and the overall county."""

    coverage_data: Dict[str, Dict[str, Any]] = {}

    try:
        logger = current_app.logger
        alert = CAPAlert.query.get(alert_id)
        if not alert or not alert.geom:
            # Try to build geometry from SAME codes (IPAWS alerts)
            if alert and not alert.geom:
                if _build_geometry_from_same_codes(alert):
                    db.session.refresh(alert)
            if not alert or not alert.geom:
                return coverage_data

        boundary_types: Dict[str, List[Tuple[Intersection, Boundary]]] = {}
        for intersection, boundary in intersections:
            boundary_types.setdefault(boundary.type, []).append((intersection, boundary))

        for boundary_type, boundaries in boundary_types.items():
            all_boundaries_of_type = Boundary.query.filter_by(type=boundary_type).all()
            if not all_boundaries_of_type:
                continue

            total_area_query = db.session.query(
                func.sum(func.ST_Area(Boundary.geom)).label('total_area')
            ).filter(Boundary.type == boundary_type).first()

            total_area = total_area_query.total_area if total_area_query and total_area_query.total_area else 0

            intersected_area = sum(
                intersection.intersection_area or 0 for intersection, _ in boundaries
            )

            coverage_percentage = 0.0
            if total_area > 0:
                coverage_percentage = (intersected_area / total_area) * 100
                coverage_percentage = min(100.0, max(0.0, coverage_percentage))

            coverage_data[boundary_type] = {
                'total_boundaries': len(all_boundaries_of_type),
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


__all__ = ['calculate_coverage_percentages', '_build_geometry_from_same_codes']
