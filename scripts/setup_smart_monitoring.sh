#!/bin/bash
# EAS Station - SMART Monitoring Setup Script
# Configures sudo access for smartctl to enable NVMe/SSD health monitoring

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "EAS Station - SMART Monitoring Setup"
echo "=========================================="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    echo "Usage: sudo $0 [username]"
    exit 1
fi

# Determine the web application user
WEB_USER="${1:-}"

if [ -z "$WEB_USER" ]; then
    echo "Detecting web application user..."

    # Try to detect from running processes
    for candidate in eas-station www-data nginx apache httpd; do
        if ps aux | grep -q "[${candidate:0:1}]${candidate:1}.*python.*app\.py"; then
            WEB_USER="$candidate"
            echo -e "${GREEN}✓ Detected user: $WEB_USER${NC}"
            break
        fi
    done

    # If still not found, check common defaults
    if [ -z "$WEB_USER" ]; then
        if id www-data &>/dev/null; then
            WEB_USER="www-data"
            echo -e "${YELLOW}! Using default user: $WEB_USER${NC}"
        elif id nginx &>/dev/null; then
            WEB_USER="nginx"
            echo -e "${YELLOW}! Using default user: $WEB_USER${NC}"
        else
            echo -e "${RED}ERROR: Could not detect web application user${NC}"
            echo "Please specify the user manually:"
            echo "  sudo $0 <username>"
            exit 1
        fi
    fi
else
    echo "Using specified user: $WEB_USER"
fi

# Verify user exists
if ! id "$WEB_USER" &>/dev/null; then
    echo -e "${RED}ERROR: User '$WEB_USER' does not exist${NC}"
    exit 1
fi

echo

# Check if smartmontools is installed
echo "Checking for smartmontools..."
if ! command -v smartctl &>/dev/null; then
    echo -e "${RED}ERROR: smartctl not found${NC}"
    echo
    echo "Please install smartmontools first:"
    echo "  Debian/Ubuntu: sudo apt install smartmontools"
    echo "  RHEL/CentOS:   sudo yum install smartmontools"
    exit 1
fi

SMARTCTL_PATH=$(which smartctl)
echo -e "${GREEN}✓ Found smartctl: $SMARTCTL_PATH${NC}"
echo

# Create sudoers file
SUDOERS_FILE="/etc/sudoers.d/eas-station-smartctl"

echo "Creating sudoers configuration..."
cat > "$SUDOERS_FILE" <<EOF
# EAS Station - SMART Monitoring
# Allow web application to run smartctl without password
# Created by: scripts/setup_smart_monitoring.sh
# User: $WEB_USER

$WEB_USER ALL=(ALL) NOPASSWD: $SMARTCTL_PATH
EOF

# Set correct permissions (must be 0440)
chmod 0440 "$SUDOERS_FILE"
echo -e "${GREEN}✓ Created: $SUDOERS_FILE${NC}"
echo

# Validate sudoers syntax
echo "Validating sudoers configuration..."
if visudo -c -f "$SUDOERS_FILE" &>/dev/null; then
    echo -e "${GREEN}✓ Sudoers syntax is valid${NC}"
else
    echo -e "${RED}ERROR: Invalid sudoers syntax${NC}"
    echo "Removing invalid file..."
    rm -f "$SUDOERS_FILE"
    exit 1
fi
echo

# Test sudo access
echo "Testing sudo access for user '$WEB_USER'..."
if sudo -u "$WEB_USER" sudo -n "$SMARTCTL_PATH" --version &>/dev/null; then
    echo -e "${GREEN}✓ Sudo access works correctly${NC}"
else
    echo -e "${RED}ERROR: Sudo access test failed${NC}"
    echo "The user may need to log out and back in for group changes to take effect."
    exit 1
fi
echo

# Test device scanning
echo "Testing device scanning..."
SCAN_OUTPUT=$(sudo -u "$WEB_USER" sudo -n "$SMARTCTL_PATH" --scan 2>&1 || true)
if [ -n "$SCAN_OUTPUT" ]; then
    echo -e "${GREEN}✓ Device scan successful:${NC}"
    echo "$SCAN_OUTPUT" | sed 's/^/  /'
else
    echo -e "${YELLOW}! No SMART-capable devices found${NC}"
    echo "  This is normal if running in a VM or container"
fi
echo

# Summary
echo "=========================================="
echo -e "${GREEN}SMART Monitoring Setup Complete!${NC}"
echo "=========================================="
echo
echo "Configuration:"
echo "  User:        $WEB_USER"
echo "  Sudoers:     $SUDOERS_FILE"
echo "  smartctl:    $SMARTCTL_PATH"
echo
echo "Next steps:"
echo "  1. Restart web services:"
echo "     sudo systemctl restart eas-station"
echo
echo "  2. Visit the health page to verify:"
echo "     http://your-server/system_health"
echo
echo "  3. Check for SMART data in the 'Storage' section"
echo
echo "Troubleshooting:"
echo "  - Check logs: journalctl -u eas-station -f | grep -i smart"
echo "  - Manual test: sudo -u $WEB_USER sudo -n smartctl -a /dev/nvme0"
echo "  - Documentation: docs/SMART_SETUP.md"
echo
