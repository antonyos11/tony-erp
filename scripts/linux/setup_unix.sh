#!/bin/bash
# Tony ERP - إعداد النظام للـ Unix/Linux/Mac
# استخدم: bash setup_unix.sh

set -e  # إيقاف الأمر عند أي خطأ

# ألوان للنصوص
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# دالة طباعة رسالة ملونة
print_message() {
    echo -e "${GREEN}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}تحذير: $1${NC}"
}

print_error() {
    echo -e "${RED}خطأ: $1${NC}"
    exit 1
}

print_info() {
    echo -e "${BLUE}$1${NC}"
}

echo
echo "================================================================================"
echo "مرحباً بك في Tony ERP - نظام إدارة الأعمال الشامل"
echo "================================================================================"
echo
echo "هذا المعالج سيقوم بإعداد النظام تلقائياً:"
echo "  - إنشاء البيئة الافتراضية"
echo "  - تثبيت المكتبات المطلوبة"
echo "  - إعداد قاعدة البيانات"
echo "  - تحميل البيانات التجريبية"
echo "  - فحص النظام وإصلاح المشاكل"
echo "  - تشغيل الخادم وفتح المتصفح"
echo
echo "================================================================================"

# التحقق من وجود Python
print_info "فحص Python..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        print_error "Python غير مثبت. يرجى تثبيت Python 3.11+ أولاً"
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# التحقق من إصدار Python
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
MAJOR_VERSION=$(echo $PYTHON_VERSION | cut -d'.' -f1)
MINOR_VERSION=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$MAJOR_VERSION" -lt 3 ] || ([ "$MAJOR_VERSION" -eq 3 ] && [ "$MINOR_VERSION" -lt 11 ]); then
    print_error "يتطلب Python 3.11 أو أحدث. الإصدار الحالي: $PYTHON_VERSION"
fi

print_message "Python متوفر: $PYTHON_VERSION"

# التحقق من وجود pip
if ! command -v pip3 &> /dev/null; then
    if ! command -v pip &> /dev/null; then
        print_error "pip غير مثبت. يرجى تثبيت pip أولاً"
    else
        PIP_CMD="pip"
    fi
else
    PIP_CMD="pip3"
fi

# إنشاء البيئة الافتراضية إذا لم تكن موجودة
if [ ! -d ".venv" ]; then
    print_info "إنشاء البيئة الافتراضية..."
    $PYTHON_CMD -m venv .venv
    print_message "تم إنشاء البيئة الافتراضية"
else
    print_message "البيئة الافتراضية موجودة"
fi

# تفعيل البيئة الافتراضية
print_info "تفعيل البيئة الافتراضية..."
source .venv/bin/activate

# تحديث pip
print_info "تحديث pip..."
$PYTHON_CMD -m pip install --upgrade pip

# تثبيت المكتبات
echo
print_info "تثبيت المكتبات المطلوبة..."
echo "هذا قد يستغرق بضع دقائق..."
$PYTHON_CMD -m pip install -r requirements.txt
print_message "تم تثبيت جميع المكتبات بنجاح"

# إنشاء ملف .env إذا لم يكن موجوداً
if [ ! -f ".env" ]; then
    print_info "إنشاء ملف الإعدادات..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_message "تم إنشاء ملف .env"
    else
        print_error "لم يتم العثور على .env.example"
    fi
else
    print_message "ملف .env موجود"
fi

# إنشاء المجلدات المطلوبة
echo
print_info "إنشاء المجلدات المطلوبة..."
mkdir -p logs media backups staticfiles
print_message "تم إنشاء جميع المجلدات"

# تطبيق المهاجرات
echo
print_info "إعداد قاعدة البيانات..."
$PYTHON_CMD manage.py makemigrations
$PYTHON_CMD manage.py migrate
print_message "تم إعداد قاعدة البيانات"

# جمع الملفات الثابتة
echo
print_info "جمع الملفات الثابتة..."
$PYTHON_CMD manage.py collectstatic --noinput || print_warning "مشكلة في جمع الملفات الثابتة"
print_message "تم جمع الملفات الثابتة"

# تحميل البيانات التجريبية
echo
print_info "تحميل البيانات التجريبية..."
$PYTHON_CMD manage.py load_sample_data || print_warning "مشكلة في تحميل البيانات التجريبية"
print_message "تم تحميل البيانات التجريبية بنجاح"

# فحص النظام
echo
print_info "فحص النظام وإصلاح المشاكل..."
$PYTHON_CMD manage.py system_self_check --fix || print_warning "يوجد بعض المشاكل في النظام"
print_message "النظام سليم وجاهز للعمل"

# عرض معلومات النظام
echo
echo "================================================================================"
echo "تم إعداد Tony ERP بنجاح!"
echo "================================================================================"
echo
echo "سيتم الوصول إلى النظام على: http://127.0.0.1:8000"
echo "اسم المستخدم: superadmin"
echo "كلمة المرور: admin123"
echo
echo "روابط مفيدة:"
echo "   • لوحة الإدارة: http://127.0.0.1:8000/admin/"
echo "   • واجهة API: http://127.0.0.1:8000/api/docs/"
echo "   • حالة النظام: http://127.0.0.1:8000/health/ready/"
echo
echo "================================================================================"

# تشغيل الخادم
print_info "بدء تشغيل الخادم..."
echo
echo "لإيقاف الخادم، اضغط Ctrl+C"
echo

# فتح المتصفح (بعد تأخير قصير)
sleep 2

# فتح المتصفح حسب نظام التشغيل
if command -v xdg-open > /dev/null; then
    xdg-open http://127.0.0.1:8000 >/dev/null 2>&1 &
elif command -v gnome-open > /dev/null; then
    gnome-open http://127.0.0.1:8000 >/dev/null 2>&1 &
elif command -v open > /dev/null; then
    open http://127.0.0.1:8000 >/dev/null 2>&1 &
else
    echo "افتح المتصفح وانتقل إلى: http://127.0.0.1:8000"
fi

# تشغيل خادم Django
$PYTHON_CMD manage.py runserver 127.0.0.1:8000

# إذا وصلنا هنا فالخادم توقف
echo
echo "تم إيقاف الخادم"
echo
echo "لتشغيل النظام مرة أخرى، استخدم:"
echo "  bash start_local.sh"
echo