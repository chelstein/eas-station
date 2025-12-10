# EAS Station - Quick Start Guide (Bare Metal)

## Overview

This guide will help you install EAS Station on a bare metal Linux server. The installation takes about 10-15 minutes and will get you to a running system where you can complete configuration through the web-based setup wizard.

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

### 3. Answer the Configuration Questions

The installer will prompt you for minimal information needed to get the system running:

#### Database Password
```
Enter database password for user 'eas_station' (min 8 characters): ********
Confirm database password: ********
```
**Important**: Use a strong, unique password. This is stored locally and used for database access.

#### Timezone
```
Common US timezones:
  America/New_York (Eastern)
  America/Chicago (Central)
  America/Denver (Mountain)
  America/Los_Angeles (Pacific)

Enter your timezone [America/New_York]: America/Chicago
```

**That's it!** The installer will handle the rest.

### 4. Create Administrator Account

After the system is installed, you'll be prompted to create your administrator account:

```
Enter administrator username (min 3 characters): admin
Enter administrator password (min 12 characters): ****************
Confirm administrator password: ****************
```

**Important**: This is your web interface login. Use a strong password!

### 5. Wait for Installation to Complete

The installer will:
- ✅ Install system dependencies (PostgreSQL, Redis, Nginx, etc.)
- ✅ Create database with your password
- ✅ Set up Python virtual environment
- ✅ Install Python dependencies
- ✅ Run database migrations
- ✅ Create administrator account
- ✅ Start all services

This takes approximately **10-15 minutes** depending on your hardware and internet connection.

### 6. Access the Web Interface

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
    (This is safe - we generated it during installation)

========================================
  🔐 LOGIN CREDENTIALS
========================================

Username: admin
Password: (the password you just entered)
```

**Log in with the credentials you created.**

### 7. Complete the Setup Wizard

After logging in for the first time, you'll be guided through the **Setup Wizard** to configure:

1. **Location Settings**
   - County name
   - State code
   - FIPS codes
   - SAME/NWS zone codes

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
