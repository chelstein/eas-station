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

"""
Audio Archive Management Routes

Provides a JSON API and minimal HTML page for inspecting and managing
on-disk audio archives produced by the AudioArchiver.

Endpoints
---------
GET  /admin/audio/archives
     Dashboard page listing all source archive directories.

GET  /api/audio/archives
     JSON: disk usage and file counts for every source archive directory.

GET  /api/audio/archives/<source_name>
     JSON: per-day breakdown for one source.

POST /api/audio/archives/<source_name>/purge
     Delete all archive files for the named source. Body (optional):
       { "days_older_than": 3 }   – purge only files older than N days
     Omit the body (or set days_older_than=0) to purge everything.
"""

import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template_string, request

logger = logging.getLogger(__name__)

# Default archive root – should match AudioArchiverConfig.output_dir.
# Override by passing archive_dir to register().
_DEFAULT_ARCHIVE_DIR = "archives"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dir_size(path: Path) -> int:
    """Recursively sum file sizes under *path*."""
    total = 0
    if not path.exists():
        return 0
    for f in path.rglob("*"):
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


def _format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for f in path.rglob("*") if f.is_file())


def _source_summary(source_dir: Path) -> Dict[str, Any]:
    """Return a summary dict for one source directory."""
    total_bytes = _dir_size(source_dir)
    total_files = _count_files(source_dir)

    # Newest file mtime
    newest_mtime: Optional[float] = None
    for f in source_dir.rglob("*"):
        if f.is_file():
            try:
                mt = f.stat().st_mtime
                if newest_mtime is None or mt > newest_mtime:
                    newest_mtime = mt
            except OSError:
                pass

    return {
        "source_name": source_dir.name,
        "total_bytes": total_bytes,
        "total_bytes_human": _format_bytes(total_bytes),
        "total_files": total_files,
        "newest_file_ts": newest_mtime,
        "newest_file_iso": (
            datetime.fromtimestamp(newest_mtime).isoformat() if newest_mtime else None
        ),
    }


