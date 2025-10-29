#!/bin/bash
#
# Docker Rolling Update Script for Stock Trading System
# This script performs zero-downtime updates for Docker containers
#
# Usage: ./docker-rolling-update.sh [service_name]
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker/docker-compose.full.yml"

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

# Service update order
SERVICES=(
    "data-collector"
    "indicator-calculator"
    "stability-calculator"
    "stock-scorer"
    "stock-screener"
    "watchlist-manager"
    "price-monitor"
    "trading-engine"
    "risk-manager"
    "orchestrator"
)

# Health check function
check_container_health() {
    local service=$1
    local max_attempts=30
    local attempt=0

    log_info "Checking health of ${service}..."

    while [ $attempt -lt $max_attempts ]; do
        local status=$(docker compose -f "${COMPOSE_FILE}" ps -q "${service}" | xargs docker inspect -f '{{.State.Status}}' 2>/dev/null || echo "unknown")

        if [ "${status}" = "running" ]; then
            # Additional health check if service has health endpoint
            local health=$(docker compose -f "${COMPOSE_FILE}" ps -q "${service}" | xargs docker inspect -f '{{.State.Health.Status}}' 2>/dev/null || echo "none")

            if [ "${health}" = "healthy" ] || [ "${health}" = "none" ]; then
                log_info "${service} is healthy"
                return 0
            fi
        fi

        attempt=$((attempt + 1))
        log_warn "Waiting for ${service} to become healthy (attempt ${attempt}/${max_attempts})..."
        sleep 2
    done

    log_error "${service} failed health check"
    return 1
}

# Update single service
update_service() {
    local service=$1

    log_step "Updating ${service}..."

    # Pull latest image
    log_info "Pulling latest image for ${service}..."
    docker compose -f "${COMPOSE_FILE}" pull "${service}" || {
        log_warn "Failed to pull image, using existing image..."
    }

    # Scale up new container
    log_info "Starting new container for ${service}..."
    docker compose -f "${COMPOSE_FILE}" up -d --no-deps --scale "${service}=2" --no-recreate "${service}" || {
        log_error "Failed to scale up ${service}"
        return 1
    }

    # Wait for new container to be healthy
    sleep 5

    # Check new container health
    if ! check_container_health "${service}"; then
        log_error "New container for ${service} is not healthy, rolling back..."
        docker compose -f "${COMPOSE_FILE}" up -d --no-deps --scale "${service}=1" --no-recreate "${service}"
        return 1
    fi

    # Scale down to 1 (removes old container)
    log_info "Removing old container for ${service}..."
    docker compose -f "${COMPOSE_FILE}" up -d --no-deps --scale "${service}=1" "${service}"

    # Final health check
    sleep 3
    if check_container_health "${service}"; then
        log_info "${service} updated successfully"
        return 0
    else
        log_error "${service} failed final health check"
        return 1
    fi
}

# Main execution
main() {
    log_step "Starting Docker rolling update..."

    # Check if Docker Compose file exists
    if [ ! -f "${COMPOSE_FILE}" ]; then
        log_error "Docker Compose file not found: ${COMPOSE_FILE}"
        exit 1
    fi

    # Create backup
    log_step "Creating pre-update backup..."
    if [ -f "${SCRIPT_DIR}/backup-database.sh" ]; then
        export BACKUP_NAME="pre_docker_update_$(date +%Y%m%d_%H%M%S)"
        "${SCRIPT_DIR}/backup-database.sh" "${BACKUP_NAME}" || {
            log_warn "Backup failed, but continuing..."
        }
    fi

    # Update services
    if [ $# -eq 1 ]; then
        local target_service="$1"
        log_info "Updating specific service: ${target_service}"

        if update_service "${target_service}"; then
            log_info "Service update completed successfully"
        else
            log_error "Service update failed"
            exit 1
        fi
    else
        log_info "Updating all services..."

        local failed_services=()

        for service in "${SERVICES[@]}"; do
            if ! update_service "${service}"; then
                failed_services+=("${service}")
            fi

            # Wait between updates
            log_info "Waiting 15 seconds before next service..."
            sleep 15
        done

        # Report results
        if [ ${#failed_services[@]} -eq 0 ]; then
            log_info "All services updated successfully!"
        else
            log_error "The following services failed to update:"
            for service in "${failed_services[@]}"; do
                log_error "  - ${service}"
            done
            exit 1
        fi
    fi

    # Cleanup
    log_step "Cleaning up unused images..."
    docker image prune -f

    log_step "Docker rolling update completed!"
}

main "$@"
