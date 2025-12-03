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
  - Docker and Docker Compose installed
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
- Basic Docker concepts

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

### Step 2: Install Docker (if not installed)

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to the docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get update
sudo apt-get install -y libffi-dev libssl-dev python3-dev python3-pip
sudo pip3 install docker-compose

# Log out and back in for group changes to take effect
exit
```

After logging back in, verify:

```bash
docker --version
docker-compose --version
```

---

### Step 3: Set Up Development Environment on Pi

```bash
# Navigate to your eas-station folder
cd ~/eas-station

# If you don't have it yet:
# git clone https://github.com/KR8MER/eas-station.git
# cd eas-station

# Copy the development Docker configuration
cp examples/docker-compose/docker-compose.development.yml docker-compose.override.yml

# Copy the example environment file if needed
if [ ! -f .env ]; then
    cp .env.example .env
fi

# Start everything with the embedded database and pgAdmin
docker-compose --profile embedded-db --profile development up -d

# Wait for containers to start
sleep 10

# Check status
docker-compose ps
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

The database hostname in your `.env` file depends on **where your Python code is running**:

| Running Mode | POSTGRES_HOST Value | Why |
|--------------|-------------------|-----|
| **In Docker container** (normal) | `alerts-db` | Docker service name |
| **PyCharm SSH debugging** (on Pi) | `localhost` | Port exposed to Pi's localhost |
| **Local debugging** (on Windows/Mac) | `192.168.1.100` | Pi's actual IP address |

### Default Configuration (Embedded Database)

The embedded database starts automatically with `--profile embedded-db`:

**Default settings** (in `docker-compose.development.yml`):
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
```bash
docker-compose restart app
```

### Verifying Database Connection

```bash
# Check app logs for connection status
docker-compose logs app | grep -i "database\|postgres"

# You should see: "Connected to PostgreSQL" or similar
```

### Database Tools

#### Option 1: pgAdmin (Included by Default)

pgAdmin is automatically started with the development environment and provides a web-based database management interface.

**Access pgAdmin**:
1. Open your web browser
2. Go to: `http://YOUR_PI_IP:5050` (e.g., `http://192.168.1.100:5050`)
3. Login:
   - Email: `admin@localhost`
   - Password: `admin`
4. Add database server (first time only):
   - Right-click **Servers** → **Register** → **Server**
   - **General** tab:
     - Name: `EAS Station Dev`
   - **Connection** tab:
     - Host: `alerts-db`
     - Port: `5432`
     - Database: `alerts_dev`
     - Username: `postgres`
     - Password: `devpassword`
   - Click **Save**

You can now browse tables, run queries, and manage the database from your web browser.

#### Option 2: Connect with psql

```bash
# From the Pi
psql -h localhost -U postgres -d alerts_dev
```

#### Option 3: External GUI Tools

Connect with desktop tools (DBeaver, TablePlus, DataGrip, etc.) from your computer:
- Host: Your Pi's IP (e.g., `192.168.1.100`)
- Port: `5432`
- Database: `alerts_dev`
- Username: `postgres`
- Password: `devpassword`

---

## Development Workflow

### Daily Workflow

1. **Start your day**:
```bash
ssh pi@192.168.1.100
cd ~/eas-station
docker-compose ps  # Verify containers are running

# If not running, start them:
# docker-compose --profile embedded-db --profile development up -d
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

The `docker-compose.development.yml` file configures your environment for debugging:

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
docker-compose ps

# Check logs
docker-compose logs app

# Restart app container
docker-compose restart app
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

**Solution**:

Check your `.env` file has the correct `POSTGRES_HOST`:

```bash
# For PyCharm SSH debugging on Pi, use:
POSTGRES_HOST=localhost

# For running in Docker container, use:
POSTGRES_HOST=alerts-db

# For local debugging on Windows/Mac, use:
POSTGRES_HOST=192.168.1.100  # Your Pi's actual IP
```

Then restart:
```bash
docker-compose restart app
docker-compose logs app
```

---

### Problem: Code Changes Not Appearing

**Solution**:

1. Check IDE sync status (bottom of window)
2. Manually trigger sync: **Tools** → **Deployment** → **Sync with Deployed to...**
3. Restart containers:
```bash
docker-compose down
docker-compose up -d
```

---

### Problem: "Permission Denied" on /dev/snd or GPIO

**Solution**:
```bash
# Add your user to necessary groups
sudo usermod -aG audio,gpio,docker $USER

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
- **Keep override file local**: Don't commit `docker-compose.override.yml` to Git

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
docker-compose logs -f audio_service

# Restart just the audio service
docker-compose restart audio_service
```

### Poller Service

```bash
# Check poller logs
docker-compose logs poller

# Run poller manually with debug output
docker-compose run --rm poller python poller/cap_poller.py --debug
```

---

## Keeping Your Git History Clean

### Use .gitignore

These files should NOT be committed (already in `.gitignore`):

```gitignore
docker-compose.override.yml
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
docker-compose --profile embedded-db --profile development up -d

# Check status
docker-compose ps
docker-compose logs -f app

# Stop debugging session
docker-compose down
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

1. ✅ Edit code in your IDE on your local machine
2. ✅ Run and debug on real Raspberry Pi hardware
3. ✅ Set breakpoints and inspect variables
4. ✅ Test with actual GPIO, audio, and SDR hardware
5. ✅ Commit only working, tested code to GitHub

**No more broken PRs. No more guess-and-check debugging. No more wasted time.**

---

## Getting Help

- **PyCharm Documentation**: [Remote Debugging with PyCharm](https://www.jetbrains.com/help/pycharm/remote-debugging-with-product.html)
- **VS Code Remote SSH**: [VS Code Remote Development](https://code.visualstudio.com/docs/remote/ssh)
- **Docker Compose Docs**: [Docker Compose Overview](https://docs.docker.com/compose/)
- **EAS Station Issues**: [GitHub Issues](https://github.com/KR8MER/eas-station/issues)

---

**Last Updated**: 2025-12-03
**Maintained By**: EAS Station Development Team
