# Remote Debugging Guide for Raspberry Pi

**Stop pushing broken code to GitHub!** This guide shows you how to develop and debug the `eas-station` project directly on your Raspberry Pi using PyCharm Professional or VS Code, eliminating the need for constant pull requests during development.

> **💡 Don't have PyCharm Professional?** Both VS Code (free) and PyCharm Professional (free for open source) work great for this project. See [Getting the Right IDE](#getting-the-right-ide) below.

---

## Table of Contents

- [Why Use This Approach?](#why-use-this-approach)
- [Getting the Right IDE](#getting-the-right-ide)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Database Configuration](#database-configuration)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Why Use This Approach?

**The Problem**: Making a PR every time you want to test code changes is:
- ⚠️ Slow and frustrating
- ⚠️ Clutters your Git history with broken code
- ⚠️ Makes debugging nearly impossible
- ⚠️ Wastes time with container rebuilds

**The Solution**: Develop and debug live on the Raspberry Pi with:
- ✅ **Real hardware testing** - Test on actual Pi hardware, not simulations
- ✅ **Instant feedback** - See changes immediately without pushing to GitHub
- ✅ **Proper debugging** - Set breakpoints, inspect variables, step through code
- ✅ **Clean Git history** - Only commit working, tested code

### How It Works (Windows → Pi)

```
Your Windows Computer                    Raspberry Pi
┌─────────────────────┐                 ┌──────────────────────┐
│  ┌───────────────┐  │   SSH + Code   │  ┌────────────────┐  │
│  │ Edit Code     │──┼────────────────>│  │ Python App     │  │
│  │ Set Breakpoint│  │                 │  │ (your code)    │  │
│  │ View Variables│  │                 │  └────────┬───────┘  │
│  └───────────────┘  │                 │           │           │
│                     │                 │           ▼           │
│  ┌───────────────┐  │   Port 5432    │  ┌────────────────┐  │
│  │ Database Tools│──┼────────────────>│  │ PostgreSQL DB  │  │
│  │ (pgAdmin, etc)│  │                 │  │ (alerts_dev)   │  │
│  └───────────────┘  │                 │  └────────────────┘  │
│                     │                 │                      │
│  ┌───────────────┐  │   Port 5050    │  ┌────────────────┐  │
│  │ Web Browser   │──┼────────────────>│  │ pgAdmin Web    │  │
│  └───────────────┘  │                 │  └────────────────┘  │
└─────────────────────┘                 └──────────────────────┘
```

**Key Insight**: Your code runs ON the Pi (via SSH), but you edit and debug from Windows!

---

## Getting the Right IDE

### Option 1: VS Code (Recommended - Free)

**Best for**: Getting started immediately without waiting for license approval.

**Pros**:
- Free forever, no license needed
- Fast and lightweight
- Excellent remote SSH support
- Great Python support with extensions
- Works on Windows, Mac, Linux

**Get it**: [https://code.visualstudio.com/](https://code.visualstudio.com/)

### Option 2: PyCharm Professional (Free for Open Source)

**Best for**: Python-focused development with advanced refactoring tools.

**Pros**:
- Best-in-class Python IDE
- Powerful debugging and refactoring
- Database tools built-in
- Free with open source license

**Get it free**:

Since `eas-station` is an open source project under AGPL-3.0, you can get a free PyCharm Professional license:

1. Go to: [JetBrains Open Source License Application](https://www.jetbrains.com/community/opensource/#support)
2. Click **Apply Now**
3. Fill out the form:
   - **Project Name**: EAS Station
   - **Project URL**: `https://github.com/KR8MER/eas-station`
   - **License Type**: AGPL-3.0
   - **Your Role**: Contributor or Maintainer
4. JetBrains typically responds within a few days

While waiting for approval, use the [30-day free trial](https://www.jetbrains.com/pycharm/download/) or start with VS Code.

### Don't Use: PyCharm Community Edition

❌ PyCharm Community lacks remote SSH development and remote debugging features required for this workflow.

---

## Prerequisites

### Required

- **Raspberry Pi** with:
  - SSH enabled
  - Git installed
  - The `eas-station` repository cloned
- **Local development machine** running Windows, macOS, or Linux
- **Network connection** between your computer and the Raspberry Pi
- **IDE**: PyCharm Professional or VS Code (see above)

### Skill Level

This guide assumes you know:
- Basic Python programming
- How to use SSH
- Basic Git commands

---

## Quick Start

### Step 1: Enable SSH on Raspberry Pi

Connect to your Pi (keyboard + monitor, or existing SSH):

```bash
# Enable and start SSH
sudo systemctl enable ssh
sudo systemctl start ssh

# Find your Pi's IP address (write this down!)
hostname -I
```

**Write down the IP address** (example: `192.168.1.100`).

---

### Step 3: Set Up Development Environment on Pi

```bash
# Navigate to your eas-station folder
cd ~/eas-station

# If you don't have it yet:
# git clone https://github.com/KR8MER/eas-station.git
# cd eas-station

# Copy the example environment file if needed
if [ ! -f .env ]; then
    cp .env.example .env
fi

# Start everything with the embedded database and pgAdmin

# Wait for containers to start
sleep 10

# Check status
```

If you see services running (including pgAdmin), the Pi setup is complete!

---

### Step 4: Set Up Your IDE

#### Option A: VS Code

1. **Install extensions**:
   - Open VS Code
   - Install **Remote - SSH** extension (by Microsoft)
   - Install **Python** extension (by Microsoft)

2. **Connect to Pi**:
   - Press `F1` (or `Ctrl+Shift+P` / `Cmd+Shift+P`)
   - Type: `Remote-SSH: Connect to Host`
   - Enter: `pi@YOUR.PI.IP.ADDRESS`
   - Enter your Pi password
   - Choose **File** → **Open Folder** → `/home/pi/eas-station`

3. **Set up debugging**:
   - Click **Run and Debug** icon (left sidebar)
   - Click **create a launch.json file** → **Python**
   - Replace contents with:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Attach to EAS Station",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/app"
                }
            ],
            "justMyCode": false
        }
    ]
}
```

4. **Test debugging**:
   - Open any Python file (like `app.py`)
   - Click in the left margin to set a breakpoint (red dot appears)
   - Press `F5` to start debugging
   - If it connects, you're done! 🎉

#### Option B: PyCharm Professional

1. **Set up SSH Interpreter**:
   - Go to: **File** → **Settings** → **Project** → **Python Interpreter**
   - Click **gear icon** ⚙️ → **Add...** → **On SSH**
   - **New server configuration**:
     - Host: Your Pi's IP address
     - Port: `22`
     - Username: `pi`
   - Click **Next**, enter password
   - Set interpreter: `/usr/bin/python3`
   - Set sync folders:
     - Local: Your project folder
     - Remote: `/home/pi/eas-station`
   - Click **Finish** and wait for sync

2. **Create Debug Configuration**:
   - Go to: **Run** → **Edit Configurations...**
   - Click **+** → **Python Debug Server**
   - Name: `EAS Station Debug`
   - Host: Your Pi's IP
   - Port: `5678`
   - Click **OK**

3. **Test debugging**:
   - Set a breakpoint (click in left margin)
   - Click debug icon (green bug) or press `Shift+F9`
   - You're done! 🎉

---

## Database Configuration

The development configuration includes an embedded PostgreSQL database for isolated development.

### Understanding Database Connection

**IMPORTANT**: The database hostname depends on WHERE your Python code is running:

| Running Mode | Where Code Runs | POSTGRES_HOST Value | Why |
|--------------|-----------------|-------------------|-----|
| **PyCharm SSH Remote Interpreter** | On Pi via SSH | `localhost` | Port exposed to Pi's localhost |
| **PyCharm Local Debugging** | On your Windows/Mac | `192.168.1.100` | Pi's actual IP address |

### Two Ways to Use PyCharm

#### Method 1: SSH Remote Interpreter (Recommended)

**How it works**:
- PyCharm on your Windows machine
- Python code runs **on the Pi** via SSH
- PyCharm just shows you the output

**Database connection** in `.env` on the Pi:
```bash
POSTGRES_HOST=localhost  # Because code runs ON the Pi
POSTGRES_PORT=5432
```

This is what the Quick Start section configures by default.

#### Method 2: Local Debugging from Windows

**How it works**:
- PyCharm on your Windows machine
- Python code runs **on Windows**
- Connects to database on Pi over network

**Database connection** in `.env` on Windows:
```bash
POSTGRES_HOST=192.168.1.100  # Your Pi's actual IP address
POSTGRES_PORT=5432
```

**Note**: You'll also need to install Python dependencies on Windows and ensure the Pi's firewall allows port 5432.

### Default Configuration (Embedded Database)

The embedded database starts automatically with `--profile embedded-db`:

- Database: `alerts_dev`
- Username: `postgres`
- Password: `devpassword`
- Port: `5432` (exposed to Pi)

**For most users** debugging via SSH on the Pi, edit your `.env`:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=alerts_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=devpassword
```

