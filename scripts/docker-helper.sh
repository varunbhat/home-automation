#!/usr/bin/env bash
# ManeYantra Docker Helper Script
# Provides easy commands to manage the Docker environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

function show_help() {
    cat << EOF
🏠 ManeYantra Docker Helper
===========================

Usage: $0 <command>

Setup Commands:
  setup           Generate secrets and setup environment
  build           Build Docker images
  quickstart      Complete setup: secrets + build + start

Service Management:
  start           Start all services
  stop            Stop all services
  restart         Restart all services
  status          Show service status

Logs & Debugging:
  logs            Follow all logs
  logs-app        Follow application logs only
  logs-rabbit     Follow RabbitMQ logs only
  shell           Open shell in application container
  rabbit-shell    Open shell in RabbitMQ container

Maintenance:
  clean           Stop and remove all containers and volumes
  reset           Complete reset (removes secrets too)

Examples:
  $0 setup        # First time setup
  $0 start        # Start services
  $0 logs         # View logs
  $0 status       # Check status

EOF
}

function setup_secrets() {
    echo "🔐 Setting up ManeYantra with secure secrets..."
    python3 scripts/setup_secrets.py
    echo "✅ Setup complete!"
}

function build_images() {
    echo "🔨 Building Docker images..."
    docker compose build
    echo "✅ Build complete!"
}

function start_services() {
    echo "🚀 Starting ManeYantra services..."
    docker compose up -d
    echo "✅ Services started!"
    echo ""
    echo "📊 Service Status:"
    docker compose ps
    echo ""
    echo "🌐 RabbitMQ Management UI: http://localhost:15672"
}

function stop_services() {
    echo "🛑 Stopping ManeYantra services..."
    docker compose down
    echo "✅ Services stopped!"
}

function restart_services() {
    echo "🔄 Restarting ManeYantra services..."
    docker compose restart
    echo "✅ Services restarted!"
}

function show_status() {
    echo "📊 Service Status:"
    docker compose ps
    echo ""
    echo "🔍 Quick health check:"
    if docker compose exec rabbitmq rabbitmq-diagnostics ping > /dev/null 2>&1; then
        echo "   ✅ RabbitMQ is healthy"
    else
        echo "   ❌ RabbitMQ is not responding"
    fi
}

function show_logs() {
    docker compose logs -f
}

function show_app_logs() {
    docker compose logs -f maneyantra
}

function show_rabbit_logs() {
    docker compose logs -f rabbitmq
}

function open_shell() {
    echo "🐚 Opening shell in ManeYantra container..."
    docker compose exec maneyantra /bin/sh
}

function open_rabbit_shell() {
    echo "🐚 Opening shell in RabbitMQ container..."
    docker compose exec rabbitmq /bin/sh
}

function clean_all() {
    echo "🧹 Cleaning up Docker resources..."
    docker compose down -v
    echo "✅ Cleanup complete!"
}

function reset_all() {
    echo "⚠️  WARNING: This will delete all data and secrets!"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "❌ Cancelled."
        exit 0
    fi

    echo "🧹 Performing complete reset..."
    docker compose down -v
    rm -f .env docker-compose.override.yml
    echo "✅ Reset complete! Run '$0 setup' to reinitialize."
}

function quickstart() {
    setup_secrets
    build_images
    start_services
    echo ""
    echo "✨ ManeYantra is now running!"
    echo "   Access RabbitMQ Management: http://localhost:15672"
    echo "   Check logs with: $0 logs"
}

# Main command handler
case "${1:-}" in
    setup)
        setup_secrets
        ;;
    build)
        build_images
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    logs-app)
        show_app_logs
        ;;
    logs-rabbit)
        show_rabbit_logs
        ;;
    shell)
        open_shell
        ;;
    rabbit-shell)
        open_rabbit_shell
        ;;
    clean)
        clean_all
        ;;
    reset)
        reset_all
        ;;
    quickstart)
        quickstart
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
