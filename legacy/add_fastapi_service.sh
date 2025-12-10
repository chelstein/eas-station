#!/bin/bash
# Script to add FastAPI service to all docker-compose files

FASTAPI_SERVICE='
  # ==========================================================================
  # FastAPI Service - New ASGI app running alongside Flask during migration
  # ==========================================================================
  # This service runs the minimal FastAPI app on port 8080 for gradual migration.
  # Flask (port 5000) remains the production app, FastAPI is under development.
  # ==========================================================================
  fastapi:
    image: eas-station:latest
    container_name: eas-fastapi
    init: true
    restart: unless-stopped
    expose:
      - "8080"  # Internal only, can be accessed via nginx reverse proxy
    ports:
      - "8080:8080"  # Exposed for direct access during development
    networks:
      - eas-network
    command: ["uvicorn", "fastapi_app_minimal:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
    env_file:
      - stack.env
    volumes:
      - app-config:/app-config
    tmpfs:
      - /tmp:size=${TMPFS_FASTAPI:-64M},mode=1777
    environment:
      # Database connection
      POSTGRES_HOST: ${POSTGRES_HOST:-alerts-db}
      POSTGRES_PORT: ${POSTGRES_PORT:-5432}
      POSTGRES_DB: ${POSTGRES_DB:-alerts}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}

      # Redis connection
      REDIS_HOST: ${REDIS_HOST:-redis}
      REDIS_PORT: ${REDIS_PORT:-6379}
      REDIS_DB: ${REDIS_DB:-0}

      # Application settings
      SECRET_KEY: ${SECRET_KEY:-}
      CONFIG_PATH: /app-config/.env
      CORS_ALLOWED_ORIGINS: ${CORS_ALLOWED_ORIGINS:-*}
    extra_hosts:
      - "host.docker.internal:host-gateway"
    security_opt:
      - no-new-privileges:true
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
'

echo "$FASTAPI_SERVICE"
