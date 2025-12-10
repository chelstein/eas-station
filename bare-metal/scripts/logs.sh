#!/bin/bash
# EAS Station Log Viewer
# Interactive log viewing for all services

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_menu() {
    clear
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}       EAS STATION LOG VIEWER${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}\n"
    echo "Select a service to view logs:"
    echo ""
    echo "  1) Web Application (Flask/Gunicorn)"
    echo "  2) SDR Hardware Service"
    echo "  3) Audio Processing Service"
    echo "  4) EAS Monitoring Service"
    echo "  5) Hardware Control Service"
    echo "  6) NOAA Alert Poller"
    echo "  7) IPAWS Alert Poller"
    echo "  8) All EAS Station Services"
    echo "  9) PostgreSQL"
    echo " 10) Redis"
    echo " 11) Nginx"
    echo ""
    echo "  0) Exit"
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -n "Enter choice [0-11]: "
}

view_logs() {
    local service=$1
    local name=$2
    echo -e "\n${GREEN}Viewing logs for: $name${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}\n"
    sleep 1
    sudo journalctl -u "$service" -f -n 100
}

while true; do
    show_menu
    read choice
    
    case $choice in
        1)
            view_logs "eas-station-web.service" "Web Application"
            ;;
        2)
            view_logs "eas-station-sdr.service" "SDR Hardware Service"
            ;;
        3)
            view_logs "eas-station-audio.service" "Audio Processing Service"
            ;;
        4)
            view_logs "eas-station-eas.service" "EAS Monitoring Service"
            ;;
        5)
            view_logs "eas-station-hardware.service" "Hardware Control Service"
            ;;
        6)
            view_logs "eas-station-noaa-poller.service" "NOAA Alert Poller"
            ;;
        7)
            view_logs "eas-station-ipaws-poller.service" "IPAWS Alert Poller"
            ;;
        8)
            echo -e "\n${GREEN}Viewing logs for: All EAS Station Services${NC}"
            echo -e "${YELLOW}Press Ctrl+C to stop${NC}\n"
            sleep 1
            sudo journalctl -u eas-station-*.service -f -n 100
            ;;
        9)
            view_logs "postgresql.service" "PostgreSQL"
            ;;
        10)
            view_logs "redis-server.service" "Redis"
            ;;
        11)
            view_logs "nginx.service" "Nginx"
            ;;
        0)
            echo -e "\n${GREEN}Goodbye!${NC}\n"
            exit 0
            ;;
        *)
            echo -e "\n${RED}Invalid choice. Please try again.${NC}"
            sleep 2
            ;;
    esac
done
