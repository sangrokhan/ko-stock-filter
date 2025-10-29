#!/bin/bash
#
# Graceful Restart Script for Stock Trading System
# This script gracefully restarts services with proper shutdown handling
#
# Usage: ./graceful-restart.sh [service_name]
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GRACE_PERIOD=30  # seconds to wait for graceful shutdown

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

# Gracefully stop a service
graceful_stop() {
    local service=$1

    log_step "Gracefully stopping ${service}..."

    # Send SIGTERM for graceful shutdown
    if systemctl is-active --quiet "${service}"; then
        log_info "Sending SIGTERM to ${service}..."
        systemctl kill -s TERM "${service}"

        # Wait for graceful shutdown
        local elapsed=0
        while [ $elapsed -lt $GRACE_PERIOD ]; do
            if ! systemctl is-active --quiet "${service}"; then
                log_info "${service} stopped gracefully"
                return 0
            fi

            sleep 1
            elapsed=$((elapsed + 1))
        done

        # Force stop if still running
        log_warn "${service} did not stop gracefully, forcing stop..."
        systemctl stop "${service}"
    else
        log_info "${service} is already stopped"
    fi

    return 0
}

# Graceful restart with health check
graceful_restart() {
    local service=$1

    log_step "Gracefully restarting ${service}..."

    # Stop gracefully
    graceful_stop "${service}"

    # Wait a moment before starting
    sleep 2

    # Start service
    log_info "Starting ${service}..."
    systemctl start "${service}"

    # Wait for startup
    sleep 5

    # Health check
    if systemctl is-active --quiet "${service}"; then
        log_info "${service} restarted successfully"
        return 0
    else
        log_error "${service} failed to start"
        return 1
    fi
}

# Main execution
main() {
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi

    if [ $# -eq 0 ]; then
        log_error "Usage: $0 <service_name>"
        log_info "Example: $0 stock-trading-trading-engine"
        exit 1
    fi

    local service="$1"

    # Add prefix if not provided
    if [[ ! "$service" =~ ^stock-trading- ]]; then
        service="stock-trading-${service}"
    fi

    # Check if service exists
    if ! systemctl list-unit-files | grep -q "^${service}.service"; then
        log_error "Service ${service} not found"
        exit 1
    fi

    # Perform graceful restart
    if graceful_restart "${service}"; then
        log_info "Graceful restart completed successfully"
        systemctl status "${service}" --no-pager
        exit 0
    else
        log_error "Graceful restart failed"
        exit 1
    fi
}

main "$@"
