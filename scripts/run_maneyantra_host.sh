#!/bin/bash

# Script to run ManeYantra on the host (outside Docker)
# This is needed for TP-Link discovery on macOS due to Docker network limitations

set -e

cd "$(dirname "$0")/.."

echo "============================================"
echo "🏠 Starting ManeYantra on Host"
echo "============================================"
echo ""

# Check if Python firewall is configured
echo "⚠️  IMPORTANT: Make sure Python is allowed through the firewall!"
echo "If you haven't already, run: sudo ./scripts/allow_python_firewall.sh"
echo ""
read -p "Press Enter to continue..."
echo ""

# Set environment variables for localhost access to Docker services
export RABBITMQ_HOST=localhost
export EUFY_BRIDGE_URL=http://localhost:3000
export EUFY_BRIDGE_WS_URL=ws://localhost:3001

echo "Configuration:"
echo "  RabbitMQ: $RABBITMQ_HOST:5672"
echo "  Eufy Bridge: $EUFY_BRIDGE_URL"
echo "  Eufy WebSocket: $EUFY_BRIDGE_WS_URL"
echo ""
echo "Starting ManeYantra..."
echo ""

# Run ManeYantra
python3 -m maneyantra.main
