"""
EAS Station - Emergency Alert System
Copyright (c) 2025 Timothy Kramer (KR8MER)

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

"""Alpha LED Sign M-Protocol management routes - Phase 9 Web UI."""

import os
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request
from flask_login import login_required

from app_core.permissions import permission_required


def register(app: Flask, logger) -> None:
    """Register Alpha LED sign management dashboard and API endpoints."""

    route_logger = logger.getChild("routes_alpha")

    @app.route("/alpha-sign")
    @login_required
    @permission_required("hardware.manage")
    def alpha_sign_dashboard():
        """Alpha LED Sign Management Dashboard - Phase 9 Web UI."""
        try:
            # Import LED controller
            from scripts.led_sign_controller import LEDSignController
            
            # Get LED sign configuration
            led_ip = os.getenv("LED_SIGN_IP", "192.168.8.122")
            led_port = int(os.getenv("LED_SIGN_PORT", "10001"))
            
            # Check if controller is available
            try:
                controller = LEDSignController(led_ip, led_port)
                is_connected = controller.connected
            except Exception as e:
                route_logger.warning(f"Could not connect to Alpha sign: {e}")
                is_connected = False
            
            return render_template(
                "alpha_sign.html",
                led_ip=led_ip,
                led_port=led_port,
                is_connected=is_connected
            )
        except Exception as exc:
            route_logger.error(f"Error loading Alpha sign dashboard: {exc}")
            return render_template(
                "error.html",
                error_message="Failed to load Alpha LED Sign dashboard",
                error_details=str(exc)
            )

    @app.route("/api/alpha/diagnostics")
    @login_required
    @permission_required("hardware.manage")
    def api_alpha_diagnostics():
        """Get complete diagnostics from Alpha LED sign (Phase 1)."""
        try:
            from scripts.led_sign_controller import LEDSignController
            
            led_ip = os.getenv("LED_SIGN_IP", "192.168.8.122")
            led_port = int(os.getenv("LED_SIGN_PORT", "10001"))
            
            controller = LEDSignController(led_ip, led_port)
            
            if not controller.connected:
                return jsonify({
                    "success": False,
                    "error": f"Not connected to sign at {led_ip}:{led_port}"
                }), 503
            
            # Get all diagnostics (Phase 1)
            diagnostics = controller.get_diagnostics()
            
            return jsonify({
                "success": True,
                "diagnostics": diagnostics,
                "connection": {
                    "host": led_ip,
                    "port": led_port,
                    "connected": True
                }
            })
        except Exception as exc:
            route_logger.error(f"Error reading diagnostics: {exc}")
            return jsonify({
                "success": False,
                "error": str(exc)
            }), 500

    @app.route("/api/alpha/sync-time", methods=["POST"])
    @login_required
    @permission_required("hardware.manage")
    def api_alpha_sync_time():
        """Sync Alpha sign time with system time (Phase 2)."""
        try:
            from scripts.led_sign_controller import LEDSignController
            
            led_ip = os.getenv("LED_SIGN_IP", "192.168.8.122")
            led_port = int(os.getenv("LED_SIGN_PORT", "10001"))
            
            controller = LEDSignController(led_ip, led_port)
            
            if not controller.connected:
                return jsonify({
                    "success": False,
                    "error": "Not connected to sign"
                }), 503
            
            # Sync time with system (Phase 2)
            success = controller.sync_time_with_system()
            
            if success:
                return jsonify({
                    "success": True,
                    "message": "Sign time synchronized with system"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to sync time - sign may not support this feature"
                }), 400
        except Exception as exc:
            route_logger.error(f"Error syncing time: {exc}")
            return jsonify({
                "success": False,
                "error": str(exc)
            }), 500

    @app.route("/api/alpha/set-time-format", methods=["POST"])
    @login_required
    @permission_required("hardware.manage")
    def api_alpha_set_time_format():
        """Set time format (12h/24h) on Alpha sign (Phase 2)."""
        try:
            from scripts.led_sign_controller import LEDSignController
            
            data = request.get_json(silent=True) or {}
            format_24h = data.get("format_24h", True)
            
            led_ip = os.getenv("LED_SIGN_IP", "192.168.8.122")
            led_port = int(os.getenv("LED_SIGN_PORT", "10001"))
            
            controller = LEDSignController(led_ip, led_port)
            
            if not controller.connected:
                return jsonify({
                    "success": False,
                    "error": "Not connected to sign"
                }), 503
            
            # Set time format (Phase 2)
            success = controller.set_time_format(format_24h=format_24h)
            
            if success:
                return jsonify({
                    "success": True,
                    "message": f"Time format set to {'24-hour' if format_24h else '12-hour'}"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to set time format"
                }), 400
        except Exception as exc:
            route_logger.error(f"Error setting time format: {exc}")
            return jsonify({
                "success": False,
                "error": str(exc)
            }), 500

    @app.route("/api/alpha/set-run-mode", methods=["POST"])
    @login_required
    @permission_required("hardware.manage")
    def api_alpha_set_run_mode():
        """Set run mode (auto/manual) on Alpha sign (Phase 2)."""
        try:
            from scripts.led_sign_controller import LEDSignController
            
            data = request.get_json(silent=True) or {}
            auto_mode = data.get("auto", True)
            
            led_ip = os.getenv("LED_SIGN_IP", "192.168.8.122")
            led_port = int(os.getenv("LED_SIGN_PORT", "10001"))
            
            controller = LEDSignController(led_ip, led_port)
            
            if not controller.connected:
                return jsonify({
                    "success": False,
                    "error": "Not connected to sign"
                }), 503
            
            # Set run mode (Phase 2)
            success = controller.set_run_mode(auto=auto_mode)
            
            if success:
                return jsonify({
                    "success": True,
                    "message": f"Run mode set to {'AUTO' if auto_mode else 'MANUAL'}"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to set run mode"
                }), 400
        except Exception as exc:
            route_logger.error(f"Error setting run mode: {exc}")
            return jsonify({
                "success": False,
                "error": str(exc)
            }), 500

    @app.route("/api/alpha/speaker", methods=["POST"])
    @login_required
    @permission_required("hardware.manage")
    def api_alpha_speaker():
        """Enable/disable speaker on Alpha sign (Phase 3)."""
        try:
            from scripts.led_sign_controller import LEDSignController
            
            data = request.get_json(silent=True) or {}
            enabled = data.get("enabled", True)
            
            led_ip = os.getenv("LED_SIGN_IP", "192.168.8.122")
            led_port = int(os.getenv("LED_SIGN_PORT", "10001"))
            
            controller = LEDSignController(led_ip, led_port)
            
            if not controller.connected:
                return jsonify({
                    "success": False,
                    "error": "Not connected to sign"
                }), 503
            
            # Set speaker (Phase 3)
            success = controller.set_speaker(enabled=enabled)
            
            if success:
                return jsonify({
                    "success": True,
                    "message": f"Speaker {'enabled' if enabled else 'disabled'}"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to set speaker state"
                }), 400
        except Exception as exc:
            route_logger.error(f"Error setting speaker: {exc}")
            return jsonify({
                "success": False,
                "error": str(exc)
            }), 500

    @app.route("/api/alpha/beep", methods=["POST"])
    @login_required
    @permission_required("hardware.manage")
    def api_alpha_beep():
        """Make Alpha sign beep (Phase 3)."""
        try:
            from scripts.led_sign_controller import LEDSignController
            
            data = request.get_json(silent=True) or {}
            count = int(data.get("count", 1))
            
            led_ip = os.getenv("LED_SIGN_IP", "192.168.8.122")
            led_port = int(os.getenv("LED_SIGN_PORT", "10001"))
            
            controller = LEDSignController(led_ip, led_port)
            
            if not controller.connected:
                return jsonify({
                    "success": False,
                    "error": "Not connected to sign"
                }), 503
            
            # Beep sign (Phase 3)
            success = controller.beep(count=count)
            
            if success:
                return jsonify({
                    "success": True,
                    "message": f"Sign beeped {count} time(s)"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to beep sign"
                }), 400
        except Exception as exc:
            route_logger.error(f"Error making beep: {exc}")
            return jsonify({
                "success": False,
                "error": str(exc)
            }), 500

    @app.route("/api/alpha/brightness", methods=["POST"])
    @login_required
    @permission_required("hardware.manage")
    def api_alpha_brightness():
        """Set brightness on Alpha sign (Phase 4)."""
        try:
            from scripts.led_sign_controller import LEDSignController
            
            data = request.get_json(silent=True) or {}
            
            led_ip = os.getenv("LED_SIGN_IP", "192.168.8.122")
            led_port = int(os.getenv("LED_SIGN_PORT", "10001"))
            
            controller = LEDSignController(led_ip, led_port)
            
            if not controller.connected:
                return jsonify({
                    "success": False,
                    "error": "Not connected to sign"
                }), 503
            
            # Handle auto mode
            if data.get("auto", False):
                success = controller.set_brightness(auto=True)
                message = "Auto brightness mode enabled"
            else:
                level = int(data.get("level", 100))
                if not 0 <= level <= 100:
                    return jsonify({
                        "success": False,
                        "error": "Brightness level must be 0-100"
                    }), 400
                success = controller.set_brightness(level=level)
                message = f"Brightness set to {level}%"
            
            if success:
                return jsonify({
                    "success": True,
                    "message": message
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to set brightness"
                }), 400
        except Exception as exc:
            route_logger.error(f"Error setting brightness: {exc}")
            return jsonify({
                "success": False,
                "error": str(exc)
            }), 500

    @app.route("/api/alpha/read-file/<label>")
    @login_required
    @permission_required("hardware.manage")
    def api_alpha_read_file(label: str):
        """Read text file from Alpha sign (Phase 5)."""
        try:
            from scripts.led_sign_controller import LEDSignController
            
            # Validate label (0-9, A-Z)
            if not (label.isdigit() or (len(label) == 1 and label.upper().isalpha())):
                return jsonify({
                    "success": False,
                    "error": "Invalid file label. Must be 0-9 or A-Z"
                }), 400
            
            led_ip = os.getenv("LED_SIGN_IP", "192.168.8.122")
            led_port = int(os.getenv("LED_SIGN_PORT", "10001"))
            
            controller = LEDSignController(led_ip, led_port)
            
            if not controller.connected:
                return jsonify({
                    "success": False,
                    "error": "Not connected to sign"
                }), 503
            
            # Read text file (Phase 5)
            content = controller.read_text_file(label.upper())
            
            if content is not None:
                return jsonify({
                    "success": True,
                    "label": label.upper(),
                    "content": content,
                    "length": len(content)
                })
            else:
                return jsonify({
                    "success": False,
                    "error": f"Could not read file '{label}' - may not exist or sign doesn't support this feature"
                }), 404
        except Exception as exc:
            route_logger.error(f"Error reading file: {exc}")
            return jsonify({
                "success": False,
                "error": str(exc)
            }), 500

    @app.route("/api/alpha/test-all", methods=["POST"])
    @login_required
    @permission_required("hardware.manage")
    def api_alpha_test_all():
        """Test all M-Protocol functions on Alpha sign."""
        try:
            from scripts.led_sign_controller import LEDSignController
            
            led_ip = os.getenv("LED_SIGN_IP", "192.168.8.122")
            led_port = int(os.getenv("LED_SIGN_PORT", "10001"))
            
            controller = LEDSignController(led_ip, led_port)
            
            if not controller.connected:
                return jsonify({
                    "success": False,
                    "error": "Not connected to sign"
                }), 503
            
            # Test all phases
            results = {
                "phase1_diagnostics": None,
                "phase2_time_sync": None,
                "phase3_speaker": None,
                "phase4_brightness": None,
                "phase5_read_file": None
            }
            
            # Phase 1: Diagnostics
            try:
                diag = controller.get_diagnostics()
                results["phase1_diagnostics"] = {
                    "success": diag is not None and len(diag) > 0,
                    "data": diag
                }
            except Exception as e:
                results["phase1_diagnostics"] = {"success": False, "error": str(e)}
            
            # Phase 2: Time sync
            try:
                results["phase2_time_sync"] = {
                    "success": controller.sync_time_with_system()
                }
            except Exception as e:
                results["phase2_time_sync"] = {"success": False, "error": str(e)}
            
            # Phase 3: Speaker test
            try:
                results["phase3_speaker"] = {
                    "success": controller.beep(count=1)
                }
            except Exception as e:
                results["phase3_speaker"] = {"success": False, "error": str(e)}
            
            # Phase 4: Brightness
            try:
                results["phase4_brightness"] = {
                    "success": controller.set_brightness(level=100)
                }
            except Exception as e:
                results["phase4_brightness"] = {"success": False, "error": str(e)}
            
            # Phase 5: Read file
            try:
                content = controller.read_text_file('0')
                results["phase5_read_file"] = {
                    "success": content is not None,
                    "content": content
                }
            except Exception as e:
                results["phase5_read_file"] = {"success": False, "error": str(e)}
            
            # Calculate overall success
            successes = sum(1 for r in results.values() if r and r.get("success"))
            total = len(results)
            
            return jsonify({
                "success": True,
                "results": results,
                "summary": {
                    "passed": successes,
                    "total": total,
                    "percentage": round(100 * successes / total, 1)
                }
            })
        except Exception as exc:
            route_logger.error(f"Error testing Alpha sign: {exc}")
            return jsonify({
                "success": False,
                "error": str(exc)
            }), 500


__all__ = ["register"]
