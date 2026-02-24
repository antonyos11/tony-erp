#!/bin/bash
# Tony ERP Database Backup Script
# Runs daily via the backup container

set -e

# Configuration
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/tony_erp_${DATE}.sql.gz"
KEEP_DAYS=30

echo "[$(date)] Starting backup..."

# Create backup
pg_dump -U ${POSTGRES_USER} -d ${POSTGRES_DB} | gzip > ${BACKUP_FILE}

# Check if backup was created successfully
if [ -f "${BACKUP_FILE}" ]; then
    SIZE=$(ls -lh ${BACKUP_FILE} | awk '{print $5}')
    echo "[$(date)] Backup created: ${BACKUP_FILE} (${SIZE})"
else
    echo "[$(date)] ERROR: Backup failed!"
    exit 1
fi

# Remove old backups
echo "[$(date)] Cleaning up backups older than ${KEEP_DAYS} days..."
find ${BACKUP_DIR} -name "tony_erp_*.sql.gz" -mtime +${KEEP_DAYS} -delete

# List remaining backups
echo "[$(date)] Current backups:"
ls -lh ${BACKUP_DIR}/*.sql.gz 2>/dev/null || echo "No backups found"

echo "[$(date)] Backup completed successfully!"
