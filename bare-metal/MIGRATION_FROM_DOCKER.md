# Migrating from Docker to Bare Metal

This guide walks you through migrating your existing Docker-based EAS Station installation to bare metal deployment.

## Prerequisites

- Root access to the system
- Existing Docker deployment running
- Debian/Ubuntu/Raspberry Pi OS host
- Backup of your data (recommended)

## Overview

Migration involves:
1. Backing up configuration and database
2. Installing bare metal version
3. Restoring configuration and data
4. Validating functionality
5. Decommissioning Docker

**Estimated Time:** 30-45 minutes

## Step-by-Step Migration

### Step 1: Backup Current Installation

#### 1.1 Export Configuration

```bash
# Find the Docker container name
docker ps | grep eas

# Export .env file
docker cp eas-app:/app/.env ./docker-eas-station.env

# Save for reference
cp ./docker-eas-station.env ./eas-station-backup-$(date +%Y%m%d).env
```

#### 1.2 Backup Database

If using the embedded PostgreSQL container:

```bash
# Export database
docker exec eas-alerts-db pg_dump -U postgres alerts > alerts-backup-$(date +%Y%m%d).sql

# Verify backup
ls -lh alerts-backup-*.sql
```

If using external PostgreSQL:
```bash
# Backup from external server
pg_dump -h your-db-host -U postgres alerts > alerts-backup-$(date +%Y%m%d).sql
```

#### 1.3 Backup Custom Files (Optional)

If you've customized any files:

```bash
# Backup custom templates, scripts, etc.
docker cp eas-app:/app/templates ./custom-templates-backup
docker cp eas-app:/app/static ./custom-static-backup
```

#### 1.4 Document Current Settings

Note these for comparison:
- Alert source feeds configured
- FIPS codes being monitored
- Any custom alert rules
- Hardware devices configured (SDR, GPIO)
- Icecast streaming settings

### Step 2: Install Bare Metal Version

#### 2.1 Clone Repository (if not already present)

```bash
# If not already cloned
git clone https://github.com/KR8MER/eas-station.git
cd eas-station

# Or update existing clone
cd eas-station
git pull origin main
```

#### 2.2 Run Installation

```bash
cd bare-metal
sudo bash scripts/install.sh
```

This will:
- Install all system dependencies
- Create service user and groups
- Set up PostgreSQL and Redis
- Install Python dependencies
- Configure nginx
- Install systemd services

**Note:** Installation may take 10-15 minutes depending on your system.

### Step 3: Stop Docker Services

```bash
# Stop Docker containers (keep data intact)
cd /path/to/docker/eas-station
docker-compose stop

# Verify they're stopped
docker ps | grep eas
```

**Important:** We're only stopping, not removing containers yet. This allows rollback if needed.

### Step 4: Restore Configuration

#### 4.1 Copy Configuration File

```bash
# Copy backed up .env to bare metal location
sudo cp ./docker-eas-station.env /opt/eas-station/.env

# Set proper ownership
sudo chown eas-station:eas-station /opt/eas-station/.env
sudo chmod 600 /opt/eas-station/.env
```

#### 4.2 Update Database Connection

Edit the configuration for bare metal:

```bash
sudo nano /opt/eas-station/.env
```

Update these values:
```bash
# Change from Docker service names to localhost
POSTGRES_HOST=localhost        # Was: alerts-db
REDIS_HOST=localhost           # Was: redis

# Port should remain the same
POSTGRES_PORT=5432
REDIS_PORT=6379
```

Save and exit (Ctrl+X, Y, Enter).

### Step 5: Restore Database

#### 5.1 Import Database Backup

```bash
# Import the backup
sudo -u postgres psql alerts < alerts-backup-*.sql

# Verify import
sudo -u postgres psql alerts -c "SELECT COUNT(*) FROM alerts;"
```

#### 5.2 Update Database Ownership

If there are permission issues:

```bash
sudo -u postgres psql alerts << EOF
-- Grant permissions to eas_station user
GRANT ALL PRIVILEGES ON DATABASE alerts TO eas_station;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO eas_station;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO eas_station;
EOF
```

