# EAS Station Bare Metal - Quick Start Guide

Get EAS Station running on bare metal in 15 minutes!

## Choose Your Installation Method

### 🚀 Fast: Install on Existing System

Already have Debian/Ubuntu/Raspberry Pi OS? Start here!

```bash
# 1. Clone and install (takes 10-15 minutes)
git clone https://github.com/KR8MER/eas-station.git && \
cd eas-station/bare-metal && \
sudo bash scripts/install.sh

# 2. Access the web interface
# Open browser to https://localhost (accept self-signed cert)

# 3. Complete setup via web interface
# - Create your administrator account
# - Configure location and EAS settings
# - Done! No nano required!
```

**That's it!** The installer automatically:
- ✓ Generates a secure SECRET_KEY
- ✓ Starts all services
- ✓ Makes the web interface immediately accessible

### 💿 Clean: Bootable ISO Image

Want a dedicated system? Build an ISO!

```bash
# 1. Build ISO (takes 30-60 minutes)
cd eas-station/bare-metal
sudo bash scripts/build-iso.sh

# 2. Burn to USB
sudo dd if=eas-station-*.iso of=/dev/sdX bs=4M status=progress

# 3. Boot and follow setup wizard
```

## Post-Installation

### First-Time Setup (via Web Interface)

After installation completes, open your browser and:

1. **Navigate to** https://localhost
   - Accept the self-signed certificate warning
   
2. **Create Administrator Account**
   - Enter a username (min 3 characters)
   - Set a strong password (min 12 characters)
   
3. **Configure Your Station** (via setup wizard)
   - Location settings (county, state, zone codes)
   - Your callsign (EAS_STATION_ID)
   - Enable/disable features (SDR, broadcast, etc.)

All configuration is done through the intuitive web interface - no command-line editing required!

### Check Status

```bash
# All services
sudo systemctl status eas-station.target

# Individual services
sudo systemctl status eas-station-web.service
sudo systemctl status eas-station-sdr.service

# View logs
sudo journalctl -u eas-station-web.service -f
```

### Access Web Interface

- **Local:** https://localhost
- **Network:** https://your-ip-address
- Accept self-signed certificate (safe for testing)

## Common Tasks

### Start/Stop Services

```bash
# Start all
sudo systemctl start eas-station.target

# Stop all
sudo systemctl stop eas-station.target

# Restart all
sudo systemctl restart eas-station.target
```

### Enable Auto-Start on Boot

```bash
sudo systemctl enable eas-station.target
```

### View Logs

```bash
# Follow logs
sudo journalctl -u eas-station-web.service -f

# Last 100 lines
sudo journalctl -u eas-station-web.service -n 100

# All services
sudo journalctl -u eas-station-*.service -f
```

### Configure SSL (Production)

```bash
# Install Let's Encrypt certificate
sudo certbot --nginx -d your-domain.com

# Certificate auto-renews
```

## Troubleshooting

### Service Won't Start

```bash
# Check status
sudo systemctl status eas-station-web.service

# Check logs
sudo journalctl -u eas-station-web.service -n 50

# Check database
sudo systemctl status postgresql
sudo systemctl status redis-server
```

### Can't Access Web Interface

```bash
# Check nginx
sudo systemctl status nginx
sudo nginx -t

# Check if port is open
sudo netstat -tlnp | grep :443
```

### SDR Not Found

```bash
# Check USB device
lsusb | grep -i rtl

# Check SoapySDR
SoapySDRUtil --find

# Check service
sudo systemctl status eas-station-sdr.service
```

## Next Steps

- 📖 Read full [README](README.md) for detailed documentation
- 🔧 Configure hardware (SDR, GPIO, displays)
- 📡 Set up your location and FIPS codes
- 🔔 Enable alert broadcasting
- 🌐 Configure remote access

## Getting Help

- **Documentation:** `/opt/eas-station/docs/`
- **GitHub Issues:** https://github.com/KR8MER/eas-station/issues
- **Discussions:** https://github.com/KR8MER/eas-station/discussions

---

**73 de KR8MER** 📡
