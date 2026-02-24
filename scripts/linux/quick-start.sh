#!/bin/bash
# Tony ERP - Quick Start Script
# سكريبت البدء السريع للمطورين الجدد

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Tony ERP - البدء السريع"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# التحقق من Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 غير مثبت"
    exit 1
fi

echo "✅ Python: $(python3 --version)"

# التحقق من pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip غير مثبت"
    exit 1
fi

# إنشاء بيئة افتراضية
if [ ! -d "venv" ]; then
    echo "📦 إنشاء بيئة افتراضية..."
    python3 -m venv venv
fi

# تفعيل البيئة الافتراضية
echo "🔧 تفعيل البيئة الافتراضية..."
source venv/bin/activate

# تثبيت المتطلبات
echo "📥 تثبيت المتطلبات..."
pip install --upgrade pip
pip install -r requirements.txt

# إنشاء ملف .env إذا لم يكن موجوداً
if [ ! -f ".env" ]; then
    echo "⚙️  إنشاء ملف .env..."
    cp .env.example .env 2>/dev/null || cat > .env << 'EOF'
DEBUG=True
SECRET_KEY=your-secret-key-here-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
LANGUAGE_CODE=ar
TIME_ZONE=Asia/Riyadh
EOF
    echo "✅ تم إنشاء .env - قم بتعديله حسب الحاجة"
fi

# إنشاء المجلدات المطلوبة
echo "📁 إنشاء المجلدات..."
mkdir -p logs backups media staticfiles

# تطبيق المهاجرات
echo "🔄 تطبيق مهاجرات قاعدة البيانات..."
python manage.py migrate

# جمع الملفات الثابتة
echo "📦 جمع الملفات الثابتة..."
python manage.py collectstatic --noinput

# إنشاء مستخدم admin
echo ""
echo "👤 إنشاء مستخدم admin..."
echo "   (اسم المستخدم الافتراضي: admin)"
python manage.py shell << 'PYTHON_SCRIPT'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@tony-erp.local', 'admin123')
    print('✅ تم إنشاء المستخدم: admin / admin123')
else:
    print('ℹ️  المستخدم admin موجود بالفعل')
PYTHON_SCRIPT

# بيانات تجريبية (اختياري)
echo ""
read -p "هل تريد إضافة بيانات تجريبية؟ (y/n): " add_data
if [ "$add_data" = "y" ] || [ "$add_data" = "Y" ]; then
    echo "🌱 إضافة بيانات تجريبية..."
    python create_sample_data.py 2>/dev/null || echo "⚠️  سكريبت البيانات غير متوفر"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ الإعداد مكتمل!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 لتشغيل الخادم:"
echo "   make run"
echo "   أو: python manage.py runserver"
echo ""
echo "🔗 الروابط:"
echo "   Dashboard: http://localhost:8000"
echo "   Admin: http://localhost:8000/admin/"
echo "   API Docs: http://localhost:8000/api/docs/"
echo ""
echo "👤 تسجيل الدخول:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📚 للمزيد من الأوامر: make help"
echo ""
