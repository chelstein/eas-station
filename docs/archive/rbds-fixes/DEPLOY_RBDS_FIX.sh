#!/bin/bash
# RBDS Fix v2.44.11 - Automated Deployment Script
# Run this on your Raspberry Pi

set -e  # Exit on error

echo "═══════════════════════════════════════════════════════════════════════"
echo "  RBDS Fix v2.44.11 - Deployment Script"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

# Check we're in the right directory
if [ ! -f "VERSION" ]; then
    echo "❌ ERROR: Not in /opt/eas-station directory"
    echo "   Please run: cd /opt/eas-station"
    exit 1
fi

echo "Step 1: Fetching latest code..."
sudo -u eas-station git fetch origin

echo "Step 2: Checking out fix branch..."
sudo -u eas-station git checkout copilot/fix-rbds-sync-issues

echo "Step 3: Pulling latest changes..."
sudo -u eas-station git pull origin copilot/fix-rbds-sync-issues

echo ""
echo "Step 4: Verifying version..."
VERSION=$(cat VERSION)
echo "   Current version: $VERSION"
if [ "$VERSION" != "2.44.11" ]; then
    echo "   ⚠️  WARNING: Expected version 2.44.11, got $VERSION"
    read -p "   Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "   ✅ Version is correct!"
fi

echo ""
echo "Step 5: Running verification test..."
if python3 test_rbds_standalone.py; then
    echo "   ✅ All tests passed!"
else
    echo "   ❌ Tests failed! Aborting deployment."
    exit 1
fi

echo ""
echo "Step 6: Deploying fix..."
read -p "Ready to run update.sh? This will restart services. (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

sudo ./update.sh

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "  ✅ DEPLOYMENT COMPLETE!"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "Monitor RBDS synchronization with:"
echo "  journalctl -u eas-station-audio.service -f | grep RBDS"
echo ""
echo "Within 5-10 seconds, you should see:"
echo "  [INFO] RBDS SYNCHRONIZED at bit X"
echo "  [INFO] RBDS group: A=XXXX B=XXXX C=XXXX D=XXXX"
echo "  [INFO] RBDS decoded: PS='STATION' PI=XXXX"
echo ""
echo "Analyze logs with:"
echo "  journalctl -u eas-station-audio.service -n 1000 | python3 rbds_diagnostic.py"
echo ""
