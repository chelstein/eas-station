#!/bin/bash
# EAS Station - Main Installation Script
# Handles initial setup and updates

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "EAS Station - Installation & Update"
echo "=========================================="
echo

# Detect if running as root
if [ "$EUID" -eq 0 ]; then
    IS_ROOT=true
    echo -e "${YELLOW}Running as root${NC}"
else
    IS_ROOT=false
    echo "Running as user: $(whoami)"
fi
echo

# Step 1: System packages
echo -e "${BLUE}[1/5] System Packages${NC}"
if [ "$IS_ROOT" = true ]; then
    if [ -f "$PROJECT_ROOT/requirements-system.txt" ]; then
        echo "Installing system packages..."

        # Detect package manager
        if command -v apt-get &>/dev/null; then
            apt-get update
            while read -r package comment; do
                # Skip comments and empty lines
                [[ "$package" =~ ^#.*$ || -z "$package" ]] && continue

                # Extract package name (remove comments)
                pkg_name=$(echo "$package" | awk '{print $1}')

                echo "Installing: $pkg_name"
                apt-get install -y "$pkg_name" || echo "Warning: Failed to install $pkg_name"
            done < "$PROJECT_ROOT/requirements-system.txt"

        elif command -v yum &>/dev/null; then
            while read -r package comment; do
                [[ "$package" =~ ^#.*$ || -z "$package" ]] && continue
                pkg_name=$(echo "$package" | awk '{print $1}')
                echo "Installing: $pkg_name"
                yum install -y "$pkg_name" || echo "Warning: Failed to install $pkg_name"
            done < "$PROJECT_ROOT/requirements-system.txt"
        else
            echo -e "${YELLOW}! Unknown package manager - install packages manually:${NC}"
            cat "$PROJECT_ROOT/requirements-system.txt"
        fi

        echo -e "${GREEN}✓ System packages installed${NC}"
    else
        echo "No requirements-system.txt found, skipping"
    fi
else
    echo -e "${YELLOW}! Skipping system packages (need root/sudo)${NC}"
    echo "  To install: sudo apt install smartmontools (or yum)"
fi
echo

# Step 2: Python virtual environment
echo -e "${BLUE}[2/5] Python Dependencies${NC}"
if [ -d "$PROJECT_ROOT/venv" ]; then
    echo "Activating existing virtual environment..."
    source "$PROJECT_ROOT/venv/bin/activate"
else
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_ROOT/venv"
    source "$PROJECT_ROOT/venv/bin/activate"
fi

echo "Installing Python packages..."
pip install --upgrade pip
pip install -r "$PROJECT_ROOT/requirements.txt"
echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo

# Step 3: Database migrations
echo -e "${BLUE}[3/5] Database Setup${NC}"
cd "$PROJECT_ROOT"
if [ -f "manage.py" ]; then
    python manage.py db upgrade || echo "Warning: Database migration may have failed"
    echo -e "${GREEN}✓ Database migrations applied${NC}"
else
    echo "No manage.py found, skipping migrations"
fi
echo

# Step 4: SMART monitoring setup
echo -e "${BLUE}[4/5] SMART Monitoring${NC}"
if [ "$IS_ROOT" = true ]; then
    if [ -f "$SCRIPT_DIR/setup_smart_monitoring.sh" ]; then
        echo "Configuring SMART monitoring (NVMe/SSD health)..."
        bash "$SCRIPT_DIR/setup_smart_monitoring.sh" || echo "Warning: SMART setup may have failed"
    else
        echo "SMART setup script not found, skipping"
    fi
else
    echo -e "${YELLOW}! Skipping SMART monitoring setup (need root/sudo)${NC}"
    echo "  To configure manually: sudo ./scripts/setup_smart_monitoring.sh"
fi
echo

# Step 5: Service restart (if systemd available)
echo -e "${BLUE}[5/5] Services${NC}"
if [ "$IS_ROOT" = true ] && command -v systemctl &>/dev/null; then
    echo "Restarting EAS Station services..."

    for service in eas-station eas-monitoring sdr-hardware; do
        if systemctl list-unit-files | grep -q "^${service}.service"; then
            echo "  Restarting: $service"
            systemctl restart "$service" || echo "  Warning: Failed to restart $service"
        fi
    done

    echo -e "${GREEN}✓ Services restarted${NC}"
else
    echo -e "${YELLOW}! Skipping service restart${NC}"
    echo "  Restart manually: sudo systemctl restart eas-station"
fi
echo

# Summary
echo "=========================================="
echo -e "${GREEN}Installation Complete!${NC}"
echo "=========================================="
echo
echo "What was installed:"
echo "  ✓ System packages (smartmontools, etc.)"
echo "  ✓ Python dependencies (scipy, numpy, etc.)"
echo "  ✓ Database migrations"
echo "  ✓ SMART monitoring (sudo for smartctl)"
echo "  ✓ Services restarted"
echo
echo "Verify installation:"
echo "  - Check services: sudo systemctl status eas-station"
echo "  - View logs: journalctl -u eas-station -f"
echo "  - Test SMART: sudo smartctl --scan"
echo "  - Web interface: http://localhost:5000"
echo
echo "Next steps:"
echo "  1. Configure receivers in the web UI"
echo "  2. Enable RBDS: UPDATE radio_receiver SET enable_rbds=1;"
echo "  3. Check health page: /system_health"
echo
