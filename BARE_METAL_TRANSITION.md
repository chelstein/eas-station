# EAS Station - Bare Metal Transition Complete

## Summary

EAS Station has been successfully transitioned from a Docker-based application to a **bare metal-only deployment**. All Docker/container infrastructure has been removed.

## What Changed

### Removed
- ❌ All Dockerfile and docker-compose files
- ❌ Docker entrypoint scripts
- ❌ Stack.env configuration files
- ❌ Container-specific code and references
- ❌ Docker deployment documentation

### Added
- ✅ Systemd service files for all components
- ✅ Bare metal installation script with full automation
- ✅ pgAdmin 4 for database management
- ✅ Comprehensive testing guide
- ✅ Migration guide from Docker

### Updated
- ✅ All code references to use `/opt/eas-station/.env`
- ✅ Diagnostics to use systemctl and journalctl
- ✅ Error messages to reference systemd commands
- ✅ Default configuration values (localhost vs container names)
- ✅ Documentation to focus on bare metal deployment

## Version

**2.18.0** - Major feature release with breaking changes

## Installation

### Quick Start

```bash
# Clone repository
git clone https://github.com/KR8MER/eas-station.git
cd eas-station/bare-metal

# Run installation script
sudo bash scripts/install.sh

# Configure
sudo nano /opt/eas-station/.env

# Start services
sudo systemctl start eas-station.target
```

### Access Points

- **Web Interface**: https://localhost
- **pgAdmin**: http://localhost/pgadmin4
- **Health Check**: http://localhost:5000/health
- **Diagnostics**: https://localhost/diagnostics

## Service Management

### Start/Stop Services

```bash
# Start all services
sudo systemctl start eas-station.target

# Stop all services
sudo systemctl stop eas-station.target

# Restart all services
sudo systemctl restart eas-station.target

# Check status
sudo systemctl status eas-station.target
```

### View Logs

```bash
# Follow web service logs
sudo journalctl -u eas-station-web.service -f

# View last 100 lines
sudo journalctl -u eas-station-web.service -n 100

# View all services
sudo journalctl -u eas-station-*.service -f

# Check for errors
sudo journalctl -u eas-station.target -p err
```

### Enable Auto-Start

```bash
# Enable services on boot
sudo systemctl enable eas-station.target

# Verify
sudo systemctl is-enabled eas-station.target
```

## System Services

The following systemd services are installed:

1. **eas-station-web.service** - Main web application (Flask/Gunicorn)
2. **eas-station-sdr.service** - SDR hardware interface
3. **eas-station-audio.service** - Audio processing and SAME encoding
4. **eas-station-eas.service** - EAS monitoring
5. **eas-station-hardware.service** - GPIO and hardware control
6. **eas-station-noaa-poller.service** - NOAA weather alert polling
7. **eas-station-ipaws-poller.service** - IPAWS federal alert polling
8. **eas-station.target** - Main target that manages all services

## Configuration

### Location
`/opt/eas-station/.env`

### Key Settings

```bash
# Database (local PostgreSQL)
POSTGRES_HOST=localhost
POSTGRES_USER=eas_station
POSTGRES_PASSWORD=changeme123  # Change this!

# Redis (local)
REDIS_HOST=localhost

# Your location
DEFAULT_COUNTY_NAME=Your County
DEFAULT_STATE_CODE=OH
DEFAULT_ZONE_CODES=OHZ001,OHC001

# EAS settings
EAS_STATION_ID=YOURCALL
EAS_BROADCAST_ENABLED=false
```

### Applying Changes

After editing `.env`:
```bash
sudo systemctl restart eas-station.target
```

## Testing

Run the comprehensive test suite:

```bash
# Check all services
sudo systemctl status eas-station.target

# Verify database
sudo -u postgres psql -d alerts -c "SELECT PostGIS_version();"

# Test Redis
redis-cli ping

# Check web health
curl http://localhost:5000/health
```

See `bare-metal/TESTING.md` for complete testing guide.

## Database Management

### pgAdmin 4

Access pgAdmin at: http://localhost/pgadmin4

**First Time Setup**:
1. Create admin email and password
2. Add server connection:
   - Host: localhost
   - Port: 5432
   - Database: alerts
   - Username: eas_station
   - Password: (from .env file)

### Command Line

```bash
# Connect to database
sudo -u postgres psql -d alerts

# List tables
\dt

# Check PostGIS
SELECT PostGIS_version();

# Exit
\q
```

## Migration from Docker

If you have an existing Docker installation:

1. **Backup Configuration**:
   ```bash
   docker cp eas-app:/app/.env ./backup.env
   ```

