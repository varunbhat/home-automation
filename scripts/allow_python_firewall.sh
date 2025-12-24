#!/bin/bash

# Script to add Python to macOS firewall allowlist
# This allows Python to accept incoming connections for TP-Link device discovery

set -e

echo "============================================"
echo "macOS Firewall Configuration for Python"
echo "============================================"
echo ""

# Find Python executable
PYTHON_PATH=$(which python3)
echo "Python location: $PYTHON_PATH"
echo ""

# Check if firewall is enabled
echo "Checking firewall status..."
FIREWALL_STATUS=$(sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate)
echo "$FIREWALL_STATUS"
echo ""

if [[ "$FIREWALL_STATUS" == *"disabled"* ]]; then
    echo "⚠️  Firewall is currently disabled."
    echo "No action needed - Python can communicate freely."
    exit 0
fi

echo "Adding Python to firewall allowlist..."
echo ""

# Add Python to the firewall allowlist
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add "$PYTHON_PATH"

# Unblock the application
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblock "$PYTHON_PATH"

# Reload firewall rules
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --reload

echo ""
echo "✅ Python has been added to the firewall allowlist!"
echo ""
echo "Verifying configuration..."
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps | grep -A 1 python3 || echo "Python entry may not show in list (this is OK)"
echo ""
echo "============================================"
echo "Configuration complete!"
echo "============================================"
echo ""
echo "You can now run ManeYantra and it should be able to"
echo "discover and communicate with TP-Link devices."
echo ""
