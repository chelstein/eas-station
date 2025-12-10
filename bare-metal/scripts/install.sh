#!/bin/bash
# EAS Station Bare Metal Installation Script
# Copyright (c) 2025 Timothy Kramer (KR8MER)
# Licensed under AGPL v3 or Commercial License

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo_error "This script must be run as root (use sudo)"
    exit 1
fi

echo_info "Starting EAS Station bare metal installation..."

# Configuration variables
INSTALL_DIR="/opt/eas-station"
SERVICE_USER="eas-station"
SERVICE_GROUP="eas-station"
VENV_DIR="${INSTALL_DIR}/venv"
LOG_DIR="/var/log/eas-station"
CONFIG_FILE="${INSTALL_DIR}/.env"

# Detect system architecture
ARCH=$(uname -m)
echo_info "Detected architecture: $ARCH"

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    OS_VERSION=$VERSION_ID
    echo_info "Detected OS: $OS $OS_VERSION"
else
    echo_error "Cannot detect OS. /etc/os-release not found."
    exit 1
fi

# Check if Debian/Ubuntu based
if [ "$OS" != "debian" ] && [ "$OS" != "ubuntu" ] && [ "$OS" != "raspbian" ]; then
    echo_warning "This script is designed for Debian/Ubuntu. Your OS is: $OS"
    read -p "Do you want to continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update package lists
echo_info "Updating package lists..."
apt-get update

# Install system dependencies
echo_info "Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libpq-dev \
    postgresql \
    postgresql-contrib \
    postgis \
    postgresql-17-postgis-3 \
    redis-server \
    nginx \
    certbot \
    python3-certbot-nginx \
    ffmpeg \
    espeak \
    libespeak-ng1 \
    ca-certificates \
    libusb-1.0-0 \
    libusb-1.0-0-dev \
    usbutils \
    python3-soapysdr \
    soapysdr-tools \
    soapysdr-module-rtlsdr \
    soapysdr-module-airspy \
    libairspy0 \
    git \
    curl \
    wget

echo_success "System dependencies installed"

# Create service user and group
echo_info "Creating service user: $SERVICE_USER"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --shell /bin/bash --home-dir "$INSTALL_DIR" --create-home "$SERVICE_USER"
    echo_success "User $SERVICE_USER created"
else
    echo_info "User $SERVICE_USER already exists"
fi

# Add service user to necessary groups for hardware access
echo_info "Adding $SERVICE_USER to hardware access groups..."
usermod -a -G dialout,plugdev,gpio,i2c,spi,audio "$SERVICE_USER" || true

# Create installation directory
echo_info "Setting up installation directory: $INSTALL_DIR"
if [ ! -d "$INSTALL_DIR" ]; then
    mkdir -p "$INSTALL_DIR"
fi

# Copy application files
echo_info "Copying application files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Copy all files except Docker-related and git
rsync -av --exclude='.git' \
    --exclude='Dockerfile*' \
    --exclude='docker-compose*.yml' \
    --exclude='.dockerignore' \
    --exclude='docker-entrypoint*.sh' \
    --exclude='.env' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    "$REPO_ROOT/" "$INSTALL_DIR/"

echo_success "Application files copied"

# Create log directory
echo_info "Creating log directory: $LOG_DIR"
mkdir -p "$LOG_DIR"
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$LOG_DIR"

# Set ownership
echo_info "Setting file permissions..."
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
chmod -R 755 "$INSTALL_DIR"

# Create Python virtual environment
echo_info "Creating Python virtual environment..."
sudo -u "$SERVICE_USER" python3 -m venv "$VENV_DIR"
echo_success "Virtual environment created"

# Install Python dependencies
echo_info "Installing Python dependencies (this may take several minutes)..."
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
echo_success "Python dependencies installed"

# Setup PostgreSQL
echo_info "Configuring PostgreSQL..."
systemctl enable postgresql
systemctl start postgresql

# Create database and user
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'alerts'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE alerts;"
sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename = 'eas_station'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER eas_station WITH PASSWORD 'changeme123';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE alerts TO eas_station;"
sudo -u postgres psql -d alerts -c "CREATE EXTENSION IF NOT EXISTS postgis;"
sudo -u postgres psql -d alerts -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"

echo_success "PostgreSQL configured"

# Install pgAdmin 4 (optional but recommended)
echo_info "Installing pgAdmin 4 for database management..."
if ! command -v pgadmin4 &> /dev/null; then
    # Add pgAdmin repository
    curl -fsS https://www.pgadmin.org/static/packages_pgadmin_org.pub | sudo gpg --dearmor -o /usr/share/keyrings/packages-pgadmin-org.gpg
    echo "deb [signed-by=/usr/share/keyrings/packages-pgadmin-org.gpg] https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt/$(lsb_release -cs) pgadmin4 main" | sudo tee /etc/apt/sources.list.d/pgadmin4.list
    
    # Update and install
    apt-get update
    apt-get install -y pgadmin4-web
    
    # Configure pgAdmin in server mode
    /usr/pgadmin4/bin/setup-web.sh --yes
    
    echo_success "pgAdmin 4 installed (access at http://localhost/pgadmin4)"
    echo_info "Default pgAdmin setup will prompt for email and password"
else
    echo_info "pgAdmin 4 already installed"
fi

# Setup Redis
echo_info "Configuring Redis..."
systemctl enable redis-server
systemctl start redis-server
echo_success "Redis configured"

# Create .env file if it doesn't exist
if [ ! -f "$CONFIG_FILE" ]; then
    echo_info "Creating default configuration file..."
    cat > "$CONFIG_FILE" << 'EOF'
