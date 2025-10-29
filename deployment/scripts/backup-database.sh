#!/bin/bash
#
# PostgreSQL Database Backup Script for Stock Trading System
# This script creates compressed backups of the PostgreSQL database
#
# Usage: ./backup-database.sh [backup_name]
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="${1:-backup_${TIMESTAMP}}"

# Database configuration (can be overridden by environment variables)
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-stock_trading}"
DB_USER="${POSTGRES_USER:-stock_user}"
DB_PASSWORD="${POSTGRES_PASSWORD:-stock_password}"

# Backup retention (days)
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

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

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

log_info "Starting database backup..."
log_info "Database: ${DB_NAME}"
log_info "Backup directory: ${BACKUP_DIR}"

# Set PostgreSQL password for pg_dump
export PGPASSWORD="${DB_PASSWORD}"

# Backup file paths
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.sql"
BACKUP_FILE_GZ="${BACKUP_FILE}.gz"

# Create backup
log_info "Creating backup: ${BACKUP_NAME}"

if pg_dump -h "${DB_HOST}" \
           -p "${DB_PORT}" \
           -U "${DB_USER}" \
           -d "${DB_NAME}" \
           --verbose \
           --format=plain \
           --no-owner \
           --no-acl \
           -f "${BACKUP_FILE}"; then
    log_info "Database dump completed successfully"
else
    log_error "Database dump failed!"
    exit 1
fi

# Compress backup
log_info "Compressing backup..."
if gzip -f "${BACKUP_FILE}"; then
    log_info "Backup compressed: ${BACKUP_FILE_GZ}"
    BACKUP_SIZE=$(du -h "${BACKUP_FILE_GZ}" | cut -f1)
    log_info "Backup size: ${BACKUP_SIZE}"
else
    log_error "Compression failed!"
    exit 1
fi

# Create backup metadata
METADATA_FILE="${BACKUP_DIR}/${BACKUP_NAME}.meta"
cat > "${METADATA_FILE}" <<EOF
{
  "backup_name": "${BACKUP_NAME}",
  "timestamp": "${TIMESTAMP}",
  "database": "${DB_NAME}",
  "host": "${DB_HOST}",
  "port": ${DB_PORT},
  "size": "${BACKUP_SIZE}",
  "created_by": "$(whoami)",
  "hostname": "$(hostname)"
}
EOF

log_info "Backup metadata saved: ${METADATA_FILE}"

# Create a symlink to the latest backup
LATEST_LINK="${BACKUP_DIR}/latest.sql.gz"
ln -sf "${BACKUP_FILE_GZ}" "${LATEST_LINK}"
log_info "Latest backup symlink updated"

# Clean up old backups
log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."
DELETED_COUNT=$(find "${BACKUP_DIR}" -name "backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete -print | wc -l)
find "${BACKUP_DIR}" -name "backup_*.meta" -type f -mtime +${RETENTION_DAYS} -delete

if [ "${DELETED_COUNT}" -gt 0 ]; then
    log_info "Deleted ${DELETED_COUNT} old backup(s)"
else
    log_info "No old backups to delete"
fi

# List current backups
log_info "Current backups:"
ls -lh "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | tail -5 || log_warn "No backups found"

# Unset password
unset PGPASSWORD

log_info "Backup completed successfully!"
log_info "Backup file: ${BACKUP_FILE_GZ}"

exit 0
