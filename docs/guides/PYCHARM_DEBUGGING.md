# Remote Debugging Guide for Bare Metal Installation

**Stop pushing broken code to GitHub!** This guide shows you how to develop and debug the `eas-station` project directly on your Raspberry Pi or Linux server using PyCharm Professional or VS Code with SSH remote development. This is perfect for using AI coding agents like ZenCoder that need real-time access to your running application.

> **💡 Don't have PyCharm Professional?** Both VS Code (free) and PyCharm Professional (free for open source) work great for this project. See [Getting the Right IDE](#getting-the-right-ide) below.

---

## Table of Contents

- [Why Use This Approach?](#why-use-this-approach)
- [Getting the Right IDE](#getting-the-right-ide)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Database Configuration](#database-configuration)
- [Debugging Individual Services](#debugging-individual-services)
- [Using with AI Coding Agents (ZenCoder, etc.)](#using-with-ai-coding-agents-zencoder-etc)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Debugging Specific Services](#debugging-specific-services)
- [Keeping Your Git History Clean](#keeping-your-git-history-clean)
- [Quick Reference](#quick-reference)
- [Summary](#summary)
- [Getting Help](#getting-help)

---

## Why Use This Approach?

**The Problem**: Making a PR every time you want to test code changes is:
- ⚠️ Slow and frustrating
- ⚠️ Clutters your Git history with broken code
- ⚠️ Makes debugging nearly impossible
- ⚠️ Prevents real-time code analysis by AI agents

**The Solution**: Develop and debug live on the bare metal installation with:
- ✅ **Real hardware testing** - Test on actual Pi hardware, not simulations
- ✅ **Instant feedback** - See changes immediately without pushing to GitHub
- ✅ **Proper debugging** - Set breakpoints, inspect variables, step through code
- ✅ **Clean Git history** - Only commit working, tested code
- ✅ **AI Agent Integration** - Let ZenCoder and other coding agents see changes and bugs in real-time
- ✅ **Full System Access** - Debug all systemd services, database, and hardware integrations

### How It Works (Windows/Mac → Linux Server)

```
Your Development Computer               Linux Server (Pi/Debian)
┌─────────────────────┐                 ┌──────────────────────────┐
│  ┌───────────────┐  │   SSH + Code   │  ┌──────────────────────┐│
│  │ PyCharm/VSCode│──┼────────────────>│  │ /opt/eas-station/    ││
│  │ Edit Code     │  │                 │  │ ├── app.py           ││
│  │ Set Breakpoint│  │                 │  │ ├── app_core/        ││
│  │ AI Agents     │  │                 │  │ └── venv/            ││
│  └───────────────┘  │                 │  └──────────────────────┘│
│                     │                 │           │               │
│  ┌───────────────┐  │   Port 5678    │  ┌────────▼──────────┐   │
│  │ Debugger      │──┼────────────────>│  │ Python Debugpy    │   │
│  │ (debugpy)     │  │                 │  │ (port 5678)       │   │
│  └───────────────┘  │                 │  └───────────────────┘   │
│                     │                 │                          │
│  ┌───────────────┐  │   Port 5432    │  ┌────────────────────┐  │
│  │ Database Tools│──┼────────────────>│  │ PostgreSQL         │  │
│  │ (DataGrip)    │  │                 │  │ (alerts database)  │  │
│  └───────────────┘  │                 │  └────────────────────┘  │
│                     │                 │                          │
│  ┌───────────────┐  │   HTTPS (443)  │  ┌────────────────────┐  │
│  │ Web Browser   │──┼────────────────>│  │ Nginx → Gunicorn   │  │
│  │               │  │                 │  │ (Web Interface)    │  │
│  └───────────────┘  │                 │  └────────────────────┘  │
└─────────────────────┘                 └──────────────────────────┘

                                        Systemd Services:
                                        ├── eas-station-web.service
                                        ├── eas-station-audio.service
                                        ├── eas-station-noaa-poller.service
                                        ├── eas-station-ipaws-poller.service
                                        ├── eas-station-eas.service
                                        ├── eas-station-sdr.service
                                        └── eas-station-hardware.service
```

**Key Insight**: Your code runs ON the Linux server via systemd services, but you edit and debug from your local machine via SSH!

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

- **Linux Server** (Raspberry Pi 4/5, Debian, Ubuntu) with:
  - EAS Station installed via bare metal installation (`install.sh`)
  - SSH enabled
  - Installation directory: `/opt/eas-station`
  - Services running via systemd
- **Local development machine** running Windows, macOS, or Linux
- **Network connection** between your computer and the server
- **IDE**: PyCharm Professional or VS Code (see above)

### Assumed Installation

This guide assumes you've already completed the bare metal installation:

```bash
# On the Linux server:
cd ~/
git clone https://github.com/KR8MER/eas-station.git
cd eas-station
sudo ./install.sh
```

If not installed yet, see [QUICKSTART-BARE-METAL.md](../QUICKSTART-BARE-METAL.md) first.

### Skill Level

This guide assumes you know:
- Basic Python programming
- How to use SSH
- Basic Git commands
- Basic systemd service management (systemctl)

---

## Quick Start

### Step 1: Enable SSH on Linux Server

Connect to your server (keyboard + monitor, or existing SSH):

```bash
# Enable and start SSH
sudo systemctl enable ssh
sudo systemctl start ssh

# Find your server's IP address (write this down!)
hostname -I
```

**Write down the IP address** (example: `192.168.1.100`).

---

### Step 2: Verify EAS Station Installation

```bash
# Check that services are installed
sudo systemctl status eas-station.target

# You should see all services listed:
# ● eas-station-web.service
# ● eas-station-audio.service
# ● eas-station-noaa-poller.service
# ● eas-station-ipaws-poller.service
# ● eas-station-eas.service
# ● eas-station-sdr.service
# ● eas-station-hardware.service
```

If not installed, run the bare metal installer first (see [Prerequisites](#prerequisites)).

---

### Step 3: Install debugpy on the Server

The Python debugging protocol needs to be installed in the virtual environment:

```bash
# Activate the virtual environment
sudo -u eas-station /opt/eas-station/venv/bin/pip install debugpy

# Verify installation
sudo -u eas-station /opt/eas-station/venv/bin/python -c "import debugpy; print('debugpy installed successfully')"
```

---

### Step 4: Set Up Your IDE

#### Option A: VS Code (Recommended for Most Users)

1. **Install extensions**:
   - Open VS Code
   - Install **Remote - SSH** extension (by Microsoft)
   - Install **Python** extension (by Microsoft)

2. **Connect to server**:
   - Press `F1` (or `Ctrl+Shift+P` / `Cmd+Shift+P`)
   - Type: `Remote-SSH: Connect to Host`
   - Enter: `eas-station@YOUR.SERVER.IP.ADDRESS` (default user for bare metal installation)
     - Note: If you installed on Raspberry Pi OS manually, you might use `pi@YOUR.PI.IP` instead
   - Enter your password
   - Choose **File** → **Open Folder** → `/opt/eas-station`

3. **Set up Python interpreter**:
   - Press `Ctrl+Shift+P` / `Cmd+Shift+P`
   - Type: `Python: Select Interpreter`
   - Choose: `/opt/eas-station/venv/bin/python`

4. **Set up debugging** (for the web service):
   - Click **Run and Debug** icon (left sidebar)
   - Click **create a launch.json file** → **Python**
   - Replace contents with:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Attach to Web Service",
            "type": "debugpy",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/opt/eas-station"
                }
            ],
            "justMyCode": false
        },
        {
            "name": "Debug Audio Service",
            "type": "debugpy",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5679
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/opt/eas-station"
                }
            ],
            "justMyCode": false
        }
    ]
}
```

5. **Enable debugging for a service**:

To debug the web service, you need to modify the systemd service to include debugpy. See [Debugging Individual Services](#debugging-individual-services) below.

6. **Test debugging**:
   - After enabling debugpy in a service (see below)
   - Open any Python file (like `app.py`)
   - Click in the left margin to set a breakpoint (red dot appears)
   - Press `F5` to start debugging
   - If it connects, you're done! 🎉

#### Option B: PyCharm Professional

1. **Set up SSH Deployment**:
   - Go to: **File** → **Settings** → **Build, Execution, Deployment** → **Deployment**
   - Click **+** → **SFTP**
   - Name: `EAS Station Server`
   - **Connection** tab:
     - Type: **SFTP**
     - Host: Your server's IP address
     - Port: `22`
     - Username: `eas-station` (or `pi` for Raspberry Pi)
     - Auth type: Password
     - Password: Your server password
   - **Mappings** tab:
     - Local path: Your project folder
     - Deployment path: `/opt/eas-station`
     - Web path: (leave empty)
   - Click **Test Connection** → **OK**

2. **Set up SSH Interpreter**:
   - Go to: **File** → **Settings** → **Project** → **Python Interpreter**
   - Click **gear icon** ⚙️ → **Add...** → **On SSH**
   - **Existing server configuration**: Select the server you just created
   - Click **Next**
   - Set interpreter: `/opt/eas-station/venv/bin/python`
   - Sync folders:
     - Local: Your project folder
     - Remote: `/opt/eas-station`
   - Click **Finish** and wait for sync

3. **Create Debug Configuration**:
   - Go to: **Run** → **Edit Configurations...**
   - Click **+** → **Python Debug Server**
   - Name: `EAS Station Web Service`
   - IDE host name: `localhost`
   - Port: `5678`
   - Path mappings:
     - Local: Your project folder
     - Remote: `/opt/eas-station`
   - Click **OK**

4. **Enable debugging for a service**:

To debug the web service, you need to modify the systemd service to include debugpy. See [Debugging Individual Services](#debugging-individual-services) below.

5. **Test debugging**:
   - After enabling debugpy in a service (see below)
   - Set a breakpoint (click in left margin)
   - Click debug icon (green bug) or press `Shift+F9`
   - You're done! 🎉

---

## Database Configuration

The bare metal installation uses a **local PostgreSQL database** running directly on the Linux server (not in a container).

### Database Connection Details

**Default configuration** (already set during installation in `/opt/eas-station/.env`):

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=alerts
POSTGRES_USER=eas_station
POSTGRES_PASSWORD=<auto-generated during install>
```

**For remote debugging from your IDE**:
- When using SSH Remote Interpreter: Use `POSTGRES_HOST=localhost` (code runs on server)
- The database password is auto-generated during installation and stored in `/opt/eas-station/.env`

### Finding Your Database Password

```bash
# On the server:
sudo grep POSTGRES_PASSWORD /opt/eas-station/.env
```

**Example output**: `POSTGRES_PASSWORD=abc123xyz789`

### Accessing the Database from Your Development Machine

The PostgreSQL database runs on the server, but you can access it from your local machine in several ways:

#### Option 1: pgAdmin Web Interface (Easiest)

pgAdmin 4 is installed on the server and accessible via web browser:

1. **Open your web browser**
2. Go to: `https://YOUR_SERVER_IP/pgadmin4` (e.g., `https://192.168.1.100/pgadmin4`)
3. Login:
   - Email: The administrator email you created during installation
   - Password: The administrator password you created during installation
4. **Add database server** (first time only):
   - Right-click **Servers** → **Register** → **Server**
   - **General** tab:
     - Name: `EAS Station`
   - **Connection** tab:
     - Host: `localhost`
     - Port: `5432`
     - Database: `alerts`
     - Username: `eas_station`
     - Password: (from `/opt/eas-station/.env` - see above)
   - Click **Save**

You can now browse tables, run queries, and manage the database from your browser!

#### Option 2: Desktop Database Tools (PyCharm DataGrip, DBeaver, TablePlus, etc.)

Connect from your local machine directly to the server's PostgreSQL:

**Connection settings**:
- **Host**: Your server's IP (e.g., `192.168.1.100`)
- **Port**: `5432`
- **Database**: `alerts`
- **Username**: `eas_station`
- **Password**: (from `/opt/eas-station/.env`)

**PyCharm Professional includes DataGrip database tools**:
1. In PyCharm, open **Database** tool window (View → Tool Windows → Database)
2. Click **+** → **Data Source** → **PostgreSQL**
3. Enter the connection settings above
4. Click **Test Connection** → **OK**

#### Option 3: psql from SSH

If you SSH into the server:

```bash
# From SSH session on the server
sudo -u postgres psql -d alerts

# Or as eas_station user (requires password from .env):
psql -h localhost -U eas_station -d alerts
```

### Ensuring Database Access from Your Local Machine

The database port (5432) needs to be accessible from your development machine. Check the firewall:

```bash
# On the server, check if port 5432 is listening
sudo netstat -tlnp | grep 5432

# If you have ufw firewall enabled, allow the port:
sudo ufw allow 5432/tcp
sudo ufw status
```

**Test connectivity from your local machine**:

```powershell
# Windows PowerShell:
Test-NetConnection -ComputerName 192.168.1.100 -Port 5432
```

```bash
# Linux/Mac terminal:
nc -zv 192.168.1.100 5432
```

If the connection fails, you may need to configure PostgreSQL to accept remote connections:

```bash
# On the server, edit postgresql.conf
sudo nano /etc/postgresql/*/main/postgresql.conf

# Find and uncomment/change:
listen_addresses = '*'  # or 'localhost,192.168.1.100'

# Save and restart PostgreSQL
sudo systemctl restart postgresql
```

---

## Debugging Individual Services

EAS Station runs as multiple systemd services. To debug a specific service, you need to enable debugpy for that service.

### Understanding the Service Architecture

```bash
# List all EAS Station services
sudo systemctl list-units 'eas-station*' --all

# Services you can debug:
# ├── eas-station-web.service      (Flask web app - port 5000 → nginx)
# ├── eas-station-audio.service    (Audio processing - eas_monitoring_service.py)
# ├── eas-station-noaa-poller.service  (NOAA weather alerts)
# ├── eas-station-ipaws-poller.service (IPAWS/FEMA alerts)
# ├── eas-station-eas.service      (EAS broadcast generation)
# ├── eas-station-sdr.service      (SDR radio monitoring)
# └── eas-station-hardware.service (Hardware control - LED/GPIO)
```

### Method 1: Temporary Debug Mode (Recommended for Testing)

This method lets you quickly test debugging without modifying systemd services.

**Example: Debug the Web Service**

1. **Stop the systemd service**:
```bash
sudo systemctl stop eas-station-web.service
```

2. **Start the service manually with debugpy** (as the service user):
```bash
# Run as the eas-station user with debugpy enabled
sudo -u eas-station /opt/eas-station/venv/bin/python -m debugpy \
    --listen 0.0.0.0:5678 \
    --wait-for-client \
    /opt/eas-station/app.py
```

3. **Attach your IDE debugger**:
   - In VS Code: Press `F5` and select "Attach to Web Service"
   - In PyCharm: Click the debug icon (green bug)

4. **Set breakpoints and debug** as normal!

5. **When done**, stop the manual process (`Ctrl+C`) and restart the systemd service:
```bash
sudo systemctl start eas-station-web.service
```

**Example: Debug the Audio Service**

```bash
# Stop the service
sudo systemctl stop eas-station-audio.service

# Run with debugpy on port 5679
sudo -u eas-station /opt/eas-station/venv/bin/python -m debugpy \
    --listen 0.0.0.0:5679 \
    --wait-for-client \
    /opt/eas-station/eas_monitoring_service.py

# Attach debugger on port 5679, then restart when done:
sudo systemctl start eas-station-audio.service
```

### Method 2: Persistent Debug Mode (For Long-Term Development)

This method modifies the systemd service file to always run with debugpy enabled.

**Example: Enable debugging for Web Service**

1. **Create a systemd override file**:
```bash
sudo systemctl edit eas-station-web.service
```

2. **Add this content** (this opens an editor):
```ini
[Service]
# Clear the original ExecStart
ExecStart=

# Replace with debugpy-enabled start command
# ⚠️ SECURITY: Using 0.0.0.0 exposes debug port to all network interfaces
# For local debugging only, use 127.0.0.1:5678 instead
# For remote debugging, ensure firewall rules are properly configured
ExecStart=/opt/eas-station/venv/bin/python -m debugpy \
    --listen 0.0.0.0:5678 \
    /opt/eas-station/venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --timeout 300 \
    --worker-class gevent \
    --worker-connections 1000 \
    --log-level info \
    --access-logfile /var/log/eas-station/web-access.log \
    --error-logfile /var/log/eas-station/web-error.log \
    app:app
```

3. **Save and exit**, then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart eas-station-web.service
```

4. **Verify debugpy is listening**:
```bash
# Check service status
sudo systemctl status eas-station-web.service

# Verify port 5678 is listening
sudo netstat -tlnp | grep 5678
```

5. **Attach your debugger** and start debugging!

6. **To revert** to normal mode (disable debugging):
```bash
# Remove the override
sudo systemctl revert eas-station-web.service

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart eas-station-web.service
```

### Method 3: Direct Code Modification (For app.py)

For the Flask web application, you can add debugpy directly to `app.py`:

1. **Edit app.py**:
```bash
# Via SSH or your IDE:
nano /opt/eas-station/app.py
```

2. **Add at the very beginning** (before imports):
```python
# Debug support - REMOVE IN PRODUCTION
import os
if os.environ.get('ENABLE_DEBUGPY', 'false').lower() == 'true':
    import debugpy
    debugpy.listen(("0.0.0.0", 5678))
    print("⚠️ debugpy listening on port 5678 - WAITING FOR DEBUGGER")
    # Remove wait-for-client in production, or the app won't start until debugger attaches
    # debugpy.wait_for_client()
    print("✓ Debugger attached!")
```

3. **Enable via environment variable**:
```bash
# Edit .env
sudo nano /opt/eas-station/.env

# Add this line:
ENABLE_DEBUGPY=true
```

4. **Restart the web service**:
```bash
sudo systemctl restart eas-station-web.service
```

5. **Attach debugger** from your IDE

6. **IMPORTANT**: Before committing to Git, either:
   - Remove the debugpy code entirely, OR
   - Set `ENABLE_DEBUGPY=false` in `.env` and never commit with it enabled

### Port Assignments for Debugging

Use different ports for each service to debug multiple services simultaneously:

| Service | Main Process | Debug Port | Launch Command |
|---------|-------------|------------|----------------|
| **Web** | `app.py` → gunicorn | `5678` | See Method 1 above |
| **Audio** | `eas_monitoring_service.py` | `5679` | See audio example above |
| **NOAA Poller** | Poller script | `5680` | `debugpy --listen 0.0.0.0:5680 ...` |
| **IPAWS Poller** | Poller script | `5681` | `debugpy --listen 0.0.0.0:5681 ...` |
| **EAS** | EAS service | `5682` | `debugpy --listen 0.0.0.0:5682 ...` |
| **SDR** | SDR service | `5683` | `debugpy --listen 0.0.0.0:5683 ...` |
| **Hardware** | Hardware service | `5684` | `debugpy --listen 0.0.0.0:5684 ...` |

### Firewall Configuration for Remote Debugging

If debugging from a remote machine (not localhost), ensure the debug ports are accessible:

```bash
# Allow debugpy ports through firewall
sudo ufw allow 5678/tcp comment 'debugpy - web service'
sudo ufw allow 5679/tcp comment 'debugpy - audio service'
# ... add more as needed

# Check firewall status
sudo ufw status
```

**⚠️ SECURITY WARNING**: Debug ports expose your application internals. Only enable on trusted networks or use SSH port forwarding for remote access.

### SSH Port Forwarding (Secure Remote Debugging)

Instead of opening firewall ports, use SSH tunneling:

```bash
# From your local machine, forward debug port 5678 through SSH:
ssh -L 5678:localhost:5678 eas-station@YOUR_SERVER_IP

# Now attach debugger to localhost:5678 on YOUR machine
# The connection is encrypted through SSH
```

---

## Using with AI Coding Agents (ZenCoder, etc.)

AI coding agents like ZenCoder work best when they can see your code, run it, and observe failures in real-time. Here's how to integrate them with your EAS Station development environment.

### Why This Setup is Perfect for AI Agents

✅ **Real-time code access** - Agent sees all files via SSH
✅ **Immediate execution** - Code changes run instantly on server
✅ **Full debugging** - Agent can use debugpy to inspect state
✅ **Database access** - Agent can query/modify the database
✅ **Log streaming** - Agent can watch systemd logs in real-time
✅ **Hardware testing** - Agent can test with actual GPIO/SDR/audio devices

### Setting Up ZenCoder with PyCharm

1. **Install ZenCoder extension** in PyCharm:
   - Go to **Settings** → **Plugins** → **Marketplace**
   - Search for "ZenCoder" and install
   - Restart PyCharm

2. **Configure ZenCoder** for remote development:
   - ZenCoder automatically uses your project's Python interpreter
   - Since you've set up SSH Remote Interpreter, ZenCoder will execute code on the server
   - No additional configuration needed!

3. **Grant ZenCoder access to debugging**:
   - Enable debugpy for the service you're working on (see above)
   - ZenCoder can attach to debugpy sessions to inspect variables
   - Share your launch.json configuration with ZenCoder

### Workflow Example: Using ZenCoder to Fix a Bug

**Scenario**: You found a bug in alert processing. Let ZenCoder help!

1. **Describe the problem to ZenCoder**:
   ```
   "The NOAA poller is crashing when processing alerts with invalid GeoJSON.
   Check the logs and fix the issue."
   ```

2. **ZenCoder can**:
   - Read the systemd logs: `journalctl -u eas-station-noaa-poller.service -n 100`
   - View the source code: `/opt/eas-station/app_core/noaa_poller.py`
   - Check the database: Query the `cap_alerts` table via psql or Python
   - Test the fix: Modify the code and restart the service
   - Verify: Check logs again to confirm the fix works

3. **ZenCoder sees changes immediately**:
   - Code edits sync to `/opt/eas-station/` via PyCharm
   - Service restarts pick up changes instantly
   - Logs show the results in real-time

4. **ZenCoder can use the debugger**:
   - Set breakpoints in the code
   - Attach to debugpy session
   - Inspect variables when the crash occurs
   - Trace the execution flow

### Example: ZenCoder Database Queries

ZenCoder can query the database directly to understand data issues:

```python
# ZenCoder can run this in the Python console (via PyCharm or SSH):
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='alerts',
    user='eas_station',
    password='<from .env>'
)
cur = conn.cursor()
cur.execute("SELECT id, event, message_type, status FROM cap_alerts WHERE status = 'Error' LIMIT 10;")
for row in cur.fetchall():
    print(row)
```

### Example: ZenCoder Log Analysis

```bash
# ZenCoder can run systemctl commands via SSH:
sudo journalctl -u eas-station-noaa-poller.service --since "1 hour ago" | grep ERROR
```

### Best Practices for AI Agent Development

1. **Give context**: Share error logs, stack traces, and database states with the agent
2. **Use descriptive file names**: AI agents parse better with clear naming
3. **Keep services running**: Don't stop all services - isolate the one you're debugging
4. **Test incrementally**: Let the agent make small changes, test, then iterate
5. **Review AI changes**: Always review and test before committing
6. **Use version control**: Commit working states frequently so you can rollback AI mistakes

### Permissions for AI Agents

ZenCoder runs as your user via PyCharm. For system commands (like `systemctl`), configure sudo access:

```bash
# On the server, edit sudoers for the eas-station user (if needed):
sudo visudo

# Add (adjust as needed for security - these are minimal permissions):
eas-station ALL=(ALL) NOPASSWD: /bin/systemctl restart eas-station-*
eas-station ALL=(ALL) NOPASSWD: /bin/systemctl stop eas-station-*
eas-station ALL=(ALL) NOPASSWD: /bin/systemctl start eas-station-*
eas-station ALL=(ALL) NOPASSWD: /bin/systemctl status eas-station-*
# Restrict journalctl to EAS Station services only
eas-station ALL=(ALL) NOPASSWD: /bin/journalctl -u eas-station-*
```

**⚠️ Security Notes**: 
- Only grant minimal necessary permissions
- The above restricts systemctl to eas-station-* services only
- journalctl is restricted to eas-station-* units to prevent reading sensitive system logs
- Consider using `sudo -v` to cache credentials instead for even tighter security

---

## Development Workflow

### Daily Workflow

1. **Connect via SSH** (your IDE handles this automatically):
```bash
# VS Code: Use Remote-SSH extension (already connected)
# PyCharm: Uses SSH interpreter (already connected)

# Or manual SSH for command-line work:
ssh eas-station@YOUR_SERVER_IP
```

2. **Check service status**:
```bash
# View all EAS Station services
sudo systemctl status eas-station.target

# Check specific service
sudo systemctl status eas-station-web.service

# View recent logs
sudo journalctl -u eas-station-web.service -f
```

3. **Edit code in your IDE**:
   - Edit files in VS Code or PyCharm
   - Changes sync to `/opt/eas-station/` automatically (PyCharm deployment)
   - Or edit directly via SSH (changes are immediate)

4. **Test changes**:
```bash
# Restart the service you modified
sudo systemctl restart eas-station-web.service

# Watch the logs for errors
sudo journalctl -u eas-station-web.service -f

# Test via web browser
# Navigate to https://YOUR_SERVER_IP
```

5. **Debug with breakpoints**:
   - Enable debugpy for the service (see [Debugging Individual Services](#debugging-individual-services))
   - Set breakpoints in your IDE
   - Attach debugger
   - Trigger the code path (web request, timer, etc.)
   - Step through code, inspect variables

6. **Iterate quickly**:
   - Make changes
   - Restart service: `sudo systemctl restart eas-station-web.service`
   - Test
   - Repeat

7. **Commit only working code**:
```bash
# On the server or via your IDE's Git integration:
git status
git diff
git add <specific-files>
git commit -m "Fix: Clear description of what you fixed"
git push origin <branch-name>
```

### Rapid Development Tips

**Tip 1: Auto-reload Flask app** (for web service only)

During development, you can run the Flask app in debug mode for automatic reloading:

```bash
# Stop the systemd service
sudo systemctl stop eas-station-web.service

# Run Flask dev server manually (as eas-station user)
sudo -u eas-station bash -c 'cd /opt/eas-station && source venv/bin/activate && FLASK_ENV=development python app.py'

# Flask will auto-reload when you save files
# Press Ctrl+C to stop, then restart the systemd service:
sudo systemctl start eas-station-web.service
```

**Tip 2: Watch logs in real-time**

```bash
# Watch all EAS Station services
sudo journalctl -u 'eas-station*' -f

# Watch specific service
sudo journalctl -u eas-station-web.service -f

# Watch with grep filter
sudo journalctl -u eas-station-web.service -f | grep ERROR
```

**Tip 3: Test database changes**

```bash
# Open psql as eas_station user
sudo -u postgres psql -d alerts

# Or from your IDE's database tools
# (see Database Configuration section)
```

### Understanding Service Dependencies

```bash
# View service dependency tree
systemd-analyze dot 'eas-station*' | dot -Tpng > /tmp/eas-services.png

# Check which services depend on which
sudo systemctl list-dependencies eas-station.target
```

**Service startup order**:
1. PostgreSQL, Redis (system services)
2. eas-station-web.service
3. eas-station-audio.service, eas-station-sdr.service
4. eas-station-*-poller.service (depends on web for database)
5. eas-station-eas.service, eas-station-hardware.service

**What this means for debugging**:
- If you restart the web service, pollers should still work (they reconnect)
- If you restart PostgreSQL, you need to restart all EAS Station services
- If you restart Redis, restart audio/poller services

### Testing on Real Hardware

**Advantages of bare metal development**:
- Test with actual GPIO pins (if on Raspberry Pi)
- Test with real audio devices (USB sound cards, SDR)
- Test with actual network performance
- Test with real-time constraints

**Example: Test SDR integration**

```bash
# Stop the SDR service
sudo systemctl stop eas-station-sdr.service

# Run manually with verbose logging
sudo -u eas-station /opt/eas-station/venv/bin/python \
    /opt/eas-station/scripts/debug/test_sdr_direct.py

# Or run with debugpy for debugging:
sudo -u eas-station /opt/eas-station/venv/bin/python -m debugpy \
    --listen 0.0.0.0:5683 --wait-for-client \
    /opt/eas-station/scripts/debug/test_sdr_direct.py
```

### Working with Multiple Developers

**Scenario**: Multiple developers on the same server

1. **Use separate Git branches**:
```bash
# Developer 1
git checkout -b feature/new-alert-parser

# Developer 2
git checkout -b feature/led-sign-update
```

2. **Each developer debugs their own service**:
   - Dev 1 debugs poller service on port 5680
   - Dev 2 debugs hardware service on port 5684

3. **Use systemd service overrides per developer**:
```bash
# Developer 1 creates override for poller:
sudo systemctl edit eas-station-noaa-poller.service
# (add debugpy)

# Developer 2 creates override for hardware:
sudo systemctl edit eas-station-hardware.service
# (add debugpy on different port)
```

4. **Communicate and merge**:
   - Test changes independently
   - Merge to main branch when working
   - Let CI/CD run tests

---

## Troubleshooting

### Problem: "Connection Refused" When Debugging

**Solution**:
```bash
# Check if debugpy is listening on the port
sudo netstat -tlnp | grep 5678

# Check service status
sudo systemctl status eas-station-web.service

# View service logs for errors
sudo journalctl -u eas-station-web.service -n 50

# Restart the service
sudo systemctl restart eas-station-web.service
```

---

### Problem: PyCharm/VS Code Can't Connect via SSH

**Solution**:
```bash
# On the server, check SSH status
sudo systemctl status ssh

# If not running, start it
sudo systemctl start ssh

# Test from your computer
ssh eas-station@192.168.1.100
```

---

### Problem: "Can't connect to database"

**Cause**: Wrong hostname in `.env` or network/firewall issue.

**Solution**:

1. **Check your `.env` file has the correct `POSTGRES_HOST`**:

```bash
# On the server, check the config:
sudo grep POSTGRES_HOST /opt/eas-station/.env

# Should be:
POSTGRES_HOST=localhost  # For local PostgreSQL on the server
```

2. **For remote desktop tools**, verify network connectivity:

```powershell
# Test from Windows PowerShell:
Test-NetConnection -ComputerName 192.168.1.100 -Port 5432
```

```bash
# Or from Linux/Mac:
nc -zv 192.168.1.100 5432
```

If this fails, check the server's firewall:
```bash
# On the server:
sudo ufw allow 5432/tcp
sudo ufw status

# Verify the port is listening:
sudo netstat -tlnp | grep 5432
```

3. **Restart the service** after changing `.env`:
```bash
sudo systemctl restart eas-station-web.service
```

---

### Problem: "Can't connect to database from remote tools"

**Cause**: Firewall blocking port 5432 or PostgreSQL not listening on external interface.

**Solution**:

1. **Configure PostgreSQL to accept remote connections**:
```bash
# ⚠️ SECURITY WARNING: The following configuration allows remote database access
# Only do this on trusted networks or use SSH tunneling instead (see below)

# Edit postgresql.conf
sudo nano /etc/postgresql/*/main/postgresql.conf

# Find and change (for all IPs - less secure):
listen_addresses = '*'
# OR for specific IP only (more secure):
listen_addresses = 'localhost,192.168.1.100'

# Edit pg_hba.conf to allow your machine
sudo nano /etc/postgresql/*/main/pg_hba.conf

# Add this line (replace with your specific network/IP for better security):
host    alerts    eas_station    192.168.1.0/24    scram-sha-256
# OR for a single IP (more secure):
# host    alerts    eas_station    192.168.1.50/32    scram-sha-256

# Restart PostgreSQL
sudo systemctl restart postgresql
```

**Security Best Practice**: Instead of exposing PostgreSQL to the network, use SSH port forwarding:
```bash
# From your local machine, create SSH tunnel:
ssh -L 5432:localhost:5432 eas-station@YOUR_SERVER_IP

# Now connect your database tools to localhost:5432 on your machine
# The connection is encrypted through SSH and no firewall changes needed
```

2. **Check server's firewall**:
```bash
# On the server:
sudo ufw allow 5432/tcp

# If ufw is not active:
sudo ufw status
```

3. **Test from your local machine**:
```powershell
# Windows PowerShell:
Test-NetConnection -ComputerName 192.168.1.100 -Port 5432

# Should show: TcpTestSucceeded : True
```

```bash
# On the server:
sudo netstat -tlnp | grep 5432

# Should show: 0.0.0.0:5432 (not 127.0.0.1:5432)
```

---

### Problem: Code Changes Not Appearing

**Solution**:

1. **Check IDE sync status** (bottom of window in PyCharm)
2. **Manually trigger sync**: **Tools** → **Deployment** → **Sync with Deployed to...**
3. **Restart the service**:
```bash
sudo systemctl restart eas-station-web.service
```

4. **Verify file was actually updated**:
```bash
# SSH to server and check file timestamp
ls -l /opt/eas-station/app.py

# Or view the file:
tail -20 /opt/eas-station/app.py
```

---

### Problem: "Permission Denied" on /dev/snd or GPIO

**Solution**:
```bash
# Add the eas-station user to necessary groups
sudo usermod -aG audio,gpio,dialout eas-station

# Restart the services for group changes to take effect
sudo systemctl restart eas-station.target

# Verify group membership
sudo -u eas-station groups
```

---

### Problem: debugpy Won't Start - "Address already in use"

**Cause**: Another process is using the debug port (5678).

**Solution**:
```bash
# Find what's using the port
sudo netstat -tlnp | grep 5678

# Kill the process (replace PID with actual PID)
sudo kill <PID>

# Or if it's another eas-station service:
sudo systemctl restart eas-station-web.service
```

---

### Problem: Service Crashes After Code Changes

**Cause**: Syntax error or runtime exception in your code.

**Solution**:
```bash
# View the service logs to find the error
sudo journalctl -u eas-station-web.service -n 100

# Common issues:
# - Python syntax errors
# - Import errors (missing dependencies)
# - Database migration needed
# - Missing environment variables

# Test the code manually before restarting service:
sudo -u eas-station /opt/eas-station/venv/bin/python -c "import app"
```

---

### Problem: Changes Work Locally But Break in Production

**Cause**: Different environment variables or database state.

**Solution**:
```bash
# Compare .env files
diff /opt/eas-station/.env /opt/eas-station/.env.example

# Check database migrations
cd /opt/eas-station
sudo -u eas-station /opt/eas-station/venv/bin/alembic current
sudo -u eas-station /opt/eas-station/venv/bin/alembic upgrade head

# Ensure dependencies are installed
sudo -u eas-station /opt/eas-station/venv/bin/pip install -r requirements.txt

# Restart all services
sudo systemctl restart eas-station.target
```

---
---

## Best Practices

### DO ✅

- **Test locally first**: Always debug on the server before pushing to GitHub
- **Use breakpoints**: Don't just add print statements - use real debugging
- **Commit often**: When something works, commit it immediately
- **Write descriptive commits**: "Fix: Describe what you fixed" not "fixed stuff"
- **Use systemd service overrides**: Don't modify the main service files in `/etc/systemd/system/`
- **Clean up debug code**: Remove or disable debugpy before committing
- **Test with real hardware**: Take advantage of bare metal for GPIO/SDR/audio testing
- **Watch logs**: Use `journalctl -f` to see real-time feedback
- **Use separate branches**: Create feature branches for AI agent experiments

### DON'T ❌

- **Don't push untested code**: Test it on the server first!
- **Don't commit broken code**: Fix it first, then commit
- **Don't commit debug configurations**: Keep those in systemd overrides
- **Don't commit secrets**: Check for passwords/API keys before committing (use `.env`)
- **Don't use `git add .`**: Add specific files only
- **Don't leave debugpy enabled**: Disable debug mode for production
- **Don't modify production services directly**: Use `systemctl edit` for overrides
- **Don't run services as root**: Always use `sudo -u eas-station` for testing

---

## Debugging Specific Services

### Audio Service

```bash
# View logs in real-time
sudo journalctl -u eas-station-audio.service -f

# Restart just the audio service
sudo systemctl restart eas-station-audio.service

# Stop and run manually with debug output
sudo systemctl stop eas-station-audio.service
sudo -u eas-station /opt/eas-station/venv/bin/python eas_monitoring_service.py
```

### Poller Service

```bash
# Check NOAA poller logs
sudo journalctl -u eas-station-noaa-poller.service -n 100

# Check IPAWS poller logs
sudo journalctl -u eas-station-ipaws-poller.service -n 100

# Run poller manually with debug output
sudo systemctl stop eas-station-noaa-poller.service
sudo -u eas-station /opt/eas-station/venv/bin/python -c "from app_core.noaa_poller import poll_noaa; poll_noaa()"
```

### Hardware Service

```bash
# View hardware service logs
sudo journalctl -u eas-station-hardware.service -f

# Test GPIO without running the service
sudo systemctl stop eas-station-hardware.service
sudo -u eas-station /opt/eas-station/venv/bin/python -c "from app_core import hardware; hardware.test_gpio()"
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
# Connect to server
ssh eas-station@192.168.1.100

# Check all services status
sudo systemctl status eas-station.target

# Check specific service
sudo systemctl status eas-station-web.service

# Restart a service after code changes
sudo systemctl restart eas-station-web.service

# Watch logs in real-time
sudo journalctl -u eas-station-web.service -f

# Stop all services
sudo systemctl stop eas-station.target

# Start all services
sudo systemctl start eas-station.target

# Enable debugpy for a service (temporary)
sudo systemctl stop eas-station-web.service
sudo -u eas-station /opt/eas-station/venv/bin/python -m debugpy \
    --listen 0.0.0.0:5678 --wait-for-client /opt/eas-station/app.py
```

### systemd Service Management

```bash
# List all EAS Station services
sudo systemctl list-units 'eas-station*'

# Edit a service (creates override)
sudo systemctl edit eas-station-web.service

# Revert service to default (remove override)
sudo systemctl revert eas-station-web.service

# Reload systemd after manual edits
sudo systemctl daemon-reload

# View service dependencies
sudo systemctl list-dependencies eas-station.target
```

### Database Quick Access

```bash
# Connect to PostgreSQL as eas_station user
sudo -u postgres psql -d alerts

# Or with password auth:
psql -h localhost -U eas_station -d alerts

# Get database password
sudo grep POSTGRES_PASSWORD /opt/eas-station/.env

# pgAdmin web interface
# Navigate to: https://YOUR_SERVER_IP/pgadmin4
```

### IDE Shortcuts

**VS Code**:
- **Set Breakpoint**: Click left margin or `F9`
- **Start Debugging**: `F5`
- **Step Over**: `F10`
- **Step Into**: `F11`
- **Continue**: `F5`
- **Stop Debugging**: `Shift+F5`

**PyCharm**:
- **Set Breakpoint**: Click left margin or `Ctrl+F8` / `Cmd+F8`
- **Start Debugging**: `Shift+F9`
- **Step Over**: `F8`
- **Step Into**: `F7`
- **Resume**: `F9`
- **Stop Debugging**: `Ctrl+F2` / `Cmd+F2`

---

## Summary

You now have a complete development environment where you can:

1. ✅ Edit code in PyCharm/VS Code on your local machine via SSH
2. ✅ Run and debug on real Linux server / Raspberry Pi hardware
3. ✅ Access the database remotely (pgAdmin web, desktop tools, PyCharm DataGrip)
4. ✅ Set breakpoints and inspect variables with debugpy
5. ✅ Test with actual GPIO, audio, and SDR hardware (bare metal advantages)
6. ✅ Let AI agents like ZenCoder see and modify code in real-time
7. ✅ Commit only working, tested code to GitHub
8. ✅ Debug individual systemd services independently

**Key Points**:
- **Code location**: `/opt/eas-station/` on the server (not `/home/pi/eas-station`)
- **Services**: Managed by systemd (not Docker containers)
- **Database**: Local PostgreSQL on server at `localhost:5432`
- **PyCharm/VS Code** → Code runs on server via SSH → Use `POSTGRES_HOST=localhost`
- **Remote database tools** → Connect to server's IP (e.g., `192.168.1.100:5432`)
- **pgAdmin web** → Access at `https://SERVER_IP/pgadmin4`
- **Debug ports**: 5678 (web), 5679 (audio), 5680-5684 (other services)

**Perfect for AI coding agents**:
- ZenCoder can see all code changes immediately
- Full database access for querying and debugging
- Real-time log streaming via journalctl
- Direct debugpy integration for deep inspection
- No container isolation - direct hardware access

**No more broken PRs. No more guess-and-check debugging. No more wasted time.**

---

## Getting Help

- **PyCharm Documentation**: [Remote Debugging with PyCharm](https://www.jetbrains.com/help/pycharm/remote-debugging-with-product.html)
- **VS Code Remote SSH**: [VS Code Remote Development](https://code.visualstudio.com/docs/remote/ssh)
- **debugpy Documentation**: [Python Debugger](https://github.com/microsoft/debugpy)
- **systemd Documentation**: [systemd.io](https://systemd.io/)
- **EAS Station Issues**: [GitHub Issues](https://github.com/KR8MER/eas-station/issues)
- **EAS Station Discussions**: [GitHub Discussions](https://github.com/KR8MER/eas-station/discussions)

---

**Last Updated**: 2025-12-10
**Maintained By**: EAS Station Development Team