### Using an External Database

If you prefer an external PostgreSQL instance:

1. Edit `.env`:
```bash
POSTGRES_HOST=192.168.1.X  # Your database server IP
POSTGRES_PORT=5432
POSTGRES_DB=alerts_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
```

2. Create the database:
```sql
CREATE DATABASE alerts_dev;
CREATE EXTENSION IF NOT EXISTS postgis;
```

3. Restart containers:
### Verifying Database Connection

```bash
# Check app logs for connection status

# You should see: "Connected to PostgreSQL" or similar
```

### Accessing the Database from Windows

The database runs on the Pi, but you can access it from your Windows machine in several ways:

#### Option 1: pgAdmin Web Interface (Easiest)

pgAdmin runs on the Pi but you access it from your Windows web browser:

1. **Open your Windows web browser**
2. Go to: `http://YOUR_PI_IP:5050` (e.g., `http://192.168.1.100:5050`)
3. Login:
   - Email: `admin@localhost`
   - Password: `admin`
4. **Add database server** (first time only):
   - Right-click **Servers** → **Register** → **Server**
   - **General** tab:
     - Name: `EAS Station Dev`
   - **Connection** tab:
     - **Port**: `5432`
     - **Database**: `alerts_dev`
     - **Username**: `postgres`
     - **Password**: `devpassword`
   - Click **Save**

