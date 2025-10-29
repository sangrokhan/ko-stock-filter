#!/bin/bash
#
# PostgreSQL Database Restore Script for Stock Trading System
# This script restores the database from a backup file
#
# Usage: ./restore-database.sh [backup_file]
#        ./restore-database.sh           # Restores from latest backup
#        ./restore-database.sh backup.sql.gz
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"

# Database configuration
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-stock_trading}"
DB_USER="${POSTGRES_USER:-stock_user}"
DB_PASSWORD="${POSTGRES_PASSWORD:-stock_password}"

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

# Function to prompt for confirmation
confirm() {
    local prompt="$1"
    local response

    read -p "${prompt} [y/N]: " response
    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Determine backup file to restore
if [ $# -eq 0 ]; then
    BACKUP_FILE="${BACKUP_DIR}/latest.sql.gz"
    log_info "No backup file specified, using latest backup"
else
    BACKUP_FILE="$1"
    if [[ ! "$BACKUP_FILE" = /* ]]; then
        BACKUP_FILE="${BACKUP_DIR}/${BACKUP_FILE}"
    fi
fi

# Check if backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    log_error "Backup file not found: ${BACKUP_FILE}"
    log_info "Available backups:"
    ls -lh "${BACKUP_DIR}"/*.sql.gz 2>/dev/null || log_warn "No backups found in ${BACKUP_DIR}"
    exit 1
fi

# Show backup information
log_info "Backup file: ${BACKUP_FILE}"
BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
log_info "Backup size: ${BACKUP_SIZE}"

# Check if metadata exists
BACKUP_META="${BACKUP_FILE%.sql.gz}.meta"
if [ -f "${BACKUP_META}" ]; then
    log_info "Backup metadata:"
    cat "${BACKUP_META}"
fi

# WARNING: This will delete all existing data
log_warn "WARNING: This will DROP and RECREATE the database!"
log_warn "Database: ${DB_NAME} on ${DB_HOST}:${DB_PORT}"
log_warn "All existing data will be LOST!"

if ! confirm "Are you sure you want to continue?"; then
    log_info "Restore cancelled by user"
    exit 0
fi

# Set PostgreSQL password
export PGPASSWORD="${DB_PASSWORD}"

# Create pre-restore backup
log_info "Creating pre-restore backup as a safety measure..."
PRE_RESTORE_BACKUP="${BACKUP_DIR}/pre_restore_$(date +"%Y%m%d_%H%M%S").sql.gz"

if pg_dump -h "${DB_HOST}" \
           -p "${DB_PORT}" \
           -U "${DB_USER}" \
           -d "${DB_NAME}" \
           --format=plain \
           --no-owner \
           --no-acl 2>/dev/null | gzip > "${PRE_RESTORE_BACKUP}"; then
    log_info "Pre-restore backup created: ${PRE_RESTORE_BACKUP}"
else
    log_warn "Could not create pre-restore backup (database may not exist yet)"
    rm -f "${PRE_RESTORE_BACKUP}"
fi

# Terminate existing connections
log_info "Terminating existing database connections..."
psql -h "${DB_HOST}" \
     -p "${DB_PORT}" \
     -U "${DB_USER}" \
     -d postgres \
     -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();" \
     > /dev/null 2>&1 || true

# Drop and recreate database
log_info "Dropping existing database..."
psql -h "${DB_HOST}" \
     -p "${DB_PORT}" \
     -U "${DB_USER}" \
     -d postgres \
     -c "DROP DATABASE IF EXISTS ${DB_NAME};" || log_warn "Database might not exist"

log_info "Creating database..."
psql -h "${DB_HOST}" \
     -p "${DB_PORT}" \
     -U "${DB_USER}" \
     -d postgres \
     -c "CREATE DATABASE ${DB_NAME};"

# Restore database
log_info "Restoring database from backup..."

if zcat "${BACKUP_FILE}" | psql -h "${DB_HOST}" \
                                 -p "${DB_PORT}" \
                                 -U "${DB_USER}" \
                                 -d "${DB_NAME}" \
                                 --single-transaction \
                                 -v ON_ERROR_STOP=1 \
                                 > /dev/null; then
    log_info "Database restored successfully!"
else
    log_error "Database restore failed!"
    log_error "Attempting to restore from pre-restore backup..."

    if [ -f "${PRE_RESTORE_BACKUP}" ]; then
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME};"
        zcat "${PRE_RESTORE_BACKUP}" | psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" > /dev/null
        log_info "Restored from pre-restore backup"
    fi

    unset PGPASSWORD
    exit 1
fi

# Verify restore
log_info "Verifying restore..."
TABLE_COUNT=$(psql -h "${DB_HOST}" \
                   -p "${DB_PORT}" \
                   -U "${DB_USER}" \
                   -d "${DB_NAME}" \
                   -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

log_info "Tables restored: ${TABLE_COUNT}"

# Run database migrations to ensure schema is up to date
log_info "Running database migrations..."
cd "${PROJECT_ROOT}"
if [ -f "alembic.ini" ]; then
    alembic upgrade head && log_info "Migrations completed" || log_warn "Migrations failed"
else
    log_warn "alembic.ini not found, skipping migrations"
fi

# Analyze database for query optimization
log_info "Analyzing database..."
psql -h "${DB_HOST}" \
     -p "${DB_PORT}" \
     -U "${DB_USER}" \
     -d "${DB_NAME}" \
     -c "ANALYZE;" > /dev/null

# Unset password
unset PGPASSWORD

log_info "Database restore completed successfully!"
log_info "Pre-restore backup saved at: ${PRE_RESTORE_BACKUP}"

exit 0
