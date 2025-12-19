#!/usr/bin/env python3
"""
Standalone TTS API test script - Tests Azure OpenAI TTS endpoint without Flask
"""

import re
import json

def validate_azure_openai_endpoint(endpoint):
    """Validate Azure OpenAI endpoint format and provide helpful feedback."""
    print("\n" + "=" * 80)
    print("Azure OpenAI Endpoint Validation")
    print("=" * 80)

    if not endpoint or not endpoint.strip():
        print("❌ ERROR: Endpoint is empty or not set")
        print("\n💡 SOLUTION:")
        print("   You need to configure the endpoint in the admin UI at:")
        print("   http://your-server/admin/tts")
        return False

    print(f"\n📍 Endpoint: {endpoint}")
    print()

    issues = []
    warnings = []

    # Check if it's an Azure endpoint
    if 'azure.com' in endpoint.lower():
        print("✓ Detected Azure OpenAI endpoint")

        # Check for required path components
        if '/openai/deployments/' not in endpoint:
            issues.append("Missing '/openai/deployments/' in path")
            print("❌ Missing '/openai/deployments/' in path")

        if '/audio/speech' not in endpoint:
            issues.append("Missing '/audio/speech' in path")
            print("❌ Missing '/audio/speech' in path")

        if '?api-version=' not in endpoint:
            warnings.append("Missing '?api-version=' parameter")
            print("⚠️  Missing '?api-version=' parameter (may still work but recommended)")

        # Try to extract deployment name
        deployment_match = re.search(r'/deployments/([^/]+)/', endpoint)
        if deployment_match:
            deployment_name = deployment_match.group(1)
            print(f"✓ Deployment name extracted: '{deployment_name}'")
            print(f"\n  ℹ️  NOTE: The deployment name '{deployment_name}' will be used as the")
            print(f"     'model' parameter in API calls, NOT the configured model name!")
        else:
            issues.append("Could not extract deployment name from URL")
            print("❌ Could not extract deployment name from URL")

        # Check API version
        version_match = re.search(r'api-version=([^&]+)', endpoint)
        if version_match:
            api_version = version_match.group(1)
            print(f"✓ API version: {api_version}")

            # Check if version is recent enough
            if '2024-' in api_version or '2025-' in api_version:
                print(f"  ✓ API version looks current")
            else:
                warnings.append(f"API version {api_version} may be outdated")
                print(f"  ⚠️  API version {api_version} may be outdated")

    elif 'api.openai.com' in endpoint.lower():
        print("✓ Detected standard OpenAI endpoint")

        expected = 'https://api.openai.com/v1/audio/speech'
        if endpoint != expected:
            warnings.append(f"Endpoint may be incorrect. Expected: {expected}")
            print(f"⚠️  Endpoint may be incorrect")
            print(f"   Expected: {expected}")
            print(f"   Got:      {endpoint}")
    else:
        warnings.append("Unknown endpoint format - not Azure or OpenAI")
        print("⚠️  Unknown endpoint format - not recognized as Azure or OpenAI")

    # Print summary
    print("\n" + "-" * 80)
    if issues:
        print("❌ VALIDATION FAILED")
        print("\n🔧 Issues found:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")

        print("\n💡 CORRECT FORMAT:")
        print("   https://YOUR-RESOURCE.openai.azure.com/openai/deployments/YOUR-DEPLOYMENT/audio/speech?api-version=2024-03-01-preview")
        print("\n   Replace:")
        print("   - YOUR-RESOURCE: Your Azure OpenAI resource name")
        print("   - YOUR-DEPLOYMENT: Your TTS deployment name (e.g., 'tts-hd', 'tts-1')")
        print("\n   📖 See: https://learn.microsoft.com/en-us/azure/ai-services/openai/text-to-speech-quickstart")
        return False
    else:
        print("✅ VALIDATION PASSED")
        if warnings:
            print("\n⚠️  Warnings:")
            for i, warning in enumerate(warnings, 1):
                print(f"   {i}. {warning}")
        return True


