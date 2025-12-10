@echo off
echo ================================================================================
echo EAS Station - Audio Fix Applicator
echo ================================================================================

echo.
echo Step 1: Starting services...
docker compose up -d
if %ERRORLEVEL% NEQ 0 (
    echo Failed to start services. Please make sure Docker Desktop is running.
    pause
    exit /b 1
)

echo.
echo Waiting 10 seconds for database to be ready...
timeout /t 10 /nobreak >nul

echo.
echo Step 2: Applying database fixes...
docker compose exec -T alerts-db psql -U postgres -d alerts < fix_all_stream_sample_rates.sql
if %ERRORLEVEL% NEQ 0 (
    echo Failed to apply database fixes.
    pause
    exit /b 1
)

echo.
echo Step 3: Restarting audio service...
docker compose restart sdr-service

echo.
echo ================================================================================
echo FIX COMPLETE!
echo ================================================================================
echo.
echo Please check:
echo 1. Icecast streams at http://localhost:8001/
echo 2. Waterfall display at http://localhost:5000/settings/radio
echo.
pause
