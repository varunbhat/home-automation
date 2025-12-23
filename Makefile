.PHONY: help setup start stop restart logs build clean status shell rabbitmq-shell test

# Default target
help:
	@echo "ManeYantra Docker Management"
	@echo "============================"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make setup          - Generate secrets and setup environment"
	@echo "  make build          - Build Docker images"
	@echo ""
	@echo "Service Management:"
	@echo "  make start          - Start all services"
	@echo "  make stop           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make status         - Show service status"
	@echo ""
	@echo "Logs & Debugging:"
	@echo "  make logs           - Follow all logs"
	@echo "  make logs-app       - Follow application logs only"
	@echo "  make logs-rabbit    - Follow RabbitMQ logs only"
	@echo "  make shell          - Open shell in application container"
	@echo "  make rabbitmq-shell - Open shell in RabbitMQ container"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Stop and remove all containers and volumes"
	@echo "  make reset          - Complete reset (removes secrets too)"
	@echo ""

# Setup - Generate secrets and create .env
setup:
	@echo "🔐 Setting up ManeYantra with secure secrets..."
	@python3 scripts/setup_secrets.py
	@echo "✅ Setup complete!"

# Build Docker images
build:
	@echo "🔨 Building Docker images..."
	docker compose build

# Start services
start:
	@echo "🚀 Starting ManeYantra services..."
	docker compose up -d
	@echo "✅ Services started!"
	@echo "   - RabbitMQ Management UI: http://localhost:15672"
	@make status

# Stop services
stop:
	@echo "🛑 Stopping ManeYantra services..."
	docker compose down
	@echo "✅ Services stopped!"

# Restart services
restart:
	@echo "🔄 Restarting ManeYantra services..."
	docker compose restart
	@echo "✅ Services restarted!"

# Show service status
status:
	@echo "📊 Service Status:"
	@docker compose ps

# Follow all logs
logs:
	docker compose logs -f

# Follow application logs only
logs-app:
	docker compose logs -f maneyantra

# Follow RabbitMQ logs only
logs-rabbit:
	docker compose logs -f rabbitmq

# Open shell in application container
shell:
	docker compose exec maneyantra /bin/sh

# Open shell in RabbitMQ container
rabbitmq-shell:
	docker compose exec rabbitmq /bin/sh

# Rebuild and restart
rebuild: build restart

# Clean - remove containers and volumes
clean:
	@echo "🧹 Cleaning up Docker resources..."
	docker compose down -v
	@echo "✅ Cleanup complete!"

# Complete reset - remove everything including secrets
reset:
	@echo "⚠️  WARNING: This will delete all data and secrets!"
	@read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
	@echo "🧹 Performing complete reset..."
	docker compose down -v
	rm -f .env docker-compose.override.yml
	@echo "✅ Reset complete! Run 'make setup' to reinitialize."

# Quick start (setup + build + start)
quickstart: setup build start
	@echo "✨ ManeYantra is now running!"
	@echo "   Access RabbitMQ Management: http://localhost:15672"
	@echo "   Check logs with: make logs"
