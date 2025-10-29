#!/bin/bash
#
# Uninstall Script for Stock Trading System (Systemd)
# Removes all systemd services and optionally removes data
#
# Usage: sudo ./uninstall-systemd.sh [--keep-data]
#

set -euo pipefail

# Configuration
INSTALL_DIR="/opt/stock-trading"
APP_USER="stocktrading"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root or with sudo"
    exit 1
fi

# Parse arguments
KEEP_DATA=false
if [ "${1:-}" = "--keep-data" ]; then
    KEEP_DATA=true
fi

# Confirmation
log_warn "This will uninstall the Stock Trading System"
if [ "${KEEP_DATA}" = false ]; then
    log_warn "WARNING: This will DELETE all data, logs, and backups!"
else
    log_info "Data will be preserved (--keep-data flag set)"
fi

read -p "Are you sure you want to continue? [y/N]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "Uninstall cancelled"
    exit 0
fi

# Uninstall
log_step "Starting uninstallation..."

# Stop and disable services
log_step "Stopping and disabling services..."
SERVICES=(
    "stock-trading-orchestrator"
    "stock-trading-risk-manager"
    "stock-trading-trading-engine"
    "stock-trading-stock-screener"
    "stock-trading-indicator-calculator"
    "stock-trading-data-collector"
)

for service in "${SERVICES[@]}"; do
    if systemctl list-unit-files | grep -q "^${service}.service"; then
        log_info "Stopping ${service}..."
        systemctl stop "${service}" 2>/dev/null || true
        systemctl disable "${service}" 2>/dev/null || true
    fi
done

# Remove systemd service files
log_step "Removing systemd service files..."
rm -f /etc/systemd/system/stock-trading-*.service
systemctl daemon-reload

# Remove cron jobs
log_step "Removing cron jobs..."
rm -f /etc/cron.d/stock-trading

# Remove logrotate configuration
log_step "Removing logrotate configuration..."
rm -f /etc/logrotate.d/stock-trading
rm -f /etc/logrotate.d/stock-trading-docker

# Remove configuration files
log_step "Removing configuration files..."
rm -rf /etc/stock-trading

# Remove application files
if [ "${KEEP_DATA}" = false ]; then
    log_step "Removing application directory..."
    rm -rf "${INSTALL_DIR}"

    # Remove database
    log_step "Removing database..."
    sudo -u postgres psql <<EOF 2>/dev/null || true
DROP DATABASE IF EXISTS stock_trading;
DROP USER IF EXISTS stock_user;
EOF

    # Remove application user
    log_step "Removing application user..."
    if id -u "${APP_USER}" > /dev/null 2>&1; then
        userdel -r "${APP_USER}" 2>/dev/null || true
    fi
else
    log_info "Preserving data in ${INSTALL_DIR}"
    log_info "Preserving database"
fi

log_step "Uninstallation complete!"

if [ "${KEEP_DATA}" = true ]; then
    log_info "Data preserved in:"
    log_info "  - Application: ${INSTALL_DIR}"
    log_info "  - Database: stock_trading"
    log_info "To completely remove data, run: sudo rm -rf ${INSTALL_DIR}"
fi

exit 0
