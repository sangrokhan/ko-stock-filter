#!/bin/bash
#
# Quick Deploy Script for Stock Trading System
# This script performs a quick deployment with minimal downtime
#
# Usage: ./quick-deploy.sh
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Main execution
main() {
    log_step "Starting quick deployment..."

    cd "${PROJECT_ROOT}"

    # Pull latest code
    log_step "Pulling latest code from repository..."
    if [ -d ".git" ]; then
        git fetch origin
        local current_branch=$(git rev-parse --abbrev-ref HEAD)
        log_info "Current branch: ${current_branch}"

        git pull origin "${current_branch}" || {
            log_error "Failed to pull latest code"
            exit 1
        }
    else
        log_warn "Not a git repository, skipping code pull"
    fi

    # Install/update dependencies
    log_step "Updating dependencies..."
    if [ -f "requirements.txt" ]; then
        if [ -d "venv" ]; then
            source venv/bin/activate
        fi

        pip install -r requirements.txt --quiet || {
            log_error "Failed to install dependencies"
            exit 1
        }
    fi

    # Run database migrations
    log_step "Running database migrations..."
    if [ -f "alembic.ini" ]; then
        alembic upgrade head || {
            log_error "Database migration failed"
            exit 1
        }
    fi

    # Build Docker images (if using Docker)
    if [ -f "docker/docker-compose.full.yml" ]; then
        log_step "Building Docker images..."
        docker compose -f docker/docker-compose.full.yml build --parallel || {
            log_warn "Docker build failed, continuing..."
        }
    fi

    # Perform rolling update
    log_step "Performing rolling update..."
    if [ -f "${SCRIPT_DIR}/rolling-update.sh" ]; then
        "${SCRIPT_DIR}/rolling-update.sh" || {
            log_error "Rolling update failed"
            exit 1
        }
    elif [ -f "${SCRIPT_DIR}/docker-rolling-update.sh" ]; then
        "${SCRIPT_DIR}/docker-rolling-update.sh" || {
            log_error "Docker rolling update failed"
            exit 1
        }
    else
        log_error "No update script found"
        exit 1
    fi

    # Verify deployment
    log_step "Verifying deployment..."
    sleep 5

    # Check service health
    local all_healthy=true
    local services=(
        "data-collector:8001"
        "indicator-calculator:8002"
        "stock-screener:8003"
        "trading-engine:8004"
        "risk-manager:8005"
    )

    for service_port in "${services[@]}"; do
        local service="${service_port%%:*}"
        local port="${service_port##*:}"

        log_info "Checking ${service} on port ${port}..."

        if curl -sf "http://localhost:${port}/health" > /dev/null 2>&1; then
            log_info "${service} is healthy"
        else
            log_warn "${service} health check failed"
            all_healthy=false
        fi
    done

    # Report results
    echo ""
    log_step "Deployment Summary"
    echo "=================="

    if [ "${all_healthy}" = true ]; then
        log_info "All services are healthy"
        log_info "Deployment completed successfully!"
    else
        log_warn "Some services are not responding to health checks"
        log_warn "Please investigate service logs"
    fi

    log_info "Deployment timestamp: $(date)"
    log_info "Current git commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
}

main "$@"
