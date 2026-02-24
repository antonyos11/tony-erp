#!/bin/bash
# ============================================
# Tony ERP - Automated Backup Script
# النسخ الاحتياطي التلقائي لنظام Tony ERP
# ============================================

set -euo pipefail

# Configuration
BACKUP_DIR="/var/www/tony_erp/backups"
APP_DIR="/var/www/tony_erp"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${DATE}"
KEEP_DAYS=30  # الاحتفاظ بالنسخ لمدة 30 يوم

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "========== بدء النسخ الاحتياطي =========="

# Create backup directory
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# 1. PostgreSQL Database Backup
log "1/4 - نسخ قاعدة البيانات PostgreSQL..."
PGPASSWORD="${POSTGRES_PASSWORD:-Tony@2026Secure!}" pg_dump \
    -h "${POSTGRES_HOST:-localhost}" \
    -p "${POSTGRES_PORT:-5432}" \
    -U "${POSTGRES_USER:-tony_user}" \
    -d "${POSTGRES_DB:-tony_erp}" \
    --format=custom \
    --compress=9 \
    -f "${BACKUP_DIR}/${BACKUP_NAME}/database.dump" 2>/dev/null

if [ $? -eq 0 ]; then
    log "   ✅ قاعدة البيانات - تم بنجاح"
else
    log "   ❌ قاعدة البيانات - فشل!"
fi

# 2. Media files backup
log "2/4 - نسخ ملفات الوسائط..."
if [ -d "${APP_DIR}/media" ]; then
    tar czf "${BACKUP_DIR}/${BACKUP_NAME}/media.tar.gz" \
        -C "${APP_DIR}" media/ 2>/dev/null
    log "   ✅ ملفات الوسائط - تم بنجاح"
else
    log "   ⏭️ لا توجد ملفات وسائط"
fi

# 3. Configuration files backup
log "3/4 - نسخ ملفات الإعدادات..."
tar czf "${BACKUP_DIR}/${BACKUP_NAME}/config.tar.gz" \
    -C "${APP_DIR}" \
    .env \
    nginx.conf \
    accountant_pro/settings.py \
    2>/dev/null || true
log "   ✅ ملفات الإعدادات - تم بنجاح"

# 4. Create final compressed archive
log "4/4 - ضغط النسخة الاحتياطية النهائية..."
cd "${BACKUP_DIR}"
tar czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}/"
rm -rf "${BACKUP_NAME}/"

# Calculate size
BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)
log "   ✅ الحجم النهائي: ${BACKUP_SIZE}"

# 5. Cleanup old backups
log "حذف النسخ الأقدم من ${KEEP_DAYS} يوم..."
DELETED=$(find "${BACKUP_DIR}" -name "backup_*.tar.gz" -mtime +${KEEP_DAYS} -delete -print | wc -l)
log "   تم حذف ${DELETED} نسخة قديمة"

log "========== انتهى النسخ الاحتياطي بنجاح =========="
log "الملف: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz (${BACKUP_SIZE})"
