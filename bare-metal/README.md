# EAS Station Bare Metal Deployment

This directory contains everything needed to run EAS Station on bare metal (without Docker) and to build a bootable ISO image.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Installation Methods](#installation-methods)
  - [Method 1: Install on Existing System](#method-1-install-on-existing-system)
  - [Method 2: Build and Deploy ISO](#method-2-build-and-deploy-iso)
- [Directory Structure](#directory-structure)
- [Service Management](#service-management)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Migration from Docker](#migration-from-docker)

## Overview

The bare metal deployment provides:

- **No Docker dependency** - Runs directly on the host OS
- **Native systemd services** - Standard Linux service management
- **Lower overhead** - Direct hardware access without containerization
- **Bootable ISO** - Pre-configured system ready to burn and boot
- **Production-ready** - Optimized for 24/7 operation

### System Requirements

- **OS**: Debian 12 (Bookworm), Ubuntu 22.04+, or Raspberry Pi OS
- **CPU**: 2+ cores (4+ recommended)
- **RAM**: 2GB minimum (4GB+ recommended)
- **Storage**: 20GB minimum (50GB+ recommended for alerts database)
- **Network**: Internet connection for alert polling

### Architecture Comparison

**Docker Deployment:**
```
Docker Host → Docker Engine → Containers → Services
```

**Bare Metal Deployment:**
```
Linux Host → systemd → Services
```

## Quick Start

### Prerequisites

```bash
# Debian/Ubuntu/Raspberry Pi OS
sudo apt-get update
sudo apt-get install git
```

### Installation

```bash
# Clone repository
git clone https://github.com/KR8MER/eas-station.git
cd eas-station/bare-metal

# Run installation script
sudo bash scripts/install.sh

# Edit configuration
sudo nano /opt/eas-station/.env

# Start services
sudo systemctl start eas-station.target

# Check status
sudo systemctl status eas-station.target
```

Access the web interface at: **https://localhost** (accept self-signed certificate)

## Installation Methods

### Method 1: Install on Existing System

Best for: Existing Debian/Ubuntu/Raspberry Pi OS installations

#### Step 1: Run Installation Script

```bash
cd eas-station/bare-metal
sudo bash scripts/install.sh
```

The script will:
- Install all system dependencies
- Create service user and groups
- Set up PostgreSQL database with PostGIS extensions
- Install pgAdmin 4 for database management (web UI at http://localhost/pgadmin4)
- Configure Redis
- Install Python dependencies in virtual environment
- Create systemd service files
- Configure nginx with SSL
- Generate self-signed certificate

#### Step 2: Configure

Edit the configuration file:

```bash
sudo nano /opt/eas-station/.env
```

Key settings to configure:

```bash
# Generate a secure secret key
SECRET_KEY=<run: python3 -c "import secrets; print(secrets.token_hex(32))">

# Database (default uses local PostgreSQL)
POSTGRES_HOST=localhost
POSTGRES_PASSWORD=changeme123

# Your location
DEFAULT_COUNTY_NAME=Your County
DEFAULT_STATE_CODE=OH
DEFAULT_ZONE_CODES=OHZ001,OHC001

# EAS settings
EAS_BROADCAST_ENABLED=false
EAS_ORIGINATOR=WXR
EAS_STATION_ID=YOURCALL
```

#### Step 3: Start Services

```bash
# Start all services
sudo systemctl start eas-station.target

# Enable auto-start on boot
sudo systemctl enable eas-station.target

# Check status
sudo systemctl status eas-station.target
```

#### Step 4: Access Web Interface

Open your browser to:
- **Local:** https://localhost
- **Network:** https://your-ip-address

Accept the self-signed certificate warning (safe for testing).

#### Step 5: (Optional) Configure Let's Encrypt SSL

For production with a domain name:

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com

# Certificate will auto-renew
```

### Method 2: Build and Deploy ISO

Best for: New installations, dedicated hardware, or multiple deployments

#### Step 1: Build ISO Image

On a Debian/Ubuntu build machine:

```bash
cd eas-station/bare-metal
sudo bash scripts/build-iso.sh
```

This will:
- Install build dependencies (live-build, etc.)
- Create a Debian Live system
- Pre-install all EAS Station dependencies
- Configure services for auto-start
- Build bootable ISO (20-60 minutes)

Output: `eas-station-YYYYMMDD.iso`

#### Step 2: Write ISO to USB

**Linux:**
```bash
# Find your USB device
lsblk

# Write ISO (replace /dev/sdX with your device)
sudo dd if=eas-station-*.iso of=/dev/sdX bs=4M status=progress
sync
```

**Windows:**
- Use [Rufus](https://rufus.ie/) or [Etcher](https://www.balena.io/etcher/)

**macOS:**
- Use [Etcher](https://www.balena.io/etcher/)

#### Step 3: Boot from USB

1. Insert USB drive into target system
2. Boot from USB (F12/F2/Del during boot to select)
3. System will boot into EAS Station Live environment

#### Step 4: First Boot Setup

On first boot:
- Default user: `easuser`
- Default password: `easstation` (you'll be prompted to change)
- Desktop shortcut will launch setup wizard
- Or run manually: `sudo /usr/local/bin/eas-station-setup`

#### Step 5: Configure and Run

The setup wizard will:
- Initialize database schema
- Configure services
- Start all components
- Show web interface URL

## Directory Structure

```
bare-metal/
├── README.md                          # This file
├── systemd/                           # Systemd service files
│   ├── eas-station.target            # Main target (starts all services)
│   ├── eas-station-web.service       # Web application (Flask/Gunicorn)
│   ├── eas-station-sdr.service       # SDR hardware service
│   ├── eas-station-audio.service     # Audio processing service
│   ├── eas-station-eas.service       # EAS monitoring service
│   ├── eas-station-hardware.service  # Hardware control (GPIO, displays)
│   ├── eas-station-noaa-poller.service  # NOAA alert poller
│   └── eas-station-ipaws-poller.service # IPAWS alert poller
├── config/
│   └── nginx-eas-station.conf        # Nginx reverse proxy config
└── scripts/
    ├── install.sh                     # Bare metal installation script
    └── build-iso.sh                   # ISO builder script
```

## Service Management

### Control All Services

```bash
# Start all services
sudo systemctl start eas-station.target

# Stop all services
sudo systemctl stop eas-station.target

# Restart all services
sudo systemctl restart eas-station.target

# Enable auto-start on boot
sudo systemctl enable eas-station.target

# Disable auto-start
sudo systemctl disable eas-station.target

# Check status
sudo systemctl status eas-station.target
```

### Control Individual Services

```bash
# Web application
sudo systemctl start eas-station-web.service
sudo systemctl status eas-station-web.service

# SDR hardware
sudo systemctl start eas-station-sdr.service
sudo systemctl status eas-station-sdr.service

# Audio processing
sudo systemctl start eas-station-audio.service
sudo systemctl status eas-station-audio.service

# EAS monitoring
sudo systemctl start eas-station-eas.service
sudo systemctl status eas-station-eas.service

# Hardware control
sudo systemctl start eas-station-hardware.service
sudo systemctl status eas-station-hardware.service

# Pollers
sudo systemctl start eas-station-noaa-poller.service
sudo systemctl start eas-station-ipaws-poller.service
```

### View Logs

```bash
# All services
sudo journalctl -u eas-station-*.service -f

# Specific service
sudo journalctl -u eas-station-web.service -f

# Last 100 lines
sudo journalctl -u eas-station-web.service -n 100

# Today's logs
sudo journalctl -u eas-station-web.service --since today

# Log files (also available)
sudo tail -f /var/log/eas-station/web-access.log
sudo tail -f /var/log/eas-station/web-error.log
```

## Configuration

### Main Configuration File

Location: `/opt/eas-station/.env`

```bash
# Edit configuration
sudo nano /opt/eas-station/.env

# After editing, restart services
sudo systemctl restart eas-station.target
```

### Service-Specific Settings

#### Web Application
- Port: 5000 (internal, proxied by nginx)
- Workers: 2 (adjust in service file based on CPU cores)
- Logs: `/var/log/eas-station/web-*.log`

#### Database
- PostgreSQL on localhost:5432
- Database: `alerts`
- User: `eas_station`

#### Redis
- localhost:6379
- Database: 0

#### Nginx
- HTTP: Port 80 (redirects to HTTPS)
- HTTPS: Port 443
- Config: `/etc/nginx/sites-available/eas-station`

### Hardware Permissions

The `eas-station` user is added to these groups for hardware access:

- `dialout` - Serial ports (USB, VFD display)
- `plugdev` - USB devices (SDR dongles)
- `gpio` - GPIO pins (Raspberry Pi)
- `i2c` - I2C devices (OLED displays)
- `spi` - SPI devices
- `audio` - Audio devices (ALSA)

To add additional permissions:
```bash
sudo usermod -a -G groupname eas-station
sudo systemctl restart eas-station-*.service
```

## Troubleshooting

### Services Won't Start

**Check service status:**
```bash
sudo systemctl status eas-station-web.service
```

**Check logs:**
```bash
sudo journalctl -u eas-station-web.service -n 50
```

**Common issues:**
- Database not running: `sudo systemctl start postgresql`
- Redis not running: `sudo systemctl start redis-server`
- Port already in use: Check for conflicting services
- Permission denied: Check file ownership and groups

### Database Connection Issues

**Check PostgreSQL:**
```bash
sudo systemctl status postgresql
sudo -u postgres psql -l
```

**Reset database password:**
```bash
sudo -u postgres psql
ALTER USER eas_station WITH PASSWORD 'new_password';
\q

# Update .env file
sudo nano /opt/eas-station/.env
# Change POSTGRES_PASSWORD=new_password

# Restart services
sudo systemctl restart eas-station.target
```

### Web Interface Not Accessible

**Check nginx:**
```bash
sudo systemctl status nginx
sudo nginx -t  # Test configuration
```

**Check ports:**
```bash
sudo netstat -tlnp | grep -E ':(80|443|5000)'
```

**Firewall issues:**
```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### SDR Device Not Found

**Check device connection:**
```bash
lsusb | grep -i rtl
SoapySDRUtil --find
```

**Check permissions:**
```bash
# User should be in plugdev group
groups eas-station

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

**Check service:**
```bash
sudo systemctl status eas-station-sdr.service
sudo journalctl -u eas-station-sdr.service -n 50
```

### High CPU/Memory Usage

**Check resource usage:**
```bash
htop
sudo systemctl status eas-station-*.service
```

**Adjust workers:**
```bash
# Edit web service file
sudo systemctl edit eas-station-web.service

# Add override:
[Service]
Environment="MAX_WORKERS=1"

# Restart
sudo systemctl daemon-reload
sudo systemctl restart eas-station-web.service
```

**Memory limits:**
Service files include memory limits. To adjust:
```bash
sudo systemctl edit eas-station-web.service

# Add override:
[Service]
MemoryLimit=1G

sudo systemctl daemon-reload
sudo systemctl restart eas-station-web.service
```

## Migration from Docker

### Export Configuration

From Docker installation:

```bash
# Export .env file
docker cp eas-app:/app/.env ./eas-station-config.env

# Export database (if using embedded database)
docker exec eas-alerts-db pg_dump -U postgres alerts > alerts-backup.sql
```

### Import to Bare Metal

```bash
# Copy configuration
sudo cp eas-station-config.env /opt/eas-station/.env
sudo chown eas-station:eas-station /opt/eas-station/.env

# Import database
sudo -u postgres psql alerts < alerts-backup.sql

# Restart services
sudo systemctl restart eas-station.target
```

### Uninstall Docker Version

```bash
# Stop Docker containers
cd /path/to/docker/installation
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Optionally remove Docker
sudo apt-get remove docker-ce docker-ce-cli containerd.io
```

## Performance Tuning

### For Raspberry Pi

Optimize for lower-spec hardware:

```bash
# Reduce workers
sudo systemctl edit eas-station-web.service
[Service]
Environment="MAX_WORKERS=1"

# Disable unused services
sudo systemctl disable eas-station-hardware.service  # If not using GPIO

# Adjust memory limits
sudo systemctl edit eas-station-audio.service
[Service]
MemoryLimit=256M
```

### For High-Performance Systems

Maximize performance:

```bash
# Increase workers (2-4x CPU cores)
sudo systemctl edit eas-station-web.service
[Service]
Environment="MAX_WORKERS=8"

# Increase memory limits
[Service]
MemoryLimit=2G
```

## Uninstallation

To completely remove EAS Station:

```bash
# Stop and disable services
sudo systemctl stop eas-station.target
sudo systemctl disable eas-station.target

# Remove service files
sudo rm /etc/systemd/system/eas-station*.service
sudo rm /etc/systemd/system/eas-station*.target
sudo systemctl daemon-reload

# Remove application
sudo rm -rf /opt/eas-station
sudo rm -rf /var/log/eas-station

# Remove nginx config
sudo rm /etc/nginx/sites-enabled/eas-station
sudo rm /etc/nginx/sites-available/eas-station
sudo systemctl reload nginx

# Remove database (optional)
sudo -u postgres dropdb alerts
sudo -u postgres dropuser eas_station

# Remove user
sudo userdel eas-station

# Remove packages (optional)
sudo apt-get autoremove postgresql redis-server nginx
```

## Support

- **Documentation:** https://github.com/KR8MER/eas-station/tree/main/docs
- **Issues:** https://github.com/KR8MER/eas-station/issues
- **Discussions:** https://github.com/KR8MER/eas-station/discussions

## License

Copyright (c) 2025 Timothy Kramer (KR8MER)

EAS Station is available under dual licensing:
- **Open Source:** GNU Affero General Public License v3 (AGPL-3.0)
- **Commercial:** Commercial License available

See LICENSE and LICENSE-COMMERCIAL files for details.

---

**73 de KR8MER** 📡
