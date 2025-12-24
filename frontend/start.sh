#!/bin/bash
# Quick start script for ManeYantra frontend

echo "🏠 ManeYantra Frontend - Starting..."
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    cp .env.example .env
    echo ""
fi

echo "🚀 Starting development server..."
echo "   Frontend: http://localhost:5173"
echo "   API: http://localhost:8000"
echo ""
echo "   Make sure ManeYantra API is running!"
echo ""

npm run dev
