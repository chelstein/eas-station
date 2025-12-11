#!/usr/bin/env python3
"""Debug script to inspect Redis metrics for EAS Station."""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import redis
import json
import datetime

from app_core.config.redis_config import (
    get_redis_host,
    get_redis_port,
    get_redis_db,
    get_redis_password,
    RedisTimeouts,
)


def inspect_metrics():
    host = get_redis_host()
    port = get_redis_port()
    db = get_redis_db()
    password = get_redis_password()

    print(f"Connecting to Redis at {host}:{port}...")
    try:
        r = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            socket_connect_timeout=RedisTimeouts.CONNECT_TIMEOUT,
        )
        r.ping()
        print("✅ Connected to Redis!")
        
        # Get radio_manager metrics
        raw_data = r.hget("eas:metrics", "radio_manager")
        if not raw_data:
            print("❌ No 'radio_manager' metrics found in 'eas:metrics'")
            return
            
        data = json.loads(raw_data)
        print("\n📊 Radio Manager Metrics:")
        print(f"  - Loaded Receivers: {data.get('loaded_receiver_count')}")
        print(f"  - Running Receivers: {data.get('running_receiver_count')}")
        
        receivers = data.get("receivers", {})
        for ident, receiver in receivers.items():
            print(f"\n  📻 Receiver: {ident}")
            print(f"     - Locked: {receiver.get('locked')}")
            print(f"     - Signal: {receiver.get('signal_strength')} dBFS")
            
            reported_at = receiver.get("reported_at")
            print(f"     - Reported At (Raw): {reported_at!r} (Type: {type(reported_at).__name__})")
            
            if reported_at:
                try:
                    # Try parsing as ISO
                    dt = datetime.datetime.fromisoformat(reported_at)
                    print(f"     - Parsed ISO: {dt}")
                except ValueError:
                    print("     - ❌ Not valid ISO format")
                    # Check if it looks like a timestamp
                    try:
                        ts = float(reported_at)
                        print(f"     - As Timestamp (sec): {datetime.datetime.fromtimestamp(ts)}")
                        print(f"     - As Timestamp (ms):  {datetime.datetime.fromtimestamp(ts/1000)}")
                    except ValueError:
                        pass

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_metrics()
