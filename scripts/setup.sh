#!/bin/bash

# ManeYantra Setup Script

set -e

echo "================================================"
echo "🏠 ManeYantra Setup Script"
echo "================================================"
echo

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version | cut -d' ' -f2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.11+ required, found $python_version"
    exit 1
fi
echo "✅ Python $python_version"

# Check if RabbitMQ is running
echo
echo "🔌 Checking RabbitMQ..."
if command -v rabbitmqctl &> /dev/null; then
    echo "✅ RabbitMQ installed"

    # Try to check RabbitMQ status
    if rabbitmqctl status &> /dev/null; then
        echo "✅ RabbitMQ is running"
        echo "   Management UI: http://localhost:15672 (guest/guest)"
    else
        echo "⚠️  RabbitMQ not responding"
        echo "   Start it with: brew services start rabbitmq (macOS)"
        echo "   Or: sudo systemctl start rabbitmq-server (Linux)"
    fi
else
    echo "⚠️  RabbitMQ not found"
    echo "   Install with: brew install rabbitmq (macOS)"
    echo "   Or: sudo apt install rabbitmq-server (Linux)"
fi

# Create virtual environment
echo
echo "🐍 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment exists"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo
echo "📦 Installing dependencies..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Setup configuration
echo
echo "⚙️  Setting up configuration..."

if [ ! -f "config/system.yaml" ]; then
    cp config/system.yaml.example config/system.yaml
    echo "✅ Created config/system.yaml"
else
    echo "✅ config/system.yaml exists"
fi

if [ ! -f "config/plugins.yaml" ]; then
    cp config/plugins.yaml.example config/plugins.yaml
    echo "✅ Created config/plugins.yaml"
else
    echo "✅ config/plugins.yaml exists"
fi

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env (edit with your credentials)"
else
    echo "✅ .env exists"
fi

# Create directories
echo
echo "📁 Creating directories..."
mkdir -p data logs config/rules
echo "✅ Directories created"

# Install in development mode
echo
echo "🔧 Installing ManeYantra..."
pip install -e . > /dev/null
echo "✅ ManeYantra installed"

echo
echo "================================================"
echo "✅ Setup complete!"
echo "================================================"
echo
echo "Next steps:"
echo "  1. Edit .env with your credentials (Eufy, etc.)"
echo "  2. Edit config/plugins.yaml to enable/disable plugins"
echo "  3. Run: source venv/bin/activate"
echo "  4. Run: maneyantra"
echo
