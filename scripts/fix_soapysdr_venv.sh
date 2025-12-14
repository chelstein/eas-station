#!/bin/bash
# Quick fix for SoapySDR venv access issue
# Run this if you get "No module named 'SoapySDR'" errors

set -e

echo "=== SoapySDR venv Fix ==="
echo ""

# Check if python3-soapysdr is installed
if ! dpkg -l | grep -q python3-soapysdr; then
    echo "❌ python3-soapysdr is NOT installed"
    echo "   Run: sudo apt-get install python3-soapysdr"
    exit 1
fi

echo "✅ python3-soapysdr package is installed"
echo ""

# Detect all Python site-packages
echo "Detecting Python paths..."
PYTHON_SITE_PACKAGES=$(python3 -c "import site; print(':'.join(site.getsitepackages()))" 2>/dev/null)
echo "  System paths: $PYTHON_SITE_PACKAGES"
echo ""

# Build PYTHONPATH
PYTHONPATH_VALUE="/opt/eas-station:${PYTHON_SITE_PACKAGES}"
echo "Updating systemd service with PYTHONPATH..."
echo "  PYTHONPATH=$PYTHONPATH_VALUE"
echo ""

# Update SDR service
if [ -f /etc/systemd/system/eas-station-sdr.service ]; then
    PYTHONPATH_ESCAPED=$(echo "$PYTHONPATH_VALUE" | sed 's/[@&|\\]/\\&/g')
    sudo sed -i "s@Environment=\"PYTHONPATH=.*\"@Environment=\"PYTHONPATH=${PYTHONPATH_ESCAPED}\"@" /etc/systemd/system/eas-station-sdr.service
    echo "✅ Updated eas-station-sdr.service"
fi

# Update audio service  
if [ -f /etc/systemd/system/eas-station-audio.service ]; then
    PYTHONPATH_ESCAPED=$(echo "$PYTHONPATH_VALUE" | sed 's/[@&|\\]/\\&/g')
    if grep -q '^Environment="PYTHONPATH=' /etc/systemd/system/eas-station-audio.service; then
        sudo sed -i "s@^Environment=\"PYTHONPATH=.*\"@Environment=\"PYTHONPATH=${PYTHONPATH_ESCAPED}\"@" /etc/systemd/system/eas-station-audio.service
    else
        sudo sed -i "/^Environment=\"PATH=/a Environment=\"PYTHONPATH=${PYTHONPATH_ESCAPED}\"" /etc/systemd/system/eas-station-audio.service
    fi
    echo "✅ Updated eas-station-audio.service"
fi

echo ""
echo "Reloading systemd..."
sudo systemctl daemon-reload
echo "✅ Done"
echo ""

echo "Testing SoapySDR import with new PYTHONPATH..."
if PYTHONPATH="$PYTHONPATH_VALUE" python3 -c "import SoapySDR; print('✅ SUCCESS - SoapySDR can be imported'); print('   API Version:', SoapySDR.getAPIVersion())" 2>&1; then
    echo ""
    echo "✅ Fix successful! Restart the service:"
    echo "   sudo systemctl restart eas-station-sdr.service"
else
    echo ""
    echo "❌ Still cannot import SoapySDR"
    echo "   This may be a Python version mismatch issue"
    echo "   Check: dpkg -L python3-soapysdr"
fi
