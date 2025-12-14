# VSCode Debugging Guide for AI Agents (GitHub Copilot)

This guide explains how GitHub Copilot (and other AI coding assistants) can help you debug the EAS Station system in VSCode, including setting up Redis, PostgreSQL, and all services.

## Prerequisites

Before starting, you need:
- **VSCode** installed on your local machine
- **Remote-SSH extension** installed in VSCode
- **EAS Station** installed on a Linux server (Raspberry Pi, Debian, Ubuntu)
- **SSH access** to the server with the `eas-station` user account

## Quick Start for Copilot-Assisted Debugging

### Step 1: Connect VSCode to Your Server

1. **Install Remote-SSH Extension**:
   - Press `Ctrl+Shift+X` (Extensions)
   - Search for "Remote - SSH" by Microsoft
   - Click Install

2. **Connect to Server**:
   - Press `F1` and type "Remote-SSH: Connect to Host"
   - Enter: `eas-station@YOUR_SERVER_IP` (e.g., `eas-station@192.168.1.100`)
   - Select "Linux" as the platform
   - Enter your password

3. **Open the Project**:
   - Once connected, File → Open Folder
   - Navigate to `/opt/eas-station`
   - Click OK

### Step 2: Configure Python Interpreter

1. Press `Ctrl+Shift+P` and type "Python: Select Interpreter"
2. Choose `/opt/eas-station/venv/bin/python`
3. If not listed, click "Enter interpreter path" and type it manually

### Step 3: Install Required VSCode Extensions

With Remote-SSH connected, install these extensions on the server:
- **Python** (by Microsoft) - Python language support
- **Python Debugger** (by Microsoft) - Debugging support
- **PostgreSQL** (by Chris Kolkman) - Database viewer
- **Redis** (by Dunn) - Redis client

## How Copilot Can Help with Debugging

As GitHub Copilot, I can help you in several ways, but **I cannot execute commands directly**. Instead, I:

1. **✅ Suggest commands** you can copy and paste
2. **✅ Analyze code** and point out potential issues
3. **✅ Explain errors** from logs you share
4. **✅ Generate debugging configurations** for VSCode
5. **✅ Suggest breakpoint locations** for specific issues
6. **❌ Cannot run commands** - You need to execute them in the terminal

## Service Architecture Quick Reference

The EAS Station runs as multiple systemd services:

```
┌─────────────────────────────────────────┐
│  EAS Station Services                   │
│                                         │
│  eas-station-web.service       (5000)  │  ← Web UI & API
│  eas-station-audio.service             │  ← Audio monitoring
│  eas-station-sdr.service               │  ← SDR hardware
│  eas-station-noaa-poller.service       │  ← NOAA polling
│  eas-station-ipaws-poller.service      │  ← IPAWS polling
│  eas-station-eas.service               │  ← EAS processing
│  eas-station-hardware.service          │  ← GPIO/displays
│                                         │
│  Dependencies:                          │
│  - PostgreSQL (localhost:5432)         │
│  - Redis (localhost:6379)              │
└─────────────────────────────────────────┘
```

## Debugging Workflow for Copilot Users

### Example 1: Debugging a Service Crash

**You**: "The audio service is crashing. Help me debug it."

**Copilot suggests**:
```bash
# Step 1: Check service status
sudo systemctl status eas-station-audio.service

# Step 2: View recent logs
sudo journalctl -u eas-station-audio.service -n 50

# Step 3: Look for errors
sudo journalctl -u eas-station-audio.service | grep -i error
```

**You**: Run these commands in VSCode terminal and share the output.

**Copilot analyzes**: "The error shows a Redis connection failure on line 234 of `eas_monitoring_service.py`. Let's check if Redis is running."

**Copilot suggests**:
```bash
# Check if Redis is running
sudo systemctl status redis-server

# If not running, start it
sudo systemctl start redis-server

# Restart audio service
sudo systemctl restart eas-station-audio.service
```

### Example 2: Setting Up Debugging with Breakpoints

**You**: "I want to debug the NOAA poller with breakpoints"

**Copilot creates** a launch configuration for you:

1. Create `.vscode/launch.json` in the project:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Attach to NOAA Poller",
            "type": "debugpy",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5680
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/opt/eas-station"
                }
            ]
        }
    ]
}
```

**Copilot suggests** running the service with debugpy:
```bash
# Stop the systemd service
sudo systemctl stop eas-station-noaa-poller.service

# Run with debugpy
sudo -u eas-station /opt/eas-station/venv/bin/python -m debugpy \
    --listen 0.0.0.0:5680 --wait-for-client \
    /opt/eas-station/poller/noaa_poller.py
```

**You**: Run the command, then press `F5` in VSCode to attach the debugger.

### Example 3: Checking Database State

**You**: "How many alerts are in the database?"

**Copilot suggests**:
```bash
# Connect to PostgreSQL
sudo -u postgres psql -d alerts

# Then run this SQL query:
SELECT COUNT(*) FROM cap_alerts;

