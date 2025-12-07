#!/usr/bin/env python3
"""
Comprehensive SDR Pipeline Fix Script

This script diagnoses and fixes all issues preventing SDR audio from working.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from app_core.extensions import db
from app_core.models import RadioReceiver, AudioSourceConfigDB

def fix_sdr_pipeline():
    """Diagnose and fix SDR pipeline issues."""
    
    app = Flask(__name__)
    
    # Database configuration
    postgres_host = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = os.getenv("POSTGRES_DB", "alerts")
    postgres_user = os.getenv("POSTGRES_USER", "postgres")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    from urllib.parse import quote_plus
    escaped_password = quote_plus(postgres_password)
    
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"postgresql://{postgres_user}:{escaped_password}@"
        f"{postgres_host}:{postgres_port}/{postgres_db}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    db.init_app(app)
    
    with app.app_context():
        print("=" * 80)
        print("SDR PIPELINE COMPREHENSIVE FIX")
        print("=" * 80)
        print()
        
        # Step 1: Check receivers
        print("STEP 1: Checking receiver configuration...")
        print("-" * 80)
        
        receivers = RadioReceiver.query.all()
        
        if not receivers:
            print("❌ ERROR: No receivers found in database!")
            print("   You need to create a receiver first.")
            return False
        
        fixes_needed = []
        
        for receiver in receivers:
            print(f"\nReceiver: {receiver.identifier} ({receiver.display_name})")
            print(f"  Driver: {receiver.driver}")
            print(f"  Frequency: {receiver.frequency_hz / 1e6:.3f} MHz")
            print(f"  IQ Sample Rate: {receiver.sample_rate / 1e6:.1f} MHz")
            print(f"  Audio Sample Rate: {receiver.audio_sample_rate or 'Not set'} Hz")
            print(f"  Modulation: {receiver.modulation_type}")
            print(f"  Audio Output: {receiver.audio_output}")
            print(f"  Enabled: {receiver.enabled}")
            print(f"  Auto Start: {receiver.auto_start}")
            
            # Check for issues and prepare fixes
            needs_fix = False
            
            if not receiver.audio_output:
                print(f"  ❌ ISSUE: audio_output is FALSE")
                fixes_needed.append(f"  - Enable audio_output for {receiver.identifier}")
                receiver.audio_output = True
                needs_fix = True
            
            if receiver.modulation_type == 'IQ':
                print(f"  ❌ ISSUE: modulation_type is 'IQ' (cannot demodulate)")
                fixes_needed.append(f"  - Change modulation_type to 'NFM' for {receiver.identifier}")
                receiver.modulation_type = 'NFM'
                needs_fix = True
            
            if not receiver.audio_sample_rate or receiver.audio_sample_rate < 20000:
                print(f"  ⚠️  ISSUE: audio_sample_rate is {receiver.audio_sample_rate}")
                fixes_needed.append(f"  - Set audio_sample_rate to 48000 for {receiver.identifier}")
                receiver.audio_sample_rate = 48000
                needs_fix = True
            
            if not receiver.enabled:
                print(f"  ⚠️  ISSUE: Receiver is disabled")
                fixes_needed.append(f"  - Enable receiver {receiver.identifier}")
                receiver.enabled = True
                needs_fix = True
            
            if not receiver.auto_start:
                print(f"  ⚠️  ISSUE: Auto-start is disabled")
                fixes_needed.append(f"  - Enable auto_start for {receiver.identifier}")
                receiver.auto_start = True
                needs_fix = True
            
            if needs_fix:
                print(f"  🔧 Applying fixes...")
        
        # Step 2: Check audio sources
        print("\n" + "=" * 80)
        print("STEP 2: Checking audio source configuration...")
        print("-" * 80)
        
        audio_sources = AudioSourceConfigDB.query.filter_by(source_type='sdr').all()
        
        if not audio_sources:
            print("❌ ERROR: No SDR audio sources found in database!")
            print("   Creating audio sources for receivers...")
            
            for receiver in receivers:
                # Create audio source for this receiver
                audio_source = AudioSourceConfigDB(
                    name=f"sdr-{receiver.identifier}",
                    source_type='sdr',
                    enabled=True,
                    auto_start=True,
                    priority=1,
                    description=f"SDR audio from {receiver.display_name}",
                    config_params={
                        'sample_rate': 48000,
                        'channels': 1,
                        'buffer_size': 4096,
                        'silence_threshold_db': -60.0,
                        'silence_duration_seconds': 5.0,
                        'device_params': {
                            'receiver_id': receiver.identifier,
                            'iq_sample_rate': receiver.sample_rate
                        }
                    }
                )
                db.session.add(audio_source)
                print(f"  ✅ Created audio source: sdr-{receiver.identifier}")
                fixes_needed.append(f"  - Created audio source for {receiver.identifier}")
        else:
            for source in audio_sources:
                print(f"\nAudio Source: {source.name}")
                print(f"  Type: {source.source_type}")
                print(f"  Enabled: {source.enabled}")
                print(f"  Auto Start: {source.auto_start}")
                
                needs_fix = False
                
                if not source.enabled:
                    print(f"  ⚠️  ISSUE: Source is disabled")
                    source.enabled = True
                    needs_fix = True
                
                if not source.auto_start:
                    print(f"  ⚠️  ISSUE: Auto-start is disabled")
                    source.auto_start = True
                    needs_fix = True
                
                # Check device_params
                device_params = source.config_params.get('device_params', {})
                receiver_id = device_params.get('receiver_id')
                
                if not receiver_id:
                    print(f"  ❌ ISSUE: No receiver_id in device_params")
                    # Try to infer from source name
                    if 'wxj93' in source.name.lower():
                        device_params['receiver_id'] = 'wxj93'
                        source.config_params['device_params'] = device_params
                        print(f"  🔧 Set receiver_id to 'wxj93'")
                        needs_fix = True
                
                # Check if iq_sample_rate is missing and add it from the receiver
                if receiver_id and 'iq_sample_rate' not in device_params:
                    receiver = RadioReceiver.query.filter_by(identifier=receiver_id).first()
                    if receiver and receiver.sample_rate:
                        print(f"  ⚠️  ISSUE: No iq_sample_rate in device_params")
                        device_params['iq_sample_rate'] = receiver.sample_rate
                        # Update the source config with modified device_params
                        config_params = source.config_params.copy()
                        config_params['device_params'] = device_params
                        source.config_params = config_params
                        print(f"  🔧 Set iq_sample_rate to {receiver.sample_rate}Hz from receiver")
                        fixes_needed.append(f"  - Added iq_sample_rate to {source.name}")
                        needs_fix = True
                
                if needs_fix:
                    print(f"  🔧 Applying fixes...")
        
        # Step 3: Apply all fixes
        if fixes_needed:
            print("\n" + "=" * 80)
            print("STEP 3: Applying fixes to database...")
            print("-" * 80)
            print("\nFixes to be applied:")
            for fix in fixes_needed:
                print(fix)
            
            try:
                db.session.commit()
                print("\n✅ All fixes applied successfully!")
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ ERROR applying fixes: {e}")
                return False
        else:
            print("\n✅ No fixes needed - configuration looks good!")
        
        # Step 4: Provide restart instructions
        print("\n" + "=" * 80)
        print("STEP 4: Restart services")
        print("-" * 80)
        print("\nTo apply these changes, restart the following services:")
        print("  docker restart sdr-service")
        print("  docker restart audio-service")
        print("\nWait 10-15 seconds after restart, then check the webapp.")
        
        # Step 5: Verification checklist
        print("\n" + "=" * 80)
        print("STEP 5: Verification checklist")
        print("-" * 80)
        print("\nAfter restarting services, verify:")
        print("  1. Webapp shows source without 'could not be loaded' error")
        print("  2. Timestamp shows current date/time (not 1970)")
        print("  3. Waterfall shows signal peaks")
        print("  4. Audio monitor shows demodulated audio")
        print("  5. Peak/RMS levels are updating")
        
        print("\n" + "=" * 80)
        print("If issues persist, check logs:")
        print("  docker logs sdr-service --tail 50")
        print("  docker logs audio-service --tail 50")
        print("=" * 80)
        
        return True

if __name__ == "__main__":
    success = fix_sdr_pipeline()
    sys.exit(0 if success else 1)