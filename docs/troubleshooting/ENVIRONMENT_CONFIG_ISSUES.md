# Environment Configuration Issues

This document addresses common environment configuration problems discovered during user troubleshooting.

## Issue 1: Icecast Password Mismatch (Duplicate Variables)

### Problem

After running the install script, you may have **TWO SETS** of Icecast passwords in your `.env` file:

**Set 1 - Consolidated JSON (used by the application):**
```bash
ICECAST_CONFIG={"source_password": "eas_station_source_password", "relay_password": "changeme_relay", "admin_user": "admin", "admin_password": "changeme_admin", "admin_email": "admin@example.com"}
```

**Set 2 - Individual variables (legacy, under CUSTOM VARIABLES):**
```bash
ICECAST_SOURCE_PASSWORD=wxx4CsMzkvGIbAWZDj57Ig
ICECAST_RELAY_PASSWORD=vW1sDCRTDSGVx91SfR8X2g
ICECAST_ADMIN_PASSWORD=64yJX-vhJ00vRUG5_j84DQ
```

**The Problem:** The install script generates secure random passwords (Set 2), but `ICECAST_CONFIG` still contains the default placeholder passwords from `.env.example`. **The application uses `ICECAST_CONFIG`, so your Icecast server is using the insecure default passwords!**

### Solution

Update the `ICECAST_CONFIG` JSON to use the secure passwords from the individual variables:

1. **Open your `.env` file:**
   ```bash
   sudo nano /opt/eas-station/.env
   ```

2. **Find the individual Icecast password variables** (usually near the bottom under "CUSTOM VARIABLES"):
   ```bash
   ICECAST_SOURCE_PASSWORD=wxx4CsMzkvGIbAWZDj57Ig
   ICECAST_RELAY_PASSWORD=vW1sDCRTDSGVx91SfR8X2g
   ICECAST_ADMIN_PASSWORD=64yJX-vhJ00vRUG5_j84DQ
   ICECAST_ADMIN=me@k8tek.net
   ```

3. **Update the `ICECAST_CONFIG` JSON** (near line 349) with these values:
   ```bash
   ICECAST_CONFIG={"source_password": "wxx4CsMzkvGIbAWZDj57Ig", "relay_password": "vW1sDCRTDSGVx91SfR8X2g", "admin_user": "admin", "admin_password": "64yJX-vhJ00vRUG5_j84DQ", "admin_email": "me@k8tek.net"}
   ```

4. **Remove the duplicate individual password variables** from the bottom of the file (they're no longer needed)

5. **Restart the services:**
   ```bash
   sudo systemctl restart eas-station-web.service
   sudo systemctl restart icecast2.service  # or whatever your Icecast service is called
   ```

### Verification

Check that Icecast is using the new passwords:

```bash
# Check Icecast config
sudo cat /etc/icecast2/icecast.xml | grep -A 2 authentication

# Test source connection
curl -u source:wxx4CsMzkvGIbAWZDj57Ig http://localhost:8000/admin/stats
```

---

## Issue 2: SSL_EMAIL Not Updated

### Problem

Your `.env` file shows:
```bash
SSL_EMAIL=admin@example.com     # Placeholder, not your real email!
ICECAST_ADMIN=me@k8tek.net      # Your actual email
```

**The Problem:** Let's Encrypt will send SSL certificate expiration warnings to `admin@example.com` (which doesn't exist), so you won't receive important notifications about certificate renewal.

### Solution

Update `SSL_EMAIL` to your actual email address:

1. **Edit the `.env` file:**
   ```bash
   sudo nano /opt/eas-station/.env
   ```

2. **Find and update the SSL_EMAIL line** (around line 31):
   ```bash
   # Before:
   SSL_EMAIL=admin@example.com
   
   # After:
   SSL_EMAIL=me@k8tek.net
   ```

3. **Also update the email in ICECAST_CONFIG** to match:
   ```bash
   ICECAST_CONFIG={"source_password": "...", "relay_password": "...", "admin_user": "admin", "admin_password": "...", "admin_email": "me@k8tek.net"}
   ```

4. **If you have a Let's Encrypt certificate**, update it with the new email:
   ```bash
   sudo certbot update_account --email me@k8tek.net
   ```

