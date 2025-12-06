#!/usr/bin/env python3
"""
Diagnostic script to check receiver configuration for audio output issues.
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

def check_receiver_config():
    """Check receiver configuration for common issues."""
    
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
        print("RECEIVER CONFIGURATION DIAGNOSTIC")
        print("=" * 80)
        print()
        
        # Check all receivers
        receivers = RadioReceiver.query.all()
        
        if not receivers:
            print("❌ No receivers found in database!")
            return
        
        print(f"Found {len(receivers)} receiver(s):\n")
        
        for receiver in receivers:
            print(f"Receiver: {receiver.identifier} ({receiver.display_name})")
            print(f"  Driver: {receiver.driver}")
            print(f"  Frequency: {receiver.frequency_hz / 1e6:.3f} MHz")
            print(f"  IQ Sample Rate: {receiver.sample_rate / 1e6:.1f} MHz")
            print(f"  Audio Sample Rate: {receiver.audio_sample_rate or 'Not set'} Hz")
            print(f"  Modulation: {receiver.modulation_type}")
            print(f"  Audio Output: {receiver.audio_output} {'✅' if receiver.audio_output else '❌ DISABLED'}")
            print(f"  Stereo: {receiver.stereo_enabled}")
            print(f"  Enabled: {receiver.enabled}")
            print(f"  Auto Start: {receiver.auto_start}")
            
            # Check for issues
            issues = []
            
            if not receiver.audio_output:
                issues.append("❌ audio_output is FALSE - demodulation disabled!")
            
            if receiver.modulation_type == 'IQ':
                issues.append("❌ modulation_type is 'IQ' - cannot demodulate to audio!")
            
            if not receiver.audio_sample_rate or receiver.audio_sample_rate < 20000:
                issues.append(f"⚠️  audio_sample_rate is {receiver.audio_sample_rate} - may use default")
            
            if not receiver.enabled:
                issues.append("⚠️  Receiver is disabled")
            
            if not receiver.auto_start:
                issues.append("⚠️  Auto-start is disabled")
            
            if issues:
                print("\n  Issues found:")
                for issue in issues:
                    print(f"    {issue}")
            else:
                print("\n  ✅ Configuration looks good!")
            
            print()
        
        # Check audio sources
        print("=" * 80)
        print("AUDIO SOURCE CONFIGURATION")
        print("=" * 80)
        print()
        
        audio_sources = AudioSourceConfigDB.query.filter_by(source_type='sdr').all()
        
        if not audio_sources:
            print("❌ No SDR audio sources found in database!")
            return
        
        print(f"Found {len(audio_sources)} SDR audio source(s):\n")
        
        for source in audio_sources:
            print(f"Audio Source: {source.name}")
            print(f"  Type: {source.source_type}")
            print(f"  Enabled: {source.enabled}")
            print(f"  Auto Start: {source.auto_start}")
            print(f"  Priority: {source.priority}")
            
            # Get receiver ID from device params
            device_params = source.config_params.get('device_params', {})
            receiver_id = device_params.get('receiver_id')
            
            if receiver_id:
                print(f"  Receiver ID: {receiver_id}")
                
                # Find matching receiver
                receiver = RadioReceiver.query.filter_by(identifier=receiver_id).first()
                if receiver:
                    print(f"  ✅ Receiver found: {receiver.display_name}")
                    if not receiver.audio_output:
                        print(f"    ❌ WARNING: Receiver has audio_output=FALSE!")
                    if receiver.modulation_type == 'IQ':
                        print(f"    ❌ WARNING: Receiver modulation is 'IQ'!")
                else:
                    print(f"  ❌ Receiver '{receiver_id}' not found!")
            else:
                print(f"  ❌ No receiver_id in device_params!")
            
            print()
        
        print("=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print()
        
        # Provide recommendations
        for receiver in receivers:
            if not receiver.audio_output or receiver.modulation_type == 'IQ':
                print(f"To fix receiver '{receiver.identifier}':")
                print(f"  UPDATE radio_receivers")
                print(f"  SET audio_output = TRUE,")
                print(f"      modulation_type = 'NFM'  -- or 'FM', 'WFM', 'AM'")
                print(f"  WHERE identifier = '{receiver.identifier}';")
                print()

if __name__ == "__main__":
    check_receiver_config()