# Or run directly:
sudo -u postgres psql -d alerts -c "SELECT COUNT(*) FROM cap_alerts;"
```

### Example 4: Monitoring Redis

**You**: "What's in Redis right now?"

**Copilot suggests**:
```bash
# List all keys
redis-cli KEYS '*'

# Get a specific value
redis-cli GET eas-audio-metrics

# Monitor Redis in real-time (see all commands)
redis-cli MONITOR
```

## Setting Up Each Component for Debugging

### PostgreSQL Database Access

**Check if PostgreSQL is running**:
```bash
sudo systemctl status postgresql
```

**Connect to database**:
```bash
# As postgres user
sudo -u postgres psql -d alerts

# As eas_station user (needs password from .env)
psql -h localhost -U eas_station -d alerts
```

**Get database password**:
```bash
grep POSTGRES_PASSWORD /opt/eas-station/.env
```

**Useful SQL queries for debugging**:
```sql
-- Count alerts
SELECT COUNT(*) FROM cap_alerts;

-- Recent alerts
SELECT id, event, headline, sent 
FROM cap_alerts 
WHERE sent > NOW() - INTERVAL '24 hours'
ORDER BY sent DESC 
LIMIT 10;

-- Check alert status distribution
SELECT status, COUNT(*) 
FROM cap_alerts 
GROUP BY status;

-- Find problematic alerts
SELECT id, event, status, sent 
FROM cap_alerts 
WHERE status = 'Error' 
LIMIT 10;
```

### Redis Cache/Queue Access

**Check if Redis is running**:
```bash
sudo systemctl status redis-server
```

**Connect to Redis**:
```bash
redis-cli
```

**Useful Redis commands for debugging**:
```bash
# Test connection
redis-cli PING

# List all keys
redis-cli KEYS '*'

# Get a value
redis-cli GET key-name

# Monitor all Redis commands in real-time
redis-cli MONITOR

# See how many keys exist
redis-cli DBSIZE

# Delete a key (for testing)
redis-cli DEL key-name

# See time-to-live for a key
redis-cli TTL key-name
```

### Service Debugging Commands

**View all EAS Station services**:
```bash
sudo systemctl list-units 'eas-station*'
```

**Check specific service**:
```bash
sudo systemctl status eas-station-web.service
```

**View logs**:
```bash
# Last 50 lines
sudo journalctl -u eas-station-web.service -n 50

# Follow in real-time
sudo journalctl -u eas-station-web.service -f

# Since specific time
sudo journalctl -u eas-station-web.service --since "1 hour ago"

# Show only errors
sudo journalctl -u eas-station-web.service | grep -i error
```

**Restart service**:
```bash
sudo systemctl restart eas-station-web.service
```

**Stop/Start service**:
```bash
sudo systemctl stop eas-station-web.service
sudo systemctl start eas-station-web.service
```

### Environment Variables & Configuration

**View environment**:
```bash
# Get all environment variables
cat /opt/eas-station/.env

# Get specific variable
grep POSTGRES_PASSWORD /opt/eas-station/.env
```

**Check which config is active**:
```bash
# Check systemd environment
systemctl show eas-station-web.service | grep Environment
```

## VSCode Debugging Configuration

### Complete launch.json for All Services

Save this as `.vscode/launch.json`:

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
            ]
        },
        {
            "name": "Attach to Audio Service",
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
            ]
        },
        {
            "name": "Attach to NOAA Poller",
            "type": "debugpy",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5680
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/opt/eas-station"
                }
            ]
        },
        {
            "name": "Attach to SDR Service",
            "type": "debugpy",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5683
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/opt/eas-station"
                }
            ]
        },
        {
            "name": "Python: Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "/opt/eas-station"
            }
        }
    ]
}
```

### How to Use Debugging

1. **Set breakpoints**: Click left of line numbers to add red dots
2. **Start service with debugpy**:
   ```bash
   sudo systemctl stop eas-station-web.service
   sudo -u eas-station /opt/eas-station/venv/bin/python -m debugpy \
       --listen 0.0.0.0:5678 --wait-for-client \
       /opt/eas-station/app.py
   ```
3. **Attach debugger**: Press `F5` → Select "Attach to Web Service"
4. **Debug**: When code hits a breakpoint, you can inspect variables, step through code

## Useful VSCode Terminal Commands