5. **Restart the web service:**
   ```bash
   sudo systemctl restart eas-station-web.service
   ```

### Verification

```bash
# Check that certbot is using your email
sudo certbot certificates

# Should show:
#   Certificate Name: easstation.com
#   ...
#   Expiry Date: ...
#   Certificate Path: /etc/letsencrypt/live/easstation.com/fullchain.pem
#   Private Key Path: /etc/letsencrypt/live/easstation.com/privkey.pem
```

---

## Issue 3: Environment Variable Consolidation Confusion

### Background

As of version 2.21.0, EAS Station consolidated many environment variables into JSON objects to reduce clutter. However, the install script still generates individual variables for backward compatibility.

**Variables affected:**
- `ICECAST_CONFIG` (replaces 5 individual Icecast variables)
- `LOCATION_CONFIG` (replaces 9 individual location variables)
- `MAIL_URL` (replaces 5 individual mail variables)
- `AZURE_OPENAI_CONFIG` (replaces 5 individual Azure variables)

### Current Behavior

- **Application prioritizes consolidated JSON variables** (`ICECAST_CONFIG`, etc.)
- **Individual variables are ignored** if the JSON version exists
- **Install script may generate both** for compatibility

### Recommendation

1. **Use the consolidated JSON variables** (e.g., `ICECAST_CONFIG`)
2. **Remove duplicate individual variables** to avoid confusion
3. **Update via Web UI** at `/admin/environment` for safety (validates JSON format)

### Example Cleanup

**Before (duplicates):**
```bash
ICECAST_CONFIG={"source_password": "...", ...}
ICECAST_SOURCE_PASSWORD=xyz123
ICECAST_RELAY_PASSWORD=abc456
ICECAST_ADMIN_PASSWORD=def789
```

**After (consolidated):**
```bash
ICECAST_CONFIG={"source_password": "xyz123", "relay_password": "abc456", "admin_password": "def789", ...}
# Individual variables removed
```

---

## Issue 4: Azure OpenAI TTS Configuration

### Problem

Users need to configure Azure OpenAI TTS endpoints and API keys for text-to-speech narration in EAS broadcasts. The configuration requires multiple values including endpoint URL, API key, model, voice, and speed.

### Solution

Use the `AZURE_OPENAI_CONFIG` JSON environment variable. This consolidated approach is cleaner and easier to manage than individual environment variables.

#### Method 1: Using the Web UI (Recommended)

1. **Navigate to** `/admin/environment` in the web interface
2. **Find the "Text-to-Speech" section**
3. **Click on "Azure OpenAI Configuration"**
4. **Use the Builder tab** to fill in:
   - **Endpoint URL**: Your full Azure OpenAI endpoint (e.g., `https://YOUR-RESOURCE.openai.azure.com/openai/deployments/YOUR-DEPLOYMENT/audio/speech?api-version=2025-03-01-preview`)
   - **API Key**: Your Azure OpenAI API key
   - **Model**: Usually `tts-1` or `tts-1-hd`
   - **Voice**: Choose from `alloy`, `echo`, `fable`, `onyx`, `nova`, or `shimmer`
   - **Speed**: Speech speed (0.25 to 4.0, default 1.0)
5. **Save changes**

The web UI provides a JSON builder that validates your configuration and makes it easy to edit.

#### Method 2: Editing .env Directly

Add or update the following line in your `.env` file:

```bash
AZURE_OPENAI_CONFIG={"endpoint": "https://YOUR-RESOURCE.openai.azure.com/openai/deployments/YOUR-DEPLOYMENT/audio/speech?api-version=2025-03-01-preview", "key": "YOUR_API_KEY", "model": "tts-1", "voice": "alloy", "speed": 1.05}
```

**Example with actual values:**
```bash
AZURE_OPENAI_CONFIG={"endpoint": "https://me-mho3uvw9-northcentralus.openai.azure.com/openai/deployments/tts-hd/audio/speech?api-version=2025-03-01-preview", "key": "sk-abc123xyz789...", "model": "tts-1", "voice": "alloy", "speed": 1.05}
```

### Important Notes

1. **Endpoint Format**: The endpoint must include the full path with deployment name and API version:
   ```
   https://{resource-name}.openai.azure.com/openai/deployments/{deployment-name}/audio/speech?api-version={version}
   ```

