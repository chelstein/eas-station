#!/usr/bin/env python3
"""Debug script to check TTS configuration and test API calls."""

import os
import sys

# Set up the Flask app context
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()

with app.app_context():
    from app_core.tts_settings import get_tts_settings
    from app_utils.eas import load_eas_config
    from app_utils.eas_tts import TTSEngine
    import logging

    # Set up logging to see debug messages
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)

    print("=" * 80)
    print("TTS Configuration Debug Report")
    print("=" * 80)
    print()

    # 1. Check database settings
    print("1. Database TTS Settings:")
    print("-" * 80)
    try:
        settings = get_tts_settings()
        print(f"   Enabled: {settings.enabled}")
        print(f"   Provider: '{settings.provider}'")
        print(f"   Azure OpenAI Endpoint: {settings.azure_openai_endpoint}")
        print(f"   Azure OpenAI Key: {'***' + settings.azure_openai_key[-4:] if settings.azure_openai_key and len(settings.azure_openai_key) > 4 else '(not set)'}")
        print(f"   Azure OpenAI Model: {settings.azure_openai_model}")
        print(f"   Azure OpenAI Voice: {settings.azure_openai_voice}")
        print(f"   Azure OpenAI Speed: {settings.azure_openai_speed}")
        print(f"   Updated At: {settings.updated_at}")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
    print()

    # 2. Check EAS config loading
    print("2. EAS Config (loaded from database):")
    print("-" * 80)
    try:
        config = load_eas_config()
        print(f"   tts_provider: '{config.get('tts_provider')}'")
        print(f"   azure_openai_endpoint: {config.get('azure_openai_endpoint')}")
        print(f"   azure_openai_key: {'***' + str(config.get('azure_openai_key'))[-4:] if config.get('azure_openai_key') else '(not set)'}")
        print(f"   azure_openai_model: {config.get('azure_openai_model')}")
        print(f"   azure_openai_voice: {config.get('azure_openai_voice')}")
        print(f"   azure_openai_speed: {config.get('azure_openai_speed')}")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
    print()

    # 3. Test TTS Engine initialization
    print("3. TTS Engine Test:")
    print("-" * 80)
    try:
        config = load_eas_config()
        tts_engine = TTSEngine(config, logger, 16000)
        print(f"   TTS Engine created successfully")
        print(f"   Provider: '{tts_engine.provider}'")

        # Try to generate a short test phrase
        if tts_engine.provider:
            print(f"   Testing TTS with provider '{tts_engine.provider}'...")
            test_text = "This is a test."
            samples = tts_engine.generate(test_text)

            if samples:
                print(f"   ✓ TTS SUCCESS: Generated {len(samples)} audio samples")
            else:
                error = tts_engine.last_error
                print(f"   ✗ TTS FAILED: {error or 'No error message'}")
        else:
            print(f"   No TTS provider configured - TTS is disabled or not set up")

    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
    print()

    # 4. Environment variables check (legacy)
    print("4. Legacy Environment Variables (should NOT be used):")
    print("-" * 80)
    env_vars = [
        'EAS_TTS_PROVIDER',
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_KEY',
        'AZURE_OPENAI_CONFIG',
    ]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'KEY' in var.upper():
                display = '***' + value[-4:] if len(value) > 4 else '***'
            else:
                display = value[:50] + '...' if len(value) > 50 else value
            print(f"   {var}: {display}")
        else:
            print(f"   {var}: (not set)")
    print()

    print("=" * 80)
    print("Debug report complete")
    print("=" * 80)
