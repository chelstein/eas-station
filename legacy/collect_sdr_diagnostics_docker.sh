#!/bin/bash
# EAS Station - Emergency Alert System
# Copyright (c) 2025 Timothy Kramer (KR8MER)
#
# This file is part of EAS Station.
#
# EAS Station is dual-licensed software:
# - GNU Affero General Public License v3 (AGPL-3.0) for open-source use
# - Commercial License for proprietary use
#
# You should have received a copy of both licenses with this software.
# For more information, see LICENSE and LICENSE-COMMERCIAL files.
#
# IMPORTANT: This software cannot be rebranded or have attribution removed.
# See NOTICE file for complete terms.
#
# Repository: https://github.com/KR8MER/eas-station

#
# SDR Diagnostic Information Collection Script
#
# This script collects comprehensive diagnostic information about SDR hardware,
# software configuration, and system status for troubleshooting.
#
# Usage:
#   bash scripts/collect_sdr_diagnostics.sh
#   bash scripts/collect_sdr_diagnostics.sh /path/to/output.txt
#

set -e

# Determine output file
if [ -n "$1" ]; then
  OUTPUT_FILE="$1"
else
  OUTPUT_FILE="sdr_diagnostics_$(date +%Y%m%d_%H%M%S).txt"
fi

echo "============================================"
echo "EAS Station SDR Diagnostics Collection"
echo "============================================"
echo ""
echo "Collecting diagnostic information..."
echo "Output will be saved to: $OUTPUT_FILE"
echo ""

# Helper function to run command and capture output
run_command() {
  local title="$1"
  shift
  echo "▶ $title"
  "$@" 2>&1 || echo "  ⚠ Command failed or not available"
}

