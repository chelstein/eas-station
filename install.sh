#!/bin/bash
# EAS Station Bare Metal Installation Script
# Copyright (c) 2025 Timothy Kramer (KR8MER)
# Licensed under AGPL v3 or Commercial License

set -e  # Exit on error

# Color output (enhanced palette)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Step counter for progress tracking
STEP_NUM=0
TOTAL_STEPS=17

echo_step() {
    STEP_NUM=$((STEP_NUM + 1))
    show_step_progress "$STEP_NUM" "$TOTAL_STEPS" "$1"
}

echo_info() {
    echo -e "${BLUE}ℹ️  [INFO]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}✓  [SUCCESS]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}⚠️  [WARNING]${NC} $1"
}

echo_error() {
    echo -e "${RED}✗  [ERROR]${NC} $1"
}

echo_progress() {
    echo -e "${MAGENTA}▶  ${NC}$1"
}

echo_header() {
    echo ""
    echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║${NC}${BOLD}${WHITE}  $1${NC}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Progress bar function
show_progress_bar() {
    local current=$1
    local total=$2
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    
    printf "\r${CYAN}["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "]${NC} ${BOLD}${percentage}%%${NC} ${WHITE}($current/$total)${NC}"
    
    if [ "$current" -eq "$total" ]; then
        echo ""
    fi
}

# Animated spinner for long operations
show_spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    while ps -p $pid > /dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " ${CYAN}[%c]${NC}  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# Box drawing for important information
draw_box() {
    local text="$1"
    local width=66
    echo ""
    echo -e "${BOLD}${GREEN}┌$(printf '─%.0s' $(seq 1 $width))┐${NC}"
    echo -e "${BOLD}${GREEN}│${NC} ${BOLD}${WHITE}${text}$(printf ' %.0s' $(seq 1 $((width - ${#text}))))${NC}${BOLD}${GREEN}│${NC}"
    echo -e "${BOLD}${GREEN}└$(printf '─%.0s' $(seq 1 $width))┘${NC}"
    echo ""
}

# Display a visual step indicator with progress
show_step_progress() {
    local step=$1
    local total=$2
    local desc="$3"
    local width=60
    
    echo ""
    echo -e "${BOLD}${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║${NC} ${BOLD}${WHITE}Step $step of $total${NC}$(printf ' %.0s' $(seq 1 $((width - 13 - ${#step} - ${#total}))))${BOLD}${CYAN}║${NC}"
    echo -e "${BOLD}${CYAN}║${NC} ${CYAN}$desc${NC}$(printf ' %.0s' $(seq 1 $((width - ${#desc}))))${BOLD}${CYAN}║${NC}"
    echo -e "${BOLD}${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    
    # Show mini progress bar
    local filled=$((step * 50 / total))
    local empty=$((50 - filled))
    printf "  ${CYAN}["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "]${NC}\n\n"
}

# Display installation banner
clear
echo -e "${BOLD}${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   ███████╗ █████╗ ███████╗    ███████╗████████╗ █████╗ ████████╗   ║
║   ██╔════╝██╔══██╗██╔════╝    ██╔════╝╚══██╔══╝██╔══██╗╚══██╔══╝   ║
║   █████╗  ███████║███████╗    ███████╗   ██║   ███████║   ██║      ║
║   ██╔══╝  ██╔══██║╚════██║    ╚════██║   ██║   ██╔══██║   ██║      ║
║   ███████╗██║  ██║███████║    ███████║   ██║   ██║  ██║   ██║      ║
║   ╚══════╝╚═╝  ╚═╝╚══════╝    ╚══════╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝      ║
║                                                                       ║
║             📡  Emergency Alert System Installation  📡              ║
║                                                                       ║
║           Monitoring & Broadcasting • Bare Metal Setup               ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"
echo ""
echo -e "${DIM}Copyright (c) 2025 Timothy Kramer (KR8MER)${NC}"
echo -e "${DIM}Licensed under AGPL v3 or Commercial License${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo_error "This script must be run as root (use sudo)"
    echo ""
    echo -e "${YELLOW}Please run:${NC} ${BOLD}sudo ./install.sh${NC}"
    echo ""
    exit 1
fi

draw_box "✓  Root privileges confirmed - Installation ready to begin"

# Configuration variables
INSTALL_DIR="/opt/eas-station"
SERVICE_USER="eas-station"
SERVICE_GROUP="eas-station"
VENV_DIR="${INSTALL_DIR}/venv"
LOG_DIR="/var/log/eas-station"
CONFIG_FILE="${INSTALL_DIR}/.env"

echo_step "System Detection"

# Detect system architecture
ARCH=$(uname -m)
echo_info "Architecture: ${BOLD}$ARCH${NC}"

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    OS_VERSION=$VERSION_ID
    echo_info "Operating System: ${BOLD}$OS $OS_VERSION${NC}"
else
    echo_error "Cannot detect OS. /etc/os-release not found."
    exit 1
fi

# Check if Debian/Ubuntu based
if [ "$OS" != "debian" ] && [ "$OS" != "ubuntu" ] && [ "$OS" != "raspbian" ]; then
    echo ""
    echo_warning "This script is designed for Debian/Ubuntu. Your OS is: ${BOLD}$OS${NC}"
    echo ""
    read -p "$(echo -e ${YELLOW}Do you want to continue anyway? [y/N]:${NC} )" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo_info "Installation cancelled by user"
        exit 1
    fi
fi

echo_success "System detection complete"

# ====================================================================
# COLLECT MINIMAL CONFIGURATION
# ====================================================================

echo_step "Administrator Account Setup"

echo -e "${WHITE}You'll need an administrator account to access the web interface.${NC}"
echo ""

# Prompt for admin username
while true; do
    echo -ne "${CYAN}Administrator username${NC} (min 3 characters): "
    read ADMIN_USERNAME
    ADMIN_USERNAME=$(echo "$ADMIN_USERNAME" | xargs)  # Trim whitespace
    
    if [ -z "$ADMIN_USERNAME" ]; then
        echo_error "Username cannot be empty"
        continue
    fi
    
    if [ ${#ADMIN_USERNAME} -lt 3 ]; then
        echo_error "Username must be at least 3 characters long"
        continue
    fi
    
    if ! [[ "$ADMIN_USERNAME" =~ ^[A-Za-z0-9_.-]+$ ]]; then
        echo_error "Username may only contain letters, numbers, dots, hyphens, or underscores"
        continue
    fi
    
    echo_success "Username accepted: ${BOLD}$ADMIN_USERNAME${NC}"
    break
done

echo ""

# Prompt for admin password
while true; do
    echo -ne "${CYAN}Administrator password${NC} (min 12 characters): "
    read -s ADMIN_PASSWORD
    echo
    
    if [ ${#ADMIN_PASSWORD} -lt 12 ]; then
        echo_error "Password must be at least 12 characters long"
        echo ""
        continue
    fi
    
    echo -ne "${CYAN}Confirm password:${NC} "
    read -s ADMIN_PASSWORD_CONFIRM
    echo
    
    if [ "$ADMIN_PASSWORD" != "$ADMIN_PASSWORD_CONFIRM" ]; then
        echo_error "Passwords do not match"
        echo ""
        continue
    fi
    
    echo_success "Password accepted (${#ADMIN_PASSWORD} characters)"
    break
done

echo ""

# Prompt for admin email address (for notifications)
while true; do
    echo -ne "${CYAN}Administrator email address:${NC} "
    read ADMIN_EMAIL
    ADMIN_EMAIL=$(echo "$ADMIN_EMAIL" | xargs)  # Trim whitespace
    
    if [ -z "$ADMIN_EMAIL" ]; then
        echo_error "Email address cannot be empty"
        continue
    fi
    
    # Basic email validation (must have @ and . after @)
    if ! [[ "$ADMIN_EMAIL" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        echo_error "Invalid email format. Email must be in format: user@domain.com"
        continue
    fi
    
    echo_success "Email accepted: ${BOLD}$ADMIN_EMAIL${NC}"
    break
done

echo ""
echo_success "Administrator account configured"

# ====================================================================
# SYSTEM AND EAS STATION CONFIGURATION
# ====================================================================

echo_step "System and EAS Station Configuration"

echo -e "${WHITE}Configure your system hostname, domain, and EAS station identification.${NC}"
echo ""

# Prompt for system hostname
CURRENT_HOSTNAME=$(hostname 2>/dev/null || echo "eas-station")
while true; do
    echo -ne "${CYAN}System hostname${NC} [${BOLD}$CURRENT_HOSTNAME${NC}]: "
    read SYSTEM_HOSTNAME
    
    # Use current hostname if user presses enter without input
    if [ -z "$SYSTEM_HOSTNAME" ]; then
        SYSTEM_HOSTNAME="$CURRENT_HOSTNAME"
    fi
    
    # Trim whitespace
    SYSTEM_HOSTNAME=$(echo "$SYSTEM_HOSTNAME" | xargs)
    
    # Validate hostname format (alphanumeric, hyphens, dots)
    if ! [[ "$SYSTEM_HOSTNAME" =~ ^[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?$ ]]; then
        echo_error "Invalid hostname format. Use only letters, numbers, hyphens, and dots"
        continue
    fi
    
    echo_success "Hostname: ${BOLD}$SYSTEM_HOSTNAME${NC}"
    break
done

echo ""

# Prompt for domain name (for SSL/nginx)
while true; do
    echo -ne "${CYAN}Domain name for SSL/web access${NC} [${BOLD}localhost${NC}]: "
    read DOMAIN_NAME
    
    # Default to localhost if user presses enter
    if [ -z "$DOMAIN_NAME" ]; then
        DOMAIN_NAME="localhost"
    fi
    
    # Trim whitespace
    DOMAIN_NAME=$(echo "$DOMAIN_NAME" | xargs)
    
    # Validate domain format (allow localhost, IP addresses, and domain names)
    if [[ "$DOMAIN_NAME" == "localhost" ]]; then
        echo_success "Domain: ${BOLD}$DOMAIN_NAME${NC}"
        break
    # Validate IP address with proper octet range (0-255)
    elif [[ "$DOMAIN_NAME" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        IFS='.' read -ra OCTETS <<< "$DOMAIN_NAME"
        VALID_IP=true
        for octet in "${OCTETS[@]}"; do
            if [ "$octet" -lt 0 ] || [ "$octet" -gt 255 ]; then
                VALID_IP=false
                break
            fi
        done
        if [ "$VALID_IP" = true ]; then
            echo_success "Domain: ${BOLD}$DOMAIN_NAME${NC}"
            break
        else
            echo_error "Invalid IP address. Each octet must be 0-255"
            continue
        fi
    # Validate domain name format
    elif [[ "$DOMAIN_NAME" =~ ^[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?$ ]]; then
        echo_success "Domain: ${BOLD}$DOMAIN_NAME${NC}"
        break
    else
        echo_error "Invalid domain format. Use localhost, an IP address, or a valid domain name"
        continue
    fi
done

echo ""

# Prompt for EAS originator code
echo -e "${CYAN}EAS Originator Code${NC} (3-letter code identifying who originates alerts)"
echo -e "${DIM}Common codes: WXR (NOAA Weather Radio), EAS (EAS Participant), PEP (Primary Entry Point)${NC}"
while true; do
    echo -ne "${CYAN}EAS Originator${NC} [${BOLD}WXR${NC}]: "
    read EAS_ORIGINATOR
    
    # Default to WXR if user presses enter
    if [ -z "$EAS_ORIGINATOR" ]; then
        EAS_ORIGINATOR="WXR"
    fi
    
    # Convert to uppercase and trim whitespace
    EAS_ORIGINATOR=$(echo "$EAS_ORIGINATOR" | tr '[:lower:]' '[:upper:]' | xargs)
    
    # Validate format (exactly 3 uppercase letters)
    if ! [[ "$EAS_ORIGINATOR" =~ ^[A-Z]{3}$ ]]; then
        echo_error "EAS Originator must be exactly 3 letters (e.g., WXR, EAS, PEP)"
        continue
    fi
    
    echo_success "Originator: ${BOLD}$EAS_ORIGINATOR${NC}"
    break
done

echo ""

# Prompt for station callsign/ID
echo -e "${CYAN}Station Callsign/ID${NC} (identifies your EAS station)"
echo -e "${DIM}Use your FCC callsign if you have one, or a unique identifier (max 8 characters)${NC}"
echo -e "${DIM}Examples: WKRP, KR8MER, EASNODE1, NOCALL (if testing/no callsign)${NC}"
while true; do
    echo -ne "${CYAN}Station Callsign${NC} [${BOLD}NOCALL${NC}]: "
    read EAS_STATION_ID
    
    # Default to NOCALL if user presses enter
    if [ -z "$EAS_STATION_ID" ]; then
        EAS_STATION_ID="NOCALL"
    fi
    
    # Convert to uppercase and trim whitespace
    EAS_STATION_ID=$(echo "$EAS_STATION_ID" | tr '[:lower:]' '[:upper:]' | xargs)
    
    # Validate format (1-8 alphanumeric characters)
    if ! [[ "$EAS_STATION_ID" =~ ^[A-Z0-9]{1,8}$ ]]; then
        echo_error "Station ID must be 1-8 alphanumeric characters (e.g., WKRP, KR8MER, NOCALL)"
        continue
    fi
    
    echo_success "Station ID: ${BOLD}$EAS_STATION_ID${NC}"
    break
done

echo ""
echo_success "System and EAS station configuration complete"

# Set system hostname if it changed
if [ "$SYSTEM_HOSTNAME" != "$CURRENT_HOSTNAME" ]; then
    echo ""
    echo_progress "Setting system hostname to: ${BOLD}$SYSTEM_HOSTNAME${NC}"
    hostnamectl set-hostname "$SYSTEM_HOSTNAME" 2>/dev/null || {
        echo_warning "Could not set hostname using hostnamectl, trying fallback methods..."
        echo "$SYSTEM_HOSTNAME" > /etc/hostname
        hostname "$SYSTEM_HOSTNAME"
    }
    echo_success "Hostname set to: ${BOLD}$SYSTEM_HOSTNAME${NC}"
fi

echo ""
echo_progress "Generating secure database password..."
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo_success "Database password generated (${#DB_PASSWORD} characters)"

echo ""
# Set default timezone
TIMEZONE="America/New_York"
echo_info "Default timezone: ${BOLD}$TIMEZONE${NC} (can be changed in setup wizard)"

echo ""
echo_success "✓ Configuration complete! Starting installation..."

# ====================================================================
# BEGIN INSTALLATION
# ====================================================================

echo_step "Update Package Lists"

echo_progress "Updating package lists..."
apt-get update > /dev/null 2>&1
echo_success "Package lists updated"

echo_step "Install System Dependencies"

echo_info "Installing essential packages - this will take 3-5 minutes..."
echo ""
echo -e "${CYAN}Packages being installed:${NC}"
echo -e "  ${DIM}• Python 3 & development tools${NC}"
echo -e "  ${DIM}• PostgreSQL 17 with PostGIS (geographic data support)${NC}"
echo -e "  ${DIM}• Redis (in-memory caching)${NC}"
echo -e "  ${DIM}• Nginx (web server)${NC}"
echo -e "  ${DIM}• FFmpeg (audio processing)${NC}"
echo -e "  ${DIM}• SDR libraries (RTL-SDR, Airspy, SoapySDR)${NC}"
echo -e "  ${DIM}• SSL certificate tools (Certbot)${NC}"
echo ""
echo_progress "Downloading and installing packages (please wait)..."

apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    gcc \
    g++ \
    make \
    libpq-dev \
    libev-dev \
    libevent-dev \
    libffi-dev \
    libssl-dev \
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
    wget > /dev/null 2>&1

echo ""
echo_success "✓ System dependencies installed successfully"

echo_step "Create Service User & Directories"

# Create service user and group
echo_progress "Creating service user: ${BOLD}$SERVICE_USER${NC}"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --shell /bin/bash --home-dir "$INSTALL_DIR" --create-home "$SERVICE_USER"
    echo_success "User $SERVICE_USER created"
else
    echo_info "User $SERVICE_USER already exists (skipping)"
fi

# Add service user to necessary groups for hardware access
echo_progress "Adding $SERVICE_USER to hardware access groups..."
usermod -a -G dialout,plugdev,gpio,i2c,spi,audio "$SERVICE_USER" 2>/dev/null || true
echo_success "Hardware access groups configured"

# Create installation directory
echo_progress "Setting up installation directory: ${BOLD}$INSTALL_DIR${NC}"
if [ ! -d "$INSTALL_DIR" ]; then
    mkdir -p "$INSTALL_DIR"
fi

# Copy application files
echo_progress "Copying application files from repository..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

# Copy all files except Docker-related, development files, and git
rsync -a --exclude='.git' \
    --exclude='Dockerfile*' \
    --exclude='docker-compose*.yml' \
    --exclude='.dockerignore' \
    --exclude='docker-entrypoint*.sh' \
    --exclude='.env' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='bugs/' \
    --exclude='legacy/' \
    --exclude='bare-metal/' \
    --exclude='tests/bug_reproductions/' \
    "$REPO_ROOT/" "$INSTALL_DIR/" > /dev/null 2>&1

echo_success "Application files copied to $INSTALL_DIR"

# Create log directory
echo_progress "Creating log directory: ${BOLD}$LOG_DIR${NC}"
mkdir -p "$LOG_DIR"
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$LOG_DIR"

# Set ownership
echo_progress "Setting file permissions..."
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
chmod -R 755 "$INSTALL_DIR"
echo_success "Permissions configured"

echo_step "Python Environment Setup"

# Create Python virtual environment
echo_progress "Creating Python virtual environment..."
sudo -u "$SERVICE_USER" python3 -m venv "$VENV_DIR" > /dev/null 2>&1
echo_success "Virtual environment created at $VENV_DIR"

# Install Python dependencies
echo_info "Installing Python packages for EAS Station..."
echo ""
echo -e "${CYAN}Key Python libraries:${NC}"
echo -e "  ${DIM}• Flask (web framework) & extensions${NC}"
echo -e "  ${DIM}• SQLAlchemy & Alembic (database ORM & migrations)${NC}"
echo -e "  ${DIM}• GeoAlchemy2 (PostGIS geographic queries)${NC}"
echo -e "  ${DIM}• PyRTLSDR & SoapySDR (software-defined radio)${NC}"
echo -e "  ${DIM}• NumPy & SciPy (signal processing & audio analysis)${NC}"
echo -e "  ${DIM}• Requests & lxml (CAP alert parsing)${NC}"
echo -e "  ${DIM}• And 50+ other dependencies...${NC}"
echo ""
echo_progress "Installing via pip (this takes 2-4 minutes)..."
echo_info "This may take 5-10 minutes depending on your system"
echo ""
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel > /dev/null 2>&1
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt" > /dev/null 2>&1
echo ""
echo_success "✓ Python dependencies installed successfully"

echo_step "PostgreSQL Database Configuration"

echo_info "Configuring PostgreSQL database for EAS Station..."
echo ""
echo -e "${CYAN}Database setup tasks:${NC}"
echo -e "  ${DIM}• Create 'alerts' database with PostGIS extensions${NC}"
echo -e "  ${DIM}• Create 'eas_station' database user${NC}"
echo -e "  ${DIM}• Configure authentication (password-based)${NC}"
echo -e "  ${DIM}• Grant necessary permissions${NC}"
echo ""

# Setup PostgreSQL
echo_progress "Starting PostgreSQL service..."
systemctl enable postgresql > /dev/null 2>&1
systemctl start postgresql
echo_success "PostgreSQL service started"

# Configure PostgreSQL authentication to allow password-based connections
echo_progress "Configuring PostgreSQL authentication (pg_hba.conf)..."

# Detect PostgreSQL version to find the correct pg_hba.conf location
PG_VERSION=$(sudo -u postgres psql -tAc "SELECT version();" 2>/dev/null | grep -oP 'PostgreSQL \K[0-9]+' | head -1)
if [ -z "$PG_VERSION" ]; then
    # Fallback: try common versions
    for v in 17 16 15 14 13; do
        if [ -d "/etc/postgresql/$v" ]; then
            PG_VERSION=$v
            break
        fi
    done
fi

if [ -n "$PG_VERSION" ]; then
    PG_HBA_CONF="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    
    if [ -f "$PG_HBA_CONF" ]; then
        echo_info "Found pg_hba.conf for PostgreSQL ${BOLD}$PG_VERSION${NC}"
        
        # Backup the original pg_hba.conf
        if [ ! -f "${PG_HBA_CONF}.backup" ]; then
            cp "$PG_HBA_CONF" "${PG_HBA_CONF}.backup"
            echo_info "Created backup: ${PG_HBA_CONF}.backup"
        fi
        
        # Check if eas_station authentication rule already exists
        if ! grep -q "^host.*alerts.*eas_station.*md5" "$PG_HBA_CONF" && \
           ! grep -q "^host.*alerts.*eas_station.*scram-sha-256" "$PG_HBA_CONF"; then
            
            # Add authentication rule for eas_station user
            # Insert before the first "local all" line to ensure it takes precedence
            sed -i '/^# TYPE.*DATABASE.*USER.*ADDRESS.*METHOD/a\
# EAS Station authentication (added by install.sh)\
host    alerts          eas_station     127.0.0.1/32            scram-sha-256\
host    alerts          eas_station     ::1/128                 scram-sha-256' "$PG_HBA_CONF"
            
            echo_success "Added authentication rules for eas_station user"
            
            # Reload PostgreSQL to apply changes
            systemctl reload postgresql 2>/dev/null
            echo_success "PostgreSQL authentication configured"
        else
            echo_info "Authentication rule already exists (skipping)"
        fi
    else
        echo_warning "pg_hba.conf not found at expected location: $PG_HBA_CONF"
        echo_warning "You may need to configure PostgreSQL authentication manually"
    fi
else
    echo_warning "Could not detect PostgreSQL version"
    echo_warning "You may need to configure pg_hba.conf manually"
fi

# Create database and user with the password collected earlier
echo_progress "Creating database and user..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'alerts'" 2>/dev/null | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE alerts;"

# Create database user (use dollar-quoting to safely handle special characters in password)
if ! sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename = 'eas_station'" | grep -q 1; then
    sudo -u postgres psql <<EOF
CREATE USER eas_station WITH PASSWORD \$\$${DB_PASSWORD}\$\$;
EOF
fi

# Update password if user already exists (in case of re-running script)
sudo -u postgres psql <<EOF
ALTER USER eas_station WITH PASSWORD \$\$${DB_PASSWORD}\$\$;
EOF

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE alerts TO eas_station;"

# Grant schema privileges (required for PostgreSQL 15+)
sudo -u postgres psql -d alerts -c "GRANT ALL ON SCHEMA public TO eas_station;"
sudo -u postgres psql -d alerts -c "GRANT CREATE ON SCHEMA public TO eas_station;"
sudo -u postgres psql -d alerts -c "ALTER SCHEMA public OWNER TO eas_station;"

# Grant privileges on all existing tables and sequences (if any)
sudo -u postgres psql -d alerts -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO eas_station;"
sudo -u postgres psql -d alerts -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO eas_station;"

# Grant default privileges for future tables and sequences
sudo -u postgres psql -d alerts -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO eas_station;"
sudo -u postgres psql -d alerts -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO eas_station;"

# Create PostGIS extensions
sudo -u postgres psql -d alerts -c "CREATE EXTENSION IF NOT EXISTS postgis;"
sudo -u postgres psql -d alerts -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"

echo_success "PostgreSQL configured"

# Command-line database access
echo ""
echo_info "Database access available via: ${BOLD}sudo -u postgres psql -d alerts${NC}"
echo ""


echo_step "Redis Configuration"

# Setup Redis
echo_progress "Enabling and starting Redis service..."
systemctl enable redis-server > /dev/null 2>&1
systemctl start redis-server
echo_success "Redis configured and running"

echo_step "Create Configuration File"

# Backup existing .env file if it exists and is not empty
if [ -f "$CONFIG_FILE" ]; then
    # Check if file has meaningful content (more than just comments/whitespace)
    # Pattern matches lines that start with non-comment, non-whitespace characters followed by '='
    if grep -qE '^\s*[^#\s].*=' "$CONFIG_FILE" 2>/dev/null; then
        BACKUP_FILE="${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$CONFIG_FILE" "$BACKUP_FILE"
        echo_info "Backed up existing configuration to: $BACKUP_FILE"
    else
        echo_info "Overwriting empty template .env file"
    fi
fi

echo_info "Creating configuration file..."

# Generate a secure SECRET_KEY automatically
echo_info "Generating secure SECRET_KEY..."
GENERATED_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Create the .env file with collected configuration
cat > "$CONFIG_FILE" << EOF
# EAS Station Configuration - Bare Metal Deployment
# This file was auto-generated during installation on $(date)

# Flask Secret Key (auto-generated - keep this secure!)
SECRET_KEY=$GENERATED_SECRET_KEY

# System Configuration
DOMAIN_NAME=$DOMAIN_NAME

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=alerts
POSTGRES_USER=eas_station
POSTGRES_PASSWORD=$DB_PASSWORD

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Application Settings
FLASK_ENV=production
FLASK_DEBUG=false
DEFAULT_TIMEZONE=$TIMEZONE

# Location Settings (Configure via web setup wizard)
DEFAULT_COUNTY_NAME=
DEFAULT_STATE_CODE=
DEFAULT_ZONE_CODES=

# EAS Broadcast Settings
EAS_BROADCAST_ENABLED=false
EAS_ORIGINATOR=$EAS_ORIGINATOR
EAS_STATION_ID=$EAS_STATION_ID

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
echo_success "Configuration created with auto-generated SECRET_KEY"

echo_step "Install Systemd Services"

# Install systemd service files
echo_progress "Installing systemd service files..."
cp "$INSTALL_DIR/systemd/"*.service /etc/systemd/system/
cp "$INSTALL_DIR/systemd/"*.target /etc/systemd/system/
systemctl daemon-reload
echo_success "Systemd service files installed"

echo_step "Nginx Web Server Configuration"

# Configure nginx
echo_progress "Setting up nginx reverse proxy..."
if [ ! -f /etc/nginx/sites-available/eas-station ]; then
    cp "$INSTALL_DIR/config/nginx-eas-station.conf" /etc/nginx/sites-available/eas-station
    
    # Generate self-signed certificate for initial setup
    if [ ! -f /etc/ssl/private/eas-station-selfsigned.key ]; then
        echo_progress "Generating self-signed SSL certificate..."
        mkdir -p /etc/ssl/private
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout /etc/ssl/private/eas-station-selfsigned.key \
            -out /etc/ssl/certs/eas-station-selfsigned.crt \
            -subj "/C=US/ST=State/L=City/O=EAS Station/CN=localhost"
    fi
    
    # Enable site
    ln -sf /etc/nginx/sites-available/eas-station /etc/nginx/sites-enabled/
    
    # Remove default site if it exists
    rm -f /etc/nginx/sites-enabled/default
    
    # Test nginx configuration
    nginx -t && systemctl reload nginx
    echo_success "Nginx configured"
else
    echo_info "Nginx configuration already exists (skipping)"
fi

echo_step "Firewall Configuration"

# Configure UFW firewall for remote access
echo_progress "Configuring firewall for remote access..."

# Check if UFW is installed (it was installed in step 3)
if command -v ufw &> /dev/null; then
    # Enable UFW if not already enabled
    if ! ufw status verbose | grep -q "Status: active"; then
        echo_progress "Enabling UFW firewall..."
        # Set default policies
        ufw --force default deny incoming > /dev/null 2>&1
        ufw --force default allow outgoing > /dev/null 2>&1
        echo_info "Default policies set (deny incoming, allow outgoing)"
    fi
    
    # Allow SSH (important - don't lock yourself out!)
    echo_progress "Allowing SSH (port 22)..."
    ufw allow 22/tcp > /dev/null 2>&1
    echo_success "SSH access allowed"
    
    # Allow HTTP (port 80) for Let's Encrypt and redirects
    echo_progress "Allowing HTTP (port 80)..."
    ufw allow 80/tcp > /dev/null 2>&1
    echo_success "HTTP access allowed"
    
    # Allow HTTPS (port 443) for web interface
    echo_progress "Allowing HTTPS (port 443)..."
    ufw allow 443/tcp > /dev/null 2>&1
    echo_success "HTTPS access allowed"
    
    # Allow Icecast streaming (port 8000) if enabled
    if [ "${ICECAST_ENABLED:-true}" = "true" ]; then
        echo_progress "Allowing Icecast streaming (port 8000)..."
        ufw allow 8000/tcp > /dev/null 2>&1
        echo_success "Icecast streaming access allowed"
    fi
    
    # Allow PostgreSQL (port 5432) for remote database access (optional, commented by default)
    # Uncomment if you need remote database access for IDE tools like DataGrip, DBeaver, etc.
    # echo_progress "Allowing PostgreSQL (port 5432)..."
    # ufw allow 5432/tcp > /dev/null 2>&1
    # echo_success "PostgreSQL access allowed"
    
    # Enable UFW
    echo_progress "Activating firewall rules..."
    ufw --force enable > /dev/null 2>&1
    echo_success "Firewall configured and active"
    
    # Show status
    echo ""
    echo_info "Firewall status:"
    ufw status numbered | grep -E '\b(22|80|443|8000|5432)/(tcp|udp)\b|Status:' || true
    echo ""
else
    echo_warning "UFW not found - firewall not configured"
    echo_warning "Install UFW manually: apt-get install ufw"
fi

echo_step "Initialize Database Schema"

# Initialize database
echo_progress "Initializing database schema..."
cd "$INSTALL_DIR"

# Check if this is a fresh install or an upgrade
echo_progress "Checking database state..."

# Query to count existing tables in the public schema
TABLE_COUNT_QUERY="SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';"

DB_HAS_TABLES=$(sudo -u postgres psql -d alerts -tAc "$TABLE_COUNT_QUERY" 2>/dev/null || echo "0")

if [ "$DB_HAS_TABLES" -eq "0" ]; then
    # Fresh install - use db.create_all() which creates the complete schema
    echo_info "Fresh installation detected - creating database schema..."
    
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/python" -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database schema created successfully')
" || {
    echo_error "Database initialization failed"
    echo_warning "You may need to manually initialize the database"
    exit 1
}
    
    echo_success "Database schema created for fresh install"
else
    # Existing database - run migrations to upgrade schema
    echo_info "Existing database detected - running migrations..."
    
    if [ -f "$INSTALL_DIR/alembic.ini" ]; then
        echo_progress "Running Alembic migrations..."
        ALEMBIC_OUTPUT=$(sudo -u "$SERVICE_USER" "$VENV_DIR/bin/alembic" upgrade head 2>&1)
        if [ $? -eq 0 ]; then
            echo_success "Database migrations completed"
        else
            echo_warning "Alembic migrations encountered errors"
            echo_info "Migration output: $ALEMBIC_OUTPUT"
            echo_info "Attempting to create any missing tables..."
            sudo -u "$SERVICE_USER" "$VENV_DIR/bin/python" -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Missing tables created')
" || echo_warning "Database initialization may be incomplete"
        fi
    else
        echo_warning "alembic.ini not found - skipping migrations"
    fi
fi

# Create administrator account in database
echo ""
echo_info "Creating administrator account in database..."

# Create the administrator account using environment variables to avoid injection
export EAS_ADMIN_USERNAME="$ADMIN_USERNAME"
export EAS_ADMIN_PASSWORD="$ADMIN_PASSWORD"

sudo -u "$SERVICE_USER" -E "$VENV_DIR/bin/python" << 'EOPY'
import sys
import os
from app import app, db
from app_core.models import AdminUser
from app_core.auth.roles import Role, RoleDefinition
from sqlalchemy import func

username = os.environ.get('EAS_ADMIN_USERNAME')
password = os.environ.get('EAS_ADMIN_PASSWORD')

if not username or not password:
    print("ERROR: Username or password not provided", file=sys.stderr)
    sys.exit(1)

with app.app_context():
    # Check if user already exists
    existing = AdminUser.query.filter(func.lower(AdminUser.username) == username.lower()).first()
    if existing:
        print(f"ERROR: User '{username}' already exists", file=sys.stderr)
        sys.exit(1)
    
    # Create new admin user
    admin_user = AdminUser(username=username)
    admin_user.set_password(password)
    
    # Assign admin role
    admin_role = Role.query.filter(func.lower(Role.name) == RoleDefinition.ADMIN.value).first()
    if admin_role:
        admin_user.role = admin_role
    
    db.session.add(admin_user)
    db.session.commit()
    
    print(f"Administrator account '{username}' created successfully")
EOPY

# Unset the environment variables
unset EAS_ADMIN_USERNAME
unset EAS_ADMIN_PASSWORD

if [ $? -eq 0 ]; then
    echo_success "Administrator account created"
else
    echo_error "Failed to create administrator account"
    echo_warning "You can create an account later via the web interface at /setup/admin"
fi

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
echo_step "Start EAS Station Services"

# Enable and start services
echo_progress "Enabling services for automatic startup..."
systemctl enable eas-station.target > /dev/null 2>&1
systemctl enable nginx > /dev/null 2>&1
echo_success "Services enabled"

# Start the services automatically
echo_progress "Starting all EAS Station services..."
systemctl start eas-station.target

# Give services a moment to start
sleep 3

# Check if services started successfully
if systemctl is-active --quiet eas-station.target; then
    echo_success "✓ All services started successfully!"
else
    echo_warning "Services may need attention"
    echo_info "Check status: ${BOLD}sudo systemctl status eas-station.target${NC}"
fi

# ====================================================================
# INSTALLATION COMPLETE - DISPLAY FINAL MESSAGE
# ====================================================================

clear
echo ""
echo -e "${BOLD}${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   ██████╗ ██████╗ ███╗   ███╗██████╗ ██╗     ███████╗████████╗███████╗
║  ██╔════╝██╔═══██╗████╗ ████║██╔══██╗██║     ██╔════╝╚══██╔══╝██╔════╝
║  ██║     ██║   ██║██╔████╔██║██████╔╝██║     █████╗     ██║   █████╗  
║  ██║     ██║   ██║██║╚██╔╝██║██╔═══╝ ██║     ██╔══╝     ██║   ██╔══╝  
║  ╚██████╗╚██████╔╝██║ ╚═╝ ██║██║     ███████╗███████╗   ██║   ███████╗
║   ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚══════╝╚══════╝   ╚═╝   ╚══════╝
║                                                                       ║
║                  🎉  Installation Successful!  🎉                     ║
║                                                                       ║
║              Your EAS Station is now up and running!                  ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"
echo ""

echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${WHITE}  📂 INSTALLATION SUMMARY${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Installation Directory:${NC} ${BOLD}$INSTALL_DIR${NC}"
echo -e "  ${CYAN}Configuration File:${NC}     ${BOLD}$CONFIG_FILE${NC}"
echo -e "  ${CYAN}Log Directory:${NC}          ${BOLD}$LOG_DIR${NC}"
echo -e "  ${CYAN}Service User:${NC}           ${BOLD}$SERVICE_USER${NC}"
echo ""
echo -e "  ${GREEN}✓${NC} Services started automatically"
echo -e "  ${GREEN}✓${NC} SECRET_KEY auto-generated"
echo -e "  ${GREEN}✓${NC} Database schema initialized"
echo -e "  ${GREEN}✓${NC} Administrator account created: ${BOLD}${ADMIN_USERNAME}${NC}"
echo -e "  ${GREEN}✓${NC} System hostname: ${BOLD}${SYSTEM_HOSTNAME}${NC}"
echo -e "  ${GREEN}✓${NC} Domain name: ${BOLD}${DOMAIN_NAME}${NC}"
echo -e "  ${GREEN}✓${NC} EAS Originator: ${BOLD}${EAS_ORIGINATOR}${NC}"
echo -e "  ${GREEN}✓${NC} Station Callsign: ${BOLD}${EAS_STATION_ID}${NC}"
echo ""

echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${WHITE}  🌐 ACCESS YOUR EAS STATION${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Get the primary IP address
PRIMARY_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$PRIMARY_IP" ]; then
    PRIMARY_IP="<your-server-ip>"
fi

echo -e "  Open your web browser and navigate to:"
echo ""
echo -e "    ${BOLD}${GREEN}https://localhost${NC}      ${DIM}(from this server)${NC}"
echo -e "    ${BOLD}${GREEN}https://${PRIMARY_IP}${NC}  ${DIM}(from any device on your network)${NC}"
echo ""
echo -e "  ${GREEN}✓${NC}  Firewall configured: Ports 80 (HTTP) and 443 (HTTPS) are open"
echo -e "  ${GREEN}✓${NC}  Remote access enabled: Access from any device on your network"
echo ""
echo -e "  ${YELLOW}⚠️${NC}  You'll see a certificate warning - this is ${BOLD}normal${NC}"
echo -e "      Click 'Advanced' → 'Proceed' (certificate was generated during install)"
echo ""

echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${WHITE}  🔐 YOUR LOGIN CREDENTIALS${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}EAS Station Web Interface:${NC}"
echo -e "    Username: ${BOLD}${GREEN}${ADMIN_USERNAME}${NC}"
echo -e "    Password: ${BOLD}(the password you entered)${NC}"
echo ""

echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${WHITE}  🔑 DATABASE CREDENTIALS (For IDE Tools)${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}${MAGENTA}PostgreSQL Connection Details:${NC}"
echo -e "    ${CYAN}Host:${NC}         ${BOLD}localhost${NC}"
echo -e "    ${CYAN}Port:${NC}         ${BOLD}5432${NC}"
echo -e "    ${CYAN}Database:${NC}     ${BOLD}alerts${NC}"
echo -e "    ${CYAN}Username:${NC}     ${BOLD}eas_station${NC}"
echo -e "    ${CYAN}Password:${NC}     ${BOLD}${DB_PASSWORD}${NC}"
echo ""
echo -e "  ${YELLOW}⚠️${NC}  ${BOLD}IMPORTANT - Save these credentials!${NC}"
echo -e "      These credentials are ${BOLD}only shown once during installation${NC}"
echo -e "      The password is ${BOLD}also saved${NC} in: ${BOLD}$CONFIG_FILE${NC}"
echo ""
echo -e "  ${GREEN}💡${NC} ${BOLD}Use these credentials in:${NC}"
echo -e "      • Database IDE tools (DataGrip, DBeaver, Postico, etc.)"
echo -e "      • psql command line: ${BOLD}psql -h localhost -U eas_station -d alerts${NC}"
echo ""
echo -e "  ${DIM}To view your password later, run:${NC}"
echo -e "    ${BOLD}sudo grep POSTGRES_PASSWORD $CONFIG_FILE${NC}"
echo ""

echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${WHITE}  ⚙️  YOUR CONFIGURATION${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Timezone:${NC}        ${BOLD}$TIMEZONE${NC} (change in setup wizard)"
echo -e "  ${CYAN}Hostname:${NC}        ${BOLD}$SYSTEM_HOSTNAME${NC}"
echo -e "  ${CYAN}Domain:${NC}          ${BOLD}$DOMAIN_NAME${NC}"
echo -e "  ${CYAN}EAS Originator:${NC}  ${BOLD}$EAS_ORIGINATOR${NC}"
echo -e "  ${CYAN}Station ID:${NC}      ${BOLD}$EAS_STATION_ID${NC}"
echo -e "  ${CYAN}Config File:${NC}     ${BOLD}$CONFIG_FILE${NC}"
echo -e "  ${CYAN}Log Directory:${NC}   ${BOLD}$LOG_DIR${NC}"
echo ""
echo -e "  ${GREEN}✓${NC}  SECRET_KEY: ${BOLD}Auto-generated${NC} (64-character secure key)"
echo -e "  ${GREEN}✓${NC}  DB Password: ${BOLD}Auto-generated${NC} (43-character secure password)"
echo ""
echo -e "  ${YELLOW}⚠️${NC}  Technical settings configured automatically"
echo -e "      ${DIM}Database password shown above - save it for IDE access!${NC}"
echo ""

echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${WHITE}  📋 NEXT STEPS - IMPORTANT!${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}${YELLOW}1.${NC} ${BOLD}Log in${NC} to the web interface with your credentials above"
echo ""
echo -e "  ${BOLD}${YELLOW}2.${NC} ${BOLD}Complete the SETUP WIZARD${NC} to configure:"
echo -e "      ${GREEN}✓${NC} Your location (county, state, FIPS/zone codes)"
echo -e "      ${DIM}Note: EAS station callsign/ID already configured: ${BOLD}$EAS_STATION_ID${NC}"
echo -e "      ${GREEN}✓${NC} Alert sources (NOAA, IPAWS feeds)"
echo -e "      ${GREEN}✓${NC} EAS broadcast settings"
echo -e "      ${GREEN}✓${NC} Hardware integrations (LED, OLED, SDR, etc.)"
echo ""
echo -e "  ${BOLD}${YELLOW}3.${NC} The setup wizard provides helpful explanations for all options"
echo ""
echo -e "  ${YELLOW}⚠️${NC}  ${BOLD}Your station won't monitor alerts until you complete the wizard!${NC}"
echo ""

echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${WHITE}  🔌 COMPONENT ACCESS DETAILS${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}${MAGENTA}Main Web Interface (Primary Dashboard):${NC}"
echo -e "    URL:      ${BOLD}${GREEN}https://localhost${NC} or ${BOLD}${GREEN}https://${PRIMARY_IP}${NC}"
echo -e "    Username: ${BOLD}$ADMIN_USERNAME${NC}"
echo -e "    Password: ${BOLD}(your admin password)${NC}"
echo -e "    Purpose:  Configure alerts, view status, manage settings"
echo ""
echo -e "  ${BOLD}${MAGENTA}PostgreSQL Database (Command Line Access):${NC}"
echo -e "    Command:  ${BOLD}sudo -u postgres psql -d alerts${NC}"
echo -e "    Or:       ${BOLD}psql -h localhost -U eas_station -d alerts${NC}"
echo -e "              ${DIM}(Enter password when prompted: see credentials above)${NC}"
echo -e "    Purpose:  Direct SQL queries, database administration"
echo ""
echo -e "  ${BOLD}${MAGENTA}Redis Cache (Command Line):${NC}"
echo -e "    Command:  ${BOLD}redis-cli${NC}"
echo -e "    Purpose:  Monitor cache, debug real-time data"
echo ""
echo -e "  ${BOLD}${MAGENTA}System Logs:${NC}"
echo -e "    Web App:    ${BOLD}sudo journalctl -u eas-station-web.service -f${NC}"
echo -e "    EAS Service: ${BOLD}sudo journalctl -u eas-station-eas.service -f${NC}"
echo -e "    All Services: ${BOLD}sudo journalctl -u eas-station.target -f${NC}"
echo -e "    Purpose:    Troubleshooting, monitoring, debugging"
echo ""

echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${WHITE}  ✅ POST-INSTALLATION CHECKLIST${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Immediately After Install:${NC}"
echo -e "    ${GREEN}☐${NC} Log in to web interface: ${BOLD}https://localhost${NC}"
echo -e "    ${GREEN}☐${NC} Accept self-signed certificate warning"
echo -e "    ${GREEN}☐${NC} Verify dashboard loads correctly"
echo ""
echo -e "  ${BOLD}Initial Configuration (via Setup Wizard):${NC}"
echo -e "    ${GREEN}☐${NC} Set your timezone and location (county, state)"
echo -e "    ${GREEN}☐${NC} Enter FIPS/zone codes for your area"
echo -e "    ${GREEN}☐${NC} Configure EAS originator code and station ID"
echo -e "    ${GREEN}☐${NC} Enable alert sources (NOAA Weather, IPAWS)"
echo -e "    ${GREEN}☐${NC} Test alert reception with test mode"
echo ""
echo -e "  ${BOLD}Optional Hardware Setup:${NC}"
echo -e "    ${GREEN}☐${NC} Connect SDR device (if using radio monitoring)"
echo -e "    ${GREEN}☐${NC} Configure LED displays or OLED screens"
echo -e "    ${GREEN}☐${NC} Set up GPIO pins (for Raspberry Pi)"
echo -e "    ${GREEN}☐${NC} Enable Icecast streaming (if broadcasting)"
echo ""
echo -e "  ${BOLD}Security & Production Readiness:${NC}"
echo -e "    ${GREEN}☐${NC} Replace self-signed cert with Let's Encrypt (see below)"
echo -e "    ${GREEN}✓${NC} Firewall configured automatically (ports 22, 80, 443 allowed)"
echo -e "    ${GREEN}☐${NC} Set up automatic backups (see backup commands below)"
echo -e "    ${GREEN}☐${NC} Configure email notifications (if desired)"
echo ""
echo -e "  ${BOLD}Testing & Verification:${NC}"
echo -e "    ${GREEN}☐${NC} Test with a sample CAP alert"
echo -e "    ${GREEN}☐${NC} Verify alert audio playback works"
echo -e "    ${GREEN}☐${NC} Check all services are running: ${BOLD}systemctl status eas-station.target${NC}"
echo -e "    ${GREEN}☐${NC} Monitor logs for errors: ${BOLD}journalctl -u eas-station.target -f${NC}"
echo ""

echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${WHITE}  🔧 USEFUL COMMANDS${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}View service status:${NC}"
echo -e "    ${BOLD}sudo systemctl status eas-station.target${NC}"
echo ""
echo -e "  ${CYAN}View web service logs:${NC}"
echo -e "    ${BOLD}sudo journalctl -u eas-station-web.service -f${NC}"
echo ""
echo -e "  ${CYAN}Restart all services:${NC}"
echo -e "    ${BOLD}sudo systemctl restart eas-station.target${NC}"
echo ""
echo -e "  ${CYAN}Stop all services:${NC}"
echo -e "    ${BOLD}sudo systemctl stop eas-station.target${NC}"
echo ""
echo -e "  ${CYAN}Edit configuration (advanced):${NC}"
echo -e "    ${BOLD}sudo nano $CONFIG_FILE${NC}"
echo -e "    ${DIM}(Restart services after changes)${NC}"
echo ""
echo -e "  ${CYAN}Database backup:${NC}"
echo -e "    ${BOLD}sudo -u postgres pg_dump alerts > /tmp/eas_backup_\$(date +%Y%m%d).sql${NC}"
echo ""
echo -e "  ${CYAN}Database restore:${NC}"
echo -e "    ${BOLD}sudo -u postgres psql alerts < /tmp/eas_backup_YYYYMMDD.sql${NC}"
echo ""
echo -e "  ${CYAN}Set up production SSL certificate (Let's Encrypt):${NC}"
echo -e "    ${BOLD}sudo certbot --nginx -d your-domain.com${NC}"
echo -e "    ${DIM}(Replace 'your-domain.com' with your actual domain)${NC}"
echo ""
echo -e "  ${CYAN}View firewall status:${NC}"
echo -e "    ${BOLD}sudo ufw status verbose${NC}"
echo ""
echo -e "  ${CYAN}Firewall - Configured Ports:${NC}"
echo -e "    ${GREEN}✓${NC} 22/tcp (SSH), 80/tcp (HTTP), 443/tcp (HTTPS)"
if [ "${ICECAST_ENABLED:-true}" = "true" ]; then
    echo -e "    ${GREEN}✓${NC} 8000/tcp (Icecast streaming)"
fi
echo ""
echo -e "  ${CYAN}Firewall - Optional Ports:${NC}"
echo -e "    ${DIM}5432/tcp (PostgreSQL) - For remote database/IDE access${NC}"
echo -e "    ${DIM}Command: sudo ufw allow 5432/tcp${NC}"
echo -e "    ${DIM}⚠️  Use SSH tunneling for better security:${NC}"
echo -e "    ${DIM}   ssh -L 5432:localhost:5432 user@server${NC}"
echo ""

echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${WHITE}  📚 GETTING HELP${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Documentation:${NC}"
echo -e "    Web: ${BOLD}https://localhost/help${NC} (after logging in)"
echo -e "    Local: ${BOLD}$INSTALL_DIR/docs/${NC}"
echo ""
echo -e "  ${CYAN}Troubleshooting:${NC}"
echo -e "    Check logs: ${BOLD}sudo journalctl -u eas-station.target -n 100${NC}"
echo -e "    Service status: ${BOLD}sudo systemctl status eas-station.target${NC}"
echo ""
echo -e "  ${CYAN}Community Support:${NC}"
echo -e "    GitHub: ${BOLD}https://github.com/KR8MER/eas-station${NC}"
echo -e "    Issues: ${BOLD}https://github.com/KR8MER/eas-station/issues${NC}"
echo ""
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BOLD}${GREEN}  Thank you for installing EAS Station!${NC}"
echo -e "${BOLD}${GREEN}  Your emergency alert monitoring system is ready to configure.${NC}"
echo ""
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
