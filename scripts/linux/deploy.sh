#!/bin/bash
# ===============================================================================
# سكريبت النشر السريع - يُستخدم بعد كل تحديث
# ===============================================================================

set -e

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║              🚀 Tony ERP - سكريبت النشر السريع                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"

PROJECT_DIR="/var/www/tony_erp"
cd $PROJECT_DIR

echo "[$(date +'%H:%M:%S')] 📥 سحب التحديثات من Git..."
git pull origin main 2>/dev/null || echo "⚠️ لا يوجد Git repository"

echo "[$(date +'%H:%M:%S')] 📦 تفعيل البيئة الافتراضية..."
source venv/bin/activate

echo "[$(date +'%H:%M:%S')] 📦 تثبيت/تحديث المتطلبات..."
pip install -r requirements.txt --quiet 2>/dev/null

echo "[$(date +'%H:%M:%S')] 🗃️ تطبيق هجرات قاعدة البيانات..."
python manage.py migrate --noinput

echo "[$(date +'%H:%M:%S')] 📁 تجميع الملفات الثابتة..."
python manage.py collectstatic --noinput --clear 2>/dev/null

echo "[$(date +'%H:%M:%S')] 🔄 إعادة تشغيل Gunicorn..."
sudo systemctl restart gunicorn

echo "[$(date +'%H:%M:%S')] 🔄 إعادة تشغيل Celery..."
sudo systemctl restart celery 2>/dev/null || echo "⚠️ Celery غير مُعد"

echo "[$(date +'%H:%M:%S')] 🔄 إعادة تحميل Nginx..."
sudo systemctl reload nginx

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ تم النشر بنجاح!                            ║"
echo "╚══════════════════════════════════════════════════════════════════╝"

# عرض حالة الخدمات
echo ""
echo "📊 حالة الخدمات:"
systemctl is-active gunicorn && echo "   ✓ Gunicorn: نشط" || echo "   ✗ Gunicorn: متوقف"
systemctl is-active nginx && echo "   ✓ Nginx: نشط" || echo "   ✗ Nginx: متوقف"
systemctl is-active redis && echo "   ✓ Redis: نشط" || echo "   ✗ Redis: متوقف"
systemctl is-active postgresql && echo "   ✓ PostgreSQL: نشط" || echo "   ✗ PostgreSQL: متوقف"

echo ""
echo "✅ الموقع جاهز للاستخدام!"
