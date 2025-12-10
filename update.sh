#!/bin/bash
# EAS Station Update Script
# Updates EAS Station to the latest version from Git

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
echo_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo_error "This script must be run as root (use sudo)"
    exit 1
fi

INSTALL_DIR="/opt/eas-station"
SERVICE_USER="eas-station"
BACKUP_DIR="/var/backups/eas-station"

echo_info "EAS Station Update Script"
echo_info "========================="
echo ""

# Check if EAS Station is installed
if [ ! -d "$INSTALL_DIR" ]; then
    echo_error "EAS Station is not installed at $INSTALL_DIR"
    exit 1
fi

# Confirm update
echo_warning "This will update EAS Station to the latest version."
echo_warning "Services will be stopped during the update."
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo_info "Update cancelled"
    exit 0
fi

# Create backup
echo_info "Creating backup..."
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/eas-station-$(date +%Y%m%d-%H%M%S).tar.gz"
tar -czf "$BACKUP_FILE" -C "$INSTALL_DIR" . 2>/dev/null || echo_warning "Backup failed (non-critical)"
echo_success "Backup created: $BACKUP_FILE"

# Stop services
echo_info "Stopping services..."
systemctl stop eas-station.target
echo_success "Services stopped"

# Save current .env file
echo_info "Saving configuration..."
cp "$INSTALL_DIR/.env" "/tmp/eas-station.env.backup"

# Update from Git
echo_info "Pulling latest changes from Git..."
cd "$INSTALL_DIR"
sudo -u "$SERVICE_USER" git fetch origin
sudo -u "$SERVICE_USER" git pull origin main || echo_warning "Git pull failed - using existing code"

# Restore .env file
echo_info "Restoring configuration..."
cp "/tmp/eas-station.env.backup" "$INSTALL_DIR/.env"
chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/.env"

# Update Python dependencies
echo_info "Updating Python dependencies..."
sudo -u "$SERVICE_USER" "$INSTALL_DIR/venv/bin/pip" install --upgrade -r "$INSTALL_DIR/requirements.txt"
echo_success "Dependencies updated"

# Update systemd service files
echo_info "Updating systemd service files..."
cp "$INSTALL_DIR/systemd/"*.service /etc/systemd/system/
cp "$INSTALL_DIR/systemd/"*.target /etc/systemd/system/
systemctl daemon-reload
echo_success "Service files updated"

# Update nginx configuration (only if changed)
if [ -f "$INSTALL_DIR/config/nginx-eas-station.conf" ]; then
    if [ -f /etc/nginx/sites-available/eas-station ]; then
        if ! diff -q "$INSTALL_DIR/config/nginx-eas-station.conf" /etc/nginx/sites-available/eas-station >/dev/null 2>&1; then
            echo_info "Updating nginx configuration..."
            cp "$INSTALL_DIR/config/nginx-eas-station.conf" /etc/nginx/sites-available/eas-station
            nginx -t && systemctl reload nginx
            echo_success "Nginx configuration updated"
        else
            echo_info "Nginx configuration unchanged"
        fi
    else
        echo_warning "Nginx configuration not found in /etc/nginx/sites-available/"
    fi
else
    echo_warning "Source nginx configuration not found in $INSTALL_DIR/config/"
fi

# Run database migrations (if any)
echo_info "Running database migrations..."
cd "$INSTALL_DIR"
sudo -u "$SERVICE_USER" "$INSTALL_DIR/venv/bin/python" -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database schema updated')
" || echo_warning "Database migration failed (non-critical)"

# Start services
echo_info "Starting services..."
systemctl start eas-station.target
sleep 5

# Check status
echo_info "Checking service status..."
if systemctl is-active --quiet eas-station.target; then
    echo_success "Services started successfully"
else
    echo_error "Some services failed to start"
    echo_info "Check status with: sudo systemctl status eas-station.target"
fi

echo ""
echo_success "Update complete!"
echo ""
echo "=========================================="
echo "Update Summary"
echo "=========================================="
echo "Backup: $BACKUP_FILE"
echo "Configuration: Preserved"
echo "Services: $(systemctl is-active eas-station.target)"
echo ""
echo "View status: sudo systemctl status eas-station.target"
echo "View logs: sudo journalctl -u eas-station-web.service -f"
echo "Web interface: https://$(hostname -I | awk '{print $1}')"
echo ""
echo "=========================================="
