# EAS Station Bare Metal Testing Guide

This guide helps you verify that your bare metal EAS Station installation is working correctly.

## Quick Health Check

Run this command to verify all services are running:

```bash
sudo systemctl status eas-station.target
```

Expected output: All services should show "active (running)" in green.

## Detailed Testing Checklist

### 1. Service Status Check

Check each service individually:

```bash
# Main target
sudo systemctl status eas-station.target

# Individual services
sudo systemctl status eas-station-web.service
sudo systemctl status eas-station-sdr.service
sudo systemctl status eas-station-audio.service
sudo systemctl status eas-station-eas.service
sudo systemctl status eas-station-hardware.service
sudo systemctl status eas-station-noaa-poller.service
sudo systemctl status eas-station-ipaws-poller.service
```

**Expected Result**: All services should be `active (running)`.

### 2. Database Connectivity

Test PostgreSQL connection:

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test database connection
sudo -u postgres psql -d alerts -c "SELECT PostGIS_version();"
```

**Expected Result**: Should display PostGIS version information.

### 3. Redis Connectivity

Test Redis connection:

```bash
# Check Redis is running
sudo systemctl status redis-server

# Test Redis connection
redis-cli ping
```

**Expected Result**: Should respond with `PONG`.

### 4. Web Interface Access

Test web application:

```bash
# Check if web service is listening
sudo netstat -tlnp | grep :5000

# Test health endpoint
curl http://localhost:5000/health
```

**Expected Result**: Health endpoint should return JSON with status "healthy".

Test via browser:
- Open https://localhost in your browser
- Accept self-signed certificate warning (safe for testing)
- Should see EAS Station login/dashboard page

### 5. Nginx Reverse Proxy

Check nginx configuration:

```bash
# Test nginx configuration
sudo nginx -t

# Check nginx status
sudo systemctl status nginx

# Verify nginx is listening on ports 80 and 443
sudo netstat -tlnp | grep nginx
```

**Expected Result**: 
- Configuration test should pass
- Nginx should be active
- Should be listening on ports 80 and 443

### 6. Log Verification

Check service logs for errors:

```bash
# Check web service logs
sudo journalctl -u eas-station-web.service -n 50

# Check for errors in all services
sudo journalctl -u eas-station-*.service -p err -n 50

# Follow logs in real-time
sudo journalctl -u eas-station.target -f
```

**Expected Result**: No CRITICAL or ERROR messages (warnings are usually okay).

### 7. Configuration File

Verify configuration is loaded:

```bash
# Check configuration file exists and has proper permissions
ls -la /opt/eas-station/.env

# Verify it's readable by the service user
sudo -u eas-station cat /opt/eas-station/.env | head -5
```

**Expected Result**: File should exist with proper permissions.

### 8. Python Environment

Verify Python virtual environment:

```bash
# Check virtual environment
ls -la /opt/eas-station/venv/

# Test Python can import key modules
sudo -u eas-station /opt/eas-station/venv/bin/python3 -c "import flask, sqlalchemy, redis, psycopg2; print('All imports successful')"
```

**Expected Result**: Should print "All imports successful".

### 9. Database Schema

Verify database schema is initialized:

```bash
# Check if tables exist
sudo -u postgres psql -d alerts -c "\dt"
```

**Expected Result**: Should show multiple tables including `cap_alert`, `radio_receiver`, etc.

### 10. pgAdmin Access (if installed)

Check pgAdmin installation:

```bash
# Check if pgAdmin is installed
dpkg -l | grep pgadmin4

# Access pgAdmin web interface
# Open browser to: http://localhost/pgadmin4
```

**Expected Result**: 
- Package should be installed
- Web interface should be accessible

## Common Issues and Solutions

### Service Won't Start

```bash
# Check service status for details
sudo systemctl status eas-station-web.service

# Check logs for error messages
sudo journalctl -u eas-station-web.service -n 100 --no-pager

# Verify dependencies
sudo systemctl status postgresql redis-server
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify database exists
sudo -u postgres psql -l | grep alerts

# Test connection with credentials from .env
PGPASSWORD=changeme123 psql -h localhost -U eas_station -d alerts -c "SELECT 1;"
```

### Port Already in Use

```bash
# Check what's using port 5000
sudo lsof -i :5000

# Check what's using port 80/443
sudo lsof -i :80
sudo lsof -i :443
```

### Permission Issues

```bash
# Fix ownership of installation directory
sudo chown -R eas-station:eas-station /opt/eas-station

# Fix ownership of log directory
sudo chown -R eas-station:eas-station /var/log/eas-station

# Verify service user groups
groups eas-station
```

## Performance Testing

### Memory Usage

Check memory usage of services:

```bash
# Overall system memory
free -h

# Per-service memory
sudo systemctl status eas-station-web.service | grep Memory
sudo systemctl status eas-station-sdr.service | grep Memory
```

### CPU Usage

Monitor CPU usage:

```bash
# Real-time monitoring
htop

# Or use top filtered for eas-station
top -u eas-station
```

### Disk Space

Check disk usage:

```bash
# Overall disk usage
df -h

# EAS Station directories
du -sh /opt/eas-station
du -sh /var/log/eas-station
```

## Restart Services After Changes

After modifying configuration:

```bash
# Restart all services
sudo systemctl restart eas-station.target

# Or restart individual services
sudo systemctl restart eas-station-web.service

# Check status after restart
sudo systemctl status eas-station.target
```

## Enable Services on Boot

Ensure services start automatically:

```bash
# Enable all services
sudo systemctl enable eas-station.target

# Verify enabled status
sudo systemctl is-enabled eas-station.target
```

## Diagnostic API

The web application includes a built-in diagnostics page:

1. Open web browser to https://localhost/diagnostics
2. Click "Run System Validation"
3. Review the results

This checks:
- Service status
- Database connectivity
- Redis connectivity
- Configuration validity
- System health

## Getting Help

If tests fail:

1. **Check logs first**: `sudo journalctl -u eas-station-web.service -n 100`
2. **Review configuration**: `sudo nano /opt/eas-station/.env`
3. **Verify dependencies**: PostgreSQL and Redis must be running
4. **Check documentation**: See [README.md](README.md) for detailed setup
5. **Report issues**: https://github.com/KR8MER/eas-station/issues

## Success Criteria

Your installation is working correctly if:

- ✅ All services show "active (running)"
- ✅ Web interface is accessible at https://localhost
- ✅ Database and Redis connections succeed
- ✅ No errors in service logs
- ✅ Diagnostics page shows all checks passing
- ✅ Services restart without errors

---

**73 de KR8MER** 📡
