#!/usr/bin/env python3
"""Test script to verify configuration file update fix."""

import os
import sys
from pathlib import Path
import tempfile

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the function we fixed
from webapp.routes_ipaws import _get_config_path, _update_env_file

def test_config_path_fallback():
    """Test that config path falls back to project directory."""
    print("Testing config path fallback...")
    
    # Clear CONFIG_PATH env var if set
    old_config_path = os.environ.pop('CONFIG_PATH', None)
    
    try:
        config_path = _get_config_path()
        print(f"✓ Config path: {config_path}")
        
        # Should fallback to project directory since /app-config doesn't exist
        expected = project_root / '.env'
        assert config_path == expected, f"Expected {expected}, got {config_path}"
        print(f"✓ Correctly falls back to project directory")
        
        # Verify parent is writable
        assert os.access(config_path.parent, os.W_OK), "Config directory not writable"
        print(f"✓ Config directory is writable")
        
        return True
    finally:
        # Restore CONFIG_PATH if it was set
        if old_config_path:
            os.environ['CONFIG_PATH'] = old_config_path


def test_update_env_file():
    """Test that we can update a config file."""
    print("\nTesting config file update...")
    
    # Create a temporary .env file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write("EXISTING_KEY=old_value\n")
        tmp.write("OTHER_KEY=other_value\n")
    
    try:
        # Set CONFIG_PATH to our temp file
        os.environ['CONFIG_PATH'] = str(tmp_path)
        
        # Test updating existing key
        _update_env_file('EXISTING_KEY', 'new_value')
        print(f"✓ Updated existing key")
        
        # Test adding new key
        _update_env_file('NEW_KEY', 'new_value')
        print(f"✓ Added new key")
        
        # Verify the file contents
        with open(tmp_path, 'r') as f:
            content = f.read()
        
        assert 'EXISTING_KEY=new_value' in content, "Existing key not updated"
        assert 'NEW_KEY=new_value' in content, "New key not added"
        assert 'OTHER_KEY=other_value' in content, "Other key was modified"
        print(f"✓ File contents correct")
        
        print(f"\nFile contents:\n{content}")
        
        return True
    finally:
        # Clean up
        os.environ.pop('CONFIG_PATH', None)
        tmp_path.unlink(missing_ok=True)


def test_permission_error_handling():
    """Test that permission errors are handled gracefully."""
    print("\nTesting permission error handling...")
    
    # Try to use a read-only path
    os.environ['CONFIG_PATH'] = '/root/.env'  # Typically not writable
    
    try:
        _update_env_file('TEST_KEY', 'test_value')
        print("✗ Should have raised PermissionError")
        return False
    except PermissionError as e:
        print(f"✓ Correctly raised PermissionError: {str(e)[:100]}")
        return True
    finally:
        os.environ.pop('CONFIG_PATH', None)


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Configuration File Fix")
    print("=" * 60)
    
    tests = [
        test_config_path_fallback,
        test_update_env_file,
        test_permission_error_handling,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    sys.exit(0 if all(results) else 1)
