#!/bin/bash
echo "=== HOST USB DEVICES ==="
lsusb
echo ""

echo "=== SDR-SERVICE DETECTION ==="
docker compose exec sdr-service SoapySDRUtil --find
echo ""

echo "=== APP DETECTION ==="
docker compose exec app SoapySDRUtil --find
echo ""
