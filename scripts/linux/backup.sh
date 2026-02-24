#!/bin/bash
# ===============================================================================
# سكريبت النسخ الاحتياطي - يعمل يومياً عبر cron
# ===============================================================================

set -e

BACKUP_DIR="/var/backups/tony_erp"
PROJECT_DIR="/var/www/tony_erp"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="tony_erp"
DB_USER="tony_user"
DB_PASS="Tony@2026Secure!"
DB_PASS="Tony@2026Secure!"

# إنشاء مجلد النسخ الاحتياطي
mkdir -p $BACKUP_DIR

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║              📦 Tony ERP - النسخ الاحتياطي                       ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "📅 التاريخ: $(date)"
echo ""

# نسخ قاعدة البيانات
echo "[1/4] 🗃️ نسخ قاعدة البيانات..."
PGPASSWORD="$DB_PASS" pg_dump -U $DB_USER -h localhost $DB_NAME > $BACKUP_DIR/db_$DATE.sql 2>/dev/null || {
    echo "⚠️ فشل نسخ PostgreSQL، محاولة SQLite..."
    cp $PROJECT_DIR/db.sqlite3 $BACKUP_DIR/db_$DATE.sqlite3 2>/dev/null || echo "⚠️ لا توجد قاعدة بيانات SQLite"
}

# نسخ ملفات الميديا
echo "[2/4] 📁 نسخ ملفات الميديا..."
if [ -d "$PROJECT_DIR/media" ] && [ "$(ls -A $PROJECT_DIR/media 2>/dev/null)" ]; then
    tar -czf $BACKUP_DIR/media_$DATE.tar.gz -C $PROJECT_DIR media/
    echo "   ✓ تم نسخ ملفات الميديا"
else
    echo "   ⚠️ لا توجد ملفات ميديا"
fi

# نسخ ملف البيئة
echo "[3/4] ⚙️ نسخ ملف الإعدادات..."
if [ -f "$PROJECT_DIR/.env" ]; then
    cp $PROJECT_DIR/.env $BACKUP_DIR/env_$DATE.txt
    echo "   ✓ تم نسخ ملف .env"
fi

# حذف النسخ القديمة (أقدم من 30 يوم)
echo "[4/4] 🗑️ حذف النسخ القديمة..."
find $BACKUP_DIR -type f -mtime +30 -delete
DELETED=$(find $BACKUP_DIR -type f -mtime +30 | wc -l)
echo "   ✓ تم حذف $DELETED ملف قديم"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ تم النسخ الاحتياطي بنجاح!                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "📂 مكان النسخ: $BACKUP_DIR"
echo ""
echo "📋 الملفات المحفوظة:"
ls -lh $BACKUP_DIR/*$DATE* 2>/dev/null | awk '{print "   • " $9 " (" $5 ")"}'

echo ""
echo "💾 إجمالي حجم النسخ الاحتياطية:"
du -sh $BACKUP_DIR | awk '{print "   " $1}'