# Main diagnostic collection
{
  echo "============================================"
  echo "EAS Station SDR Diagnostics Report"
  echo "Generated: $(date)"
  echo "============================================"
  echo ""
  
  echo "### SYSTEM INFORMATION ###"
  echo ""
  run_command "Hostname" hostname
  echo ""
  run_command "Operating System" uname -a
  echo ""
  run_command "Docker Version" docker --version
  echo ""
  run_command "Docker Compose Version" docker compose version
  echo ""
  
  echo ""
  echo "### USB HARDWARE DETECTION ###"
  echo ""
  run_command "All USB Devices" lsusb
  echo ""
  run_command "SDR-Related USB Devices" lsusb | grep -E "RTL|Airspy|Realtek" || echo "  No SDR devices found via lsusb"
  echo ""
  
  echo ""
  echo "### SOAPYSDR DEVICE DETECTION ###"
  echo ""
  run_command "SoapySDR Device Enumeration (App Container)" docker compose exec -T app SoapySDRUtil --find
  echo ""
  run_command "SoapySDR Info (App Container)" docker compose exec -T app SoapySDRUtil --info
  echo ""
  
  # Check if sdr-service exists
  if docker compose ps sdr-service >/dev/null 2>&1; then
    run_command "SoapySDR Device Enumeration (SDR Service)" docker compose exec -T sdr-service SoapySDRUtil --find
    echo ""
  fi
  
  echo ""
  echo "### CONTAINER STATUS ###"
  echo ""
  run_command "All Containers" docker compose ps
  echo ""
  run_command "Container Resource Usage" docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" || docker stats --no-stream
  echo ""
  
  echo ""
  echo "### SERVICE LOGS ###"
  echo ""
  echo "--- SDR Service (last 100 lines) ---"
  run_command "SDR Service Logs" docker compose logs --tail=100 sdr-service
  echo ""
  
  echo "--- Audio Service (last 100 lines) ---"
  run_command "Audio Service Logs" docker compose logs --tail=100 audio-service
  echo ""
  
  echo "--- App Service (last 50 lines, SDR-related) ---"
  run_command "App SDR Logs" docker compose logs --tail=200 app | grep -i "sdr\|radio\|receiver" || echo "  No SDR-related logs in app service"
  echo ""
  
  echo ""
  echo "### DATABASE CONFIGURATION ###"
  echo ""
  echo "--- Radio Receivers ---"
  run_command "Radio Receivers Table" docker compose exec -T app psql -U postgres -d alerts -c "
    SELECT 
      id,
      identifier,
      display_name,
      driver,
      frequency_hz,
      ROUND(frequency_hz::numeric / 1000000, 3) AS frequency_mhz,
      sample_rate,
      gain,
      modulation_type,
      audio_output,
      enabled,
      auto_start
    FROM radio_receivers
    ORDER BY id;
  "
  echo ""
  
  echo "--- Audio Source Configs ---"
  run_command "Audio Source Configs" docker compose exec -T app psql -U postgres -d alerts -c "
    SELECT 
      id,
      name,
      source_type,
      config_params,
      enabled,
      auto_start
    FROM audio_source_configs
    WHERE source_type = 'redis_sdr' OR config_params::text LIKE '%receiver%'
    ORDER BY id;
  "
  echo ""
  
  echo ""
  echo "### REDIS STATUS ###"
  echo ""
  run_command "Redis Ping" docker compose exec -T redis redis-cli ping
  echo ""
  run_command "Redis Info" docker compose exec -T redis redis-cli info server
  echo ""
  run_command "Redis Pub/Sub Channels" docker compose exec -T redis redis-cli pubsub channels 'sdr:*'
  echo ""
  run_command "Redis SDR Metrics" docker compose exec -T redis redis-cli get sdr:metrics
  echo ""
  
  echo ""
  echo "### SDR DIAGNOSTICS SCRIPT ###"
  echo ""
  run_command "Python SDR Diagnostics" docker compose exec -T app python3 scripts/sdr_diagnostics.py
  echo ""
  
  echo ""
  echo "### NETWORK CONNECTIVITY ###"
  echo ""
  run_command "Container Network" docker compose exec -T app ip addr show
  echo ""
  run_command "DNS Resolution" docker compose exec -T app nslookup google.com || docker compose exec -T app ping -c 1 8.8.8.8
  echo ""
  
  echo ""
  echo "### ENVIRONMENT VARIABLES (sanitized) ###"
  echo ""
  echo "Note: Passwords and secrets are redacted"
  echo ""
  run_command "App Environment" docker compose exec -T app printenv | grep -E "SDR|RADIO|AUDIO|REDIS" | sed 's/PASSWORD=.*/PASSWORD=***REDACTED***/' | sed 's/SECRET=.*/SECRET=***REDACTED***/' | sort
  echo ""
  
  echo ""
  echo "### DISK SPACE ###"
  echo ""
  run_command "Disk Usage" df -h
  echo ""
  run_command "Docker Disk Usage" docker system df
  echo ""
  
  echo ""
  echo "### SYSTEM RESOURCE CHECK ###"
  echo ""
  run_command "Memory Usage" free -h
  echo ""
  run_command "CPU Info" cat /proc/cpuinfo | grep -E "model name|processor|cpu MHz" | head -20
  echo ""
  run_command "Load Average" uptime
  echo ""
  
  echo ""
  echo "### USB DEVICE MESSAGES (Recent) ###"
  echo ""
  run_command "USB Kernel Messages" dmesg | grep -i usb | tail -50
  echo ""
  
  echo ""
  echo "============================================"
  echo "DIAGNOSTIC SUMMARY"
  echo "============================================"
  echo ""
  
  # Generate summary
  echo "Quick Status:"
  echo ""
  
  # Check if containers are running
  if docker compose ps | grep -q "Up"; then
    echo "✓ Docker containers are running"
  else
    echo "✗ Some Docker containers are not running"
  fi
  
  # Check if SDR devices detected
  if lsusb | grep -qE "RTL|Airspy|Realtek"; then
    echo "✓ SDR hardware detected via USB"
  else
    echo "✗ No SDR hardware detected via USB"
  fi
  
  # Check if SoapySDR can see devices
  if docker compose exec -T app SoapySDRUtil --find 2>/dev/null | grep -q "driver"; then
    echo "✓ SoapySDR can enumerate devices"
  else
    echo "✗ SoapySDR cannot find devices"
  fi
  
  # Check database has receivers configured
  if docker compose exec -T app psql -U postgres -d alerts -c "SELECT COUNT(*) FROM radio_receivers;" 2>/dev/null | grep -q "[1-9]"; then
    echo "✓ Radio receivers configured in database"
  else
    echo "⚠ No radio receivers configured in database"
  fi
  
  echo ""
  echo "============================================"
  echo "Diagnostic collection complete"
  echo "============================================"
  echo ""
  echo "Next Steps:"
  echo "1. Review the diagnostic output above"
  echo "2. Check the troubleshooting guide: docs/troubleshooting/SDR_MASTER_TROUBLESHOOTING_GUIDE.md"
  echo "3. If reporting an issue, attach this file: $OUTPUT_FILE"
  echo ""
  
} 2>&1 | tee "$OUTPUT_FILE"

echo ""
echo "✓ Diagnostics saved to: $OUTPUT_FILE"
echo ""
echo "File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo ""
echo "You can now:"
echo "  - Review the file: less $OUTPUT_FILE"
echo "  - Search for errors: grep -i error $OUTPUT_FILE"
echo "  - Attach to GitHub issue when asking for help"
echo ""