All these commands run in the VSCode integrated terminal (`Ctrl+``):

### Check System Health
```bash
# All services status
sudo systemctl status eas-station.target

# Disk space
df -h

# Memory usage
free -h

# Check what's listening on ports
sudo netstat -tlnp | grep -E "(5000|5432|6379)"
```

### Python Environment
```bash
# Activate venv
source /opt/eas-station/venv/bin/activate

# Check Python version
python --version

# List installed packages
pip list

# Install missing package
pip install package-name
```

### File Operations
```bash
# Find files
find /opt/eas-station -name "*.py" | grep audio

# Search in files
grep -r "error_handling" /opt/eas-station --include="*.py"

# Check file permissions
ls -la /opt/eas-station/app.py

# Tail log files
tail -f /var/log/eas-station/audio.log
```

## Common Debugging Scenarios

### Scenario 1: Service Won't Start

**Problem**: Service fails to start after code changes.

**Copilot debugging approach**:
1. Check service status: `sudo systemctl status eas-station-web.service`
2. View logs: `sudo journalctl -u eas-station-web.service -n 50`
3. Look for Python syntax errors or missing imports
4. Test Python file manually: `python /opt/eas-station/app.py`
5. Check environment variables are set correctly

### Scenario 2: Database Connection Errors

**Problem**: Services can't connect to PostgreSQL.

**Copilot debugging approach**:
1. Check PostgreSQL is running: `sudo systemctl status postgresql`
2. Test connection: `psql -h localhost -U eas_station -d alerts`
3. Verify credentials in `.env` match database user
4. Check PostgreSQL logs: `sudo tail -50 /var/log/postgresql/postgresql-*-main.log`

### Scenario 3: Redis Connection Failures

**Problem**: Services report Redis connection errors.

**Copilot debugging approach**:
1. Check Redis is running: `sudo systemctl status redis-server`
2. Test connection: `redis-cli PING`
3. Check if port 6379 is listening: `sudo netstat -tlnp | grep 6379`
4. Verify Redis is configured to accept connections from localhost

### Scenario 4: SDR Device Not Found

**Problem**: "SoapySDR::Device::make() no match" error.

**Copilot debugging approach**:
1. Check SoapySDR installation: `SoapySDRUtil --info`
2. List devices: `SoapySDRUtil --find`
3. Check Python bindings: `python -c "import SoapySDR; print(SoapySDR.getAPIVersion())"`
4. Verify PYTHONPATH includes system packages: `echo $PYTHONPATH`
5. Check service environment: `systemctl show eas-station-sdr.service | grep PYTHONPATH`

## Tips for Working with Copilot

### What to Share with Copilot

When asking for help debugging, share:
- ✅ **Error messages** from logs
- ✅ **Service status** output
- ✅ **Relevant code snippets**
- ✅ **Configuration files** (.env entries, systemd service files)
- ✅ **What you've already tried**

### How to Ask Effective Questions

❌ Bad: "It doesn't work"
✅ Good: "The audio service crashes with 'Redis connection refused'. Here's the log output: [paste logs]"

❌ Bad: "Fix the database"
✅ Good: "I'm getting 'password authentication failed' when connecting to PostgreSQL. Here's my .env config (credentials removed): [paste config]"

### Workflow Example

**You**: "The NOAA poller is timing out"

**Copilot**: "Let's debug this step by step. First, check the service logs:"
```bash
sudo journalctl -u eas-station-noaa-poller.service -n 100
```

**You**: [Paste log output showing timeout errors]

**Copilot**: "I see the timeout is happening at the NOAA API request. Let's test the network connection:"
```bash
# Test NOAA API connectivity
curl -v https://api.weather.gov/alerts/active

# Check DNS resolution
nslookup api.weather.gov

# Test with timeout
timeout 10 curl https://api.weather.gov/alerts/active
```

**You**: [Run commands and share results]

**Copilot**: "The API is responding but slowly. Let's increase the timeout in the code. Edit `/opt/eas-station/poller/noaa_poller.py` and change line 45 from `timeout=5` to `timeout=30`"

## Next Steps

Once you're comfortable with the basics:
1. Read the full debugging guide: `docs/guides/PYCHARM_DEBUGGING.md`
2. Explore the architecture docs: `docs/architecture/SYSTEM_ARCHITECTURE.md`
3. Check the troubleshooting guide: `docs/TROUBLESHOOTING_504_TIMEOUT.md`
4. Review the agent guidelines: `docs/development/AGENTS.md`

## Quick Reference Card

```
┌─────────────────────────────────────────────────────┐
│ ESSENTIAL COMMANDS FOR COPILOT DEBUGGING           │
├─────────────────────────────────────────────────────┤
│ Service Status:                                     │
│   sudo systemctl status eas-station-web.service    │
│                                                     │
│ View Logs:                                          │
│   sudo journalctl -u eas-station-web.service -n 50 │
│                                                     │
│ Restart Service:                                    │
│   sudo systemctl restart eas-station-web.service   │
│                                                     │
│ Check Database:                                     │
│   sudo -u postgres psql -d alerts -c "SELECT COUNT(*) FROM cap_alerts;" │
│                                                     │
│ Check Redis:                                        │
│   redis-cli PING                                    │
│                                                     │
│ Test Python:                                        │
│   source /opt/eas-station/venv/bin/activate        │
│   python -c "import app; print('OK')"              │
└─────────────────────────────────────────────────────┘
```

---

**Remember**: As GitHub Copilot, I suggest and explain - **you** execute the commands. Together, we can debug any issue!
