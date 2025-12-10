#!/bin/bash
# EAS Station ISO Builder Script
# Creates a bootable Debian-based ISO with EAS Station pre-installed
# Copyright (c) 2025 Timothy Kramer (KR8MER)
# Licensed under AGPL v3 or Commercial License

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

# Configuration
ISO_NAME="eas-station-$(date +%Y%m%d).iso"
BUILD_DIR="/tmp/eas-station-iso-build"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo_info "EAS Station ISO Builder"
echo_info "======================="
echo ""
echo_info "Output ISO: $ISO_NAME"
echo_info "Build directory: $BUILD_DIR"
echo ""

# Detect architecture
ARCH=$(uname -m)
case "$ARCH" in
    x86_64)
        DEBIAN_ARCH="amd64"
        ;;
    aarch64|arm64)
        DEBIAN_ARCH="arm64"
        ;;
    armv7l|armhf)
        DEBIAN_ARCH="armhf"
        ;;
    *)
        echo_error "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac
echo_info "Building for architecture: $DEBIAN_ARCH"

# Install build dependencies
echo_info "Installing build dependencies..."
apt-get update
apt-get install -y \
    live-build \
    debootstrap \
    squashfs-tools \
    xorriso \
    isolinux \
    syslinux-efi \
    grub-pc-bin \
    grub-efi-amd64-bin \
    grub-efi-ia32-bin \
    mtools \
    dosfstools

echo_success "Build dependencies installed"

# Clean previous build
if [ -d "$BUILD_DIR" ]; then
    echo_info "Cleaning previous build directory..."
    rm -rf "$BUILD_DIR"
fi

# Create build directory
echo_info "Creating build directory..."
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Initialize live-build configuration
echo_info "Initializing live-build configuration..."
lb config \
    --debian-installer false \
    --debian-installer-gui false \
    --archive-areas "main contrib non-free non-free-firmware" \
    --architectures "$DEBIAN_ARCH" \
    --linux-flavours generic \
    --distribution bookworm \
    --apt-recommends false \
    --apt-secure true \
    --bootappend-live "boot=live components quiet splash" \
    --iso-application "EAS Station" \
    --iso-preparer "EAS Station Project" \
    --iso-publisher "KR8MER" \
    --iso-volume "EAS_STATION_LIVE"

echo_success "Live-build configured"

# Create package list
echo_info "Creating package list..."
mkdir -p config/package-lists
cat > config/package-lists/eas-station.list.chroot << 'EOF'
# Base system
linux-image-generic
systemd
systemd-sysv
dbus
network-manager

# Development tools
build-essential
git
curl
wget

# Python
python3
python3-pip
python3-venv
python3-dev

# Database
postgresql
postgresql-contrib
postgis
postgresql-17-postgis-3

# Redis
redis-server

# Web server
nginx
certbot
python3-certbot-nginx

# Audio and multimedia
ffmpeg
alsa-utils
pulseaudio
espeak
libespeak-ng1

# SDR support
libusb-1.0-0
libusb-1.0-0-dev
usbutils
python3-soapysdr
soapysdr-tools
soapysdr-module-rtlsdr
soapysdr-module-airspy
libairspy0
rtl-sdr
librtlsdr0

# Hardware support (GPIO, I2C, SPI)
gpiod
libgpiod2
i2c-tools
python3-smbus

# System utilities
ca-certificates
rsync
htop
nano
vim
sudo
openssh-server

# Desktop environment (minimal - for initial setup only)
xorg
lightdm
xfce4
xfce4-terminal
firefox-esr

# Additional utilities
less
man-db
file
lsof
strace
tcpdump
net-tools
EOF

echo_success "Package list created"

# Create hooks for customization
echo_info "Creating customization hooks..."
mkdir -p config/hooks/normal

# Hook 1: Install EAS Station
cat > config/hooks/normal/0100-install-eas-station.hook.chroot << 'EOF'
#!/bin/bash
set -e

echo "Installing EAS Station..."

# Create installation directory
mkdir -p /opt/eas-station
cd /opt/eas-station

# Note: The actual application files will be copied later via includes
# This hook just sets up the environment

# Create service user
useradd --system --shell /bin/bash --home-dir /opt/eas-station --no-create-home eas-station

# Add to hardware groups
usermod -a -G dialout,plugdev,gpio,i2c,spi,audio eas-station || true

# Create log directory
mkdir -p /var/log/eas-station
chown eas-station:eas-station /var/log/eas-station

echo "EAS Station environment prepared"
EOF

# Hook 2: Configure services
cat > config/hooks/normal/0200-configure-services.hook.chroot << 'EOF'
#!/bin/bash
set -e

echo "Configuring services..."

# Enable services to start on boot
systemctl enable postgresql
systemctl enable redis-server
systemctl enable nginx
systemctl enable ssh

# Configure PostgreSQL
sudo -u postgres psql -c "CREATE USER eas_station WITH PASSWORD 'easstation2025';"
sudo -u postgres psql -c "CREATE DATABASE alerts OWNER eas_station;"
sudo -u postgres psql -d alerts -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Create first-boot setup script
cat > /usr/local/bin/eas-station-setup << 'SETUP_EOF'
#!/bin/bash
# First-boot setup wizard

