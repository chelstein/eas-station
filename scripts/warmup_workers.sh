#!/bin/bash
# Warmup script to trigger database initialization in gunicorn workers
# This should be run after gunicorn starts but before nginx routes traffic to it
#
# The problem: Workers appear running but are stuck initializing database on first request
# The solution: Make a warmup request to trigger initialization while we can wait

set -e

MAX_WAIT=120  # Maximum 2 minutes to wait for workers to be ready
RETRY_INTERVAL=2

echo "Warming up gunicorn workers (triggering database initialization)..."
echo "This may take up to 2 minutes on first startup or after database migrations."
echo ""

START_TIME=$(date +%s)

# Function to check if workers respond
check_workers() {
    # Try to hit a simple endpoint that will trigger database initialization
    # Use /health endpoint which is public and should work
    timeout 5 curl -s -f http://127.0.0.1:5000/health >/dev/null 2>&1
    return $?
}

ATTEMPT=1
while [ $(($(date +%s) - START_TIME)) -lt $MAX_WAIT ]; do
    echo -n "Attempt $ATTEMPT: "
    
    if check_workers; then
        echo "✓ Workers are responding!"
        echo ""
        echo "Database initialization complete. Service is ready."
        exit 0
    else
        echo "Workers not ready yet, waiting ${RETRY_INTERVAL}s..."
        sleep $RETRY_INTERVAL
        ATTEMPT=$((ATTEMPT + 1))
    fi
done

# Timeout reached
echo ""
echo "✗ Workers did not respond within ${MAX_WAIT} seconds"
echo ""
echo "The workers may be stuck during database initialization."
echo "Check the logs: journalctl -u eas-station-web.service -n 100"
echo ""
echo "Common causes:"
echo "  1. Database is not running: systemctl status postgresql"
echo "  2. Database connection timeout: check DATABASE_URL in .env"
echo "  3. Large database migration in progress: wait longer or check PostgreSQL logs"
echo "  4. Connection pool exhausted: check for zombie database connections"
exit 1