# EAS Station Configuration - Bare Metal Deployment
# Edit this file with your settings

# Flask Secret Key (generate with: python3 -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=change_me_to_a_random_64_character_string

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=alerts
POSTGRES_USER=eas_station
POSTGRES_PASSWORD=changeme123

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Application Settings
FLASK_ENV=production
FLASK_DEBUG=false
DEFAULT_TIMEZONE=America/New_York

# Location Settings (Configure for your area)
DEFAULT_COUNTY_NAME=
DEFAULT_STATE_CODE=
DEFAULT_ZONE_CODES=

# EAS Broadcast Settings
EAS_BROADCAST_ENABLED=false
EAS_ORIGINATOR=WXR
EAS_STATION_ID=NOCALL

# SDR Settings
SDR_ENABLED=false
SDR_ARGS=driver=rtlsdr

# Audio Settings
AUDIO_STREAMING_PORT=5002

# Icecast Settings
ICECAST_ENABLED=false
ICECAST_SERVER=localhost
ICECAST_PORT=8000
ICECAST_SOURCE_PASSWORD=changeme_source
ICECAST_ADMIN_PASSWORD=changeme_admin

# GPIO Settings
GPIO_ENABLED=false

# Hardware Integration
LED_SIGN_ENABLED=false
VFD_DISPLAY_ENABLED=false
EOF
    chown "$SERVICE_USER:$SERVICE_GROUP" "$CONFIG_FILE"
    chmod 600 "$CONFIG_FILE"
    echo_success "Default configuration created"
    echo_warning "Please edit $CONFIG_FILE with your settings"
fi

# Install systemd service files
echo_info "Installing systemd service files..."
cp "$INSTALL_DIR/bare-metal/systemd/"*.service /etc/systemd/system/
cp "$INSTALL_DIR/bare-metal/systemd/"*.target /etc/systemd/system/
systemctl daemon-reload
echo_success "Systemd service files installed"

# Configure nginx
echo_info "Configuring nginx..."
if [ ! -f /etc/nginx/sites-available/eas-station ]; then
    cp "$INSTALL_DIR/bare-metal/config/nginx-eas-station.conf" /etc/nginx/sites-available/eas-station
    
    # Generate self-signed certificate for initial setup
    if [ ! -f /etc/ssl/private/eas-station-selfsigned.key ]; then
        echo_info "Generating self-signed SSL certificate..."
        mkdir -p /etc/ssl/private
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout /etc/ssl/private/eas-station-selfsigned.key \
            -out /etc/ssl/certs/eas-station-selfsigned.crt \
            -subj "/C=US/ST=State/L=City/O=EAS Station/CN=localhost"
        
        # Update nginx config to use self-signed cert
        sed -i 's|ssl_certificate /etc/letsencrypt|#ssl_certificate /etc/letsencrypt|g' /etc/nginx/sites-available/eas-station
        sed -i 's|#ssl_certificate /etc/ssl|ssl_certificate /etc/ssl|g' /etc/nginx/sites-available/eas-station
    fi
    
    # Enable site
    ln -sf /etc/nginx/sites-available/eas-station /etc/nginx/sites-enabled/
    
    # Remove default site if it exists
    rm -f /etc/nginx/sites-enabled/default
    
    # Test nginx configuration
    nginx -t && systemctl reload nginx
    echo_success "Nginx configured"
else
    echo_info "Nginx configuration already exists, skipping"
fi

# Initialize database
echo_info "Initializing database schema..."
cd "$INSTALL_DIR"
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/python" -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database schema created')
" || echo_warning "Database initialization failed - may need manual setup"

# Create udev rules for USB devices
echo_info "Creating udev rules for SDR devices..."
cat > /etc/udev/rules.d/99-eas-station-sdr.rules << 'EOF'
# RTL-SDR
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2832", GROUP="plugdev", MODE="0666"

# Airspy
SUBSYSTEM=="usb", ATTRS{idVendor}=="1d50", ATTRS{idProduct}=="60a1", GROUP="plugdev", MODE="0666"

# HackRF
SUBSYSTEM=="usb", ATTRS{idVendor}=="1d50", ATTRS{idProduct}=="6089", GROUP="plugdev", MODE="0666"
EOF
udevadm control --reload-rules
udevadm trigger
echo_success "Udev rules created"

# Enable and start services
echo_info "Enabling EAS Station services..."
systemctl enable eas-station.target
systemctl enable nginx

echo_success "Installation complete!"
echo ""
echo "=========================================="
echo "EAS Station Installation Summary"
echo "=========================================="
echo "Installation directory: $INSTALL_DIR"
echo "Configuration file: $CONFIG_FILE"
echo "Log directory: $LOG_DIR"
echo "Service user: $SERVICE_USER"
echo ""
echo "Next steps:"
echo "1. Edit configuration: sudo nano $CONFIG_FILE"
echo "2. Generate a secure SECRET_KEY:"
echo "   python3 -c \"import secrets; print(secrets.token_hex(32))\""
echo "3. Configure your location and EAS settings"
echo "4. Start services: sudo systemctl start eas-station.target"
echo "5. Check status: sudo systemctl status eas-station.target"
echo "6. Access web interface: https://localhost (accept self-signed cert)"
echo ""
echo "For production SSL with Let's Encrypt:"
echo "  sudo certbot --nginx -d your-domain.com"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u eas-station-web.service -f"
echo "  sudo tail -f /var/log/eas-station/*.log"
echo ""
echo "=========================================="
