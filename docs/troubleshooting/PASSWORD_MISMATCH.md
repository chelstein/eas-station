# Database Password Authentication Failure - Root Cause Analysis

## The Real Problem

You're seeing:
```
OperationalError: connection to server at "localhost" (::1), port 5432 failed: 
FATAL: password authentication failed for user "eas-station"
```

**What this actually means:**
- ✅ PostgreSQL IS running and reachable (both IPv4 and IPv6 work)
- ✅ The connection attempt succeeded (reached PostgreSQL)
- ❌ PostgreSQL **rejected the password** you provided
- This is NOT a network/IPv6 issue - it's an **authentication issue**

## Root Cause: Password Mismatch

The password in your `/opt/eas-station/.env` file doesn't match the password stored in PostgreSQL for user "eas-station".

**Why this happens:**
1. The `.env` file was created/updated with a new password
2. PostgreSQL still has the OLD password for the user
3. Services try to connect with NEW password → PostgreSQL rejects it

## Solution: Synchronize the Password

### Option 1: Run the Fix Script (RECOMMENDED)

```bash
sudo /opt/eas-station/scripts/database/fix_database_user.sh
```

This script will:
1. Read the password from your `.env` file
2. Update PostgreSQL user "eas-station" with that password
3. Fix any permission issues
4. **No data loss** - safe to run

### Option 2: Manual Password Reset

If you want to do it manually:

```bash
# Extract password from .env file
DB_PASS=$(grep "^DATABASE_URL=" /opt/eas-station/.env | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')

# Update PostgreSQL user password
sudo -u postgres psql <<EOF
ALTER USER "eas-station" WITH PASSWORD '\$\$${DB_PASS}\$\$';
EOF

# Restart services
sudo systemctl restart eas-station.target
```

### Option 3: Test Connection First

Verify the issue is indeed password mismatch:

```bash
# Extract the password
DB_PASS=$(grep "^DATABASE_URL=" /opt/eas-station/.env | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')

# Try to connect (will prompt for password)
psql -h 127.0.0.1 -U eas-station -d alerts -c "SELECT version();"

# When prompted, paste the password from:
echo "$DB_PASS"
```

If the manual connection fails with the same password error, you've confirmed the mismatch.

## About IPv6 vs IPv4

The error shows `(::1)` which is IPv6, but this is **NOT the problem**. 

- Both IPv4 (127.0.0.1) and IPv6 (::1) work fine
- The connection succeeded - PostgreSQL was reached
- The password was rejected **after** the connection was established
- Using `127.0.0.1` instead of `localhost` is still recommended for consistency, but won't fix this specific error

## Why the OperationalError Occurs

`OperationalError` from psycopg2 means:
- "The database operation failed"
- In this case: authentication failed
- It's PostgreSQL saying "no, wrong password"
- Not a network issue, not a configuration issue - it's authentication

## Next Steps

1. **Run the fix script:**
   ```bash
   sudo /opt/eas-station/scripts/database/fix_database_user.sh
   ```

2. **Restart services:**
   ```bash
   sudo systemctl restart eas-station.target
   ```

3. **Check logs:**
   ```bash
   sudo journalctl -u eas-station-poller.service -n 20
   ```

4. **Verify connection works:**
   ```bash
   sudo journalctl -u eas-station-web.service -n 20 | grep -i database
   ```

## If Fix Script Doesn't Work

Check these:

1. **Verify .env file exists and is readable:**
   ```bash
   ls -la /opt/eas-station/.env
   sudo cat /opt/eas-station/.env | grep DATABASE_URL
   ```

2. **Check PostgreSQL user exists:**
   ```bash
   sudo -u postgres psql -c "\du" | grep eas-station
   ```

3. **Check pg_hba.conf allows the connection:**
   ```bash
   sudo cat /etc/postgresql/*/main/pg_hba.conf | grep eas-station
   ```
   Should show:
   ```
   host    alerts    "eas-station"    127.0.0.1/32    scram-sha-256
   host    alerts    "eas-station"    ::1/128         scram-sha-256
   ```

4. **Reload PostgreSQL if pg_hba.conf was changed:**
   ```bash
   sudo systemctl reload postgresql
   ```
