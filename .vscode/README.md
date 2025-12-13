# VSCode Configuration for EAS Station

This directory contains VSCode workspace configuration for remote development on EAS Station.

## 📁 Files

| File | Purpose | Committed to Git? |
|------|---------|-------------------|
| `settings.json` | Workspace settings (Python paths, formatting, DB config) | ✅ Yes |
| `launch.json` | Debug configurations for services | ✅ Yes |
| `tasks.json` | Common development tasks (restart services, view logs) | ✅ Yes |
| `extensions.json` | Recommended VSCode extensions | ✅ Yes |
| `VSCODE_SETUP.md` | Complete setup guide | ✅ Yes |
| `settings.local.json` | Local overrides (user-specific) | ❌ No (in .gitignore) |

## 🚀 Quick Start

**See [VSCODE_SETUP.md](./VSCODE_SETUP.md) for complete instructions.**

**TL;DR**:
1. Install VSCode + Remote-SSH extension
2. Connect to `easstation-dev.local` as user `eas-station`
3. Open folder: `/opt/eas-station`
4. Select Python interpreter: `/opt/eas-station/venv/bin/python`
5. Done! Start coding.

## 🔒 Security

**These files DO NOT contain secrets:**
- All configuration uses relative paths or asks for passwords
- Database password is read from `.env` (which is in `.gitignore`)
- SSH credentials are in your `~/.ssh/config` (not in repo)
- SQLTools asks for password each time (doesn't save it)

**User-specific files (not committed):**
- `.vscode/settings.local.json` - for your personal overrides
- `.vscode/sqltools.settings.json` - auto-generated (in .gitignore)

## 🛠️ Database Access

PostgreSQL connection is configured in `settings.json` with:
- Host: `localhost` (when connected via Remote-SSH)
- Database: `alerts`
- Username: `eas_station`
- Password: **Asks each time** (reads from `.env` or prompts)

**Get password**:
```bash
grep DATABASE_URL /opt/eas-station/.env
```

## 📝 Customization

Create `.vscode/settings.local.json` for personal settings that won't be committed:

```json
{
  "editor.fontSize": 14,
  "terminal.integrated.fontSize": 12,
  "workbench.colorTheme": "Dark+ (default dark)"
}
```

This file is in `.gitignore` so your preferences stay private.

## 🆘 Help

- **Setup issues?** See [VSCODE_SETUP.md](./VSCODE_SETUP.md) → Troubleshooting
- **Can't connect?** Check SSH config in `~/.ssh/config`
- **Python not found?** Select interpreter: `/opt/eas-station/venv/bin/python`
- **Database issues?** Run task: `Database: Show Connection Info`

## 🔗 Links

- [VSCode Remote Development](https://code.visualstudio.com/docs/remote/ssh)
- [Python in VSCode](https://code.visualstudio.com/docs/languages/python)
- [SQLTools Extension](https://marketplace.visualstudio.com/items?itemName=mtxr.sqltools)