### Step 6: Start Bare Metal Services

```bash
# Start all services
sudo systemctl start eas-station.target

# Check status
sudo systemctl status eas-station.target
```

If any services fail:
```bash
# Check logs for specific service
sudo journalctl -u eas-station-web.service -n 50

# Common issues:
# - Database connection (check credentials in .env)
# - Missing Python packages (rerun: cd /opt/eas-station && sudo -u eas-station venv/bin/pip install -r requirements.txt)
# - Port conflicts (check if Docker still running)
```

### Step 7: Verify Functionality

#### 7.1 Access Web Interface

Open browser to: `https://localhost` or `https://your-ip-address`

Accept self-signed certificate warning (same as Docker).

#### 7.2 Verify Key Functions

✅ Check these work:
- [ ] Dashboard loads
- [ ] Alert history shows previous alerts
- [ ] Configuration pages accessible
- [ ] Database connection working
- [ ] Redis connection working
- [ ] Pollers running (check Recent Alerts)
- [ ] SDR service (if configured)
- [ ] Hardware service (if configured)

#### 7.3 Check Service Logs

```bash
# Web application
sudo journalctl -u eas-station-web.service -n 20

# Pollers
sudo journalctl -u eas-station-noaa-poller.service -n 20
sudo journalctl -u eas-station-ipaws-poller.service -n 20

# Or use interactive viewer
cd /opt/eas-station/bare-metal
sudo bash scripts/logs.sh
```

### Step 8: Restore Custom Files (If Applicable)

If you backed up custom files:

```bash
# Restore custom templates
sudo cp -r ./custom-templates-backup/* /opt/eas-station/templates/

# Restore custom static files
sudo cp -r ./custom-static-backup/* /opt/eas-station/static/

# Set ownership
sudo chown -R eas-station:eas-station /opt/eas-station/templates
sudo chown -R eas-station:eas-station /opt/eas-station/static

# Restart web service
sudo systemctl restart eas-station-web.service
```

### Step 9: Enable Auto-Start

```bash
# Enable services to start on boot
sudo systemctl enable eas-station.target

# Verify
sudo systemctl is-enabled eas-station.target
```

### Step 10: Update Nginx/SSL (If Needed)

If you were using Let's Encrypt with Docker:

```bash
# The bare metal nginx config is already set up for SSL
# Request new certificate
sudo certbot --nginx -d your-domain.com

# Certificates will auto-renew
```

If using custom certificates:

```bash
# Copy certificates
sudo cp your-cert.pem /etc/ssl/certs/
sudo cp your-key.pem /etc/ssl/private/

# Update nginx config
sudo nano /etc/nginx/sites-available/eas-station
# Update ssl_certificate and ssl_certificate_key paths

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### Step 11: Monitor for 24 Hours

After migration, monitor the system:

```bash
# Check service status periodically
sudo systemctl status eas-station.target

# Monitor logs
sudo journalctl -u eas-station-*.service -f

# Or use status script
cd /opt/eas-station/bare-metal
sudo bash scripts/status.sh
```

Verify:
- Alerts are being received
- Database is updating
- No service restarts/crashes
- Resource usage is acceptable

### Step 12: Decommission Docker

Once you're confident everything works:

```bash
# Stop Docker containers
cd /path/to/docker/eas-station
docker-compose down

# Remove volumes (WARNING: Deletes all Docker data)
docker-compose down -v

# Optional: Remove Docker images
docker images | grep eas
docker rmi eas-station:latest eas-nginx:latest eas-icecast:latest

# Optional: Uninstall Docker (if not used for other things)
# sudo apt-get remove docker-ce docker-ce-cli containerd.io
```

## Rollback Procedure

If you need to roll back to Docker:

```bash
# Stop bare metal services
sudo systemctl stop eas-station.target

# Start Docker containers
cd /path/to/docker/eas-station
docker-compose up -d

