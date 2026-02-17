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

All archive management is performed from the web UI — no CLI required.

Endpoints
---------
GET  /admin/audio/archives
     Full management dashboard (HTML).

GET  /api/audio/archives
     JSON: disk stats for every source archive directory.

GET  /api/audio/archives/<source_name>/settings
     JSON: archiver config stored in AudioSourceConfigDB.config_params["archive"].

POST /api/audio/archives/<source_name>/settings
     Save archiver config to DB (does not start/stop the archiver).
     Body: AudioArchiverConfig fields (enabled, output_dir, segment_duration_seconds,
           retention_days, max_disk_bytes, format, bitrate).

POST /api/audio/archives/<source_name>/start
     Save config to DB (enabled=true) and send Redis command to audio-service
     to start the archiver immediately.

POST /api/audio/archives/<source_name>/stop
     Send Redis command to stop the archiver and set enabled=false in DB.

POST /api/audio/archives/<source_name>/purge
     Delete archive files.  Body (optional): {"days_older_than": N}

GET  /api/audio/archives/sources
     JSON: all AudioSourceConfigDB records with their archive config.
"""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request, send_file

logger = logging.getLogger(__name__)

_DEFAULT_ARCHIVE_DIR = "archives"


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def _dir_size(path: Path) -> int:
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


def _count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for f in path.rglob("*") if f.is_file())


def _format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _newest_mtime(source_dir: Path) -> Optional[float]:
    best: Optional[float] = None
    if source_dir.exists():
        for f in source_dir.rglob("*"):
            if f.is_file():
                try:
                    mt = f.stat().st_mtime
                    if best is None or mt > best:
                        best = mt
                except OSError:
                    pass
    return best


def _source_disk_summary(source_dir: Path) -> Dict[str, Any]:
    total_bytes = _dir_size(source_dir)
    total_files = _count_files(source_dir)
    newest = _newest_mtime(source_dir)
    return {
        "source_name": source_dir.name,
        "total_bytes": total_bytes,
        "total_bytes_human": _format_bytes(total_bytes),
        "total_files": total_files,
        "newest_file_ts": newest,
        "newest_file_iso": datetime.fromtimestamp(newest).isoformat() if newest else None,
    }


def _purge_source(source_dir: Path, days_older_than: int = 0) -> Dict[str, Any]:
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
                    continue
            for f in date_dir.iterdir():
                if f.is_file():
                    try:
                        result["bytes_freed"] += f.stat().st_size
                        f.unlink()
                        result["files_deleted"] += 1
                    except OSError as exc:
                        logger.warning("Archive purge: cannot delete %s: %s", f, exc)
            try:
                date_dir.rmdir()
            except OSError:
                pass
    except Exception as exc:
        result["error"] = str(exc)
        logger.error("Archive purge error for %s: %s", source_dir, exc)

    return result


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_DEFAULT_ARCHIVE_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "output_dir": "archives",
    "segment_duration_seconds": 3600,
    "retention_days": 7,
    "max_disk_bytes": 0,
    "format": "wav",
    "bitrate": 128,
}


def _get_archive_config(source_name: str) -> Optional[Dict[str, Any]]:
    """Return the archive config for *source_name* from the DB, or None if not found."""
    try:
        from app_core.models import AudioSourceConfigDB
        db_config = AudioSourceConfigDB.query.filter_by(name=source_name).first()
        if db_config is None:
            return None
        config_params = db_config.config_params or {}
        archive = dict(_DEFAULT_ARCHIVE_CONFIG)
        archive.update(config_params.get("archive", {}))
        return archive
    except Exception as exc:
        logger.error("Error reading archive config for '%s': %s", source_name, exc)
        return None


def _save_archive_config(source_name: str, archive_cfg: Dict[str, Any]) -> bool:
    """Merge *archive_cfg* into AudioSourceConfigDB.config_params["archive"]."""
    try:
        from app_core.extensions import db
        from app_core.models import AudioSourceConfigDB
        db_config = AudioSourceConfigDB.query.filter_by(name=source_name).first()
        if db_config is None:
            return False
        config_params = dict(db_config.config_params or {})
        existing = dict(_DEFAULT_ARCHIVE_CONFIG)
        existing.update(config_params.get("archive", {}))
        existing.update(archive_cfg)
        config_params["archive"] = existing
        db_config.config_params = config_params
        db.session.commit()
        return True
    except Exception as exc:
        logger.error("Error saving archive config for '%s': %s", source_name, exc)
        try:
            from app_core.extensions import db
            db.session.rollback()
        except Exception:
            pass
        return False


def _all_sources_with_archive_config() -> List[Dict[str, Any]]:
    """Return all AudioSourceConfigDB records with their archive config."""
    try:
        from app_core.models import AudioSourceConfigDB
        rows = AudioSourceConfigDB.query.order_by(AudioSourceConfigDB.name).all()
        result = []
        for row in rows:
            config_params = row.config_params or {}
            archive = dict(_DEFAULT_ARCHIVE_CONFIG)
            archive.update(config_params.get("archive", {}))
            result.append({
                "source_name": row.name,
                "source_type": row.source_type,
                "enabled": row.enabled,
                "archive": archive,
            })
        return result
    except Exception as exc:
        logger.error("Error listing sources: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def register(app: Flask, logger_arg, archive_dir: str = _DEFAULT_ARCHIVE_DIR) -> None:
    """Attach audio archive management routes to *app*."""

    route_logger = logger_arg.getChild("routes_audio_archive")
    archive_root = Path(archive_dir)

    # ------------------------------------------------------------------
    # Dashboard page
    # ------------------------------------------------------------------

    @app.route("/admin/audio/archives")
    def audio_archives_dashboard():
        return render_template("admin/audio_archives.html")

    # ------------------------------------------------------------------
    # API: all sources with settings + disk stats
    # ------------------------------------------------------------------

    @app.route("/api/audio/archives/sources", methods=["GET"])
    def api_audio_archives_sources():
        sources = _all_sources_with_archive_config()

        # Enrich each source with its current disk usage
        for s in sources:
            source_dir = archive_root / s["source_name"]
            disk = _source_disk_summary(source_dir)
            s["disk_bytes"] = disk["total_bytes"]
            s["disk_bytes_human"] = disk["total_bytes_human"]
            s["disk_files"] = disk["total_files"]
            s["newest_file_iso"] = disk["newest_file_iso"]

        return jsonify({"sources": sources, "archive_dir": str(archive_root)})

    # ------------------------------------------------------------------
    # API: disk-only summary (no DB lookup)
    # ------------------------------------------------------------------

    @app.route("/api/audio/archives", methods=["GET"])
    def api_audio_archives_list():
        sources: List[Dict[str, Any]] = []
        if archive_root.exists():
            for source_dir in sorted(archive_root.iterdir()):
                if source_dir.is_dir():
                    try:
                        sources.append(_source_disk_summary(source_dir))
                    except Exception as exc:
                        route_logger.warning("Error reading archive dir %s: %s", source_dir, exc)

        total_bytes = sum(s["total_bytes"] for s in sources)
        return jsonify({
            "sources": sources,
            "total_bytes": total_bytes,
            "total_bytes_human": _format_bytes(total_bytes),
            "total_files": sum(s["total_files"] for s in sources),
            "archive_dir": str(archive_root),
        })

    # ------------------------------------------------------------------
    # API: get settings for one source
    # ------------------------------------------------------------------

    @app.route("/api/audio/archives/<source_name>/settings", methods=["GET"])
    def api_audio_archive_get_settings(source_name: str):
        cfg = _get_archive_config(source_name)
        if cfg is None:
            return jsonify({"error": f"Source '{source_name}' not found"}), 404
        return jsonify({"source_name": source_name, "archive": cfg})

    # ------------------------------------------------------------------
    # API: save settings (does NOT start/stop archiver)
    # ------------------------------------------------------------------

    @app.route("/api/audio/archives/<source_name>/settings", methods=["POST"])
    def api_audio_archive_save_settings(source_name: str):
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        if not _save_archive_config(source_name, body):
            return jsonify({"error": f"Failed to save settings for '{source_name}'"}), 500
        cfg = _get_archive_config(source_name)
        return jsonify({"source_name": source_name, "archive": cfg, "saved": True})

    # ------------------------------------------------------------------
    # API: start archiver
    # ------------------------------------------------------------------

    @app.route("/api/audio/archives/<source_name>/start", methods=["POST"])
    def api_audio_archive_start(source_name: str):
        body: Dict[str, Any] = request.get_json(silent=True) or {}

        # Merge any overrides from request body into existing config
        existing = _get_archive_config(source_name)
        if existing is None:
            return jsonify({"error": f"Source '{source_name}' not found"}), 404

        merged = dict(existing)
        merged.update(body)
        merged["enabled"] = True

        if not _save_archive_config(source_name, merged):
            return jsonify({"error": "Failed to save archive config"}), 500

        try:
            from app_core.audio.redis_commands import get_audio_command_publisher
            publisher = get_audio_command_publisher()
            result = publisher.start_archiver(source_name, merged)
            return jsonify({"source_name": source_name, "result": result})
        except Exception as exc:
            route_logger.error("archiver start command failed for '%s': %s", source_name, exc)
            return jsonify({
                "source_name": source_name,
                "result": {"success": False, "message": str(exc)},
            }), 500

    # ------------------------------------------------------------------
    # API: stop archiver
    # ------------------------------------------------------------------

    @app.route("/api/audio/archives/<source_name>/stop", methods=["POST"])
    def api_audio_archive_stop(source_name: str):
        # Persist disabled state to DB
        _save_archive_config(source_name, {"enabled": False})

        try:
            from app_core.audio.redis_commands import get_audio_command_publisher
            publisher = get_audio_command_publisher()
            result = publisher.stop_archiver(source_name)
            return jsonify({"source_name": source_name, "result": result})
        except Exception as exc:
            route_logger.error("archiver stop command failed for '%s': %s", source_name, exc)
            return jsonify({
                "source_name": source_name,
                "result": {"success": False, "message": str(exc)},
            }), 500

    # ------------------------------------------------------------------
    # API: purge archive files
    # ------------------------------------------------------------------

    @app.route("/api/audio/archives/<source_name>/purge", methods=["POST"])
    def api_audio_archive_purge(source_name: str):
        source_dir = archive_root / Path(source_name).name  # prevent path traversal
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        days_older_than = 0
        try:
            days_older_than = int(body.get("days_older_than", 0))
        except (TypeError, ValueError):
            pass

        route_logger.info(
            "Archive purge requested for '%s' (days_older_than=%d)",
            source_name, days_older_than,
        )
        result = _purge_source(source_dir, days_older_than=days_older_than)
        result["bytes_freed_human"] = _format_bytes(result["bytes_freed"])
        status = 200 if result["error"] is None else 500
        return jsonify(result), status

    # ------------------------------------------------------------------
    # API: list archive files for one source, grouped by date
    # ------------------------------------------------------------------

    @app.route("/api/audio/archives/<source_name>/files", methods=["GET"])
    def api_audio_archive_files(source_name: str):
        source_dir = archive_root / Path(source_name).name  # prevent path traversal
        if not source_dir.exists():
            return jsonify({"dates": []})

        dates: List[Dict[str, Any]] = []
        for date_dir in sorted(source_dir.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue
            files: List[Dict[str, Any]] = []
            for f in sorted(date_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in (".wav", ".mp3"):
                    try:
                        stat = f.stat()
                        files.append({
                            "filename": f.name,
                            "date": date_dir.name,
                            "size_bytes": stat.st_size,
                            "size_human": _format_bytes(stat.st_size),
                            "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        })
                    except OSError:
                        pass
            if files:
                dates.append({"date": date_dir.name, "files": files})

        return jsonify({"source_name": source_name, "dates": dates})

    # ------------------------------------------------------------------
    # API: serve / download one archive file
    # ------------------------------------------------------------------

    @app.route(
        "/api/audio/archives/<source_name>/files/<date>/<filename>",
        methods=["GET"],
    )
    def api_audio_archive_serve(source_name: str, date: str, filename: str):
        # Prevent path traversal in every segment
        safe_source = Path(source_name).name
        safe_date   = Path(date).name
        safe_file   = Path(filename).name

        file_path = archive_root / safe_source / safe_date / safe_file
        if not file_path.exists() or not file_path.is_file():
            return jsonify({"error": "File not found"}), 404

        suffix = file_path.suffix.lower()
        if suffix not in (".wav", ".mp3"):
            return jsonify({"error": "File type not served"}), 403

        mime = "audio/wav" if suffix == ".wav" else "audio/mpeg"
        as_attachment = request.args.get("download", "0") == "1"
        return send_file(
            file_path,
            mimetype=mime,
            as_attachment=as_attachment,
            download_name=safe_file,
            conditional=True,
        )

    # ------------------------------------------------------------------
    # API: stream metadata log (recent now-playing history)
    # ------------------------------------------------------------------

    @app.route("/api/audio/archives/<source_name>/metadata-log", methods=["GET"])
    def api_audio_archive_metadata_log(source_name: str):
        try:
            from app_core.models import StreamMetadataLog
            limit = min(int(request.args.get("limit", 100)), 500)
            rows = (
                StreamMetadataLog.query
                .filter_by(source_name=source_name)
                .order_by(StreamMetadataLog.timestamp.desc())
                .limit(limit)
                .all()
            )
            entries = [
                {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "title": r.title,
                    "artist": r.artist,
                    "album": r.album,
                    "artwork_url": r.artwork_url,
                    "length": r.length,
                    "display": r.display,
                    "raw": r.raw,
                }
                for r in rows
            ]
            return jsonify({"source_name": source_name, "entries": entries})
        except Exception as exc:
            route_logger.error("metadata-log query failed for '%s': %s", source_name, exc)
            return jsonify({"source_name": source_name, "entries": []})

    # ------------------------------------------------------------------
    # API: clear (delete) the metadata log for one source
    # ------------------------------------------------------------------

    @app.route("/api/audio/archives/<source_name>/metadata-log", methods=["DELETE"])
    def api_audio_archive_metadata_log_clear(source_name: str):
        try:
            from app_core.extensions import db
            from app_core.models import StreamMetadataLog
            deleted = (
                StreamMetadataLog.query
                .filter_by(source_name=source_name)
                .delete(synchronize_session=False)
            )
            db.session.commit()
            route_logger.info("Cleared %d metadata-log rows for '%s'", deleted, source_name)
            return jsonify({"source_name": source_name, "deleted": deleted})
        except Exception as exc:
            route_logger.error("metadata-log clear failed for '%s': %s", source_name, exc)
            return jsonify({"error": str(exc)}), 500

    route_logger.info("Audio archive routes registered (archive_dir=%s)", archive_root)


__all__ = ["register"]
