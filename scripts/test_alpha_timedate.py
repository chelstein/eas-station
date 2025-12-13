#!/usr/bin/env python3
"""
Test script for Alpha LED Sign M-Protocol Phase 2: Time/Date Control.
Demonstrates setting time, date, day of week, time format, and run mode.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.led_sign_controller import Alpha9120CController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_time_date_control(host: str, port: int = 10001):
    """
    Test M-Protocol Phase 2 time/date control functionality.
    
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
    print("Alpha LED Sign Time/Date Control - M-Protocol Phase 2")
    print("="*60 + "\n")
    
    # Test 1: Sync time with system
    print("🕐 Test 1: Sync Time with System")
    print("-" * 60)
    
    success = controller.sync_time_with_system()
    if success:
        now = datetime.now()
        print(f"✅ Sign synchronized to system time")
        print(f"   Current time: {now.strftime('%Y-%m-%d %H:%M:%S %A')}")
    else:
        print("❌ Failed to sync time")
    
    # Test 2: Set specific time and date
    print("\n🕑 Test 2: Set Specific Time/Date")
    print("-" * 60)
    
    test_time = datetime(2025, 12, 25, 12, 0, 0)  # Christmas noon
    success = controller.set_time_and_date(test_time)
    if success:
        print(f"✅ Time set to: {test_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("❌ Failed to set specific time")
    
    # Wait a moment
    import time
    time.sleep(1)
    
    # Test 3: Set back to current time
    print("\n🕒 Test 3: Restore Current Time")
    print("-" * 60)
    
    success = controller.set_time_and_date()
    if success:
        print(f"✅ Time restored to: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("❌ Failed to restore time")
    
    # Test 4: Set day of week
    print("\n📅 Test 4: Set Day of Week")
    print("-" * 60)
    
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    current_day = datetime.now().weekday()
    # Convert Python weekday (0=Monday) to Alpha weekday (0=Sunday)
    alpha_day = (current_day + 1) % 7
    
    success = controller.set_day_of_week(alpha_day)
    if success:
        print(f"✅ Day set to: {days[alpha_day]}")
    else:
        print("⚠️  Failed to set day of week (may not be supported)")
    
    # Test 5: Set time format to 24-hour
    print("\n🕓 Test 5: Set Time Format (24-hour)")
    print("-" * 60)
    
    success = controller.set_time_format(format_24h=True)
    if success:
        print("✅ Time format set to 24-hour")
    else:
        print("⚠️  Failed to set time format (may not be supported)")
    
    # Test 6: Set time format to 12-hour
    print("\n🕔 Test 6: Set Time Format (12-hour)")
    print("-" * 60)
    
    success = controller.set_time_format(format_24h=False)
    if success:
        print("✅ Time format set to 12-hour")
    else:
        print("⚠️  Failed to set time format (may not be supported)")
    
    # Restore to 24-hour for consistency
    controller.set_time_format(format_24h=True)
    
    # Test 7: Set run mode to auto
    print("\n⚙️  Test 7: Set Run Mode (Auto)")
    print("-" * 60)
    
    success = controller.set_run_mode(auto=True)
    if success:
        print("✅ Run mode set to AUTO")
        print("   Sign will display scheduled messages")
    else:
        print("⚠️  Failed to set run mode (may not be supported)")
    
    # Test 8: Set run mode to manual
    print("\n⚙️  Test 8: Set Run Mode (Manual)")
    print("-" * 60)
    
    success = controller.set_run_mode(auto=False)
    if success:
        print("✅ Run mode set to MANUAL")
        print("   Sign will hold current message")
    else:
        print("⚠️  Failed to set run mode (may not be supported)")
    
    # Restore to auto mode
    controller.set_run_mode(auto=True)
    
    # Test 9: Display test message showing time
    print("\n📤 Test 9: Display Message with Time")
    print("-" * 60)
    
    now = datetime.now()
    test_success = controller.send_message(
        lines=[
            "TIME SYNC TEST",
            f"DATE: {now.strftime('%m/%d/%Y')}",
            f"TIME: {now.strftime('%H:%M:%S')}",
            f"DAY: {now.strftime('%A')}"
        ]
    )
    
    if test_success:
        print("✅ Test message sent successfully")
        print("   Check sign display for time/date")
    else:
        print("❌ Failed to send test message")
    
    # Summary
    print("\n" + "="*60)
    print("Time/Date Control Test Complete")
    print("="*60)
    print(f"\nCurrent System Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %A')}")
    print("Sign should now display this time/date information")
    
    # Cleanup
    controller.disconnect()
    logger.info("Test complete, disconnected")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test Alpha LED Sign M-Protocol time/date control'
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
        success = test_time_date_control(args.host, args.port)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)
