.PHONY: help install clean test lint format run-dev run-prod docker-build docker-up docker-down deploy backup restore health

# Default target
help:
	@echo "Stock Trading System - Available Commands"
	@echo "=========================================="
	@echo ""
	@echo "Development:"
	@echo "  make install          - Install dependencies and set up environment"
	@echo "  make clean            - Clean up generated files and caches"
	@echo "  make test             - Run tests"
	@echo "  make lint             - Run linters"
	@echo "  make format           - Format code with black and isort"
	@echo "  make run-dev          - Run in development mode"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     - Build Docker images"
	@echo "  make docker-up        - Start all services with Docker Compose"
	@echo "  make docker-down      - Stop all Docker services"
	@echo "  make docker-logs      - View Docker logs"
	@echo "  make docker-clean     - Clean Docker resources"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-systemd   - Deploy using systemd"
	@echo "  make deploy-docker    - Deploy using Docker"
	@echo "  make rolling-update   - Perform rolling update"
	@echo "  make quick-deploy     - Quick deployment"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate       - Run database migrations"
	@echo "  make db-upgrade       - Upgrade database schema"
	@echo "  make db-downgrade     - Downgrade database schema"
	@echo "  make backup           - Backup database"
	@echo "  make restore          - Restore database from backup"
	@echo ""
	@echo "Monitoring:"
	@echo "  make health           - Run health checks"
	@echo "  make logs             - View application logs"
	@echo "  make status           - Check service status"
	@echo ""

# Development
install:
	@echo "Installing dependencies..."
	python3 -m venv venv || true
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	@echo "Installation complete!"

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	@echo "Clean complete!"

test:
	@echo "Running tests..."
	./venv/bin/pytest tests/ -v --cov=. --cov-report=html

lint:
	@echo "Running linters..."
	./venv/bin/flake8 services/ shared/
	./venv/bin/mypy services/ shared/

format:
	@echo "Formatting code..."
	./venv/bin/black services/ shared/ tests/
	./venv/bin/isort services/ shared/ tests/
	@echo "Code formatted!"

run-dev:
	@echo "Starting development services..."
	cd docker && docker compose -f docker-compose.yml up

# Docker commands
docker-build:
	@echo "Building Docker images..."
	@echo "Step 1: Building base image..."
	docker build -t stock-trading-base:latest -f docker/Dockerfile.base .
	@echo "Step 2: Building service images..."
	cd docker && docker compose -f docker-compose.full.yml build

docker-up:
	@echo "Starting Docker services..."
	cd docker && docker compose -f docker-compose.full.yml up -d
	@echo "Services started!"
	@make docker-ps

docker-down:
	@echo "Stopping Docker services..."
	cd docker && docker compose -f docker-compose.full.yml down

docker-logs:
	cd docker && docker compose -f docker-compose.full.yml logs -f

docker-ps:
	cd docker && docker compose -f docker-compose.full.yml ps

docker-clean:
	@echo "Cleaning Docker resources..."
	cd docker && docker compose -f docker-compose.full.yml down -v
	docker system prune -f
	@echo "Docker cleaned!"

# Deployment
deploy-systemd:
	@echo "Deploying with systemd..."
	sudo ./deployment/scripts/install-systemd.sh

deploy-docker:
	@echo "Deploying with Docker..."
	@make docker-build
	@make docker-up

rolling-update:
	@echo "Performing rolling update..."
	sudo ./deployment/scripts/rolling-update.sh

quick-deploy:
	@echo "Quick deployment..."
	./deployment/scripts/quick-deploy.sh

# Database
db-migrate:
	@echo "Running database migrations..."
	./venv/bin/alembic upgrade head

db-upgrade:
	@echo "Upgrading database..."
	./venv/bin/alembic upgrade head

db-downgrade:
	@echo "Downgrading database..."
	./venv/bin/alembic downgrade -1

backup:
	@echo "Creating database backup..."
	./deployment/scripts/backup-database.sh

restore:
	@echo "Restoring database..."
	./deployment/scripts/restore-database.sh

# Monitoring
health:
	@echo "Running health checks..."
	./deployment/scripts/health-check.sh

logs:
	@echo "Viewing logs..."
	tail -f logs/*.log

status:
	@echo "Checking service status..."
	@if command -v systemctl &> /dev/null; then \
		systemctl status stock-trading-orchestrator --no-pager || true; \
	elif command -v docker &> /dev/null; then \
		cd docker && docker compose -f docker-compose.full.yml ps; \
	else \
		echo "No deployment detected"; \
	fi

# Setup helpers
setup-cron:
	@echo "Setting up cron jobs..."
	sudo ./deployment/scripts/setup-cron.sh

setup-logrotate:
	@echo "Setting up log rotation..."
	sudo cp deployment/logrotate/stock-trading /etc/logrotate.d/

# Utilities
shell:
	./venv/bin/python

requirements:
	./venv/bin/pip freeze > requirements.txt
