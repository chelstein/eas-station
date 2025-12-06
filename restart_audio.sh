#!/bin/bash
set -e

echo "================================================================================"
echo "EAS Station - Audio Service Restart"
echo "================================================================================"
echo ""
echo "This script will restart the audio service to apply recent fixes."
echo ""

# Determine docker command
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    DOCKER_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_CMD="docker-compose"
else
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Check for pi override
COMPOSE_FILES="-f docker-compose.yml"
if [ -f "docker-compose.pi.yml" ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.pi.yml"
fi

echo "Restarting sdr-service..."
$DOCKER_CMD $COMPOSE_FILES restart sdr-service

echo ""
echo "Waiting for service to initialize (30 seconds)..."
sleep 30

echo ""
echo "Checking logs for errors..."
$DOCKER_CMD $COMPOSE_FILES logs --tail=50 sdr-service

echo ""
echo "================================================================================"
echo "RESTART COMPLETE"
echo "================================================================================"
echo "Please check the web interface:"
echo "1. Refresh the page"
echo "2. Verify the 'Audio monitor is not running' message is gone"
echo "3. Verify the date/time is correct"
echo ""
