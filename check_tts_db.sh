#!/bin/bash
# Quick script to check TTS settings directly from the database

echo "================================================================================"
echo "TTS Configuration Check"
echo "================================================================================"
echo ""

# Find the database file
echo "🔍 Looking for database file..."
if [ -f "instance/app.db" ]; then
    DB_PATH="instance/app.db"
elif [ -f "/var/lib/eas-station/app.db" ]; then
    DB_PATH="/var/lib/eas-station/app.db"
elif [ -f "/opt/eas-station/instance/app.db" ]; then
    DB_PATH="/opt/eas-station/instance/app.db"
else
    # Try to find it
    DB_PATH=$(find /opt/eas-station /var/lib -name "app.db" 2>/dev/null | head -1)
fi

if [ -z "$DB_PATH" ] || [ ! -f "$DB_PATH" ]; then
    echo "❌ Database file not found!"
    echo ""
    echo "Searched in:"
    echo "  - instance/app.db"
    echo "  - /var/lib/eas-station/app.db"
    echo "  - /opt/eas-station/instance/app.db"
    echo ""
    echo "Please locate your database file and run:"
    echo "  sqlite3 /path/to/app.db 'SELECT * FROM tts_settings;'"
    exit 1
fi

echo "✓ Found database: $DB_PATH"
echo ""

# Check if sqlite3 is available
if ! command -v sqlite3 &> /dev/null; then
    echo "❌ sqlite3 command not found"
    echo ""
    echo "Installing sqlite3..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y sqlite3
    elif command -v yum &> /dev/null; then
        sudo yum install -y sqlite
    else
        echo "Please install sqlite3 manually and rerun this script"
        exit 1
    fi
fi

echo "📋 TTS Settings from database:"
echo "--------------------------------------------------------------------------------"
sqlite3 "$DB_PATH" <<EOF
.mode column
.headers on
.width 10 10 60 20 15 15 10
SELECT
    enabled,
    provider,
    CASE
        WHEN LENGTH(azure_openai_endpoint) > 60 THEN SUBSTR(azure_openai_endpoint, 1, 57) || '...'
        ELSE COALESCE(azure_openai_endpoint, '(not set)')
    END as endpoint,
    CASE
        WHEN azure_openai_key IS NOT NULL AND LENGTH(azure_openai_key) > 4
        THEN '***' || SUBSTR(azure_openai_key, -4)
        ELSE '(not set)'
    END as api_key,
    azure_openai_model as model,
    azure_openai_voice as voice,
    azure_openai_speed as speed
FROM tts_settings
WHERE id = 1;
EOF

echo ""
echo "--------------------------------------------------------------------------------"
echo ""

# Check what the settings say
ENABLED=$(sqlite3 "$DB_PATH" "SELECT enabled FROM tts_settings WHERE id=1;")
PROVIDER=$(sqlite3 "$DB_PATH" "SELECT provider FROM tts_settings WHERE id=1;")

if [ "$ENABLED" = "0" ] || [ -z "$PROVIDER" ]; then
    echo "❌ TTS IS DISABLED"
    echo ""
    echo "💡 SOLUTION:"
    echo "   1. Go to http://your-server/admin/tts"
    echo "   2. Set 'TTS Enabled' to 'Enabled'"
    echo "   3. Select 'Azure OpenAI' as provider"
    echo "   4. Fill in your endpoint and API key"
    echo "   5. Click 'Save Settings'"
    echo ""
    echo "   OR use the interactive configuration script:"
    echo "   python3 enable_tts.py"
else
    echo "✅ TTS is ENABLED with provider: $PROVIDER"
    echo ""

    if [ "$PROVIDER" = "azure_openai" ]; then
        ENDPOINT=$(sqlite3 "$DB_PATH" "SELECT azure_openai_endpoint FROM tts_settings WHERE id=1;")
        KEY=$(sqlite3 "$DB_PATH" "SELECT azure_openai_key FROM tts_settings WHERE id=1;")

        if [ -z "$ENDPOINT" ] || [ -z "$KEY" ]; then
            echo "⚠️  WARNING: Azure OpenAI credentials are incomplete"
            echo "   Endpoint: ${ENDPOINT:-(not set)}"
            echo "   API Key: ${KEY:+(set)}${KEY:-(not set)}"
        else
            echo "✅ Azure OpenAI credentials are configured"
            echo ""
            echo "🧪 To test the API endpoint, run:"
            echo "   python3 test_tts_api.py"
            echo ""
            echo "   Or test by generating an alert at:"
            echo "   http://your-server/eas/workflow"
        fi
    fi
fi

echo ""
echo "================================================================================"
echo "Check complete"
echo "================================================================================"
