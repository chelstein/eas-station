#!/usr/bin/env python3
"""
Quick script to enable and configure TTS via database
Run this if the web UI is not accessible
"""

import sys
import os

def enable_tts_in_database():
    """Enable TTS directly in the database."""

    print("=" * 80)
    print("EAS Station - TTS Quick Configuration Tool")
    print("=" * 80)
    print()
    print("This script will help you enable and configure TTS.")
    print()

    # Check for database
    db_path = 'instance/app.db'
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        print()
        print("💡 SOLUTIONS:")
        print("   1. Make sure you're running this from the EAS Station root directory")
        print("   2. Run database migrations: flask db upgrade")
        print("   3. Start the application first to create the database")
        return False

    try:
        import sqlite3
    except ImportError:
        print("❌ sqlite3 module not available")
        return False

    print("📋 TTS Provider Options:")
    print("   1. Azure OpenAI (cloud, high quality, requires API key)")
    print("   2. Azure Cognitive Services (cloud, requires API key)")
    print("   3. pyttsx3 (offline, free, lower quality)")
    print("   4. None (disable TTS)")
    print()

    provider_choice = input("Select provider (1-4): ").strip()

    provider_map = {
        '1': 'azure_openai',
        '2': 'azure',
        '3': 'pyttsx3',
        '4': ''
    }

    provider = provider_map.get(provider_choice, '')

    if not provider:
        print("\n❌ Disabling TTS...")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE tts_settings SET enabled = 0, provider = '' WHERE id = 1")
            conn.commit()
            conn.close()
            print("✅ TTS disabled successfully")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    # Azure OpenAI configuration
    if provider == 'azure_openai':
        print("\n" + "=" * 80)
        print("Azure OpenAI Configuration")
        print("=" * 80)
        print()
        print("You'll need:")
        print("1. Azure OpenAI endpoint URL")
        print("2. API key")
        print()
        print("Format: https://YOUR-RESOURCE.openai.azure.com/openai/deployments/YOUR-DEPLOYMENT/audio/speech?api-version=2024-03-01-preview")
        print()

        endpoint = input("Enter endpoint URL: ").strip()
        if not endpoint:
            print("❌ Endpoint is required")
            return False

        api_key = input("Enter API key: ").strip()
        if not api_key:
            print("❌ API key is required")
            return False

        voice = input("Enter voice (default: alloy): ").strip() or 'alloy'
        model = input("Enter model (default: tts-1): ").strip() or 'tts-1'
        speed = input("Enter speed 0.25-4.0 (default: 1.0): ").strip() or '1.0'

        try:
            speed = float(speed)
            if speed < 0.25 or speed > 4.0:
                print("⚠️  Speed out of range, using 1.0")
                speed = 1.0
        except ValueError:
            print("⚠️  Invalid speed, using 1.0")
            speed = 1.0

        # Update database
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tts_settings
                SET enabled = 1,
                    provider = ?,
                    azure_openai_endpoint = ?,
                    azure_openai_key = ?,
                    azure_openai_model = ?,
                    azure_openai_voice = ?,
                    azure_openai_speed = ?
                WHERE id = 1
            """, (provider, endpoint, api_key, model, voice, speed))
            conn.commit()
            conn.close()

            print("\n✅ TTS configuration saved!")
            print()
            print("📋 Configuration Summary:")
            print(f"   Provider: {provider}")
            print(f"   Endpoint: {endpoint}")
            print(f"   API Key: {'***' + api_key[-4:]}")
            print(f"   Model: {model}")
            print(f"   Voice: {voice}")
            print(f"   Speed: {speed}")
            print()
            print("💡 Next steps:")
            print("   1. Test with: python3 test_tts_api.py")
            print("   2. Verify in web UI: http://your-server/admin/tts")
            print("   3. Generate a test alert to verify TTS works")
            return True

        except Exception as e:
            print(f"\n❌ Error updating database: {e}")
            import traceback
            traceback.print_exc()
            return False

    elif provider == 'pyttsx3':
        print("\n✅ Configuring pyttsx3 (offline TTS)...")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE tts_settings SET enabled = 1, provider = 'pyttsx3' WHERE id = 1")
            conn.commit()
            conn.close()
            print("✅ TTS configured for pyttsx3")
            print("\n💡 Note: Make sure pyttsx3 and its dependencies are installed")
            print("   sudo apt-get install espeak ffmpeg")
            print("   pip install pyttsx3")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    elif provider == 'azure':
        print("\n❌ Azure Cognitive Services configuration not yet implemented in this script")
        print("   Please use the web UI at: http://your-server/admin/tts")
        return False

    return False


if __name__ == "__main__":
    success = enable_tts_in_database()
    sys.exit(0 if success else 1)
