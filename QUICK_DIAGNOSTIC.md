# Quick Diagnostic - Run This On Your Server

## You said TTS is enabled and configured but not working. Let's verify what's actually in the database.

### Step 1: Find your database

```bash
cd /opt/eas-station  # Or wherever your app is installed

# Check your .env for database location
grep DATABASE_URL .env
```

### Step 2: Check TTS settings directly

#### If using PostgreSQL:
```bash
psql "$DATABASE_URL" -c "SELECT id, enabled, provider, azure_openai_endpoint, LENGTH(azure_openai_key) as key_length FROM tts_settings WHERE id=1;"
```

#### If using SQLite:
```bash
# Find the database
find /opt /var/lib -name "app.db" 2>/dev/null | head -1

# Or it might be at:
DB="/opt/eas-station/instance/app.db"

# Check settings
sqlite3 "$DB" "SELECT id, enabled, provider, azure_openai_endpoint, LENGTH(azure_openai_key) as key_length FROM tts_settings WHERE id=1;"
```

### Step 3: Check what you get

**Expected output if properly configured:**
```
id | enabled | provider      | azure_openai_endpoint                                    | key_length
---+---------+---------------+----------------------------------------------------------+-----------
 1 | 1       | azure_openai  | https://xxx.openai.azure.com/openai/deployments/xxx/...  | 32
```

**If you see:**
- `enabled | 0` → **TTS is disabled!**
- `provider |` (empty) → **Provider not set!**
- `key_length | ` (NULL) → **API key not saved!**

### Step 4: If database looks correct, trace the config flow

```bash
cd /opt/eas-station
python3 trace_config_flow.py
```

This will show you EXACTLY what values are:
1. In the database
2. Loaded by `load_eas_config()`
3. Received by TTSEngine

---

## Common Issues

### Issue A: Settings not saved to database

**Symptom:** You filled out the form at `/admin/tts` but database still shows empty/disabled

**Causes:**
1. JavaScript error preventing form submission
2. Database write error (check logs)
3. Wrong database being checked (dev vs prod)

**Fix:**
- Check browser console for errors when you click Save
- Check app logs for database errors
- Use `enable_tts.py` script to configure directly

### Issue B: Boolean stored as string

**Symptom:** Database shows `enabled='1'` (string) instead of `enabled=1` (boolean)

**Cause:** Some database drivers store booleans as strings

**Fix:** This should still work, but verify with trace script

### Issue C: Provider case mismatch

**Symptom:** Database has `provider='Azure_OpenAI'` but code expects `'azure_openai'`

**Cause:** Form didn't enforce lowercase

**Fix:** Code does `.strip().lower()` so this should work, but verify

---

## What to report back

After running the diagnostic, tell me:

1. **Database values:**
   ```
   enabled = ?
   provider = ?
   endpoint = ?
   key_length = ?
   ```

2. **trace_config_flow.py output:**
   - What does STEP 2 show for `config['tts_provider']`?
   - What does STEP 3 show for `tts.provider`?
   - What issues does STEP 4 report?

3. **When you generate a test alert:**
   - Any errors in browser console?
   - Any TTS-related lines in app logs?
   - Does the audio file get created?
   - Does it have voice in it?

This will tell us EXACTLY where the config is getting lost!
