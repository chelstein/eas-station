#!/usr/bin/env python3
"""
Test script for Alpha LED Sign M-Protocol diagnostics functionality.
Demonstrates reading sign information, status, and configuration.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.led_sign_controller import Alpha9120CController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_sign_diagnostics(host: str, port: int = 10001):
    """
    Test M-Protocol Phase 1 diagnostics functionality.
    
    Args:
        host: IP address of Alpha LED sign (or Waveshare adapter)
        port: TCP port (default 10001)
    """
    logger.info(f"Connecting to Alpha LED sign at {host}:{port}...")
    
    # Create controller and connect
    controller = Alpha9120CController(host=host, port=port)
    
    if not controller.connected:
        logger.error("Failed to connect to sign")
        return False
    
    logger.info("✅ Connected to sign successfully")
    print("\n" + "="*60)
    print("Alpha LED Sign Diagnostics - M-Protocol Phase 1")
    print("="*60 + "\n")
    
    # Test 1: Read serial number
    print("📋 Reading Sign Information...")
    print("-" * 60)
    
    serial = controller.read_serial_number()
    if serial:
        print(f"✅ Serial Number: {serial}")
    else:
        print("⚠️  Could not read serial number (sign may not support this)")
    
    # Test 2: Read model number
    model = controller.read_model_number()
    if model:
        print(f"✅ Model Number: {model}")
    else:
        print("⚠️  Could not read model number")
    
    # Test 3: Read firmware version
    firmware = controller.read_firmware_version()
    if firmware:
        print(f"✅ Firmware Version: {firmware}")
    else:
        print("⚠️  Could not read firmware version")
    
    # Test 4: Read memory configuration
    print("\n💾 Reading Memory Configuration...")
    print("-" * 60)
    
    memory = controller.read_memory_configuration()
    if memory:
        print(f"✅ Memory Info:")
        for key, value in memory.items():
            print(f"   - {key}: {value}")
    else:
        print("⚠️  Could not read memory configuration")
    
    # Test 5: Read temperature
    print("\n🌡️  Reading Temperature Sensor...")
    print("-" * 60)
    
    temp = controller.read_temperature()
    if temp:
        print(f"✅ Temperature: {temp}°F ({(temp - 32) * 5/9:.1f}°C)")
    else:
        print("⚠️  Could not read temperature (sensor may not be available)")
    
    # Test 6: Get comprehensive diagnostics
    print("\n🔍 Comprehensive Diagnostics...")
    print("-" * 60)
    
    diagnostics = controller.get_diagnostics()
    print("✅ Complete diagnostic report:")
    for key, value in diagnostics.items():
        if isinstance(value, dict):
            print(f"   {key}:")
            for sub_key, sub_value in value.items():
                print(f"      - {sub_key}: {sub_value}")
        else:
            print(f"   {key}: {value}")
    
    # Test 7: Send test message to confirm bidirectional works
    print("\n📤 Testing Bidirectional Communication...")
    print("-" * 60)
    
    test_success = controller.send_message(
        lines=[
            "DIAGNOSTIC TEST",
            "M-PROTOCOL",
            "PHASE 1 COMPLETE",
            "ALPHA LED SIGN"
        ]
    )
    
    if test_success:
        print("✅ Test message sent successfully")
        print("   Check sign display for confirmation")
    else:
        print("❌ Failed to send test message")
    
    # Summary
    print("\n" + "="*60)
    print("Diagnostics Test Complete")
    print("="*60)
    print(f"\nConnection: {'✅ Active' if controller.connected else '❌ Failed'}")
    print(f"Serial Number: {serial or 'N/A'}")
    print(f"Model: {model or 'N/A'}")
    print(f"Firmware: {firmware or 'N/A'}")
    print(f"Temperature: {f'{temp}°F' if temp else 'N/A'}")
    
    # Cleanup
    controller.disconnect()
    logger.info("Test complete, disconnected")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test Alpha LED Sign M-Protocol diagnostics'
    )
    parser.add_argument(
        'host',
        help='IP address of Alpha LED sign (or Waveshare adapter)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=10001,
        help='TCP port (default: 10001)'
    )
    
    args = parser.parse_args()
    
    try:
        success = test_sign_diagnostics(args.host, args.port)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)
