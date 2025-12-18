#!/usr/bin/env python3
"""
Debug script to trace config flow from database to TTS engine
Run this on your server to see exactly what config values are being loaded
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()

with app.app_context():
    from app_core.tts_settings import get_tts_settings
    from app_utils.eas import load_eas_config

    print("=" * 80)
    print("CONFIG FLOW DEBUG")
    print("=" * 80)
    print()

    # Step 1: Check database
    print("STEP 1: Database TTS Settings")
    print("-" * 80)
    settings = get_tts_settings()
    print(f"settings.enabled = {settings.enabled}")
    print(f"settings.provider = '{settings.provider}'")
    print(f"settings.azure_openai_endpoint = {settings.azure_openai_endpoint}")
    print(f"settings.azure_openai_key = {'***' if settings.azure_openai_key else '(empty)'}")
    print(f"settings.azure_openai_model = {settings.azure_openai_model}")
    print(f"settings.azure_openai_voice = {settings.azure_openai_voice}")
    print(f"settings.azure_openai_speed = {settings.azure_openai_speed}")
    print()

    # Step 2: Check what load_eas_config produces
    print("STEP 2: load_eas_config() Output")
    print("-" * 80)
    config = load_eas_config()

    print(f"config['tts_provider'] = '{config.get('tts_provider')}'")
    print(f"config['azure_openai_endpoint'] = {config.get('azure_openai_endpoint')}")
    print(f"config['azure_openai_key'] = {'***' if config.get('azure_openai_key') else '(empty)'}")
    print(f"config['azure_openai_model'] = {config.get('azure_openai_model')}")
    print(f"config['azure_openai_voice'] = {config.get('azure_openai_voice')}")
    print(f"config['azure_openai_speed'] = {config.get('azure_openai_speed')}")
    print()

    # Step 3: Check what TTSEngine sees
    print("STEP 3: TTSEngine Config Access")
    print("-" * 80)
    from app_utils.eas_tts import TTSEngine
    import logging
    logger = logging.getLogger(__name__)

    tts = TTSEngine(config, logger, 16000)
    print(f"tts.provider = '{tts.provider}'")
    print(f"  (from config.get('tts_provider'))")
    print()

    # Try to access the config values TTS engine will use
    print("Values TTSEngine will use:")
    print(f"  endpoint = '{tts.config.get('azure_openai_endpoint') or ''}'")
    print(f"  api_key = {'***' if tts.config.get('azure_openai_key') else '(empty)'}")
    print(f"  model = '{tts.config.get('azure_openai_model') or ''}'")
    print(f"  voice = '{tts.config.get('azure_openai_voice') or ''}'")
    print(f"  speed = {tts.config.get('azure_openai_speed')}")
    print()

    # Step 4: Check if values match
    print("STEP 4: Verification")
    print("-" * 80)

    issues = []

    if settings.enabled and settings.provider:
        db_provider = settings.provider.strip().lower()
        config_provider = config.get('tts_provider', '').strip().lower()

        if db_provider != config_provider:
            issues.append(f"Provider mismatch: DB='{db_provider}' vs Config='{config_provider}'")

        if settings.provider == 'azure_openai':
            if settings.azure_openai_endpoint != config.get('azure_openai_endpoint'):
                issues.append("Endpoint mismatch between DB and config")
            if settings.azure_openai_key != config.get('azure_openai_key'):
                issues.append("API key mismatch between DB and config")

    if issues:
        print("❌ ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        if not settings.enabled:
            print("⚠️  TTS is DISABLED in database")
        elif not settings.provider:
            print("⚠️  TTS provider is EMPTY in database")
        elif not config.get('tts_provider'):
            print("❌ Config has empty tts_provider even though DB has it set!")
            print("   This is the bug!")
        else:
            print("✓ Database and config values match")

    print()
    print("=" * 80)
