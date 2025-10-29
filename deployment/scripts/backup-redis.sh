#!/bin/bash
#
# Redis Backup Script for Stock Trading System
# This script creates backups of Redis data
#
# Usage: ./backup-redis.sh [backup_name]
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups/redis}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="${1:-redis_backup_${TIMESTAMP}}"

# Redis configuration
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
REDIS_DATA_DIR="${REDIS_DATA_DIR:-/var/lib/redis/stock-trading}"

# Backup retention (days)
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Create backup directory
mkdir -p "${BACKUP_DIR}"

log_info "Starting Redis backup..."
log_info "Redis: ${REDIS_HOST}:${REDIS_PORT}"
log_info "Backup directory: ${BACKUP_DIR}"

# Trigger Redis BGSAVE
log_info "Triggering Redis background save..."

REDIS_CMD="redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT}"
if [ -n "${REDIS_PASSWORD}" ]; then
    REDIS_CMD="${REDIS_CMD} -a ${REDIS_PASSWORD}"
fi

if ${REDIS_CMD} BGSAVE | grep -q "Background saving started"; then
    log_info "Background save initiated"

    # Wait for save to complete
    log_info "Waiting for save to complete..."
    while true; do
        LASTSAVE=$(${REDIS_CMD} LASTSAVE)
        sleep 1
        NEWSAVE=$(${REDIS_CMD} LASTSAVE)
        if [ "${NEWSAVE}" != "${LASTSAVE}" ]; then
            break
        fi
    done
    log_info "Background save completed"
else
    log_error "Failed to initiate background save"
    exit 1
fi

# Copy RDB file
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.rdb"

if [ -f "${REDIS_DATA_DIR}/dump.rdb" ]; then
    cp "${REDIS_DATA_DIR}/dump.rdb" "${BACKUP_FILE}"
    log_info "RDB file copied to: ${BACKUP_FILE}"

    # Compress backup
    gzip -f "${BACKUP_FILE}"
    BACKUP_FILE="${BACKUP_FILE}.gz"
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    log_info "Backup compressed: ${BACKUP_FILE}"
    log_info "Backup size: ${BACKUP_SIZE}"
else
    log_error "Redis dump file not found at: ${REDIS_DATA_DIR}/dump.rdb"
    exit 1
fi

# Create backup metadata
METADATA_FILE="${BACKUP_DIR}/${BACKUP_NAME}.meta"
cat > "${METADATA_FILE}" <<EOF
{
  "backup_name": "${BACKUP_NAME}",
  "timestamp": "${TIMESTAMP}",
  "redis_host": "${REDIS_HOST}",
  "redis_port": ${REDIS_PORT},
  "size": "${BACKUP_SIZE}",
  "created_by": "$(whoami)",
  "hostname": "$(hostname)"
}
EOF

# Create symlink to latest
ln -sf "${BACKUP_FILE}" "${BACKUP_DIR}/latest.rdb.gz"

# Clean up old backups
log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."
DELETED_COUNT=$(find "${BACKUP_DIR}" -name "redis_backup_*.rdb.gz" -type f -mtime +${RETENTION_DAYS} -delete -print | wc -l)
find "${BACKUP_DIR}" -name "redis_backup_*.meta" -type f -mtime +${RETENTION_DAYS} -delete

if [ "${DELETED_COUNT}" -gt 0 ]; then
    log_info "Deleted ${DELETED_COUNT} old backup(s)"
fi

log_info "Redis backup completed successfully!"
log_info "Backup file: ${BACKUP_FILE}"

exit 0
