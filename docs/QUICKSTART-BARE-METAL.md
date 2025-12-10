# EAS Station - Quick Start Guide (Bare Metal)

## Overview

This guide will help you install EAS Station on a bare metal Linux server. The installation is **fully automated** - you'll only need to create an administrator account, and the script handles everything else.

**Installation Time**: 10-15 minutes

## Prerequisites

- **Operating System**: Debian 11+, Ubuntu 20.04+, or Raspbian
- **Hardware**: Raspberry Pi 4/5, or any Linux server with 2GB+ RAM
- **Root Access**: You must have sudo/root access
- **Internet Connection**: Required for package installation

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/KR8MER/eas-station.git
cd eas-station
```

### 2. Run the Installation Script

```bash
sudo ./install.sh
```

### 3. Create Administrator Account

The installer will prompt you to create an administrator account:

```
Enter administrator username (min 3 characters): admin
Enter administrator password (min 12 characters): ****************
Confirm administrator password: ****************
```

**This account is used for:**
- EAS Station web interface login
- pgAdmin 4 database manager login

**That's it!** The script automatically:
- ✅ Generates a secure database password
- ✅ Creates and configures PostgreSQL database
- ✅ Installs and configures pgAdmin 4
- ✅ Sets up all system dependencies
- ✅ Runs database migrations
- ✅ Configures Nginx with SSL
- ✅ Starts all services

### 4. Wait for Installation to Complete

The installer will display progress as it:
- Installs system packages (PostgreSQL, Redis, Nginx, etc.)
- Sets up Python environment
- Configures database with auto-generated password
- Installs and configures pgAdmin 4
- Creates SSL certificate
- Starts all services

**Installation takes approximately 10-15 minutes.**

### 5. Access the Web Interface and pgAdmin

Once installation completes, you'll see:

```
========================================
  🌐 ACCESS YOUR EAS STATION
========================================

Open your web browser and navigate to:

  https://localhost
  OR
  https://192.168.1.100

⚠️  Accept the self-signed certificate warning

========================================
  🔐 LOGIN CREDENTIALS
========================================

EAS Station Web Interface:
  Username: admin
  Password: (the password you entered)

pgAdmin 4 Database Manager:
  URL: https://localhost/pgadmin4
  Email: admin@localhost
  Password: (same as above)
```

**Log in with the credentials you created.**

### 6. Complete the Setup Wizard

After logging into the EAS Station web interface, you'll see the **Setup Wizard** to configure:

1. **Location Settings**
   - County name
   - State code
   - FIPS codes
   - SAME/NWS zone codes
   - Timezone (default: America/New_York)

2. **Station Identification**
   - Your callsign or station ID
   - EAS originator code

3. **Alert Sources**
   - NOAA Weather alerts
   - IPAWS (FEMA) alerts
   - Custom CAP feeds

4. **EAS Broadcast**
   - Enable/disable audio generation
   - SAME encoding settings

5. **Hardware Integration** (Optional)
   - LED signs
   - OLED displays
   - VFD displays
   - SDR receivers
   - GPIO relays

The setup wizard provides helpful explanations and examples for each setting.

**⚠️ Important**: You do NOT need to configure database settings, SECRET_KEY, or other technical options. These were automatically configured during installation.

## Using pgAdmin 4

pgAdmin 4 is automatically installed and configured for database management:

1. **Access pgAdmin**: Navigate to `https://localhost/pgadmin4`
2. **Login**: Use your administrator email and password
3. **Add Server** (first time only):
   - Right-click "Servers" → "Register" → "Server"
   - **General tab**: Name = "EAS Station"
   - **Connection tab**:
     - Host: localhost
     - Port: 5432
     - Database: alerts
     - Username: eas_station
     - Password: (found in `/opt/eas-station/.env` as POSTGRES_PASSWORD)
   - Save password: ✓ (optional)

4. **Browse Data**: Explore tables, run queries, view alerts, etc.

## Post-Installation

### Set Up Production SSL (Recommended)

For production deployments with a domain name:

```bash
sudo certbot --nginx -d your-domain.com
```

This replaces the self-signed certificate with a trusted Let's Encrypt certificate.

## Useful Commands

### Service Management

```bash
# View all services status
sudo systemctl status eas-station.target

# Restart all services
sudo systemctl restart eas-station.target

# Stop all services
sudo systemctl stop eas-station.target

# Start all services
sudo systemctl start eas-station.target
```

### Logs

```bash
# Web service logs
sudo journalctl -u eas-station-web.service -f

# Poller service logs
sudo journalctl -u eas-station-poller.service -f

# All EAS Station logs
sudo journalctl -u eas-station.target -f
```

### Configuration

```bash
# Edit configuration file
sudo nano /opt/eas-station/.env

# After editing, restart services
sudo systemctl restart eas-station.target
```

### Database

```bash
# Access database
sudo -u postgres psql -d alerts

# Backup database
sudo -u postgres pg_dump alerts > /tmp/eas-station-backup.sql

# Restore database
sudo -u postgres psql -d alerts < /tmp/eas-station-backup.sql
```

## Troubleshooting

### Database Permission Errors

If you see `permission denied for schema public` errors:

```bash
sudo /opt/eas-station/scripts/database/fix_database_permissions.sh
sudo /opt/eas-station/scripts/database/init_database.sh
sudo systemctl restart eas-station.target
```

### Missing Tables

```bash
cd /opt/eas-station
sudo -u eas-station /opt/eas-station/venv/bin/alembic upgrade head
sudo systemctl restart eas-station.target
```

### Service Won't Start

```bash
# Check service status
sudo systemctl status eas-station-web.service

# View detailed logs
sudo journalctl -u eas-station-web.service -n 100

# Check configuration
sudo nano /opt/eas-station/.env
```

### Web Interface Not Accessible

1. **Check firewall**: Ensure port 443 (HTTPS) is open
2. **Check Nginx**: `sudo systemctl status nginx`
3. **Check certificate**: `sudo ls -l /etc/ssl/private/eas-station-selfsigned.key`

## Getting Help

- **Documentation**: https://github.com/KR8MER/eas-station/tree/main/docs
- **Issues**: https://github.com/KR8MER/eas-station/issues
- **Discussions**: https://github.com/KR8MER/eas-station/discussions

## What's Next?

Your EAS Station is now monitoring for alerts! The system will:

1. **Poll Alert Sources**: Automatically fetch CAP alerts from configured sources
2. **Process Alerts**: Filter alerts by your location (zone codes)
3. **Generate Audio**: Create SAME-encoded EAS audio (if broadcast enabled)
4. **Display Alerts**: Show active alerts on web interface and displays
5. **Trigger Outputs**: Activate GPIO relays when alerts are active

Explore the web interface to customize your station and add additional features!

---

**Installed Successfully?** ⭐ Star the repository and share your setup!
