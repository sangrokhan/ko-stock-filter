#!/bin/bash
#
# Cron Job Setup Script for Stock Trading System
# Sets up automated tasks like backups and health checks
#
# Usage: sudo ./setup-cron.sh
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root or with sudo"
    exit 1
fi

log_info "Setting up cron jobs for Stock Trading System..."

# Create cron job file
CRON_FILE="/etc/cron.d/stock-trading"

cat > "${CRON_FILE}" <<'EOF'
# Cron jobs for Stock Trading System
#
# Format: minute hour day month weekday user command

# Database backups - Daily at 2:00 AM
0 2 * * * root /opt/stock-trading/deployment/scripts/backup-database.sh >> /opt/stock-trading/logs/backup.log 2>&1

# Redis backups - Every 6 hours
0 */6 * * * root /opt/stock-trading/deployment/scripts/backup-redis.sh >> /opt/stock-trading/logs/backup-redis.log 2>&1

# Health check - Every 5 minutes (logs only if failed)
*/5 * * * * root /opt/stock-trading/deployment/scripts/health-check.sh > /dev/null 2>&1 || echo "$(date): Health check failed" >> /opt/stock-trading/logs/health-check.log

# Clean old logs - Weekly on Sunday at 3:00 AM
0 3 * * 0 root find /opt/stock-trading/logs -name "*.log.*" -mtime +30 -delete

# Clean old backups - Daily at 4:00 AM (handled by backup scripts retention)
# Backups older than 30 days are automatically cleaned during backup

# Restart orchestrator daily at 1:00 AM (graceful restart)
0 1 * * * root /opt/stock-trading/deployment/scripts/graceful-restart.sh orchestrator >> /opt/stock-trading/logs/restart.log 2>&1

# System resource monitoring - Every 15 minutes
*/15 * * * * root df -h | grep -E '^/dev/' >> /opt/stock-trading/logs/disk-usage.log 2>&1
*/15 * * * * root free -m >> /opt/stock-trading/logs/memory-usage.log 2>&1

EOF

chmod 644 "${CRON_FILE}"

log_info "Cron jobs installed to ${CRON_FILE}"
log_info ""
log_info "Scheduled tasks:"
log_info "  - Daily database backup at 2:00 AM"
log_info "  - Redis backup every 6 hours"
log_info "  - Health check every 5 minutes"
log_info "  - Clean old logs weekly on Sunday at 3:00 AM"
log_info "  - Graceful restart daily at 1:00 AM"
log_info "  - Resource monitoring every 15 minutes"
log_info ""
log_info "To view cron logs:"
log_info "  tail -f /opt/stock-trading/logs/backup.log"
log_info "  tail -f /opt/stock-trading/logs/health-check.log"
log_info ""
log_warn "Note: Adjust schedules in ${CRON_FILE} as needed"

exit 0
