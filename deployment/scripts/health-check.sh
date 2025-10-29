#!/bin/bash
#
# Health Check Script for Stock Trading System
# Checks the health of all services and reports status
#
# Usage: ./health-check.sh
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

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

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
}

# Check function
check() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
}

# Check HTTP endpoint
check_http() {
    local name=$1
    local url=$2
    local expected=${3:-200}

    check
    if response=$(curl -s -o /dev/null -w "%{http_code}" "${url}" 2>/dev/null); then
        if [ "${response}" = "${expected}" ]; then
            log_pass "${name} - HTTP ${response}"
        else
            log_fail "${name} - HTTP ${response} (expected ${expected})"
        fi
    else
        log_fail "${name} - Connection failed"
    fi
}

# Check systemd service
check_systemd() {
    local name=$1
    local service=$2

    check
    if systemctl is-active --quiet "${service}"; then
        log_pass "${name} - Running"
    else
        log_fail "${name} - Not running"
    fi
}

# Check database
check_database() {
    check
    if PGPASSWORD="${POSTGRES_PASSWORD:-stock_password}" psql -h localhost -U "${POSTGRES_USER:-stock_user}" -d "${POSTGRES_DB:-stock_trading}" -c "SELECT 1" > /dev/null 2>&1; then
        log_pass "PostgreSQL - Connected"
    else
        log_fail "PostgreSQL - Connection failed"
    fi
}

# Check Redis
check_redis() {
    check
    if redis-cli ping > /dev/null 2>&1; then
        log_pass "Redis - Responding"
    else
        log_fail "Redis - Not responding"
    fi
}

# Main health check
main() {
    echo "========================================"
    echo "Stock Trading System - Health Check"
    echo "========================================"
    echo "Timestamp: $(date)"
    echo ""

    # Infrastructure checks
    echo "Infrastructure Services:"
    echo "----------------------------------------"
    check_database
    check_redis
    echo ""

    # Service health endpoints
    echo "Application Services (HTTP):"
    echo "----------------------------------------"
    check_http "Data Collector" "http://localhost:8001/health"
    check_http "Indicator Calculator" "http://localhost:8002/health"
    check_http "Stock Screener" "http://localhost:8003/health"
    check_http "Trading Engine" "http://localhost:8004/health"
    check_http "Risk Manager" "http://localhost:8005/health"
    echo ""

    # Systemd services (if running in systemd mode)
    if command -v systemctl &> /dev/null; then
        echo "Systemd Services:"
        echo "----------------------------------------"
        check_systemd "PostgreSQL" "postgresql"
        check_systemd "Redis" "redis-server"
        check_systemd "Data Collector" "stock-trading-data-collector"
        check_systemd "Indicator Calculator" "stock-trading-indicator-calculator"
        check_systemd "Stock Screener" "stock-trading-stock-screener"
        check_systemd "Trading Engine" "stock-trading-trading-engine"
        check_systemd "Risk Manager" "stock-trading-risk-manager"
        check_systemd "Orchestrator" "stock-trading-orchestrator"
        echo ""
    fi

    # Docker containers (if running in Docker mode)
    if command -v docker &> /dev/null; then
        echo "Docker Containers:"
        echo "----------------------------------------"
        if docker ps > /dev/null 2>&1; then
            local containers=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "stock-trading|data-collector|trading-engine" || true)
            if [ -n "${containers}" ]; then
                echo "${containers}"
            else
                log_warn "No stock trading containers found"
            fi
        else
            log_warn "Docker not accessible"
        fi
        echo ""
    fi

    # Summary
    echo "========================================"
    echo "Health Check Summary"
    echo "========================================"
    echo "Total checks: ${TOTAL_CHECKS}"
    echo -e "${GREEN}Passed: ${PASSED_CHECKS}${NC}"
    echo -e "${RED}Failed: ${FAILED_CHECKS}${NC}"
    echo ""

    if [ ${FAILED_CHECKS} -eq 0 ]; then
        echo -e "${GREEN}All systems operational!${NC}"
        exit 0
    else
        echo -e "${RED}Some systems are not healthy${NC}"
        exit 1
    fi
}

main "$@"
