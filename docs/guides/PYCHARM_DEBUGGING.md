# Complete Development Setup Guide for zencoder.ai Integration

**Transform your development workflow!** This comprehensive guide shows you how to set up your Raspberry Pi or Linux server so that **zencoder.ai** (https://zencoder.ai) can work alongside you like a pair programmer sitting at your desk. Zencoder will be able to:

- ✅ **Run your code** and see the output in real-time
- ✅ **Debug issues** by setting breakpoints and inspecting variables
- ✅ **View database transactions** and query data directly
- ✅ **Access the web interface** to test UI changes
- ✅ **Monitor system logs** and service status
- ✅ **Execute tests** and verify fixes immediately

This guide will hold your hand through every step of the setup process, from SSH configuration to database access to debugging tools. By the end, zencoder.ai will have complete visibility into your EAS Station development environment.

> **💡 New to this setup?** Don't worry! This guide assumes no prior experience with remote development. We'll explain everything step-by-step.

---

## Table of Contents

- [Why This Setup is Perfect for zencoder.ai](#why-this-setup-is-perfect-for-zenco derai)
- [What You'll Learn](#what-youll-learn)
- [Prerequisites](#prerequisites)
- [Part 1: Setting Up Your IDE (PyCharm or VS Code)](#part-1-setting-up-your-ide-pycharm-or-vs-code)
- [Part 2: Enabling zencoder.ai to Run Code](#part-2-enabling-zenco derai-to-run-code)
- [Part 3: Database Access for zencoder.ai](#part-3-database-access-for-zenco derai)
- [Part 4: Viewing the Web Interface](#part-4-viewing-the-web-interface)
- [Part 5: Debugging with zencoder.ai](#part-5-debugging-with-zenco derai)
- [Part 6: Advanced Features](#part-6-advanced-features)
- [Complete zencoder.ai Workflow Examples](#complete-zenco derai-workflow-examples)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)
- [Best Practices](#best-practices)
- [Quick Reference Commands](#quick-reference-commands)
- [Summary and Next Steps](#summary-and-next-steps)

---

## Why This Setup is Perfect for zencoder.ai

**zencoder.ai** (https://zencoder.ai) is an AI coding assistant that needs full access to your development environment to be truly effective. Think of it as having an expert developer sitting next to you who can:

### What Makes This Special

Traditional development workflows have limitations:
- ❌ Code runs in isolated environments
- ❌ AI can't see real-time errors
- ❌ No access to live databases
- ❌ Can't test on actual hardware
- ❌ Limited to suggesting code, not testing it

**With this setup, zencoder.ai becomes a true pair programmer:**
- ✅ **Executes code directly** on your Raspberry Pi/server
- ✅ **Sees actual output** - errors, logs, database queries
- ✅ **Tests in real environment** - real hardware, real services
- ✅ **Debugs with breakpoints** - inspect variables, step through code
- ✅ **Views the web UI** - test frontend changes immediately
- ✅ **Monitors services** - systemd status, log files, resource usage
- ✅ **Queries database** - see actual alert data, verify changes
- ✅ **Iterates instantly** - make changes, test, fix, repeat

### How It Works

```
┌─────────────────────────────────────────────────────────┐
│  Your Computer (Windows/Mac/Linux)                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │  IDE (PyCharm / VS Code)                         │  │
│  │  • You edit code                                 │  │
│  │  • zencoder.ai suggests changes                  │  │
│  │  • Changes sync to server instantly              │  │
│  └──────────────────┬───────────────────────────────┘  │
│                     │ SSH Connection                    │
│                     │ (encrypted tunnel)                │
└─────────────────────┼───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Linux Server / Raspberry Pi                            │
│  ┌──────────────────────────────────────────────────┐  │
│  │  /opt/eas-station/                               │  │
│  │  • Code runs HERE                                │  │
│  │  • zencoder.ai executes commands HERE            │  │
│  │  • Debugger attaches HERE                        │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  PostgreSQL Database                             │  │
│  │  • zencoder.ai queries HERE                      │  │
│  │  • See real alert data                           │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Web Server (Nginx → Gunicorn → Flask)          │  │
│  │  • Access at https://your-server-ip              │  │
│  │  • zencoder.ai can test UI changes               │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Systemd Services                                │  │
│  │  • eas-station-web, audio, pollers, etc.        │  │
│  │  • zencoder.ai can restart and monitor          │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Key Insight**: Your code doesn't run on your local machine - it runs on the Linux server via SSH. This means zencoder.ai can access everything: real hardware, live database, running services, log files, and more!

---

## What You'll Learn

By the end of this guide, you'll have configured:

1. **SSH Remote Development** - Edit code locally, run it on the server
2. **Python Remote Interpreter** - Execute Python code on the server from your IDE
3. **Database Access** - Connect to PostgreSQL from multiple tools
4. **Web UI Testing** - Access the EAS Station web interface
5. **Remote Debugging** - Set breakpoints, inspect variables, step through code
6. **Service Management** - Start/stop/restart systemd services
7. **Log Monitoring** - View real-time service logs
8. **zencoder.ai Integration** - Enable AI assistant to do all of the above

This is a **production-grade development setup** used by professional developers. You'll learn skills that apply to any remote development project, not just EAS Station.

---

---

## Part 1: Setting Up Your IDE (PyCharm or VS Code)

This section will help you choose and configure your IDE for remote development. Both PyCharm Professional and VS Code work excellently - choose based on your preference.

### Step 1.1: Choose Your IDE

#### Option A: VS Code (Recommended for Beginners - FREE)

**Why VS Code?**
- ✅ Completely free, no license needed
- ✅ Fast and lightweight
- ✅ Excellent remote SSH support
- ✅ Great Python support with extensions
- ✅ Works on Windows, Mac, Linux
- ✅ Perfect for zencoder.ai integration

**Get it**: Download from [https://code.visualstudio.com/](https://code.visualstudio.com/)

#### Option B: PyCharm Professional (Best for Python - FREE for Open Source)

**Why PyCharm Professional?**
- ✅ Best-in-class Python IDE
- ✅ Powerful debugging and refactoring
- ✅ Database tools built-in (DataGrip)
- ✅ **Free with open source license**

**Get it free for open source**:

Since `eas-station` is an open source project under AGPL-3.0, you qualify for a free license:

1. Go to: [JetBrains Open Source License Application](https://www.jetbrains.com/community/opensource/#support)
2. Click **Apply Now**
3. Fill out the form:
   - **Project Name**: EAS Station
   - **Project URL**: `https://github.com/KR8MER/eas-station`
   - **License Type**: AGPL-3.0
   - **Your Role**: Contributor or Maintainer
4. JetBrains typically responds within a few days

While waiting for approval, use the [30-day free trial](https://www.jetbrains.com/pycharm/download/) or start with VS Code.

**⚠️ Don't Use PyCharm Community Edition** - It lacks remote SSH development features required for this workflow.

---

### Step 1.2: Configure VS Code for Remote Development

**Follow these steps if you chose VS Code:**

#### Install Required Extensions

1. **Open VS Code**
2. Click the **Extensions** icon in the left sidebar (or press `Ctrl+Shift+X` / `Cmd+Shift+X`)
3. Search for and install these extensions:
   - **Remote - SSH** (by Microsoft) - Essential for remote development
   - **Python** (by Microsoft) - Python language support
   - **PostgreSQL** (by Chris Kolkman) - Database management (optional but helpful)

#### Connect to Your Server

1. **Press `F1`** (or `Ctrl+Shift+P` / `Cmd+Shift+P`) to open the command palette
2. Type: `Remote-SSH: Connect to Host` and press Enter
3. Type: `eas-station@YOUR_SERVER_IP` 
   - Replace `YOUR_SERVER_IP` with your server's IP address (e.g., `192.168.1.100`)
   - If you don't know your server's IP, see [Finding Your Server IP](#finding-your-server-ip) below
4. Press Enter
5. Select the platform: **Linux**
6. Enter your password when prompted
7. Wait for VS Code to connect (this may take 30-60 seconds the first time)

#### Open the EAS Station Directory

1. Once connected, click **File** → **Open Folder**
2. Type or navigate to: `/opt/eas-station`
3. Click **OK**
4. Enter your password again if prompted

#### Configure Python Interpreter

1. **Press `Ctrl+Shift+P` / `Cmd+Shift+P`** to open command palette
2. Type: `Python: Select Interpreter`
3. Choose: `/opt/eas-station/venv/bin/python` (the virtual environment Python)
   - If you don't see it, click **Enter interpreter path** and type it manually

**✅ VS Code is now configured!** Skip to [Part 2](#part-2-enabling-zenco derai-to-run-code).

---

### Step 1.3: Configure PyCharm Professional for Remote Development

**Follow these steps if you chose PyCharm:**

#### Set Up SSH Deployment

1. **Open PyCharm** and create a new project or open an existing one
2. Go to: **File** → **Settings** (Windows/Linux) or **PyCharm** → **Preferences** (Mac)
3. Navigate to: **Build, Execution, Deployment** → **Deployment**
4. Click the **+** button and select **SFTP**
5. Name it: `EAS Station Server`
6. Configure the **Connection** tab:
   - **Type**: SFTP
   - **Host**: Your server's IP address (e.g., `192.168.1.100`)
   - **Port**: `22`
   - **Username**: `eas-station` (or `pi` if on Raspberry Pi)
   - **Auth type**: Password
   - **Password**: Your server password (save it)
   - Click **Test Connection** - you should see "Successfully connected"
7. Configure the **Mappings** tab:
   - **Local path**: Your local project folder (can be empty for now)
   - **Deployment path**: `/opt/eas-station`
   - **Web path**: (leave empty)
8. Click **OK**

#### Set Up SSH Interpreter

1. Go to: **File** → **Settings** → **Project** → **Python Interpreter**
2. Click the **gear icon** ⚙️ → **Add...**
3. Select **SSH Interpreter**
4. Choose **Existing server configuration** and select the server you just created
5. Click **Next**
6. Set the interpreter path: `/opt/eas-station/venv/bin/python`
7. Configure sync folders:
   - **Local**: Your project folder
   - **Remote**: `/opt/eas-station`
8. Click **Finish**
9. Wait for PyCharm to sync files and index the project (this can take 2-5 minutes)

**✅ PyCharm is now configured!** Continue to Part 2.

---

### Finding Your Server IP

**If you don't know your server's IP address:**

Connect to the server directly (keyboard + monitor, or existing SSH) and run:

```bash
hostname -I
```

You'll see output like: `192.168.1.100 172.17.0.1`

The first IP address (e.g., `192.168.1.100`) is your server's local network IP.

**Write this down** - you'll need it throughout this guide!

---

## Prerequisites

### What You Need Before Starting

**On the Linux Server (Raspberry Pi or Debian/Ubuntu):**
- EAS Station installed via bare metal installation (`install.sh`)
- SSH server enabled
- Installation directory: `/opt/eas-station`
- Services running via systemd
- Network connection (same network as your computer, or internet-accessible)

**On Your Development Computer (Windows/Mac/Linux):**
- PyCharm Professional OR VS Code (we'll help you choose)
- Network access to the Linux server
- SSH client (built into modern Windows, Mac, and Linux)
- Web browser (for accessing the UI)

**If You Haven't Installed EAS Station Yet:**

```bash
# On the Linux server:
cd ~/
git clone https://github.com/KR8MER/eas-station.git
cd eas-station
sudo ./install.sh
```

See [QUICKSTART-BARE-METAL.md](../QUICKSTART-BARE-METAL.md) for detailed installation instructions.

### Skill Level

**Don't worry if you're new to this!** This guide is designed for beginners and will explain:
- How SSH works and how to use it
- How to connect to a remote server
- How to use an IDE with remote development
- How to access databases remotely
- How to configure debugging tools

If you can follow step-by-step instructions, you can do this!

---

## Part 2: Enabling zencoder.ai to Run Code

Now that your IDE is connected to the server, let's configure zencoder.ai to have **complete access** to execute commands, run Python code, and manage the system.

### Step 2.1: Understanding How zencoder.ai Works with Your IDE

**Let me explain what's happening:**

When you installed VS Code or PyCharm and connected it to your server via SSH:
- Your IDE is now a "remote control" for the server
- When you open a file in the IDE, you're editing a file **on the server**, not your local computer
- When you run code, it runs **on the server**
- When zencoder.ai suggests code changes, those changes happen **on the server**

Think of it like this:
```
Your Computer                    The Server (Raspberry Pi)
┌─────────────┐                 ┌──────────────────────┐
│   Your IDE  │  SSH Connection │  EAS Station Files   │
│  (VSCode or │────────────────>│  /opt/eas-station/   │
│  PyCharm)   │    (encrypted)  │                      │
│             │                 │  Python runs HERE    │
│ zencoder.ai │────────────────>│  Database is HERE    │
│ sends       │                 │  Redis is HERE       │
│ commands    │                 │  Services run HERE   │
└─────────────┘                 └──────────────────────┘
```

**Why this matters:**
- zencoder.ai can see everything on the server (files, databases, logs, services)
- zencoder.ai can run commands as if it's logged into the server directly
- Changes happen instantly - no "upload" or "deploy" step needed

Now let's give zencoder.ai permission to do everything!

### Step 2.2: Grant sudo Permissions for Service Management

**What are we doing here?**

The EAS Station runs as several "services" (background programs) managed by systemd. To let zencoder.ai restart services, view logs, and manage the system, we need to give special permissions.

Normally, when you want to do system administration tasks, Linux asks for your password (that's what `sudo` does - it means "run this as the administrator"). But we want zencoder.ai to do these things automatically without stopping to ask for a password every time.

**Let's set this up step by step:**

#### Step A: Connect to Your Server

Open a terminal on your computer:
- **Windows**: Press `Win+R`, type `cmd`, press Enter
- **Mac**: Press `Cmd+Space`, type `terminal`, press Enter  
- **Linux**: Press `Ctrl+Alt+T`

Then connect to your server:

```bash
ssh eas-station@YOUR_SERVER_IP
```

Replace `YOUR_SERVER_IP` with the actual IP (like `192.168.1.100`).

**What you'll see:**
```
eas-station@192.168.1.100's password:
```

Type your password (you won't see it as you type - that's normal for security) and press Enter.

**You're now connected!** You'll see something like:
```
eas-station@raspberrypi:~$
```

This is the server's command prompt. Any commands you type now run on the server.

#### Step B: Edit the Permissions File

Now we'll edit the "sudoers" file - this controls who can do what on the system.

Type this command:

```bash
sudo visudo
```

Press Enter. You'll see a text file open up in a text editor called `nano`.

**Understanding what you see:**

You'll see a file with lots of comments (lines starting with `#`). Don't worry about those - we're just adding to the end.

#### Step C: Add the New Permissions

**Use your arrow keys** to scroll to the very bottom of the file.

**Copy and paste these lines** at the end (or type them carefully):

```bash
# ==============================================================================
# EAS STATION PERMISSIONS FOR ZENCODER.AI
# ==============================================================================
# These permissions allow the eas-station user (and zencoder.ai working
# through your IDE) to manage services, view logs, and access system resources
# WITHOUT needing to type a password every time.
#
# This is safe because:
# - Only the eas-station user has these permissions
# - Commands are restricted to specific programs
# - Access requires SSH authentication first
# ==============================================================================

# -------------------- Service Management --------------------
# Start, stop, restart EAS Station services
eas-station ALL=(ALL) NOPASSWD: /bin/systemctl start eas-station*
eas-station ALL=(ALL) NOPASSWD: /bin/systemctl stop eas-station*
eas-station ALL=(ALL) NOPASSWD: /bin/systemctl restart eas-station*
eas-station ALL=(ALL) NOPASSWD: /bin/systemctl reload eas-station*
eas-station ALL=(ALL) NOPASSWD: /bin/systemctl status eas-station*
eas-station ALL=(ALL) NOPASSWD: /bin/systemctl daemon-reload
eas-station ALL=(ALL) NOPASSWD: /bin/systemctl edit eas-station*
eas-station ALL=(ALL) NOPASSWD: /bin/systemctl revert eas-station*
eas-station ALL=(ALL) NOPASSWD: /bin/systemctl list-units eas-station*
eas-station ALL=(ALL) NOPASSWD: /bin/systemctl list-dependencies eas-station*

# -------------------- Log Viewing --------------------
# View service logs (essential for debugging)
eas-station ALL=(ALL) NOPASSWD: /bin/journalctl -u eas-station*
eas-station ALL=(ALL) NOPASSWD: /bin/journalctl *
eas-station ALL=(ALL) NOPASSWD: /usr/bin/tail /var/log/*
eas-station ALL=(ALL) NOPASSWD: /usr/bin/less /var/log/*
eas-station ALL=(ALL) NOPASSWD: /usr/bin/cat /var/log/*

# -------------------- System Monitoring --------------------
# Check what's running, network connections, resource usage
eas-station ALL=(ALL) NOPASSWD: /bin/netstat
eas-station ALL=(ALL) NOPASSWD: /bin/ss
eas-station ALL=(ALL) NOPASSWD: /usr/bin/lsof
eas-station ALL=(ALL) NOPASSWD: /usr/bin/ps
eas-station ALL=(ALL) NOPASSWD: /usr/bin/top
eas-station ALL=(ALL) NOPASSWD: /usr/bin/htop

# -------------------- Database Access --------------------
# Connect to PostgreSQL database
eas-station ALL=(ALL) NOPASSWD: /usr/bin/psql
eas-station ALL=(ALL) NOPASSWD: /bin/su - postgres

# -------------------- Redis Access --------------------
# Access Redis (used for real-time communication between services)
eas-station ALL=(ALL) NOPASSWD: /usr/bin/redis-cli

# -------------------- File Management --------------------
# Fix file ownership and permissions if needed
eas-station ALL=(ALL) NOPASSWD: /bin/chown -R eas-station\:eas-station /opt/eas-station/*
eas-station ALL=(ALL) NOPASSWD: /bin/chmod * /opt/eas-station/*
eas-station ALL=(ALL) NOPASSWD: /bin/ls -la /opt/eas-station/*
eas-station ALL=(ALL) NOPASSWD: /usr/bin/find /opt/eas-station/*

# -------------------- Network Testing --------------------
# Test network connectivity
eas-station ALL=(ALL) NOPASSWD: /bin/ping
eas-station ALL=(ALL) NOPASSWD: /usr/bin/curl
eas-station ALL=(ALL) NOPASSWD: /usr/bin/wget
eas-station ALL=(ALL) NOPASSWD: /usr/bin/nc

# -------------------- Package Management --------------------
# Install Python packages (for dependencies)
eas-station ALL=(ALL) NOPASSWD: /opt/eas-station/venv/bin/pip install *
eas-station ALL=(ALL) NOPASSWD: /opt/eas-station/venv/bin/pip3 install *
eas-station ALL=(ALL) NOPASSWD: /usr/bin/apt-get update
eas-station ALL=(ALL) NOPASSWD: /usr/bin/apt-get install *

# -------------------- Text Editors --------------------
# Edit files (useful for quick config changes)
eas-station ALL=(ALL) NOPASSWD: /usr/bin/nano /opt/eas-station/*
eas-station ALL=(ALL) NOPASSWD: /usr/bin/vim /opt/eas-station/*
```

#### Step D: Save the File

**To save and exit:**

1. Press `Ctrl+X` (this means "exit")
2. You'll see: `Save modified buffer?` - Press `Y` for "yes"
3. You'll see the filename - just press `Enter` to confirm

**What you should see:**
```
[ Wrote 50 lines ]
```

That means it saved successfully!

#### Step E: Test the Permissions

Let's make sure it worked. Try these commands (they should NOT ask for a password):

```bash
# Check web service status
sudo systemctl status eas-station-web.service
```

Press `q` to exit when you're done reading.

```bash
# View last 10 log lines
sudo journalctl -u eas-station-web.service -n 10
```

```bash
# Test Redis connection
sudo redis-cli ping
```

You should see: `PONG`

**If any command asks for a password**, something went wrong. Double-check the sudoers file by running `sudo visudo` again.

**✅ If no passwords were requested, you're done with this step!**

### Step 2.3: Install Python Debugging Support (debugpy)

**What is debugpy?**

`debugpy` is a tool that lets you pause your running code at specific lines (called "breakpoints") and look inside to see:
- What values variables have
- What the program is doing at that exact moment
- Where errors are happening

Think of it like pausing a video to examine a single frame - except you're pausing your code!

**Let's install it:**

In your SSH session (or in your IDE's terminal), run:

```bash
# Install debugpy into the EAS Station virtual environment
sudo -u eas-station /opt/eas-station/venv/bin/pip install debugpy
```

**What this command does:**
- `sudo -u eas-station` = Run as the eas-station user
- `/opt/eas-station/venv/bin/pip` = Use the Python package installer from the virtual environment
- `install debugpy` = Install the debugpy package

You'll see output like:
```
Collecting debugpy
  Downloading debugpy-1.8.0-cp311-cp311-linux_armv7l.whl (3.4 MB)
Installing collected packages: debugpy
Successfully installed debugpy-1.8.0
```

**Verify it installed correctly:**

```bash
sudo -u eas-station /opt/eas-station/venv/bin/python -c "import debugpy; print('✅ debugpy installed successfully')"
```

You should see: `✅ debugpy installed successfully`

**✅ Great! Now your server can support debugging.**

---

### Step 2.4: Understanding Breakpoints (What They Are and How to Use Them)

**What is a breakpoint?**

Imagine you're reading a recipe while cooking, but you want to pause after step 3 to check if the sauce looks right. A breakpoint is like putting a bookmark at step 3 - the program will run normally until it hits that line, then it **stops and waits** for you to look around.

**Why are breakpoints useful?**

Instead of adding `print()` statements everywhere to see what's happening, you can:
1. Set a breakpoint on the line you're curious about
2. Run the program
3. When it hits that line, everything pauses
4. You can examine all variables, see the call stack, and step through code line by line

**Real example:**

Let's say you have this code:
```python
def calculate_alert_priority(alert):
    severity = alert.get('severity')  # ← Set breakpoint here
    urgency = alert.get('urgency')
    priority = severity * urgency
    return priority
```

If you set a breakpoint on line 2 (where the arrow is), when the function runs:
1. The program will run normally until it reaches that line
2. **Everything stops** - the function hasn't finished yet
3. You can now inspect:
   - What is `alert`? (maybe it's `{'severity': 3, 'urgency': 2}`)
   - What is `severity`? (maybe it's `3`)
   - You can even change the values and see what happens!
4. Then you can "step" to the next line and watch `urgency` get set
5. Continue stepping to see `priority` calculated

**How to set a breakpoint:**

**In VS Code:**
- Click in the left margin (the gray area left of the line numbers) next to any line
- A red dot appears = breakpoint is set
- Click again to remove it

**In PyCharm:**
- Click in the left margin next to any line
- A red dot appears = breakpoint is set  
- Click again to remove it

**What happens when code hits a breakpoint:**

Your IDE will highlight the current line in yellow and show you:
- **Variables panel** - see all current variable values
- **Call stack** - how did we get to this line? What functions called what?
- **Debug console** - type Python commands to explore

**Debugger controls (buttons you'll see):**

- **Continue (▶️)** - Resume running until next breakpoint
- **Step Over (⤵️)** - Execute this line and go to the next line in this function
- **Step Into (⬇️)** - If this line calls a function, go inside that function
- **Step Out (⬆️)** - Finish this function and return to the caller
- **Stop (⏹️)** - Stop debugging completely

**A simple analogy:**

Think of debugging like watching a movie:
- **Normal running** = Watching the movie at normal speed
- **Breakpoint** = Pausing at a specific scene
- **Step Over** = Advance one frame (but don't go into flashbacks)
- **Step Into** = Jump into a flashback scene to see details
- **Step Out** = Exit the flashback and return to main story
- **Continue** = Resume playing until next pause point

**We'll set up actual debugging in Part 5**, but now you understand what it means!

### Step 2.4: Configure Redis Access

**What is Redis?**

Redis is like a super-fast sticky note board that the EAS Station services use to talk to each other in real-time. For example:
- The audio service writes: "I'm processing an alert right now"
- The web service reads: "Oh, there's an alert being processed - show that on the dashboard"

For zencoder.ai to see what services are doing, it needs to read these "sticky notes."

**Let's set it up:**

#### Step A: Check Redis is Running

```bash
sudo systemctl status redis-server
```

You should see `Active: active (running)` in green. If not, start it:

```bash
sudo systemctl start redis-server
```

#### Step B: Test the Connection

```bash
redis-cli ping
```

You should see: `PONG`

This is like knocking on a door and hearing someone answer - Redis is alive and responding!

#### Step C: Explore What's in Redis

**See all the "keys" (sticky notes) currently stored:**

```bash
redis-cli --scan
```

You might see output like:
```
eas-audio-metrics
eas-sdr-status
eas-current-alert
eas-service-health
```

These are the different pieces of information services are sharing.

**View a specific piece of information:**

```bash
# See audio service metrics
redis-cli GET eas-audio-metrics
```

You might see JSON data like:
```json
{"service":"audio","status":"running","last_check":"2025-01-15T10:30:00Z"}
```

**Monitor Redis in real-time (see all commands as they happen):**

```bash
redis-cli monitor
```

Now Redis will show you every command as services communicate:
```
1642234567.890123 [0 127.0.0.1:45678] "SET" "eas-audio-metrics" "{...}"
1642234568.123456 [0 127.0.0.1:45679] "GET" "eas-audio-metrics"
```

This is incredibly useful for debugging! You can see exactly what services are saying to each other.

Press `Ctrl+C` to stop monitoring.

#### Step D: Useful Redis Commands for Debugging

```bash
# List all keys
redis-cli KEYS '*'

# Get a value
redis-cli GET key-name

# Delete a key (if testing)
redis-cli DEL key-name

# See how long until a key expires
redis-cli TTL key-name

# Get info about Redis itself
redis-cli INFO

# See how many keys exist
redis-cli DBSIZE
```

**✅ Now zencoder.ai can monitor Redis to understand service communication!**

### Step 2.5: Test Code Execution with zencoder.ai

Now let's verify zencoder.ai can execute code. This is where everything comes together!

#### Step A: Open Your IDE's Terminal

**In VS Code:**
- Press `` Ctrl+` `` (that's Ctrl and the backtick key, usually above Tab)
- OR click **Terminal** → **New Terminal** from the menu

**In PyCharm:**
- Click **View** → **Tool Windows** → **Terminal**
- OR click the **Terminal** tab at the bottom of the window

**Important:** The terminal should show you're connected to the **server**, not your local computer.

You should see:
```bash
eas-station@raspberrypi:/opt/eas-station$
```

NOT:
```bash
C:\Users\YourName>           # ← This would be Windows local
yourname@yourlaptop:~$       # ← This would be Linux/Mac local
```

If you see your local computer's prompt, you need to reconnect to the server in your IDE.

#### Step B: Verify Python Environment

Let's check that Python is set up correctly:

```bash
# 1. Check which Python we're using
which python
```

**Expected output:** `/opt/eas-station/venv/bin/python`

If you see `/usr/bin/python` or something else, the virtual environment isn't activated. Run:
```bash
source /opt/eas-station/venv/bin/activate
```

You should now see `(venv)` at the start of your prompt:
```bash
(venv) eas-station@raspberrypi:/opt/eas-station$
```

#### Step C: Test Basic Python Execution

```bash
# 2. Run a simple Hello World
python -c "print('✅ Hello from EAS Station!')"
```

**What this does:**
- `python` = Run the Python interpreter
- `-c` = Execute the following code as a command
- The text in quotes is Python code

**Expected output:** `✅ Hello from EAS Station!`

#### Step D: Test Flask (The Web Framework)

```bash
# 3. Verify Flask is available
python -c "from flask import Flask; print('✅ Flask is ready')"
```

**Expected output:** `✅ Flask is ready`

If you see an error like `ModuleNotFoundError: No module named 'flask'`, the virtual environment isn't activated properly.

#### Step E: Test Database Connection Library

```bash
# 4. Verify database library
python -c "import psycopg2; print('✅ Database library available')"
```

**Expected output:** `✅ Database library available`

#### Step F: Test Service Status

```bash
# 5. Check all EAS Station services
sudo systemctl status eas-station.target
```

**What you should see:**
```
● eas-station.target - EAS Station Services
     Loaded: loaded
     Active: active
```

And a list of services:
```
● eas-station-web.service          - EAS Station Web Service
● eas-station-audio.service        - EAS Station Audio Service
● eas-station-noaa-poller.service  - NOAA Weather Alert Poller
...
```

Press `q` to quit.

#### Step G: View Recent Logs

```bash
# 6. See what the web service has been doing
sudo journalctl -u eas-station-web.service -n 20
```

**What this does:**
- `journalctl` = View system logs
- `-u eas-station-web.service` = Filter to just this service
- `-n 20` = Show the last 20 lines

You'll see log entries like:
```
Jan 15 10:30:00 raspberrypi gunicorn[1234]: [INFO] Starting gunicorn 21.2.0
Jan 15 10:30:01 raspberrypi gunicorn[1234]: [INFO] Listening at: http://0.0.0.0:5000
```

#### Step H: Test Redis

```bash
# 7. Verify Redis responds
redis-cli ping
```

**Expected output:** `PONG`

#### Step I: List Running Python Processes

```bash
# 8. See all Python programs currently running
ps aux | grep python
```

You'll see output like:
```
eas-station  1234  0.5  2.1  123456  54321 ?  Ss  10:30  0:02 /opt/eas-station/venv/bin/python /opt/eas-station/app.py
eas-station  1235  0.3  1.8  111222  33444 ?  Ss  10:30  0:01 /opt/eas-station/venv/bin/python /opt/eas-station/eas_monitoring_service.py
```

This shows you which Python programs are running and using how much CPU and memory.

#### Step J: Test zencoder.ai Can Run These Commands

Now, the moment of truth! Ask zencoder.ai to run one of these commands. For example, in your IDE, you might say:

> "zencoder.ai, can you check the status of the web service?"

zencoder.ai should be able to run:
```bash
sudo systemctl status eas-station-web.service
```

And report back what it found!

**✅ If all these commands worked, zencoder.ai now has full code execution access!**

#### What Just Happened?

You've proven that:
1. ✅ Your IDE's terminal connects to the server
2. ✅ Python works in the virtual environment
3. ✅ Flask and database libraries are available
4. ✅ Services can be checked without passwords
5. ✅ Logs can be viewed
6. ✅ Redis responds
7. ✅ System processes can be inspected

This means zencoder.ai can now:
- Run Python code
- Check if services are working
- Read logs to diagnose problems
- Query Redis
- Monitor system resources

**Next, we'll set up database access so zencoder.ai can query actual alert data!**

---

## Part 3: Database Access for zencoder.ai

The EAS Station stores all alert data in a PostgreSQL database with PostGIS spatial extensions. This section will show you how to let zencoder.ai query the database, view alert data, check geographic data, and understand database transactions.

### Step 3.1: Understanding the Database Setup

**What is the database storing?**

The EAS Station database contains:
- **Alert data** - Every emergency alert received (weather warnings, AMBER alerts, etc.)
- **Geographic boundaries** - County and state boundaries for targeting alerts
- **System configuration** - Settings, user accounts, API keys
- **Historical logs** - Past alerts, broadcast history, verification data

**Database Details:**
- **Database Name**: `alerts`
- **Database User**: `eas_station`
- **Database Location**: Running on the server at `localhost:5432`
- **Type**: PostgreSQL 17 with PostGIS 3.4 (spatial/geographic features)

### Step 3.2: Find Your Database Password

The database password was auto-generated during installation and stored in the `.env` file.

**In your IDE terminal, run:**

```bash
# View the database password
grep POSTGRES_PASSWORD /opt/eas-station/.env
```

**Expected output:**
```
POSTGRES_PASSWORD=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

**Copy this password** - you'll need it multiple times. Save it somewhere safe (like a password manager or secure note).

**Understanding the .env file:**

The `.env` file contains all sensitive configuration:
- Database passwords
- Secret keys for encryption
- API keys
- Domain names

**⚠️ Important:** Never commit the `.env` file to Git - it contains secrets!

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
# ⚠️ SECURITY WARNING: Using 0.0.0.0 exposes debug port to all network interfaces
# - Debug ports allow ARBITRARY CODE EXECUTION - attackers can run any Python code
# - Only use 0.0.0.0 on isolated/trusted networks (never public internet)
# - For local debugging only, use 127.0.0.1:5678 instead
# - For remote debugging, use SSH port forwarding (see below) to keep ports local
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

**⚠️ CRITICAL SECURITY WARNING**: 
- **Debug ports allow ARBITRARY CODE EXECUTION** - anyone who can connect can run any Python code on your server
- **NEVER expose debug ports to the public internet**
- Only enable on isolated/trusted networks (e.g., home LAN, private VPN)
- **Preferred approach**: Use SSH port forwarding (see below) instead of opening firewall ports
- If you must open firewall ports, restrict by source IP using ufw: `sudo ufw allow from 192.168.1.50 to any port 5678`

### SSH Port Forwarding (Secure Remote Debugging)

**RECOMMENDED**: Instead of opening firewall ports, use SSH tunneling:

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
