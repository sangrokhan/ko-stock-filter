#!/bin/bash
#
# Rolling Update Script for Stock Trading System
# This script performs zero-downtime updates by restarting services one at a time
#
# Usage: ./rolling-update.sh [service_name]
#        ./rolling-update.sh                # Updates all services
#        ./rolling-update.sh trading-engine # Updates specific service
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

# Service update order (respects dependencies)
SERVICES=(
    "stock-trading-data-collector"
    "stock-trading-indicator-calculator"
    "stock-trading-stock-screener"
    "stock-trading-trading-engine"
    "stock-trading-risk-manager"
    "stock-trading-orchestrator"
)

# Health check function
check_service_health() {
    local service=$1
    local max_attempts=30
    local attempt=0

    log_info "Checking health of ${service}..."

    while [ $attempt -lt $max_attempts ]; do
        if systemctl is-active --quiet "${service}"; then
            log_info "${service} is healthy"
            return 0
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

    # Check if service exists
    if ! systemctl list-unit-files | grep -q "^${service}.service"; then
        log_warn "${service} not found, skipping..."
        return 0
    fi

    # Check current status
    if systemctl is-active --quiet "${service}"; then
        log_info "${service} is currently running"

        # Reload service configuration
        log_info "Reloading ${service} configuration..."
        systemctl reload "${service}" 2>/dev/null || {
            log_warn "Reload not supported, performing restart..."
            systemctl restart "${service}"
        }

        # Wait for service to stabilize
        sleep 5

        # Health check
        if check_service_health "${service}"; then
            log_info "${service} updated successfully"
        else
            log_error "${service} failed to restart properly"
            return 1
        fi
    else
        log_warn "${service} is not running, starting..."
        systemctl start "${service}"

        if check_service_health "${service}"; then
            log_info "${service} started successfully"
        else
            log_error "${service} failed to start"
            return 1
        fi
    fi

    return 0
}

# Main execution
main() {
    log_step "Starting rolling update..."

    # Check if running as root or with sudo
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi

    # Specific service or all services
    if [ $# -eq 1 ]; then
        local target_service="stock-trading-$1"
        log_info "Updating specific service: ${target_service}"

        if update_service "${target_service}"; then
            log_info "Service update completed successfully"
        else
            log_error "Service update failed"
            exit 1
        fi
    else
        log_info "Updating all services..."

        # Create pre-update backup
        log_step "Creating pre-update database backup..."
        if [ -f "${SCRIPT_DIR}/backup-database.sh" ]; then
            sudo -u postgres "${SCRIPT_DIR}/backup-database.sh" "pre_update_$(date +%Y%m%d_%H%M%S)" || {
                log_warn "Backup failed, but continuing with update..."
            }
        fi

        # Update services one by one
        local failed_services=()

        for service in "${SERVICES[@]}"; do
            if ! update_service "${service}"; then
                failed_services+=("${service}")
            fi

            # Wait between service updates
            log_info "Waiting 10 seconds before next service..."
            sleep 10
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

    log_step "Rolling update completed!"
}

main "$@"