2. **Backup Database**:
   ```bash
   docker exec eas-alerts-db pg_dump -U postgres alerts > backup.sql
   ```

3. **Install Bare Metal**:
   ```bash
   cd eas-station/bare-metal
   sudo bash scripts/install.sh
   ```

4. **Restore Configuration**:
   ```bash
   sudo cp backup.env /opt/eas-station/.env
   ```

5. **Restore Database**:
   ```bash
   sudo -u postgres psql alerts < backup.sql
   ```

6. **Start Services**:
   ```bash
   sudo systemctl start eas-station.target
   ```

See `bare-metal/MIGRATION_FROM_DOCKER.md` for details.

## Troubleshooting

### Service Won't Start

```bash
# Check status
sudo systemctl status eas-station-web.service

# View logs
sudo journalctl -u eas-station-web.service -n 50

# Check dependencies
sudo systemctl status postgresql redis-server
```

### Database Issues

```bash
# Check PostgreSQL
sudo systemctl status postgresql

# Test connection
PGPASSWORD=changeme123 psql -h localhost -U eas_station -d alerts -c "SELECT 1;"

# Reset password
sudo -u postgres psql -c "ALTER USER eas_station WITH PASSWORD 'newpassword';"
```

### Port Conflicts

```bash
# Check port 5000 (Flask)
sudo lsof -i :5000

# Check port 80/443 (nginx)
sudo lsof -i :80
sudo lsof -i :443
```

### Build Failures (gevent)

If you encounter "failed to build gevent" during installation:

```bash
# Install build dependencies
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    python3-dev \
    libev-dev \
    libevent-dev \
    libffi-dev \
    libssl-dev

# Retry Python package installation
sudo -u eas-station /opt/eas-station/venv/bin/pip install --upgrade pip
sudo -u eas-station /opt/eas-station/venv/bin/pip install -r /opt/eas-station/requirements.txt
```

**Note**: The installation script automatically installs these dependencies, but if you're doing a manual installation, ensure these packages are present.

## Benefits of Bare Metal

### vs Docker
- ✅ **Lower Overhead** - No container runtime
- ✅ **Direct Hardware Access** - Native SDR, GPIO, audio
- ✅ **Simpler Management** - Standard systemd commands
- ✅ **Better Performance** - No virtualization layer
- ✅ **Easier Debugging** - Direct log access with journalctl
- ✅ **Standard Linux Patterns** - Familiar to sysadmins

### Resource Usage
- No Docker daemon overhead
- Direct memory allocation (no container limits)
- Native filesystem performance
- Full CPU access without scheduling overhead

## Documentation

### Quick Reference
- **Installation**: `bare-metal/README.md`
- **Quick Start**: `bare-metal/QUICKSTART.md`
- **Testing**: `bare-metal/TESTING.md`
- **Migration**: `bare-metal/MIGRATION_FROM_DOCKER.md`

### Full Documentation
- **Main README**: `README.md`
- **Architecture**: `docs/architecture/SYSTEM_ARCHITECTURE.md`
- **Theory of Operation**: `docs/architecture/THEORY_OF_OPERATION.md`
- **Changelog**: `docs/reference/CHANGELOG.md`

## Support

- **Documentation**: https://github.com/KR8MER/eas-station/tree/main/docs
- **Issues**: https://github.com/KR8MER/eas-station/issues
- **Discussions**: https://github.com/KR8MER/eas-station/discussions

## Future Enhancements

### Planned Features
1. **Frontend Log Viewer** - View systemd logs through web UI
2. **Database User Management** - Change PostgreSQL passwords from app
3. **Frontend Overhaul** - Improved configuration interface
4. **Security Hardening** - Force default password changes

### Contributing

Contributions welcome! See:
- `docs/process/CONTRIBUTING.md`
- `docs/development/AGENTS.md`

## License

EAS Station is dual-licensed:
- **Open Source**: GNU AGPL v3
- **Commercial**: Commercial license available

See `LICENSE` and `LICENSE-COMMERCIAL` for details.

---

## Quick Commands Cheat Sheet

```bash
# Install
cd bare-metal && sudo bash scripts/install.sh

# Configure
sudo nano /opt/eas-station/.env

# Start
sudo systemctl start eas-station.target

# Stop
sudo systemctl stop eas-station.target

# Restart
sudo systemctl restart eas-station.target

# Status
sudo systemctl status eas-station.target

# Logs
sudo journalctl -u eas-station-web.service -f

# Enable on boot
sudo systemctl enable eas-station.target

# Test
curl http://localhost:5000/health
```

---

**73 de KR8MER** 📡

**Version**: 2.18.0  
**Date**: December 10, 2025  
**Breaking Change**: Docker support removed - bare metal only