# Your data is still in Docker volumes
```

## Common Migration Issues

### Issue: Database Connection Fails

**Symptom:** Web service won't start, logs show database connection error

**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check credentials in .env
sudo nano /opt/eas-station/.env

# Test connection manually
sudo -u eas-station psql -h localhost -U eas_station -d alerts
```

### Issue: Port Conflicts

**Symptom:** Nginx fails to start, port already in use

**Solution:**
```bash
# Check what's using port 443
sudo netstat -tlnp | grep :443

# If Docker nginx still running
docker ps | grep nginx
docker stop <container-id>

# Restart nginx
sudo systemctl restart nginx
```

### Issue: Missing Python Dependencies

**Symptom:** Services crash with ImportError

**Solution:**
```bash
# Reinstall requirements
cd /opt/eas-station
sudo -u eas-station venv/bin/pip install --upgrade -r requirements.txt

# Restart services
sudo systemctl restart eas-station.target
```

### Issue: Permission Denied on Hardware

**Symptom:** SDR service can't access USB device

**Solution:**
```bash
# Add user to plugdev group (should have been done by installer)
sudo usermod -a -G plugdev eas-station

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Restart SDR service
sudo systemctl restart eas-station-sdr.service
```

### Issue: Alerts Not Appearing

**Symptom:** No new alerts in dashboard after migration

**Solution:**
```bash
# Check pollers are running
sudo systemctl status eas-station-noaa-poller.service
sudo systemctl status eas-station-ipaws-poller.service

# Check logs for errors
sudo journalctl -u eas-station-noaa-poller.service -n 50

# Verify network connectivity
curl -I https://api.weather.gov/
```

## Performance Comparison

After migration, you should see:

| Metric | Docker | Bare Metal | Your Result |
|--------|--------|------------|-------------|
| RAM Usage | ~1.2 GB | ~650 MB | __________ |
| CPU (Idle) | 2-3% | 0.5-1% | __________ |
| CPU (Active) | 25-30% | 20-25% | __________ |
| Startup Time | ~30 sec | ~10 sec | __________ |

Check your results:
```bash
# Memory usage
free -h

# CPU usage
top -b -n 1 | grep eas-station

# Service startup time
systemd-analyze blame | grep eas-station
```

## Post-Migration Optimization

### Reduce Memory Usage

For systems with limited RAM:

```bash
# Reduce Gunicorn workers
sudo systemctl edit eas-station-web.service

# Add:
[Service]
Environment="MAX_WORKERS=1"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart eas-station-web.service
```

### Optimize for Raspberry Pi

```bash
# Disable unused services
sudo systemctl disable eas-station-hardware.service  # If not using GPIO

# Set memory limits
sudo systemctl edit eas-station-audio.service
[Service]
MemoryLimit=256M

# Apply changes
sudo systemctl daemon-reload
sudo systemctl restart eas-station.target
```

## Getting Help

If you encounter issues during migration:

1. **Check logs:** `sudo journalctl -u eas-station-*.service -f`
2. **Check status:** `sudo systemctl status eas-station.target`
3. **Review documentation:** `/opt/eas-station/bare-metal/README.md`
4. **GitHub Issues:** https://github.com/KR8MER/eas-station/issues
5. **Discussions:** https://github.com/KR8MER/eas-station/discussions

## Maintenance After Migration

### Daily Checks

```bash
# Quick status check
sudo systemctl status eas-station.target

# Or use status script
cd /opt/eas-station/bare-metal
sudo bash scripts/status.sh
```

### Weekly Updates

```bash
# Update EAS Station
cd /opt/eas-station/bare-metal
sudo bash scripts/update.sh
```

### Monthly Backups

```bash
# Automated backup
sudo -u postgres pg_dump alerts > /backup/alerts-$(date +%Y%m%d).sql
sudo tar czf /backup/eas-station-$(date +%Y%m%d).tar.gz /opt/eas-station
```

## Congratulations!

You've successfully migrated from Docker to bare metal deployment. You should now have:

✅ Lower resource usage
✅ Better hardware access
✅ Native systemd service management
✅ Improved performance
✅ All your data and configuration preserved

Enjoy your optimized EAS Station installation!

---

**73 de KR8MER** 📡
