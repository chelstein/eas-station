# How to Apply the TTS Configuration Fix

## Summary

**Problem Identified:**
The broadcast builder was using a **stale cached configuration** loaded at app startup. Even after you configured TTS via the web UI, the app continued using the old cached config where TTS was disabled.

**Solution:**
The code has been fixed to reload TTS settings fresh from the database each time audio is generated. This is now committed to branch `claude/debug-tts-api-83ZgG`.

---

## Step 1: Find Your Database

On your server at `/opt/eas-station`, run:

```bash
# Find the database file
find /opt /var -name "app.db" -o -name "*.db" 2>/dev/null | grep -v node_modules

# Or check your .env file
cd /opt/eas-station
grep DATABASE_URL .env
```

**Common locations:**
- `/opt/eas-station/instance/app.db` (SQLite)
- PostgreSQL (check DATABASE_URL in .env)

---

## Step 2: Check Current TTS Settings

### If using SQLite:

```bash
DB_PATH="/path/to/your/app.db"  # Replace with actual path

sqlite3 "$DB_PATH" "SELECT enabled, provider, azure_openai_endpoint FROM tts_settings WHERE id=1;"
```

### If using PostgreSQL:

```bash
# Get connection info from .env
source .env  # Or check .env manually

# Connect and check
psql "$DATABASE_URL" -c "SELECT enabled, provider, azure_openai_endpoint FROM tts_settings WHERE id=1;"
```

**What you should see:**
- If `enabled = 0` or `provider = ''`: TTS is disabled - configure via web UI
- If you see your endpoint and key: TTS is configured but wasn't working due to stale cache

---

## Step 3: Pull the Fix

On your server:

```bash
cd /opt/eas-station

# Pull the latest changes
git fetch origin claude/debug-tts-api-83ZgG
git checkout claude/debug-tts-api-83ZgG
git pull origin claude/debug-tts-api-83ZgG
```

---

## Step 4: Restart Your Application

The fix requires restarting the app to reload the code:

### If using Docker:

```bash
docker-compose restart
# or
docker restart eas-station
```

### If using systemd:

```bash
sudo systemctl restart eas-station
```

### If running manually:

```bash
# Stop the current process (Ctrl+C or kill)
# Then restart:
python3 app.py
# or
gunicorn app:app
```

---

## Step 5: Configure TTS (If Not Already Done)

1. **Go to** `http://your-server/admin/tts`

2. **Enable TTS:**
   - TTS Enabled: **Enabled**
   - Provider: **Azure OpenAI**

3. **Enter credentials:**
   - **Endpoint URL:** (full format required)
     ```
     https://YOUR-RESOURCE.openai.azure.com/openai/deployments/YOUR-DEPLOYMENT/audio/speech?api-version=2024-03-01-preview
     ```
   - **API Key:** Your Azure OpenAI key
   - **Voice:** Choose from alloy, echo, fable, onyx, nova, shimmer
   - **Model:** tts-1 or tts-1-hd
   - **Speed:** 0.25 to 4.0 (default: 1.0)

4. **Click Save Settings**

---

## Step 6: Test TTS

### Option 1: Generate Test Alert via Web UI

1. Go to `http://your-server/eas/workflow`
2. Create a test alert
3. **Enable "Include TTS voiceover"**
4. Generate the alert
5. Listen to the audio - it should include voice

### Option 2: Check Logs

```bash
# Check for TTS-related messages
tail -f /var/log/eas-station/app.log | grep -i tts

# Or wherever your logs are:
tail -f logs/eas_station.log | grep -i tts
```

**Success messages:**
```
✅ Appended Azure OpenAI TTS voiceover using voice alloy
```

**Error messages:**
```
❌ Azure OpenAI TTS credentials not configured
❌ Azure OpenAI TTS API returned status 404
❌ Azure OpenAI endpoint is incomplete
```

---

## What Changed in the Fix

### Before (Broken):
```python
# Config loaded ONCE at app startup
eas_config = load_eas_config(app.root_path)  # Startup

# Later, when generating audio:
manual_config = dict(eas_config)  # Uses stale cached config!
generator = EASAudioGenerator(manual_config, logger)
```

**Problem:** If you configured TTS after the app started, the cached `eas_config` still had `tts_provider = ''` (disabled).

### After (Fixed):
```python
# Config reloaded FRESH when generating audio
fresh_config = load_eas_config(current_app.root_path)  # Fresh from DB!
manual_config = dict(fresh_config)
generator = EASAudioGenerator(manual_config, logger)
```

**Solution:** TTS settings are read from the database every time audio is generated. Changes take effect **immediately** without restart.

---

## Verification

After applying the fix and configuring TTS:

1. **Update TTS settings** at `/admin/tts`
2. **Generate an alert** immediately (no restart needed)
3. **TTS should work** with the new settings

The stale cache issue is now fixed!

---

## Still Having Issues?

If TTS still doesn't work after:
- ✅ Pulling the fix
- ✅ Restarting the app
- ✅ Configuring TTS via web UI

Then run the diagnostic tools:

```bash
cd /opt/eas-station

# Check database settings
./check_tts_db.sh

# Test API endpoint (requires requests library)
python3 test_tts_api.py
```

Or check the detailed troubleshooting guide:
```bash
cat TTS_TROUBLESHOOTING.md
```

---

## Files Modified in This Fix

1. **webapp/eas/workflow.py** - Workflow builder now reloads config
2. **webapp/admin/audio.py** - Admin audio builder now reloads config
3. **TTS_TROUBLESHOOTING.md** - Complete troubleshooting guide
4. **test_tts_api.py** - API endpoint diagnostic tool
5. **enable_tts.py** - Interactive configuration script
6. **check_tts_db.sh** - Database settings checker

All changes are in branch: **`claude/debug-tts-api-83ZgG`**
