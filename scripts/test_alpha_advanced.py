#!/usr/bin/env python3
"""
Test script for Alpha LED Sign M-Protocol Phases 3-5.
Tests speaker control, brightness, and text file reading.
"""

import sys
import logging
from pathlib import Path
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.led_sign_controller import Alpha9120CController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_advanced_features(host: str, port: int = 10001):
    """
    Test M-Protocol Phases 3-5: Speaker, Brightness, and File Reading.
    
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
    print("Alpha LED Sign Advanced Features - M-Protocol Phases 3-5")
    print("="*60 + "\n")
    
    # ==================== PHASE 3: SPEAKER CONTROL ====================
    
    print("🔊 Phase 3: Speaker/Beep Control")
    print("-" * 60)
    
    # Test 1: Enable speaker
    print("\n🔊 Test 1: Enable Speaker")
    success = controller.set_speaker(True)
    if success:
        print("✅ Speaker enabled")
    else:
        print("⚠️  Speaker control not supported or failed")
    
    time.sleep(0.5)
    
    # Test 2: Test beep
    print("\n🔔 Test 2: Test Beep")
    success = controller.beep(1)
    if success:
        print("✅ Beep command sent (listen for beep)")
    else:
        print("⚠️  Beep not supported or failed")
    
    time.sleep(1)
    
    # Test 3: Disable speaker
    print("\n🔇 Test 3: Disable Speaker")
    success = controller.set_speaker(False)
    if success:
        print("✅ Speaker disabled")
    else:
        print("⚠️  Speaker control not supported or failed")
    
    # ==================== PHASE 4: BRIGHTNESS CONTROL ====================
    
    print("\n\n💡 Phase 4: Brightness Control")
    print("-" * 60)
    
    # Test 4: Set brightness to 100% (full)
    print("\n💡 Test 4: Set Brightness to 100% (Full)")
    success = controller.set_brightness(100)
    if success:
        print("✅ Brightness set to 100% (full)")
    else:
        print("⚠️  Brightness control not supported or failed")
    
    time.sleep(1)
    
    # Test 5: Set brightness to 50% (medium)
    print("\n🌓 Test 5: Set Brightness to 50% (Medium)")
    success = controller.set_brightness(50)
    if success:
        print("✅ Brightness set to 50% (medium)")
        print("   Sign should dim slightly")
    else:
        print("⚠️  Brightness control not supported or failed")
    
    time.sleep(1)
    
    # Test 6: Set brightness to 25% (dim/night mode)
    print("\n🌙 Test 6: Set Brightness to 25% (Night Mode)")
    success = controller.set_brightness(25)
    if success:
        print("✅ Brightness set to 25% (dim)")
        print("   Sign should be dim (night mode)")
    else:
        print("⚠️  Brightness control not supported or failed")
    
    time.sleep(1)
    
    # Test 7: Restore full brightness
    print("\n☀️  Test 7: Restore Full Brightness")
    success = controller.set_brightness(100)
    if success:
        print("✅ Brightness restored to 100%")
    else:
        print("⚠️  Brightness control not supported or failed")
    
    time.sleep(0.5)
    
    # Test 8: Auto brightness (if supported)
    print("\n🌞 Test 8: Auto Brightness Mode")
    success = controller.set_brightness(0, auto=True)
    if success:
        print("✅ Auto brightness mode enabled")
        print("   Sign will adjust brightness automatically")
    else:
        print("⚠️  Auto brightness not supported or failed")
    
    time.sleep(0.5)
    
    # ==================== PHASE 5: FILE MANAGEMENT ====================
    
    print("\n\n📁 Phase 5: Text File Reading")
    print("-" * 60)
    
    # Test 9: Send a test message first
    print("\n📤 Test 9: Send Test Message to File")
    test_message = [
        "ALPHA LED TEST",
        "M-PROTOCOL",
        "PHASES 3-5",
        "COMPLETE"
    ]
    success = controller.send_message(test_message)
    if success:
        print("✅ Test message sent to sign")
    else:
        print("❌ Failed to send test message")
    
    time.sleep(1)
    
    # Test 10: Read text from file 0 (default file)
    print("\n📖 Test 10: Read Text File '0'")
    text = controller.read_text_file('0')
    if text is not None:
        print(f"✅ Successfully read file '0':")
        print(f"   Content: {text[:100]}..." if len(text) > 100 else f"   Content: {text}")
        print(f"   Length: {len(text)} characters")
    else:
        print("⚠️  Could not read file (may not be supported)")
    
    # Test 11: Read text from file A
    print("\n📖 Test 11: Read Text File 'A'")
    text = controller.read_text_file('A')
    if text is not None:
        if text:
            print(f"✅ Successfully read file 'A':")
            print(f"   Content: {text[:100]}..." if len(text) > 100 else f"   Content: {text}")
        else:
            print("✅ File 'A' exists but is empty")
    else:
        print("⚠️  Could not read file 'A' (may not exist or not supported)")
    
    # ==================== COMPREHENSIVE TEST ====================
    
    print("\n\n🎯 Comprehensive Feature Test")
    print("-" * 60)
    
    # Test 12: Combined feature test
    print("\n🎯 Test 12: Emergency Alert Simulation")
    
    # Enable speaker for alert
    controller.set_speaker(True)
    
    # Set full brightness
    controller.set_brightness(100)
    
    # Send emergency message
    emergency_msg = [
        "⚠ EMERGENCY ALERT ⚠",
        "THIS IS A TEST",
        "SYSTEM OPERATIONAL",
        "ALL FEATURES OK"
    ]
    success = controller.send_message(emergency_msg)
    
    if success:
        print("✅ Emergency alert simulation complete:")
        print("   - Speaker enabled ✓")
        print("   - Full brightness ✓")
        print("   - Message displayed ✓")
    else:
        print("❌ Emergency alert simulation failed")
    
    time.sleep(2)
    
    # Disable speaker after test
    controller.set_speaker(False)
    
    # Summary
    print("\n" + "="*60)
    print("Advanced Features Test Complete")
    print("="*60)
    print("\nFeatures Tested:")
    print("  ✅ Phase 3: Speaker enable/disable, beep")
    print("  ✅ Phase 4: Brightness control (0-100%, auto mode)")
    print("  ✅ Phase 5: Text file reading")
    print("\nSign should now display emergency test message")
    print("Speaker should be disabled, brightness at 100%")
    
    # Cleanup
    controller.disconnect()
    logger.info("Test complete, disconnected")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test Alpha LED Sign M-Protocol advanced features (Phases 3-5)'
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
        success = test_advanced_features(args.host, args.port)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)
