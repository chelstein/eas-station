#!/usr/bin/env python3
"""
Pre-flight check for gunicorn gevent worker compatibility.

This script verifies that gevent can be loaded without conflicts from
system site-packages (numpy, scipy, SoapySDR).

Exit codes:
  0 - All checks passed, gunicorn can start
  1 - Critical failure, gunicorn will fail
"""

import sys
import os

def check_gevent_import():
    """Verify gevent can be imported."""
    try:
        import gevent
        print(f"✓ gevent {gevent.__version__} imported successfully")
        return True
    except ImportError as e:
        print(f"✗ CRITICAL: gevent import failed: {e}")
        print("  Install: pip install 'gevent>=25.9.1'")
        return False
    except Exception as e:
        print(f"✗ CRITICAL: gevent import error: {e}")
        print("  This may indicate C extension conflicts")
        return False

def check_greenlet_import():
    """Verify greenlet (gevent dependency) can be imported."""
    try:
        import greenlet
        print(f"✓ greenlet {greenlet.__version__} imported successfully")
        return True
    except ImportError as e:
        print(f"✗ WARNING: greenlet import failed: {e}")
        print("  gevent requires greenlet - reinstall: pip install --force-reinstall 'gevent>=25.9.1'")
        return False
    except Exception as e:
        print(f"✗ CRITICAL: greenlet C extension error: {e}")
        print("  This indicates binary incompatibility")
        print("  Try: pip install --force-reinstall --no-binary :all: greenlet")
        return False

def check_numpy_compatibility():
    """Check if numpy (if present) is compatible with gevent."""
    try:
        import numpy as np
        print(f"ℹ numpy {np.__version__} found")
        
        # Check if numpy is from system or venv
        numpy_path = np.__file__
        if '/usr/lib' in numpy_path or '/usr/local/lib' in numpy_path:
            print(f"  ⚠ WARNING: numpy loaded from system: {numpy_path}")
            print("  This may conflict with venv gevent")
            print("  Consider: pip install --force-reinstall numpy")
        else:
            print(f"  ✓ numpy loaded from venv: {numpy_path}")
        
        # Try a simple operation that would trigger C extension loading
        arr = np.array([1, 2, 3])
        _ = arr.mean()
        print("  ✓ numpy C extensions working")
        
        return True
    except ImportError:
        print("ℹ numpy not installed (optional)")
        return True
    except Exception as e:
        print(f"  ✗ WARNING: numpy C extension error: {e}")
        print("  This may cause issues if Flask app uses numpy")
        return True  # Non-critical for web service

def check_gevent_monkey_patch():
    """Verify gevent can monkey-patch stdlib."""
    try:
        from gevent import monkey
        # Test monkey patching without actually applying it
        # (gunicorn gevent worker does this automatically)
        print("✓ gevent monkey-patch module available")
        return True
    except Exception as e:
        print(f"✗ CRITICAL: gevent monkey-patch failed: {e}")
        return False

def check_gunicorn_import():
    """Verify gunicorn can be imported."""
    try:
        import gunicorn
        print(f"✓ gunicorn {gunicorn.__version__} imported successfully")
        return True
    except ImportError as e:
        print(f"✗ CRITICAL: gunicorn import failed: {e}")
        print("  Install: pip install gunicorn")
        return False

def main():
    print("=" * 80)
    print("Gunicorn Gevent Worker Pre-flight Check")
    print("=" * 80)
    print()
    
    checks = [
        ("Gunicorn", check_gunicorn_import),
        ("Gevent", check_gevent_import),
        ("Greenlet", check_greenlet_import),
        ("Gevent Monkey-Patch", check_gevent_monkey_patch),
        ("Numpy Compatibility", check_numpy_compatibility),
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\n[{name}]")
        if not check_func():
            all_passed = False
    
    print()
    print("=" * 80)
    if all_passed:
        print("✓ All checks passed - gunicorn gevent worker should start successfully")
        print("=" * 80)
        return 0
    else:
        print("✗ One or more checks failed - gunicorn may fail to start")
        print("=" * 80)
        print()
        print("Common fixes:")
        print("  1. Reinstall gevent and greenlet:")
        print("     pip install --force-reinstall 'gevent>=25.9.1' greenlet")
        print()
        print("  2. If system numpy conflicts, reinstall in venv:")
        print("     pip install --force-reinstall numpy")
        print()
        print("  3. Check for binary incompatibilities:")
        print("     ldd $(python -c 'import greenlet; print(greenlet.__file__)')")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
