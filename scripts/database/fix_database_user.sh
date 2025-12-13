#!/bin/bash
# EAS Station Database User Fix Script
# Copyright (c) 2025 Timothy Kramer (KR8MER)
# Licensed under AGPL v3 or Commercial License
#
# This script ensures the correct database user "eas-station" exists
# and removes any incorrectly named users like "eas_station"

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

echo ""
echo "═══════════════════════════════════════════════════════════"
echo " EAS Station Database User Fix"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo_error "This script must be run as root or with sudo"
    exit 1
fi

# Load DATABASE_URL from .env file
ENV_FILE="/opt/eas-station/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo_error ".env file not found at $ENV_FILE"
    exit 1
fi

# Extract database password from DATABASE_URL
echo_info "Reading database configuration from .env file..."
DATABASE_URL=$(grep "^DATABASE_URL=" "$ENV_FILE" | cut -d'=' -f2-)

if [ -z "$DATABASE_URL" ]; then
    echo_error "DATABASE_URL not found in .env file"
    exit 1
fi

# Parse DATABASE_URL to extract password
# Format: postgresql+psycopg2://user:password@host:port/database
DB_PASSWORD=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')

if [ -z "$DB_PASSWORD" ]; then
    echo_error "Could not extract database password from DATABASE_URL"
    exit 1
fi

echo_success "Database configuration loaded"
echo ""

# Check for incorrectly named users
echo_info "Checking for incorrectly named database users..."

INCORRECT_USERS=()
for user in "eas_station" "easstation" "eas-station-old"; do
    if sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename = '$user'" 2>/dev/null | grep -q 1; then
        INCORRECT_USERS+=("$user")
        echo_warning "Found incorrect user: $user"
    fi
done

# Check if correct user exists
if sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename = 'eas-station'" 2>/dev/null | grep -q 1; then
    echo_success "Correct user 'eas-station' exists"
    USER_EXISTS=true
else
    echo_warning "Correct user 'eas-station' does not exist"
    USER_EXISTS=false
fi

echo ""

# If there are incorrect users and the correct user exists, offer to clean up
if [ ${#INCORRECT_USERS[@]} -gt 0 ]; then
    if [ "$USER_EXISTS" = true ]; then
        echo_warning "Found ${#INCORRECT_USERS[@]} incorrectly named user(s) that should be removed"
        echo ""
        echo "This script will:"
        echo "  1. Reassign ownership of all objects from incorrect users to 'eas-station'"
        echo "  2. Drop the incorrect user(s)"
        echo "  3. Update password for 'eas-station' user"
        echo ""
        read -p "Do you want to proceed? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo_info "Operation cancelled"
            exit 0
        fi
        
        # Reassign ownership and drop each incorrect user
        for user in "${INCORRECT_USERS[@]}"; do
            echo_info "Processing user: $user"
            
            # Reassign database ownership
            sudo -u postgres psql -d alerts <<EOF 2>/dev/null || true
REASSIGN OWNED BY "$user" TO "eas-station";
DROP OWNED BY "$user";
DROP USER IF EXISTS "$user";
EOF
            echo_success "Removed user: $user"
        done
    else
        echo_warning "Incorrect users exist but correct user 'eas-station' is missing"
        echo_info "Will create correct user and remove incorrect ones"
        
        # Create the correct user first
        echo_info "Creating database user 'eas-station'..."
        sudo -u postgres psql <<EOF 2>/dev/null
CREATE USER "eas-station" WITH PASSWORD \$\$${DB_PASSWORD}\$\$;
GRANT ALL PRIVILEGES ON DATABASE alerts TO "eas-station";
EOF
        echo_success "User 'eas-station' created"
        
        # Now reassign and drop incorrect users
        for user in "${INCORRECT_USERS[@]}"; do
            echo_info "Migrating objects from $user to eas-station..."
            sudo -u postgres psql -d alerts <<EOF 2>/dev/null || true
REASSIGN OWNED BY "$user" TO "eas-station";
DROP OWNED BY "$user";
DROP USER IF EXISTS "$user";
EOF
            echo_success "Removed user: $user"
        done
    fi
elif [ "$USER_EXISTS" = false ]; then
    # Create the correct user
    echo_info "Creating database user 'eas-station'..."
    sudo -u postgres psql <<EOF 2>/dev/null
CREATE USER "eas-station" WITH PASSWORD \$\$${DB_PASSWORD}\$\$;
GRANT ALL PRIVILEGES ON DATABASE alerts TO "eas-station";
EOF
    echo_success "User 'eas-station' created"
fi

# Update password and permissions (in case password changed)
echo ""
echo_info "Updating password and permissions for 'eas-station'..."
sudo -u postgres psql <<EOF 2>/dev/null
ALTER USER "eas-station" WITH PASSWORD \$\$${DB_PASSWORD}\$\$;
GRANT ALL PRIVILEGES ON DATABASE alerts TO "eas-station";
EOF

# Grant schema privileges (required for PostgreSQL 15+)
sudo -u postgres psql -d alerts <<EOF 2>/dev/null
GRANT ALL ON SCHEMA public TO "eas-station";
GRANT CREATE ON SCHEMA public TO "eas-station";
GRANT ALL ON ALL TABLES IN SCHEMA public TO "eas-station";
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO "eas-station";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "eas-station";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "eas-station";
EOF

echo_success "Password and permissions updated"
echo ""
echo_success "Database user configuration fixed!"
echo ""
echo_info "Next steps:"
echo "  1. Restart all EAS Station services: sudo systemctl restart eas-station.target"
echo "  2. Check logs: sudo journalctl -u eas-station.target -f"
echo ""