def _source_detail(source_dir: Path) -> Dict[str, Any]:
    """Return a per-day breakdown for one source directory."""
    summary = _source_summary(source_dir)
    days: List[Dict[str, Any]] = []

    if source_dir.exists():
        for date_dir in sorted(source_dir.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue
            try:
                datetime.strptime(date_dir.name, "%Y-%m-%d")
            except ValueError:
                continue

            day_bytes = _dir_size(date_dir)
            files = sorted(
                (
                    {
                        "name": f.name,
                        "bytes": f.stat().st_size,
                        "bytes_human": _format_bytes(f.stat().st_size),
                        "mtime_iso": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    }
                    for f in date_dir.iterdir()
                    if f.is_file()
                ),
                key=lambda x: x["name"],
                reverse=True,
            )
            days.append(
                {
                    "date": date_dir.name,
                    "bytes": day_bytes,
                    "bytes_human": _format_bytes(day_bytes),
                    "file_count": len(files),
                    "files": files,
                }
            )

    summary["days"] = days
    return summary


def _purge_source(source_dir: Path, days_older_than: int = 0) -> Dict[str, Any]:
    """
    Delete archive files for one source.

    Args:
        source_dir: Root directory for the source.
        days_older_than: If > 0 only delete files/dirs older than this many
                         days.  If 0, delete everything.

    Returns:
        Dict with files_deleted, bytes_freed, error.
    """
    result: Dict[str, Any] = {"files_deleted": 0, "bytes_freed": 0, "error": None}

    if not source_dir.exists():
        return result

    cutoff = (
        datetime.now() - timedelta(days=days_older_than)
        if days_older_than > 0
        else None
    )

    try:
        for date_dir in sorted(source_dir.iterdir()):
            if not date_dir.is_dir():
                continue

            if cutoff is not None:
                try:
                    dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
                except ValueError:
                    continue
                if dir_date >= cutoff:
                    continue  # Keep this directory

            for f in date_dir.iterdir():
                if f.is_file():
                    try:
                        result["bytes_freed"] += f.stat().st_size
                        f.unlink()
                        result["files_deleted"] += 1
                    except OSError as exc:
                        logger.warning("Archive purge: could not delete %s: %s", f, exc)
            try:
                date_dir.rmdir()
            except OSError:
                pass  # Directory not empty – leave it

    except Exception as exc:
        result["error"] = str(exc)
        logger.error("Archive purge error for %s: %s", source_dir, exc)

    return result


# ---------------------------------------------------------------------------
# Simple dashboard template (inline – no separate file needed)
# ---------------------------------------------------------------------------

_DASHBOARD_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Audio Archives – EAS Station</title>
<style>
  body { font-family: sans-serif; margin: 2rem; color: #222; }
  h1 { font-size: 1.5rem; margin-bottom: 1rem; }
  table { border-collapse: collapse; width: 100%; max-width: 900px; }
  th, td { border: 1px solid #ccc; padding: .5rem .75rem; text-align: left; }
  th { background: #f0f0f0; }
  .purge-btn { background: #c0392b; color: #fff; border: none; padding: .3rem .75rem;
               cursor: pointer; border-radius: 3px; }
  .purge-btn:hover { background: #a93226; }
  .msg { margin: .5rem 0; padding: .5rem; border-radius: 3px; }
  .msg.ok { background: #d5f5e3; border: 1px solid #27ae60; }
  .msg.err { background: #fadbd8; border: 1px solid #c0392b; }
</style>
</head>
<body>
<h1>Audio Archives</h1>

<div id="status"></div>

<table id="archives-table">
  <thead><tr>
    <th>Source</th>
    <th>Files</th>
    <th>Disk Usage</th>
    <th>Newest File</th>
    <th>Actions</th>
  </tr></thead>
  <tbody id="archives-body">
    <tr><td colspan="5">Loading…</td></tr>
  </tbody>
</table>

<script>
function showMsg(text, ok) {
  const el = document.getElementById('status');
  el.innerHTML = '<div class="msg ' + (ok ? 'ok' : 'err') + '">' + text + '</div>';
  setTimeout(() => { el.innerHTML = ''; }, 5000);
}

function renderTable(sources) {
  const tbody = document.getElementById('archives-body');
  if (!sources.length) {
    tbody.innerHTML = '<tr><td colspan="5">No archives found.</td></tr>';
    return;
  }
  tbody.innerHTML = sources.map(s => {
    const newest = s.newest_file_iso
      ? new Date(s.newest_file_iso).toLocaleString()
      : '—';
    return '<tr>' +
      '<td>' + s.source_name + '</td>' +
      '<td>' + s.total_files + '</td>' +
      '<td>' + s.total_bytes_human + '</td>' +
      '<td>' + newest + '</td>' +
      '<td><button class="purge-btn" onclick="purge(' + JSON.stringify(s.source_name) + ')">Purge All</button></td>' +
    '</tr>';
  }).join('');
}

function loadTable() {
  fetch('/api/audio/archives')
    .then(r => r.json())
    .then(d => renderTable(d.sources || []))
    .catch(e => showMsg('Error loading archives: ' + e, false));
}

function purge(sourceName) {
  if (!confirm('Delete ALL archive files for "' + sourceName + '"?')) return;
  fetch('/api/audio/archives/' + encodeURIComponent(sourceName) + '/purge', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({}),
  })
  .then(r => r.json())
  .then(d => {
    if (d.error) { showMsg('Purge failed: ' + d.error, false); }
    else { showMsg('Purged ' + d.files_deleted + ' file(s) (' + d.bytes_freed_human + ')', true); loadTable(); }
  })
  .catch(e => showMsg('Request failed: ' + e, false));
}

loadTable();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def register(app: Flask, logger_arg, archive_dir: str = _DEFAULT_ARCHIVE_DIR) -> None:
    """Attach audio archive management routes to *app*.

    Args:
        app: Flask application.
        logger_arg: Module-level logger supplied by the route registration
                    framework.
        archive_dir: Root directory where AudioArchiver writes files.  Must
                     match ``AudioArchiverConfig.output_dir``.
    """

    route_logger = logger_arg.getChild("routes_audio_archive")
    archive_root = Path(archive_dir)

    # ------------------------------------------------------------------
    # Dashboard page
    # ------------------------------------------------------------------

    @app.route("/admin/audio/archives")
    def audio_archives_dashboard():
        return _DASHBOARD_TEMPLATE, 200, {"Content-Type": "text/html; charset=utf-8"}

    # ------------------------------------------------------------------
    # API: list all sources
    # ------------------------------------------------------------------

    @app.route("/api/audio/archives", methods=["GET"])
    def api_audio_archives_list():
        sources: List[Dict[str, Any]] = []

        if archive_root.exists():
            for source_dir in sorted(archive_root.iterdir()):
                if source_dir.is_dir():
                    try:
                        sources.append(_source_summary(source_dir))
                    except Exception as exc:
                        route_logger.warning(
                            "Error summarising archive dir %s: %s", source_dir, exc
                        )

        total_bytes = sum(s["total_bytes"] for s in sources)
        total_files = sum(s["total_files"] for s in sources)

        return jsonify(
            {
                "sources": sources,
                "total_bytes": total_bytes,
                "total_bytes_human": _format_bytes(total_bytes),
                "total_files": total_files,
                "archive_dir": str(archive_root),
            }
        )

    # ------------------------------------------------------------------
    # API: detail for one source
    # ------------------------------------------------------------------

    @app.route("/api/audio/archives/<source_name>", methods=["GET"])
    def api_audio_archives_source(source_name: str):
        # Restrict to the archive root (no path traversal)
        source_dir = archive_root / Path(source_name).name

        if not source_dir.exists():
            return jsonify({"error": f"No archives for '{source_name}'"}), 404

        try:
            detail = _source_detail(source_dir)
            return jsonify(detail)
        except Exception as exc:
            route_logger.error("Error reading archive detail for %s: %s", source_name, exc)
            return jsonify({"error": str(exc)}), 500

    # ------------------------------------------------------------------
    # API: purge one source
    # ------------------------------------------------------------------

    @app.route("/api/audio/archives/<source_name>/purge", methods=["POST"])
    def api_audio_archives_purge(source_name: str):
        # Restrict to the archive root (no path traversal)
        source_dir = archive_root / Path(source_name).name

        body: Dict[str, Any] = {}
        try:
            body = request.get_json(silent=True) or {}
        except Exception:
            pass

        days_older_than = 0
        try:
            days_older_than = int(body.get("days_older_than", 0))
        except (TypeError, ValueError):
            pass

        route_logger.info(
            "Archive purge requested for '%s' (days_older_than=%d)",
            source_name,
            days_older_than,
        )

        result = _purge_source(source_dir, days_older_than=days_older_than)
        result["bytes_freed_human"] = _format_bytes(result["bytes_freed"])

        status = 200 if result["error"] is None else 500
        return jsonify(result), status

    route_logger.info("Audio archive routes registered (archive_dir=%s)", archive_root)


__all__ = ["register"]
