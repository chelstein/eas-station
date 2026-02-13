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


def _build_geometry_from_same_codes(alert) -> bool:
    """Build alert geometry from SAME geocodes via US county boundary lookup.

    When an IPAWS alert has no inline polygon but carries SAME geocodes,
    this function looks up matching county boundaries in ``us_county_boundaries``
    and stores a union geometry on the alert.  Returns True if geometry was
    set, False otherwise.
    """
    try:
        from app_core.models import USCountyBoundary
    except ImportError:
        return False

    raw_json = alert.raw_json if isinstance(alert.raw_json, dict) else {}
    same_codes = raw_json.get('properties', {}).get('geocode', {}).get('SAME', [])
    if not same_codes:
        return False

    # Convert 6-digit SAME codes to 5-digit GEOIDs:  039137 -> 39137
    geoids = set()
    for code in same_codes:
        if not isinstance(code, str) or len(code) < 5:
            continue
        # SAME format: PSSCCC  (P=part, SS=state, CCC=county)
        # GEOID format: SSCCC
        # Statewide codes end in 000 - skip (no single county to look up)
        if code.endswith('000'):
            continue
        # Strip leading zero: 039137 -> 39137
        geoid = code.lstrip('0')
        if len(geoid) < 4:
            continue
        geoids.add(geoid)

    if not geoids:
        return False

    # Check if any matching rows exist
    count = USCountyBoundary.query.filter(
        USCountyBoundary.geoid.in_(geoids)
    ).count()
    if count == 0:
        return False

    # Build a union of all matching county geometries
    from sqlalchemy import text
    union_result = db.session.execute(
        text("""
            SELECT ST_SetSRID(ST_Multi(ST_Union(geom)), 4326)
            FROM us_county_boundaries
            WHERE geoid = ANY(:geoids)
              AND geom IS NOT NULL
        """),
        {"geoids": list(geoids)},
    ).scalar()

    if union_result is None:
        return False

    alert.geom = union_result
    db.session.commit()
    current_app.logger.info(
        'Built geometry from %d SAME codes (%d matched) for alert %s',
        len(same_codes), count, alert.identifier,
    )
    return True


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
