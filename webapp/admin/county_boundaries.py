"""Admin routes for US county boundary management."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request, current_app
from werkzeug.utils import secure_filename

from app_core.auth.roles import require_permission
from app_core.county_boundaries import (
    delete_counties,
    get_county_count,
    get_loaded_states,
    load_counties_from_shapefile,
    search_counties,
    STATE_ABBREV_TO_FIPS,
)

logger = logging.getLogger(__name__)

county_boundaries_bp = Blueprint(
    "county_boundaries", __name__, url_prefix="/admin"
)


@county_boundaries_bp.route("/county_boundaries")
@require_permission("system.configure")
def county_boundaries_page():
    """Admin page for managing US county boundaries."""
    total = get_county_count()
    states = get_loaded_states()

    # Check if bundled shapefile is available
    from app_core.county_boundaries import _find_bundled_shapefile
    bundled_path = _find_bundled_shapefile()

    return render_template(
        "admin/county_boundaries.html",
        total_counties=total,
        loaded_states=states,
        bundled_shapefile_available=bundled_path is not None,
        state_list=sorted(STATE_ABBREV_TO_FIPS.keys()),
    )


@county_boundaries_bp.route("/county_boundaries/info")
@require_permission("system.configure")
def county_boundaries_info():
    """Return county boundary stats as JSON."""
    return jsonify({
        "success": True,
        "total_counties": get_county_count(),
        "states": get_loaded_states(),
    })


@county_boundaries_bp.route("/county_boundaries/search")
@require_permission("system.configure")
def county_boundaries_search():
    """Search county boundaries."""
    query = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", 50)), 200)
    results = search_counties(query, limit=limit)
    return jsonify({"success": True, "results": results, "count": len(results)})


@county_boundaries_bp.route("/county_boundaries/load", methods=["POST"])
@require_permission("system.configure")
def county_boundaries_load():
    """Load county boundaries from bundled shapefile."""
    state_filter = request.form.get("state") or request.json.get("state") if request.is_json else request.form.get("state")
    replace = (request.form.get("replace") or (request.json.get("replace") if request.is_json else "")) == "true"

    from app_core.county_boundaries import _find_bundled_shapefile
    shp_path = _find_bundled_shapefile()
    if not shp_path:
        return jsonify({"success": False, "error": "Bundled shapefile not found on server"}), 404

    result = load_counties_from_shapefile(
        str(shp_path),
        state_filter=state_filter or None,
        replace=replace,
    )

    if result.get("error"):
        return jsonify({"success": False, "error": result["error"]}), 400

    state_label = f" for {state_filter}" if state_filter else ""
    return jsonify({
        "success": True,
        "message": (
            f"Loaded {result['inserted']} county boundaries{state_label}"
            f" ({result['skipped']} skipped, {result['errors']} errors)"
        ),
        **result,
    })


@county_boundaries_bp.route("/county_boundaries/upload", methods=["POST"])
@require_permission("system.configure")
def county_boundaries_upload():
    """Upload a shapefile ZIP and load county boundaries."""
    import tempfile
    import zipfile

    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    filename = secure_filename(uploaded.filename)
    if not filename.lower().endswith(".zip"):
        return jsonify({"success": False, "error": "Only .zip shapefile archives are accepted"}), 400

    state_filter = request.form.get("state") or None
    replace = request.form.get("replace") == "true"

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, filename)
        uploaded.save(zip_path)

        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tmpdir)
        except zipfile.BadZipFile:
            return jsonify({"success": False, "error": "Invalid ZIP file"}), 400

        # Find .shp file in extracted contents
        shp_files = list(Path(tmpdir).rglob("*.shp"))
        if not shp_files:
            return jsonify({"success": False, "error": "No .shp file found in ZIP archive"}), 400

        result = load_counties_from_shapefile(
            str(shp_files[0]),
            state_filter=state_filter,
            replace=replace,
        )

    if result.get("error"):
        return jsonify({"success": False, "error": result["error"]}), 400

    return jsonify({
        "success": True,
        "message": f"Loaded {result['inserted']} county boundaries from upload",
        **result,
    })


@county_boundaries_bp.route("/county_boundaries/delete", methods=["POST"])
@require_permission("system.configure")
def county_boundaries_delete():
    """Delete county boundaries, optionally filtered by state."""
    state_filter = None
    if request.is_json:
        state_filter = request.json.get("state")
    else:
        state_filter = request.form.get("state")

    count = delete_counties(state_filter=state_filter or None)
    label = f" for {state_filter}" if state_filter else ""
    return jsonify({
        "success": True,
        "message": f"Deleted {count} county boundaries{label}",
        "deleted": count,
    })


__all__ = ["county_boundaries_bp"]