You can now browse tables, run queries, and manage the database from your Windows browser!

#### Option 2: Windows Desktop Database Tools (PyCharm DataGrip, DBeaver, TablePlus, etc.)

Connect from Windows desktop tools directly to the Pi:

**Connection settings**:
- **Host**: Your Pi's IP (e.g., `192.168.1.100`)
- **Port**: `5432`
- **Database**: `alerts_dev`
- **Username**: `postgres`
- **Password**: `devpassword`

**PyCharm Professional includes DataGrip database tools**:
1. In PyCharm, open **Database** tool window (View → Tool Windows → Database)
2. Click **+** → **Data Source** → **PostgreSQL**
3. Enter the connection settings above
4. Click **Test Connection** → **OK**

#### Option 3: psql from the Pi

If you SSH into the Pi:
```bash
# From SSH session on the Pi
psql -h localhost -U postgres -d alerts_dev
```

### Ensuring Database Access from Windows

The database port (5432) is automatically exposed when you start with `--profile embedded-db`. Verify the Pi's firewall allows it:

```bash
# On the Pi, check if port 5432 is listening
sudo netstat -tlnp | grep 5432

# If you have ufw firewall enabled, allow the port:
sudo ufw allow 5432/tcp
sudo ufw status
```

**Test connectivity from Windows**:
```powershell
# In Windows PowerShell, test if you can reach the database port
Test-NetConnection -ComputerName 192.168.1.100 -Port 5432
```

---

## Development Workflow

### Daily Workflow

1. **Start your day**:
```bash
ssh pi@192.168.1.100
cd ~/eas-station

# If not running, start them:
```

2. **Edit code**:
   - Edit files in your IDE (VS Code or PyCharm)
   - Changes are synced to the Pi automatically

3. **Debug**:
   - Set breakpoints in your IDE
   - Start debugger (`F5` in VS Code, or debug button in PyCharm)
   - Inspect variables, step through code

4. **Test on hardware**:
   - Your code runs on actual Raspberry Pi hardware
   - Test with real GPIO, audio, SDR devices

5. **Commit only working code**:
```bash
git status
git diff
git add <files>
git commit -m "Fix: Clear description of changes"
git push origin <branch-name>
```

### Understanding the Development Configuration

**Key Features**:
- Debug port 5678 exposed for remote debugging
- Live code reloading (volumes mounted)
- Flask debug mode and verbose logging
- Hardware disabled (prevents accidental GPIO/LED activation)
- Test audio files instead of real radio input
- Separate development database

**Safety Features**:
- EAS broadcast relay disabled
- GPIO pins disabled
- LED signs disabled
- Test data instead of live data

---

## Troubleshooting

### Problem: "Connection Refused" When Debugging

**Solution**:
```bash
# Check container status

# Check logs

# Restart app container
```

---

### Problem: PyCharm/VS Code Can't Connect via SSH

**Solution**:
```bash
# On the Pi, check SSH status
sudo systemctl status ssh

# If not running, start it
sudo systemctl start ssh

# Test from your computer
ssh pi@192.168.1.100
```

---

### Problem: "Can't connect to database"

**Cause**: Wrong hostname in `.env` or network/firewall issue.

**Solution**:

1. **Check your `.env` file has the correct `POSTGRES_HOST`**:

```bash
# For PyCharm SSH Remote Interpreter (code runs ON Pi):
POSTGRES_HOST=localhost

POSTGRES_HOST=alerts-db

# For local debugging on Windows (code runs ON Windows):
POSTGRES_HOST=192.168.1.100  # Your Pi's actual IP
```

2. **For Windows desktop tools or local debugging**, verify network connectivity:

```powershell
# Test from Windows PowerShell:
Test-NetConnection -ComputerName 192.168.1.100 -Port 5432
```

If this fails, check the Pi's firewall:
```bash
# On the Pi:
sudo ufw allow 5432/tcp
sudo ufw status

# Verify the port is exposed:
sudo netstat -tlnp | grep 5432
```

