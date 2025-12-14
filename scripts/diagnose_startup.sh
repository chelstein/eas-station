#!/bin/bash
# EAS Station Startup Diagnostic Script
# Run this on your production server to diagnose why the app won't start
# Usage: sudo ./scripts/diagnose_startup.sh

echo "================================================================================"
echo "EAS STATION STARTUP DIAGNOSTIC"
echo "================================================================================"
echo ""

echo "1. Checking if services are running..."
echo "--------------------------------------"
systemctl is-active eas-station-web.service && echo "✓ Web service is ACTIVE" || echo "✗ Web service is INACTIVE"
systemctl is-active postgresql.service && echo "✓ PostgreSQL is ACTIVE" || echo "✗ PostgreSQL is INACTIVE"
systemctl is-active redis.service && echo "✓ Redis is ACTIVE" || echo "✗ Redis is INACTIVE"
echo ""

echo "2. Checking what's listening on port 5000..."
echo "--------------------------------------"
ss -tlnp | grep :5000 || echo "Nothing listening on port 5000"
echo ""

echo "3. Checking web service status..."
echo "--------------------------------------"
systemctl status eas-station-web.service --no-pager -l | tail -30
echo ""

echo "4. Checking recent web service logs..."
echo "--------------------------------------"
journalctl -u eas-station-web.service -n 50 --no-pager
echo ""

echo "5. Checking for startup error files..."
echo "--------------------------------------"
ls -lth /tmp/eas-station-web-startup-error-* 2>/dev/null | head -5 || echo "No startup error files found"
echo ""
if ls /tmp/eas-station-web-startup-error-* &>/dev/null; then
    echo "Latest error file contents:"
    cat $(ls -t /tmp/eas-station-web-startup-error-* | head -1)
    echo ""
fi

echo "6. Checking Python/gunicorn processes..."
echo "--------------------------------------"
ps aux | grep -E "gunicorn|python.*app\.py|python.*wsgi" | grep -v grep || echo "No EAS Station processes found"
echo ""

echo "7. Checking database connectivity..."
echo "--------------------------------------"
sudo -u postgres psql alerts -c "SELECT version();" 2>&1 | head -3
sudo -u postgres psql alerts -c "SELECT PostGIS_version();" 2>&1 | head -3
echo ""

echo "8. Checking Python environment..."
echo "--------------------------------------"
if [ -f /opt/eas-station/venv/bin/python3 ]; then
    echo "Virtual environment exists"
    /opt/eas-station/venv/bin/python3 --version
    echo "Testing app import..."
    cd /opt/eas-station
    /opt/eas-station/venv/bin/python3 -c "import app; print('✓ app.py imports successfully')" 2>&1 || echo "✗ app.py import FAILED"
else
    echo "✗ Virtual environment not found at /opt/eas-station/venv"
fi
echo ""

echo "9. Checking .env file..."
echo "--------------------------------------"
if [ -f /opt/eas-station/.env ]; then
    echo "✓ .env file exists"
    echo "DATABASE_URL configured: $(grep -q DATABASE_URL /opt/eas-station/.env && echo YES || echo NO)"
    echo "SECRET_KEY configured: $(grep -q SECRET_KEY /opt/eas-station/.env && echo YES || echo NO)"
else
    echo "✗ .env file not found"
fi
echo ""

echo "10. Checking system resources..."
echo "--------------------------------------"
free -h | grep -E "Mem:|Swap:"
df -h /opt/eas-station 2>/dev/null || df -h /
echo ""

echo "================================================================================"
echo "DIAGNOSTIC COMPLETE"
echo "================================================================================"
echo ""
echo "Next steps:"
echo "1. If web service is inactive, try: sudo systemctl start eas-station-web.service"
echo "2. If service fails to start, check the journalctl output above for errors"
echo "3. If startup error files exist, review their contents above"
echo "4. If Python import fails, there may be missing dependencies"
echo ""