2. **Backward Compatibility**: If you have existing individual environment variables (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, etc.), they will still work. However, `AZURE_OPENAI_CONFIG` takes precedence if both are present.

3. **Provider Selection**: Don't forget to set `EAS_TTS_PROVIDER=azure_openai` to use Azure OpenAI TTS.

4. **Testing**: After configuration, test by creating a test EAS message in the web UI. Check the logs for any TTS errors.

### Troubleshooting

**"Azure OpenAI TTS credentials are missing"**
- Verify the JSON is valid (use the web UI's JSON validator)
- Ensure both `endpoint` and `key` fields are not empty
- Check for typos in field names (must be lowercase)

**"Could not extract deployment name from Azure endpoint"**
- Your endpoint must include `/deployments/YOUR-DEPLOYMENT/` in the path
- Example: `https://resource.openai.azure.com/openai/deployments/tts-hd/audio/speech?api-version=...`

**"Azure OpenAI TTS is configured but synthesis failed"**
- Verify your API key is correct
- Check that the deployment name in the endpoint matches your Azure deployment
- Ensure the API version is supported by your deployment
- Review application logs for detailed error messages

---

## General Troubleshooting

### How to Check Which Variables Are Being Used

```bash
# Check the application logs for loaded config
sudo journalctl -u eas-station-web.service -n 100 | grep -i config

# Or use the web UI environment page
# Navigate to: /admin/environment
```

### Safe Way to Update Environment Variables

**Option 1: Web UI (Recommended)**
1. Navigate to `/admin/environment`
2. Find the variable category
3. Edit and save (validates format automatically)

**Option 2: Command Line**
1. Edit the file: `sudo nano /opt/eas-station/.env`
2. Save changes
3. Restart services: `sudo systemctl restart eas-station-web.service`
4. Check logs: `sudo journalctl -u eas-station-web.service -f`

---

## Prevention

### Future Installs

When running the install script:

1. **Provide your actual email** when prompted (not admin@example.com)
2. **Review the generated `.env` file** before starting services
3. **Check for duplicate variables** and consolidate them
4. **Update via Web UI** for complex JSON configurations

### Automated Check Script

Save this as `check-env-duplicates.sh`:

```bash
#!/bin/bash
# Check for duplicate Icecast password variables

ENV_FILE="/opt/eas-station/.env"

echo "Checking for duplicate environment variables..."
echo

# Check Icecast passwords
if grep -q "ICECAST_CONFIG=" "$ENV_FILE" && grep -q "ICECAST_SOURCE_PASSWORD=" "$ENV_FILE"; then
    echo "⚠️  WARNING: Both ICECAST_CONFIG and individual ICECAST_*_PASSWORD variables found"
    echo "   Application will use ICECAST_CONFIG. Individual variables should be removed."
    echo
fi

# Check emails
SSL_EMAIL=$(grep "^SSL_EMAIL=" "$ENV_FILE" | cut -d= -f2)
ICECAST_ADMIN=$(grep "^ICECAST_ADMIN=" "$ENV_FILE" | cut -d= -f2)

if [ "$SSL_EMAIL" = "admin@example.com" ]; then
    echo "⚠️  WARNING: SSL_EMAIL is still set to placeholder value"
    echo "   Update to your actual email: sudo nano $ENV_FILE"
    echo
fi

if [ -n "$ICECAST_ADMIN" ] && [ "$SSL_EMAIL" != "$ICECAST_ADMIN" ]; then
    echo "ℹ️  INFO: SSL_EMAIL and ICECAST_ADMIN are different"
    echo "   SSL_EMAIL: $SSL_EMAIL"
    echo "   ICECAST_ADMIN: $ICECAST_ADMIN"
    echo "   Consider using the same email for consistency."
    echo
fi

echo "Check complete."
```

Make it executable and run:
```bash
chmod +x check-env-duplicates.sh
./check-env-duplicates.sh
```

---

## Related Documentation

- [Configuration Migration Guide](../guides/CONFIGURATION_MIGRATION.md)
- [Environment Variables Reference](../reference/ENVIRONMENT_VARIABLES.md)
- [HTTPS Setup Guide](../guides/HTTPS_SETUP.md)