3. **Restart containers** after changing `.env`:
---

### Problem: "Can't connect to database from Windows tools"

**Cause**: Firewall blocking port 5432 or database not exposed.

**Solution**:

```yaml
alerts-db:
  ports:
    - "5432:5432"  # This line must be present
```

2. **Check Pi's firewall**:
```bash
# On the Pi:
sudo ufw allow 5432/tcp

# If ufw is not active:
sudo ufw status
```

3. **Test from Windows**:
```powershell
# Windows PowerShell:
Test-NetConnection -ComputerName 192.168.1.100 -Port 5432

# Should show: TcpTestSucceeded : True
```

```bash
# On the Pi:
sudo netstat -tlnp | grep 5432

# Should show: 0.0.0.0:5432 (not 127.0.0.1:5432)
```

---

### Problem: Code Changes Not Appearing

**Solution**:

1. Check IDE sync status (bottom of window)
2. Manually trigger sync: **Tools** → **Deployment** → **Sync with Deployed to...**
3. Restart containers:
---

### Problem: "Permission Denied" on /dev/snd or GPIO

**Solution**:
```bash
# Add your user to necessary groups

# Log out and back in
exit
# (SSH back in)

# Verify group membership
groups
```

---

## Best Practices

### DO ✅

- **Test locally first**: Always debug on the Pi before pushing to GitHub
- **Use breakpoints**: Don't just add print statements - use real debugging
- **Commit often**: When something works, commit it immediately
- **Write descriptive commits**: "Fix: Describe what you fixed" not "fixed stuff"

### DON'T ❌

- **Don't push untested code**: Test it on the Pi first!
- **Don't commit broken code**: Fix it first, then commit
- **Don't commit debug configurations**: Keep those in override files
- **Don't commit secrets**: Check for passwords/API keys before committing
- **Don't use `git add .`**: Add specific files only

---

## Debugging Specific Services

### Audio Service

```bash
# View logs in real-time

# Restart just the audio service
```

### Poller Service

```bash
# Check poller logs

# Run poller manually with debug output
```

---

## Keeping Your Git History Clean

### Use .gitignore

These files should NOT be committed (already in `.gitignore`):

```gitignore
*.log
__pycache__/
.env
dev_data/
```

### Check Before Committing

```bash
# Always check what you're about to commit
git status
git diff

# Only add specific files
git add app.py app_core/alerts.py

# NOT this (adds everything):
# git add .
```

### Write Good Commit Messages

❌ Bad:
```
git commit -m "fixed stuff"
git commit -m "update"
```

✅ Good:
```
git commit -m "Fix: Audio service crash when USB device disconnects"
git commit -m "Add: Retry logic for failed IPAWS poll requests"
git commit -m "Improve: Alert deduplication performance"
```

---

## Quick Reference

### Daily Commands

```bash
# Start debugging session
ssh pi@192.168.1.100
cd ~/eas-station

# Check status

# Stop debugging session
```

### IDE Shortcuts

**VS Code**:
- **Set Breakpoint**: Click left margin or `F9`
- **Start Debugging**: `F5`
- **Step Over**: `F10`
- **Step Into**: `F11`
- **Continue**: `F5`

**PyCharm**:
- **Set Breakpoint**: Click left margin or `Ctrl+F8` / `Cmd+F8`
- **Start Debugging**: `Shift+F9`
- **Step Over**: `F8`
- **Step Into**: `F7`
- **Resume**: `F9`

---

## Summary

You now have a complete development environment where you can:

1. ✅ Edit code in PyCharm/VS Code on your Windows machine
2. ✅ Run and debug on real Raspberry Pi hardware
3. ✅ Access the database from Windows (pgAdmin web, desktop tools, PyCharm DataGrip)
4. ✅ Set breakpoints and inspect variables
5. ✅ Test with actual GPIO, audio, and SDR hardware
6. ✅ Commit only working, tested code to GitHub

**Key Points**:
- **PyCharm on Windows** → Code runs on Pi via SSH → Database uses `localhost`
- **Windows database tools** → Connect to Pi's IP (e.g., `192.168.1.100:5432`)
- **pgAdmin web** → Access from Windows browser at `http://PI_IP:5050`

**No more broken PRs. No more guess-and-check debugging. No more wasted time.**

---

## Getting Help

- **PyCharm Documentation**: [Remote Debugging with PyCharm](https://www.jetbrains.com/help/pycharm/remote-debugging-with-product.html)
- **VS Code Remote SSH**: [VS Code Remote Development](https://code.visualstudio.com/docs/remote/ssh)
- **EAS Station Issues**: [GitHub Issues](https://github.com/KR8MER/eas-station/issues)

---

**Last Updated**: 2025-12-03
**Maintained By**: EAS Station Development Team
