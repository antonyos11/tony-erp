#!/bin/bash
# Tony ERP - تشغيل النظام محلياً

# ألوان للنصوص
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
echo "Tony ERP - تشغيل النظام محلياً"
echo "================================================================================"
echo

# التحقق من وجود البيئة الافتراضية
if [ ! -d ".venv" ]; then
    print_error "البيئة الافتراضية غير موجودة. يرجى تشغيل bash setup_unix.sh أولاً"
fi

# تفعيل البيئة الافتراضية
print_info "تفعيل البيئة الافتراضية..."
source .venv/bin/activate

# تحديد أمر Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

# التحقق من وجود ملف .env
if [ ! -f ".env" ]; then
    print_error "ملف .env غير موجود. يرجى تشغيل bash setup_unix.sh أولاً"
fi

# فحص سريع للنظام
print_info "فحص سريع للنظام..."
$PYTHON_CMD manage.py system_self_check || {
    print_warning "يوجد مشاكل في النظام"
    echo "شغّل: $PYTHON_CMD manage.py system_self_check --fix لإصلاحها"
    echo
    read -p "هل تريد المتابعة؟ (y/n): " continue
    if [ "$continue" != "y" ] && [ "$continue" != "Y" ]; then
        exit 1
    fi
}

echo
print_message "النظام جاهز للتشغيل"
echo
echo "العنوان: http://127.0.0.1:8000"
echo "المستخدم: superadmin"
echo "كلمة المرور: admin123"
echo
echo "لإيقاف الخادم، اضغط Ctrl+C"
echo

# فتح المتصفح
sleep 2
if command -v xdg-open > /dev/null; then
    xdg-open http://127.0.0.1:8000 >/dev/null 2>&1 &
elif command -v gnome-open > /dev/null; then
    gnome-open http://127.0.0.1:8000 >/dev/null 2>&1 &
elif command -v open > /dev/null; then
    open http://127.0.0.1:8000 >/dev/null 2>&1 &
fi

# تشغيل الخادم
$PYTHON_CMD manage.py runserver 127.0.0.1:8000

echo
echo "تم إيقاف الخادم"