def test_api_call(endpoint, api_key, model, voice, speed):
    """Test actual API call to Azure OpenAI TTS."""
    print("\n" + "=" * 80)
    print("Azure OpenAI TTS API Test")
    print("=" * 80)

    if not endpoint or not api_key:
        print("❌ Cannot test API: endpoint or API key is missing")
        return False

    try:
        import requests
    except ImportError:
        print("❌ requests library not installed - cannot test API")
        print("   Install with: pip install requests")
        return False

    # Extract deployment name for model parameter
    deployment_name = None
    if 'azure.com' in endpoint.lower():
        deployment_match = re.search(r'/deployments/([^/]+)/', endpoint)
        if deployment_match:
            deployment_name = deployment_match.group(1)

    api_model = deployment_name if deployment_name else model

    print(f"\n📋 Test Parameters:")
    print(f"   Endpoint: {endpoint}")
    print(f"   API Key: {'***' + api_key[-4:] if len(api_key) > 4 else '***'}")
    print(f"   Model (sent): {api_model}")
    print(f"   Voice: {voice}")
    print(f"   Speed: {speed}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": api_model,
        "input": "This is a test of the emergency alert system.",
        "voice": voice,
        "speed": speed,
        "response_format": "wav",
    }

    print(f"\n🔄 Sending test request...")
    print(f"   POST {endpoint}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=30,
        )

        print(f"\n📨 Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
        print(f"   Content Length: {len(response.content)} bytes")

        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')

            # Check if we got audio or an error
            if 'audio' in content_type.lower() or 'wav' in content_type.lower():
                print(f"\n✅ SUCCESS: Received audio data ({len(response.content)} bytes)")
                print(f"   Content-Type: {content_type}")
                return True
            elif 'json' in content_type.lower() or 'text' in content_type.lower():
                print(f"\n❌ ERROR: Received {content_type} instead of audio")
                try:
                    error_data = response.json()
                    print(f"   Response: {json.dumps(error_data, indent=2)}")
                except (json.JSONDecodeError, ValueError):
                    print(f"   Response: {response.text[:500]}")
                return False
            else:
                # Might be audio without proper content-type
                if len(response.content) > 1000:
                    print(f"\n✅ LIKELY SUCCESS: Received {len(response.content)} bytes")
                    print(f"   (Content-Type header may be incorrect but data size suggests audio)")
                    return True
                else:
                    print(f"\n⚠️  WARNING: Received small response ({len(response.content)} bytes)")
                    print(f"   This may be an error message instead of audio")
                    return False
        else:
            print(f"\n❌ ERROR: API returned status {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error details: {json.dumps(error_data, indent=2)}")
            except (json.JSONDecodeError, ValueError):
                print(f"   Error details: {response.text[:500]}")

            # Provide specific guidance based on status code
            if response.status_code == 401:
                print(f"\n💡 SOLUTION: Authentication failed")
                print(f"   - Check that your API key is correct")
                print(f"   - Verify the key hasn't expired")
            elif response.status_code == 404:
                print(f"\n💡 SOLUTION: Endpoint not found")
                print(f"   - Verify your deployment name in the endpoint URL")
                print(f"   - Check that the deployment exists in your Azure portal")
                print(f"   - Ensure the endpoint URL is complete and correct")
            elif response.status_code == 400:
                print(f"\n💡 SOLUTION: Bad request")
                print(f"   - Check that your deployment supports TTS (not just chat)")
                print(f"   - Verify the API version is compatible")

            return False

    except requests.exceptions.Timeout:
        print(f"\n❌ ERROR: Request timed out after 30 seconds")
        print(f"   - Check your network connection")
        print(f"   - Verify the endpoint URL is correct")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ ERROR: Connection failed")
        print(f"   Details: {e}")
        print(f"   - Check your network connection")
        print(f"   - Verify the endpoint URL is reachable")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function - reads config from database and tests TTS."""
    print("=" * 80)
    print("TTS CONFIGURATION DIAGNOSTIC TOOL")
    print("=" * 80)
    print()
    print("This tool will help diagnose TTS configuration issues.")
    print()

    # Try to read from database
    print("📂 Checking database configuration...")
    try:
        # Try to read directly from SQLite database
        import sqlite3
        db_path = 'instance/app.db'

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT enabled, provider, azure_openai_endpoint, azure_openai_key, azure_openai_model, azure_openai_voice, azure_openai_speed FROM tts_settings WHERE id = 1")
            row = cursor.fetchone()
            conn.close()

            if row:
                enabled, provider, endpoint, api_key, model, voice, speed = row
                print(f"✓ Found TTS settings in database")
                print(f"\n📋 Current Configuration:")
                print(f"   Enabled: {enabled}")
                print(f"   Provider: '{provider}'")
                print(f"   Endpoint: {endpoint or '(not set)'}")
                print(f"   API Key: {'***' + api_key[-4:] if api_key and len(api_key) > 4 else '(not set)'}")
                print(f"   Model: {model}")
                print(f"   Voice: {voice}")
                print(f"   Speed: {speed}")

                if not enabled or not provider:
                    print(f"\n❌ TTS IS DISABLED")
                    print(f"\n💡 SOLUTION:")
                    print(f"   1. Go to http://your-server/admin/tts")
                    print(f"   2. Set 'TTS Enabled' to 'Enabled'")
                    print(f"   3. Select a provider (e.g., 'Azure OpenAI')")
                    print(f"   4. Fill in the required credentials")
                    print(f"   5. Click 'Save Settings'")
                    return

                if provider == 'azure_openai':
                    # Validate endpoint
                    if validate_azure_openai_endpoint(endpoint):
                        # Test API call
                        test_api_call(endpoint, api_key, model, voice, speed)
                else:
                    print(f"\n✓ Provider '{provider}' does not use API endpoint validation")
                    print(f"   (This diagnostic tool only tests Azure OpenAI)")
            else:
                print(f"❌ No TTS settings found in database")
                print(f"\n💡 SOLUTION:")
                print(f"   Run database migrations: flask db upgrade")
        except sqlite3.Error as e:
            print(f"❌ Database error: {e}")
    except ImportError:
        print(f"⚠️  sqlite3 not available, cannot read database")
        print(f"   Please manually check settings at http://your-server/admin/tts")

    print("\n" + "=" * 80)
    print("Diagnostic complete")
    print("=" * 80)


if __name__ == "__main__":
    main()
