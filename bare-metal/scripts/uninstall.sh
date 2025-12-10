#!/bin/bash
# EAS Station Uninstall Script
# Removes EAS Station completely from the system

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

echo_warning "EAS Station Uninstall Script"
echo_warning "============================"
echo ""
echo_warning "This will COMPLETELY REMOVE EAS Station from your system, including:"
echo_warning "  - Application files (/opt/eas-station)"
echo_warning "  - Systemd service files"
echo_warning "  - Nginx configuration"
echo_warning "  - Log files (/var/log/eas-station)"
echo_warning ""
echo_warning "The following will NOT be removed (you can remove manually if desired):"
echo_warning "  - PostgreSQL database and user"
echo_warning "  - System packages (nginx, postgresql, redis, etc.)"
echo_warning "  - Service user (eas-station)"
echo ""
read -p "Are you SURE you want to uninstall? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    echo_info "Uninstall cancelled"
    exit 0
fi

# Stop and disable services
echo_info "Stopping and disabling services..."
systemctl stop eas-station.target 2>/dev/null || true
systemctl disable eas-station.target 2>/dev/null || true

# Remove systemd service files
echo_info "Removing systemd service files..."
rm -f /etc/systemd/system/eas-station*.service
rm -f /etc/systemd/system/eas-station*.target
systemctl daemon-reload
echo_success "Service files removed"

# Remove nginx configuration
echo_info "Removing nginx configuration..."
rm -f /etc/nginx/sites-enabled/eas-station
rm -f /etc/nginx/sites-available/eas-station
systemctl reload nginx 2>/dev/null || true
echo_success "Nginx configuration removed"

# Remove application files
echo_info "Removing application files..."
rm -rf /opt/eas-station
echo_success "Application files removed"

# Remove log files
echo_info "Removing log files..."
rm -rf /var/log/eas-station
echo_success "Log files removed"

# Remove udev rules
echo_info "Removing udev rules..."
rm -f /etc/udev/rules.d/99-eas-station-sdr.rules
udevadm control --reload-rules 2>/dev/null || true
echo_success "Udev rules removed"

echo ""
echo_success "EAS Station has been uninstalled!"
echo ""
echo "=========================================="
echo "Remaining Components (Optional Removal)"
echo "=========================================="
echo ""
echo "To remove the database:"
echo "  sudo -u postgres dropdb alerts"
echo "  sudo -u postgres dropuser eas_station"
echo ""
echo "To remove the service user:"
echo "  sudo userdel eas-station"
echo ""
echo "To remove system packages:"
echo "  sudo apt-get autoremove postgresql redis-server nginx"
echo ""
echo "To remove self-signed SSL certificate:"
echo "  sudo rm /etc/ssl/certs/eas-station-selfsigned.crt"
echo "  sudo rm /etc/ssl/private/eas-station-selfsigned.key"
echo ""
echo "=========================================="
