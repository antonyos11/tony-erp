#!/bin/bash
# ==============================================================
# RITA ERP Backup Script — Sprint 20
# ==============================================================
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/www/rita-erp/backups"
PROJECT_DIR="/var/www/rita-erp"

mkdir -p $BACKUP_DIR

# Database backup
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    cp "$PROJECT_DIR/db.sqlite3" "$BACKUP_DIR/db_$DATE.sqlite3"
    echo "[OK] Database backup: db_$DATE.sqlite3"
else
    # PostgreSQL backup (if configured)
    if command -v pg_dump &> /dev/null; then
        pg_dump rita_erp > "$BACKUP_DIR/db_$DATE.sql" 2>/dev/null && echo "[OK] PostgreSQL backup: db_$DATE.sql"
    fi
fi

# Media files backup
if [ -d "$PROJECT_DIR/media" ]; then
    tar -czf "$BACKUP_DIR/media_$DATE.tar.gz" "$PROJECT_DIR/media/" 2>/dev/null
    echo "[OK] Media backup: media_$DATE.tar.gz"
fi

# Clean old backups (older than 30 days)
find "$BACKUP_DIR" -mtime +30 -delete 2>/dev/null
echo "[OK] Old backups cleaned"

echo "[DONE] Backup completed: $DATE"
echo "Backup size: $(du -sh $BACKUP_DIR | cut -f1)"