clear
echo "================================================"
echo "    EAS Station - First Boot Setup"
echo "================================================"
echo ""
echo "This wizard will help you configure EAS Station."
echo ""
read -p "Press Enter to continue..."

# Run the installation script
cd /opt/eas-station
bash bare-metal/scripts/install.sh

echo ""
echo "Setup complete! EAS Station will start automatically."
echo "Access the web interface at: https://$(hostname -I | awk '{print $1}')"
echo ""
read -p "Press Enter to continue..."
SETUP_EOF

chmod +x /usr/local/bin/eas-station-setup

# Create desktop shortcut for setup
mkdir -p /etc/skel/Desktop
cat > /etc/skel/Desktop/eas-station-setup.desktop << 'DESKTOP_EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=EAS Station Setup
Comment=Configure EAS Station
Exec=sudo /usr/local/bin/eas-station-setup
Icon=utilities-terminal
Terminal=true
Categories=System;Settings;
DESKTOP_EOF
chmod +x /etc/skel/Desktop/eas-station-setup.desktop

echo "Services configured"
EOF

# Hook 3: Configure system
cat > config/hooks/normal/0300-configure-system.hook.chroot << 'EOF'
#!/bin/bash
set -e

echo "Configuring system..."

# Set hostname
echo "eas-station" > /etc/hostname

# Configure hosts
cat > /etc/hosts << 'HOSTS_EOF'
127.0.0.1       localhost
127.0.1.1       eas-station

# IPv6
::1             localhost ip6-localhost ip6-loopback
ff02::1         ip6-allnodes
ff02::2         ip6-allrouters
HOSTS_EOF

# Create default user (user will set password on first boot)
useradd -m -s /bin/bash -G sudo,audio,video,plugdev,dialout easuser
echo "easuser:easstation" | chpasswd
# User will be prompted to change password on first login

# Configure sudo without password for first boot setup
echo "easuser ALL=(ALL) NOPASSWD: /usr/local/bin/eas-station-setup" > /etc/sudoers.d/eas-station-setup
chmod 440 /etc/sudoers.d/eas-station-setup

# Set up autologin for first boot
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << 'AUTOLOGIN_EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin easuser --noclear %I $TERM
AUTOLOGIN_EOF

echo "System configured"
EOF

# Make hooks executable
chmod +x config/hooks/normal/*.hook.chroot

echo_success "Hooks created"

# Copy EAS Station files to be included in the ISO
echo_info "Copying EAS Station application files..."
mkdir -p config/includes.chroot/opt/eas-station
rsync -av --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    "$REPO_ROOT/" config/includes.chroot/opt/eas-station/

echo_success "Application files copied"

# Create README for ISO
mkdir -p config/includes.binary
cat > config/includes.binary/README.txt << 'EOF'
EAS Station Live ISO
====================

This is a bootable ISO image containing EAS Station pre-installed.

Installation Options:
1. Boot from USB/CD and run live (temporary, no installation)
2. Install to hard drive/SSD (permanent installation)

First Boot:
- Default user: easuser
- Default password: easstation (change on first login)
- A setup wizard will guide you through configuration
- Access web interface at: https://<your-ip-address>

Documentation:
- Full documentation: https://github.com/KR8MER/eas-station
- Installation guide: /opt/eas-station/docs/

Support:
- GitHub Issues: https://github.com/KR8MER/eas-station/issues
- Documentation: https://github.com/KR8MER/eas-station/tree/main/docs

Copyright (c) 2025 Timothy Kramer (KR8MER)
Licensed under AGPL v3 or Commercial License
EOF

echo_success "ISO configuration complete"

# Build the ISO
echo_info "Building ISO (this will take 20-60 minutes)..."
echo_info "Progress will be shown below..."
echo ""

lb build 2>&1 | tee build.log

# Check if build was successful
if [ -f live-image-"$DEBIAN_ARCH".hybrid.iso ]; then
    mv live-image-"$DEBIAN_ARCH".hybrid.iso "$ISO_NAME"
    
    echo ""
    echo_success "ISO build complete!"
    echo ""
    echo "=========================================="
    echo "ISO Image Details"
    echo "=========================================="
    echo "Filename: $ISO_NAME"
    echo "Location: $BUILD_DIR/$ISO_NAME"
    echo "Size: $(du -h "$ISO_NAME" | cut -f1)"
    echo ""
    echo "To burn to USB:"
    echo "  sudo dd if=$ISO_NAME of=/dev/sdX bs=4M status=progress"
    echo "  (replace /dev/sdX with your USB device)"
    echo ""
    echo "Or use a GUI tool like:"
    echo "  - Etcher (https://www.balena.io/etcher/)"
    echo "  - Rufus (Windows)"
    echo "  - UNetbootin"
    echo ""
    echo "=========================================="
else
    echo_error "ISO build failed. Check build.log for details."
    exit 1
fi
