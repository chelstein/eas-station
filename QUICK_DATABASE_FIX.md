# Quick Fix Guide - Database Authentication Issues

## Your Situation

You have the **correct DATABASE_URL** in your `.env` file:
```
DATABASE_URL=postgresql+psycopg2://eas-station:WtKI9j3bi9tUVkHpxelnsLRMufQL8973x4DLJwy8d0g@localhost:5432/alerts
```

But you're seeing errors like:
```
FATAL: password authentication failed for user "eas_station"
```

## Most Likely Cause

**Your services just need to be restarted** to pick up the correct DATABASE_URL from the `.env` file!

Services were probably running with old/missing configuration before the `.env` file was properly set up.

---

## SOLUTION: Run update.sh (Simplest Fix)

```bash
cd /opt/eas-station
sudo ./update.sh
```

**This will:**
✅ Stop all services  
✅ Pull the latest code fixes  
✅ Reload systemd configuration  
✅ Restart all services with correct environment  
✅ Run database migrations  
✅ Everything works!

---

## Alternative: Quick Restart (If you don't want to update)

```bash
sudo systemctl daemon-reload
sudo systemctl restart eas-station.target
```

---

## If Errors Still Persist

There might be an incorrect database user "eas_station" (with underscore) in PostgreSQL.

**Run the fix script:**
```bash
sudo /opt/eas-station/scripts/database/fix_database_user.sh
```

This will:
- Detect and remove incorrect users
- Keep your data safe (reassigns ownership first)
- Set up the correct "eas-station" user

---

## What We Fixed

1. **Poller service environment loading** - Made `.env` file required (was optional)
2. **Created fix script** - Cleans up incorrect database users
3. **Created restart script** - Easy way to restart services with error detection

All these fixes are in the code now - running `update.sh` will apply them automatically!

---

## Questions?

See full documentation:
- `/opt/eas-station/docs/troubleshooting/DATABASE_AUTH_FIX.md`
- `/opt/eas-station/scripts/database/README_fix_database_user.md`
