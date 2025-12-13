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

def check_permissions():
    """
    Check file system permissions.
    
    Returns:
        tuple: (success: bool, issues: list) - Always returns a tuple for consistent unpacking
    """
    issues = []
    
    # Check if running as root (usually means testing)
    if os.geteuid() == 0:
        print("  Running as root - skipping permission checks")
        return True, []  # Return consistent tuple format
    
    # Check project directory
    project_dir = "/opt/eas-station"
    if os.path.exists(project_dir):
        if not os.access(project_dir, os.R_OK):
            issues.append(f"Cannot read {project_dir}")
        if not os.access(project_dir, os.W_OK):
            issues.append(f"Cannot write to {project_dir}")
    else:
        issues.append(f"Project directory {project_dir} does not exist")
    
    # Check log directory
    log_dir = "/var/log/eas-station"
    if os.path.exists(log_dir):
        if not os.access(log_dir, os.W_OK):
            issues.append(f"Cannot write to {log_dir}")
    else:
        print(f"  ⚠ Log directory {log_dir} does not exist (will be created on service start)")
    
    # Check venv directory
    venv_dir = "/opt/eas-station/venv"
    if os.path.exists(venv_dir):
        if not os.access(venv_dir, os.R_OK):
            issues.append(f"Cannot read {venv_dir}")
    else:
        issues.append(f"Virtual environment {venv_dir} does not exist")
    
    return len(issues) == 0, issues

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
    
    print("File System Permissions:")
    print("-" * 80)
    perm_ok, perm_issues = check_permissions()
    if perm_ok:
        print("  ✓ All permissions OK")
    else:
        for issue in perm_issues:
            print(f"  ✗ {issue}")
            all_ok = False
    print()
    
    if all_ok:
        print("=" * 80)
        print("✓ All critical dependencies and permissions are OK")
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
        print("✗ Issues found that will prevent service startup!")
        print("=" * 80)
        print()
        
        if not perm_ok:
            print("To fix permission issues:")
            print("  sudo chown -R eas-station:eas-station /opt/eas-station")
            print("  sudo mkdir -p /var/log/eas-station")
            print("  sudo chown eas-station:eas-station /var/log/eas-station")
            print()
        
        print("To fix missing dependencies:")
        print("  cd /opt/eas-station")
        print("  source venv/bin/activate")
        print("  pip install -r requirements.txt")
        print("  deactivate")
        print()
        print("After fixing issues, restart the service:")
        print("  sudo systemctl restart eas-station-web.service")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
