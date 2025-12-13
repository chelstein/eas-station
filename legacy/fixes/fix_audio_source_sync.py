#!/usr/bin/env python3
"""
Fix Audio Source Sync for SDR Receivers

This script ensures that every enabled radio receiver with audio_output=True
has a corresponding audio source configuration in the database.

This is critical for the audio chain to work:
1. sdr-service reads from SDR hardware and publishes IQ samples to Redis
2. audio-service needs AudioSourceConfigDB entries to know which Redis channels to subscribe to
3. Without audio source configs, audio-service won't create RedisSDRSourceAdapter instances
4. Without adapters, no audio flows to the EAS monitor

Usage:
    python fix_audio_source_sync.py [--dry-run]
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment
config_path = os.environ.get('CONFIG_PATH', '.env')
if os.path.exists(config_path):
    load_dotenv(config_path, override=True)
    print(f"✅ Loaded environment from: {config_path}")
else:
    load_dotenv(override=True)
    print("Using default .env")

# Initialize Flask app for database access
from flask import Flask
from app_core.extensions import db
from app_core.models import RadioReceiver, AudioSourceConfigDB
from app_core.audio.ingest import AudioSourceType

app = Flask(__name__)

# Database configuration
database_url = os.getenv("DATABASE_URL")
if not database_url:
    # Fallback: build from individual POSTGRES_* variables
    postgres_host = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = os.getenv("POSTGRES_DB", "alerts")
    postgres_user = os.getenv("POSTGRES_USER", "eas-station")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    from urllib.parse import quote_plus
    escaped_password = quote_plus(postgres_password)
    
    database_url = (
        f"postgresql://{postgres_user}:{escaped_password}@"
        f"{postgres_host}:{postgres_port}/{postgres_db}"
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

def derive_source_name(receiver_identifier: str) -> str:
    """Generate audio source name from receiver identifier."""
    return f"sdr-{receiver_identifier}"

def recommend_audio_settings(receiver: RadioReceiver):
    """Recommend audio sample rate and channels based on receiver config."""
    modulation = (receiver.modulation_type or 'IQ').upper()
    
    # Determine channels (stereo for wide FM, mono for others)
    if modulation in ('FM', 'WFM', 'WBFM') and receiver.stereo_enabled:
        channels = 2  # Stereo for FM broadcast
    else:
        channels = 1  # Mono for everything else
    
    # Determine sample rate
    if modulation in ('FM', 'WFM', 'WBFM'):
        sample_rate = 48000 if channels == 2 else 32000
    elif modulation in ('NFM', 'AM'):
        sample_rate = 24000
    else:
        sample_rate = 44100  # Safe default
    
    return sample_rate, channels

def sync_audio_sources(dry_run=False):
    """Sync audio sources for all enabled radio receivers."""
    print("\n" + "="*80)
    print("SYNCING AUDIO SOURCES FOR RADIO RECEIVERS")
    print("="*80)
    
    with app.app_context():
        # Get all radio receivers
        receivers = RadioReceiver.query.all()
        print(f"\nFound {len(receivers)} radio receiver(s)")
        
        created = 0
        updated = 0
        skipped = 0
        removed = 0
        
        for receiver in receivers:
            source_name = derive_source_name(receiver.identifier)
            
            print(f"\n📻 Processing receiver: {receiver.identifier} ({receiver.display_name})")
            print(f"   Frequency: {receiver.frequency_hz/1e6:.3f} MHz")
            print(f"   Enabled: {receiver.enabled}")
            print(f"   Audio Output: {receiver.audio_output}")
            
            # Check if audio source should exist
            should_have_audio_source = receiver.enabled and receiver.audio_output
            
            # Find existing audio source
            db_config = AudioSourceConfigDB.query.filter_by(name=source_name).first()
            
            if should_have_audio_source:
                # Receiver needs an audio source
                sample_rate, channels = recommend_audio_settings(receiver)
                buffer_size = 4096 if channels == 1 else 8192
                silence_threshold = float(receiver.squelch_threshold_db or -60.0)
                silence_duration = max(float(receiver.squelch_close_ms or 750) / 1000.0, 0.1)
                
                device_params = {
                    'receiver_id': receiver.identifier,
                    'receiver_display_name': receiver.display_name,
                    'receiver_driver': receiver.driver,
                    'receiver_frequency_hz': float(receiver.frequency_hz or 0.0),
                    'receiver_modulation': (receiver.modulation_type or 'IQ').upper(),
                    'iq_sample_rate': receiver.sample_rate,
                    'demod_mode': receiver.modulation_type or 'FM',
                    'rbds_enabled': bool(receiver.enable_rbds),
                    'squelch_enabled': bool(receiver.squelch_enabled),
                    'squelch_threshold_db': silence_threshold,
                    'squelch_open_ms': int(receiver.squelch_open_ms or 150),
                    'squelch_close_ms': int(receiver.squelch_close_ms or 750),
                    'carrier_alarm_enabled': bool(receiver.squelch_alarm),
                }
                
                config_params = {
                    'sample_rate': sample_rate,
                    'channels': channels,
                    'buffer_size': buffer_size,
                    'silence_threshold_db': silence_threshold,
                    'silence_duration_seconds': silence_duration,
                    'device_params': device_params,
                    'managed_by': 'radio',  # CRITICAL: This flag tells audio-service to use RedisSDRSourceAdapter
                    'squelch_enabled': bool(receiver.squelch_enabled),
                    'squelch_threshold_db': silence_threshold,
                    'squelch_open_ms': int(receiver.squelch_open_ms or 150),
                    'squelch_close_ms': int(receiver.squelch_close_ms or 750),
                    'carrier_alarm_enabled': bool(receiver.squelch_alarm),
                }
                
                freq_display = f"{receiver.frequency_hz/1e6:.3f} MHz" if receiver.frequency_hz else "Unknown"
                description = f"SDR monitor for {receiver.display_name} · {freq_display}"
                
                if db_config is None:
                    # Create new audio source
                    print(f"   ➕ Creating audio source: {source_name}")
                    print(f"      Sample Rate: {sample_rate} Hz")
                    print(f"      Channels: {channels}")
                    print(f"      Auto Start: {receiver.auto_start}")
                    
                    if not dry_run:
                        db_config = AudioSourceConfigDB(
                            name=source_name,
                            source_type=AudioSourceType.SDR.value,
                            config_params=config_params,
                            priority=10,
                            enabled=True,
                            auto_start=receiver.auto_start,
                            description=description,
                        )
                        db.session.add(db_config)
                        created += 1
                    else:
                        print(f"      [DRY RUN] Would create audio source")
                        created += 1
                else:
                    # Update existing audio source
                    needs_update = False
                    changes = []
                    
                    if (db_config.config_params or {}) != config_params:
                        needs_update = True
                        changes.append("config_params")
                    
                    if not db_config.enabled:
                        needs_update = True
                        changes.append("enabled")
                    
                    if db_config.auto_start != receiver.auto_start:
                        needs_update = True
                        changes.append("auto_start")
                    
                    if (db_config.description or '') != description:
                        needs_update = True
                        changes.append("description")
                    
                    if needs_update:
                        print(f"   🔄 Updating audio source: {source_name}")
                        print(f"      Changes: {', '.join(changes)}")
                        
                        if not dry_run:
                            db_config.config_params = config_params
                            db_config.enabled = True
                            db_config.auto_start = receiver.auto_start
                            db_config.description = description
                            db_config.priority = 10
                            updated += 1
                        else:
                            print(f"      [DRY RUN] Would update audio source")
                            updated += 1
                    else:
                        print(f"   ✅ Audio source already up-to-date: {source_name}")
                        skipped += 1
            else:
                # Receiver disabled or audio output disabled - remove audio source if it exists
                if db_config is not None:
                    print(f"   ➖ Removing audio source: {source_name}")
                    print(f"      Reason: Receiver disabled or audio_output=False")
                    
                    if not dry_run:
                        db.session.delete(db_config)
                        removed += 1
                    else:
                        print(f"      [DRY RUN] Would remove audio source")
                        removed += 1
                else:
                    print(f"   ⏭️  Skipping (no audio output needed)")
                    skipped += 1
        
        # Commit changes
        if not dry_run:
            db.session.commit()
            print(f"\n✅ Changes committed to database")
        else:
            print(f"\n[DRY RUN] No changes committed")
        
        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"  Created: {created}")
        print(f"  Updated: {updated}")
        print(f"  Removed: {removed}")
        print(f"  Skipped (no changes): {skipped}")
        
        if created > 0 or updated > 0:
            print("\n⚠️  IMPORTANT: Restart audio-service container for changes to take effect:")
            print("   docker restart eas-audio-service")
        
        return created + updated + removed > 0

def main():
    parser = argparse.ArgumentParser(description="Sync audio sources for SDR receivers")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be done without making changes")
    args = parser.parse_args()
    
    try:
        changed = sync_audio_sources(dry_run=args.dry_run)
        
        if changed:
            print("\n✅ Audio source sync completed successfully")
            if not args.dry_run:
                print("\nNext steps:")
                print("1. Restart audio-service: docker restart eas-audio-service")
                print("2. Check audio-service logs: docker logs -f eas-audio-service")
                print("3. Look for '✅ Loaded Redis SDR source' messages")
            return 0
        else:
            print("\n✅ No changes needed - audio sources are already in sync")
            return 0
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
