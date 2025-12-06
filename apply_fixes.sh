#!/bin/bash
set -e

echo "================================================================================"
echo "EAS Station - Audio Fix Applicator"
echo "================================================================================"

# Determine docker command
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    DOCKER_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_CMD="docker-compose"
else
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

echo ""
echo "Step 1: Starting services..."
$DOCKER_CMD up -d

echo ""
echo "Waiting 10 seconds for database to be ready..."
sleep 10

echo ""
echo "Step 2: Applying database fixes..."
$DOCKER_CMD exec -T alerts-db psql -U postgres -d alerts < fix_all_stream_sample_rates.sql

echo ""
echo "Step 3: Restarting audio service..."
$DOCKER_CMD restart sdr-service

echo ""
echo "================================================================================"
echo "FIX COMPLETE!"
echo "================================================================================"
echo ""
echo "Please check:"
echo "1. Icecast streams at http://localhost:8001/"
echo "2. Waterfall display at http://localhost:5000/settings/radio"
echo ""
