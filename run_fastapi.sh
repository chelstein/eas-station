#!/bin/bash
# EAS Station - FastAPI Server Startup Script
# Copyright (c) 2025 Timothy Kramer (KR8MER)

set -e

echo "========================================="
echo "EAS Station - FastAPI Server"
echo "========================================="

# Load environment variables if .env exists
if [ -f .env ]; then
    echo "Loading environment from .env file..."
    set -a
    source .env
    set +a
fi

# Check if running in development or production mode
MODE="${1:-dev}"

if [ "$MODE" = "dev" ]; then
    echo "Starting in DEVELOPMENT mode with auto-reload..."
    echo "Server will be available at: http://localhost:8000"
    echo "API Documentation at: http://localhost:8000/docs"
    echo ""
    exec uvicorn fastapi_app_minimal:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --log-level info
elif [ "$MODE" = "prod" ]; then
    echo "Starting in PRODUCTION mode..."
    echo "Server will be available at: http://localhost:8000"
    echo ""
    exec uvicorn fastapi_app_minimal:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 4 \
        --log-level warning \
        --no-access-log
else
    echo "Usage: $0 [dev|prod]"
    echo "  dev  - Development mode with auto-reload (default)"
    echo "  prod - Production mode with multiple workers"
    exit 1
fi
