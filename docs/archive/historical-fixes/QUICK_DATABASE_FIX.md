# Quick Fix Guide - Database Authentication Issues

## Your Situation

You have the **correct DATABASE_URL** format in your `.env` file:
```
DATABASE_URL=postgresql+psycopg2://eas_station:PASSWORD@127.0.0.1:5432/alerts
```

But you're seeing errors like:
```
FATAL: password authentication failed for user "eas-station"
connection to server at "localhost" (::1), port 5432 failed
```

**The Real Problem:** The password in your `.env` file doesn't match the password in PostgreSQL!

This is an `OperationalError` from psycopg2, which means PostgreSQL **received** your connection but **rejected** the password. It's not a network issue - it's authentication.

## Most Likely Cause

**The password in your `.env` file doesn't match the password in PostgreSQL!**

PostgreSQL is successfully receiving your connection (both IPv4 and IPv6 work), but it's rejecting the password. This is a `psycopg2.OperationalError` which means the database operation (authentication) failed.

**Why this happens:**
- The `.env` file has one password
- PostgreSQL database has a different password for user "eas-station"
- When services try to connect, PostgreSQL says "wrong password"

---

## SOLUTION 1: Sync the Password (CRITICAL FIRST STEP)

```bash
sudo /opt/eas-station/scripts/database/fix_database_user.sh
```

**This will:**
✅ Extract password from your `.env` file  
✅ Update PostgreSQL user "eas-station" with that password  
✅ Fix permissions  
✅ No data loss - completely safe  

**Then restart services:**
```bash
sudo systemctl restart eas-station.target
```

---

## SOLUTION 2: Run update.sh (Applies code fixes too)

```bash
cd /opt/eas-station
sudo ./update.sh
```

**Note:** update.sh will pull the latest code but **won't** sync your password. You still need to run the fix script above after update.sh completes.

---

## If Errors Still Persist After Running Fix Script

If the password sync didn't help, check:

1. **PostgreSQL is running:**
   ```bash
   sudo systemctl status postgresql
   ```

2. **pg_hba.conf is configured properly:**
   ```bash
   sudo cat /etc/postgresql/*/main/pg_hba.conf | grep eas-station
   ```
   Should show authentication rules for both IPv4 and IPv6

3. **Reload PostgreSQL if pg_hba.conf was changed:**
   ```bash
   sudo systemctl reload postgresql
   ```

---

## What We Fixed

1. **Database password sync script** - Extracts password from .env and updates PostgreSQL
2. **Poller service environment loading** - Made `.env` file required (was optional)
3. **IPv4 vs localhost** - Changed all defaults to use `127.0.0.1` instead of `localhost`
4. **Created fix script** - Cleans up incorrect database users and syncs passwords

**ACTION REQUIRED:**
```bash
sudo /opt/eas-station/scripts/database/fix_database_user.sh
sudo systemctl restart eas-station.target
```

---

## Questions?

See full documentation:
- `/opt/eas-station/docs/troubleshooting/PASSWORD_MISMATCH.md` - Password authentication issues
- `/opt/eas-station/docs/troubleshooting/DATABASE_AUTH_FIX.md` - Complete troubleshooting  
- `/opt/eas-station/scripts/database/README_fix_database_user.md` - Fix script documentation

---

## Technical Note: IPv6 vs IPv4

The error shows `(::1)` which is IPv6, but this is **NOT the root cause**.

- Both IPv4 (127.0.0.1) and IPv6 (::1) work for PostgreSQL connections
- The connection succeeded - PostgreSQL was reached
- The password was rejected **after** connection was established
- **Using `127.0.0.1` instead of `localhost` is recommended for consistency**

But the real issue is the **password mismatch**, not IPv6!
