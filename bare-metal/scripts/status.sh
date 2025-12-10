#!/bin/bash
# EAS Station Status Check Script
# Shows status of all services and components

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}\n"
}

check_service() {
    local service=$1
    if systemctl is-active --quiet "$service"; then
        echo -e "  ${GREEN}●${NC} $service - ${GREEN}running${NC}"
    else
        echo -e "  ${RED}●${NC} $service - ${RED}stopped${NC}"
    fi
}

check_port() {
    local port=$1
    local name=$2
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        echo -e "  ${GREEN}●${NC} Port $port ($name) - ${GREEN}listening${NC}"
    else
        echo -e "  ${RED}●${NC} Port $port ($name) - ${RED}not listening${NC}"
    fi
}

echo_header "EAS STATION STATUS"

# System information
echo "System Information:"
echo "  Hostname: $(hostname)"
echo "  IP Address: $(hostname -I | awk '{print $1}')"
echo "  Uptime: $(uptime -p)"
echo ""

# Main target status
echo_header "SERVICES STATUS"
check_service "eas-station.target"
echo ""

# Individual services
echo "Core Services:"
check_service "postgresql.service"
check_service "redis-server.service"
check_service "nginx.service"
echo ""

echo "EAS Station Services:"
check_service "eas-station-web.service"
check_service "eas-station-sdr.service"
check_service "eas-station-audio.service"
check_service "eas-station-eas.service"
check_service "eas-station-hardware.service"
check_service "eas-station-noaa-poller.service"
check_service "eas-station-ipaws-poller.service"
echo ""

# Port status
echo_header "NETWORK STATUS"
check_port "80" "HTTP"
check_port "443" "HTTPS"
check_port "5000" "Flask"
check_port "5432" "PostgreSQL"
check_port "6379" "Redis"
echo ""

# Resource usage
echo_header "RESOURCE USAGE"
echo "Memory:"
free -h | grep -E "^Mem|^Swap" | awk '{printf "  %-8s %8s / %-8s (%5s used)\n", $1, $3, $2, $3/$2*100"%"}'
echo ""

echo "Disk Usage:"
df -h / | tail -n 1 | awk '{printf "  Root:     %8s / %-8s (%5s used)\n", $3, $2, $5}'
if [ -d "/opt/eas-station" ]; then
    du -sh /opt/eas-station 2>/dev/null | awk '{printf "  EAS App:  %8s\n", $1}'
fi
echo ""

# Recent errors
echo_header "RECENT ERRORS (Last 10)"
journalctl -u eas-station-*.service --since "1 hour ago" -p err -n 10 --no-pager || echo "  No errors in the last hour"
echo ""

# Quick actions
echo_header "QUICK ACTIONS"
echo "  View logs:        sudo journalctl -u eas-station-web.service -f"
echo "  Restart all:      sudo systemctl restart eas-station.target"
echo "  Stop all:         sudo systemctl stop eas-station.target"
echo "  Start all:        sudo systemctl start eas-station.target"
echo "  Web interface:    https://$(hostname -I | awk '{print $1}')"
echo ""
