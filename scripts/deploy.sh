#!/bin/bash
# =============================================================
# RITA ERP — Deploy Script
# Usage: bash scripts/deploy.sh
# =============================================================
set -e

PROJECT_DIR="/var/www/rita-erp"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="rita-erp"

echo "🚀 RITA ERP — بدء النشر..."
echo "=============================="

# الانتقال إلى مجلد المشروع
cd "$PROJECT_DIR"

# تفعيل البيئة الافتراضية
echo "📦 تفعيل البيئة الافتراضية..."
source "$VENV_DIR/bin/activate"

# تثبيت المتطلبات
echo "📥 تثبيت المتطلبات..."
pip install -r requirements.txt --quiet

# تطبيق الترحيلات
echo "🗄️  تطبيق الترحيلات..."
python manage.py migrate --settings=config.settings.production

# جمع الملفات الثابتة
echo "📁 جمع الملفات الثابتة..."
python manage.py collectstatic --noinput --settings=config.settings.production

# إعادة تشغيل الخدمة
echo "🔄 إعادة تشغيل الخدمة..."
sudo systemctl restart "$SERVICE_NAME"

echo ""
echo "✅ النشر اكتمل بنجاح!"
echo "=============================="
