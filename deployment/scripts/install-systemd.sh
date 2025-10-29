#!/bin/bash
#
# Systemd Installation Script for Stock Trading System
# This script sets up the complete systemd deployment
#
# Usage: sudo ./install-systemd.sh
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INSTALL_DIR="/opt/stock-trading"
APP_USER="stocktrading"
APP_GROUP="stocktrading"

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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root or with sudo"
    exit 1
fi

# Main installation
main() {
    log_step "Starting Stock Trading System installation..."

    # Install system dependencies
    log_step "Installing system dependencies..."
    apt update
    apt install -y \
        python3.11 \
        python3.11-venv \
        python3-pip \
        postgresql-15 \
        postgresql-client-15 \
        redis-server \
        gcc \
        g++ \
        make \
        libpq-dev \
        curl \
        git \
        logrotate

    # Create application user
    log_step "Creating application user..."
    if ! id -u "${APP_USER}" > /dev/null 2>&1; then
        useradd -r -m -d "${INSTALL_DIR}" -s /bin/bash "${APP_USER}"
        log_info "User ${APP_USER} created"
    else
        log_warn "User ${APP_USER} already exists"
    fi

    # Create directory structure
    log_step "Creating directory structure..."
    mkdir -p "${INSTALL_DIR}"
    mkdir -p "${INSTALL_DIR}/logs"
    mkdir -p "${INSTALL_DIR}/data"
    mkdir -p "${INSTALL_DIR}/backups"
    mkdir -p /etc/stock-trading

    # Copy application files
    log_step "Copying application files..."
    if [ "${PROJECT_ROOT}" != "${INSTALL_DIR}" ]; then
        rsync -av --exclude='.git' \
                  --exclude='venv' \
                  --exclude='__pycache__' \
                  --exclude='*.pyc' \
                  "${PROJECT_ROOT}/" "${INSTALL_DIR}/"
    fi

    # Set ownership
    chown -R "${APP_USER}:${APP_GROUP}" "${INSTALL_DIR}"

    # Create virtual environment
    log_step "Creating Python virtual environment..."
    if [ ! -d "${INSTALL_DIR}/venv" ]; then
        sudo -u "${APP_USER}" python3.11 -m venv "${INSTALL_DIR}/venv"
    fi

    # Install Python dependencies
    log_step "Installing Python dependencies..."
    sudo -u "${APP_USER}" "${INSTALL_DIR}/venv/bin/pip" install --upgrade pip
    sudo -u "${APP_USER}" "${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

    # Configure PostgreSQL
    log_step "Configuring PostgreSQL..."
    systemctl enable postgresql
    systemctl start postgresql

    # Create database (if not exists)
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'stock_trading'" | grep -q 1 || {
        log_info "Creating database..."
        sudo -u postgres psql <<EOF
CREATE USER stock_user WITH PASSWORD 'stock_password';
CREATE DATABASE stock_trading OWNER stock_user;
GRANT ALL PRIVILEGES ON DATABASE stock_trading TO stock_user;
EOF
        log_warn "Default database credentials created. Please change the password!"
    }

    # Run database migrations
    log_step "Running database migrations..."
    cd "${INSTALL_DIR}"
    sudo -u "${APP_USER}" "${INSTALL_DIR}/venv/bin/alembic" upgrade head || {
        log_warn "Database migrations failed, you may need to run them manually"
    }

    # Configure Redis
    log_step "Configuring Redis..."
    systemctl enable redis-server
    systemctl start redis-server

    # Install systemd service files
    log_step "Installing systemd service files..."
    cp "${INSTALL_DIR}/deployment/systemd"/*.service /etc/systemd/system/
    systemctl daemon-reload

    # Install log rotation
    log_step "Installing log rotation configuration..."
    cp "${INSTALL_DIR}/deployment/logrotate/stock-trading" /etc/logrotate.d/

    # Create environment file template
    log_step "Creating environment file templates..."
    for service in data-collector indicator-calculator stock-screener trading-engine risk-manager orchestrator; do
        if [ ! -f "/etc/stock-trading/${service}.env" ]; then
            cat > "/etc/stock-trading/${service}.env" <<EOF
# Environment configuration for ${service}
DATABASE_URL=postgresql://stock_user:stock_password@localhost:5432/stock_trading
REDIS_HOST=localhost
REDIS_PORT=6379
LOG_LEVEL=INFO
EOF
            chmod 600 "/etc/stock-trading/${service}.env"
        fi
    done

    # Enable services
    log_step "Enabling systemd services..."
    systemctl enable stock-trading-postgres
    systemctl enable stock-trading-redis
    systemctl enable stock-trading-data-collector
    systemctl enable stock-trading-indicator-calculator
    systemctl enable stock-trading-stock-screener
    systemctl enable stock-trading-trading-engine
    systemctl enable stock-trading-risk-manager
    systemctl enable stock-trading-orchestrator

    # Installation complete
    log_step "Installation completed!"
    echo ""
    log_info "Next steps:"
    echo "  1. Configure environment files in /etc/stock-trading/"
    echo "  2. Update database password in environment files"
    echo "  3. Add API keys to environment files"
    echo "  4. Start services:"
    echo "     sudo systemctl start stock-trading-orchestrator"
    echo "  5. Check status:"
    echo "     sudo systemctl status stock-trading-orchestrator"
    echo "  6. View logs:"
    echo "     sudo journalctl -u stock-trading-orchestrator -f"
    echo ""
    log_warn "IMPORTANT: Change default database password!"
    log_warn "IMPORTANT: Configure API keys in /etc/stock-trading/*.env"
}

main "$@"
