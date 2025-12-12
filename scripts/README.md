# EAS Station Utility Scripts

## 🔧 Fix for Existing Deployments

### Missing .git Directory? Run This:

```bash
sudo bash /opt/eas-station/scripts/fix_git.sh
```

**Fixes:**
- ✅ Version showing "unknown"
- ✅ update.sh not working properly  
- ✅ Files not updating
- ✅ Missing git metadata

---

## Configuration Tools

### `merge_env.py` - Add Missing .env Variables
```bash
python3 scripts/merge_env.py --backup
```
Adds new variables from .env.example to your .env

### `migrate_env.py` - Move Systemd Vars to .env  
```bash
sudo python3 scripts/migrate_env.py --backup
```
Fixes settings that don't work when updated via web UI

---

## All Scripts

| Script | Purpose | Command |
|--------|---------|---------|
| `fix_git.sh` | Restore .git directory | `sudo bash scripts/fix_git.sh` |
| `merge_env.py` | Add new .env variables | `python3 scripts/merge_env.py --backup` |
| `migrate_env.py` | Move systemd→.env | `sudo python3 scripts/migrate_env.py --backup` |

---

**Full documentation:** See [docs/guides/CONFIGURATION_MIGRATION.md](../docs/guides/CONFIGURATION_MIGRATION.md)
