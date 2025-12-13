#!/usr/bin/env python3
"""
Check critical dependencies for EAS Station web service.

This script verifies that all required packages for the web service are installed
and working correctly. Run this if the web service fails to start.

Usage:
    /opt/eas-station/venv/bin/python3 scripts/check_dependencies.py
"""

import sys
import os

def check_dependency(name, import_name=None, critical=True):
    """Check if a dependency is available."""
    if import_name is None:
        import_name = name
    
    try:
        __import__(import_name)
        print(f"✓ {name:30s} OK")
        return True
    except ImportError as e:
        status = "CRITICAL" if critical else "WARNING"
        print(f"✗ {name:30s} {status} - {e}")
        return not critical

def main():
    print("=" * 80)
    print("EAS Station Web Service Dependency Check")
    print("=" * 80)
    print()
    
    all_ok = True
    
    print("Critical Dependencies (web service will NOT start without these):")
    print("-" * 80)
    all_ok &= check_dependency("Flask", "flask", critical=True)
    all_ok &= check_dependency("Flask-SocketIO", "flask_socketio", critical=True)
    all_ok &= check_dependency("gunicorn", "gunicorn", critical=True)
    all_ok &= check_dependency("gevent", "gevent", critical=True)
    all_ok &= check_dependency("SQLAlchemy", "sqlalchemy", critical=True)
    all_ok &= check_dependency("psycopg2", "psycopg2", critical=True)
    all_ok &= check_dependency("GeoAlchemy2", "geoalchemy2", critical=True)
    print()
    
    print("Important Dependencies (features may be degraded without these):")
    print("-" * 80)
    check_dependency("redis", "redis", critical=False)
    check_dependency("requests", "requests", critical=False)
    check_dependency("psutil", "psutil", critical=False)
    check_dependency("pytz", "pytz", critical=False)
    print()
    
    if all_ok:
        print("=" * 80)
        print("✓ All critical dependencies are installed")
        print("=" * 80)
        print()
        print("If the web service still fails to start, check:")
        print("  1. Database connectivity: systemctl status postgresql")
        print("  2. Service logs: journalctl -u eas-station-web.service -n 50")
        print("  3. Database configuration in .env file")
        print()
        return 0
    else:
        print("=" * 80)
        print("✗ Missing critical dependencies!")
        print("=" * 80)
        print()
        print("To fix, run:")
        print("  cd /opt/eas-station")
        print("  source venv/bin/activate")
        print("  pip install -r requirements.txt")
        print()
        print("After installing dependencies, restart the service:")
        print("  sudo systemctl restart eas-station-web.service")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
