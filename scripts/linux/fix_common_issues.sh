#!/bin/bash
# Tony ERP - إصلاح المشاكل الشائعة

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
}

print_info() {
    echo -e "${BLUE}$1${NC}"
}

echo
echo "================================================================================"
echo "Tony ERP - إصلاح المشاكل الشائعة"
echo "================================================================================"
echo

echo "هذا المعالج سيحاول إصلاح المشاكل الشائعة:"
echo "  - حذف ملفات Python المؤقتة (.pyc)"
echo "  - إعادة تطبيق المهاجرات"
echo "  - إعادة جمع الملفات الثابتة"
echo "  - إعادة بناء حاويات Docker (إن أمكن)"
echo "  - فحص شامل للنظام"
echo

read -p "هل تريد المتابعة؟ (y/n): " continue
if [ "$continue" != "y" ] && [ "$continue" != "Y" ]; then
    echo "تم الإلغاء"
    exit 0
fi

echo

# حذف ملفات Python المؤقتة
print_info "حذف ملفات Python المؤقتة..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
print_message "تم حذف ملفات Python المؤقتة"

# تحديد أمر Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

# التحقق من وجود البيئة الافتراضية
if [ -d ".venv" ]; then
    print_info "تفعيل البيئة الافتراضية..."
    source .venv/bin/activate
    
    print_info "إعادة تطبيق المهاجرات..."
    # makemigrations should only run in development, not in fix scripts
    $PYTHON_CMD manage.py migrate --run-syncdb
    print_message "تم إعادة تطبيق المهاجرات"
    
    print_info "إعادة جمع الملفات الثابتة..."
    $PYTHON_CMD manage.py collectstatic --noinput --clear
    print_message "تم إعادة جمع الملفات الثابتة"
    
    print_info "فحص شامل للنظام..."
    $PYTHON_CMD manage.py system_self_check --fix
    print_message "تم فحص النظام"
else
    print_warning "لم يتم العثور على البيئة الافتراضية"
fi

# التحقق من وجود Docker
if command -v docker &> /dev/null; then
    echo
    print_info "إعادة بناء حاويات Docker..."
    docker compose down >/dev/null 2>&1 || true
    docker compose build --no-cache
    docker system prune -f >/dev/null 2>&1 || true
    print_message "تم إعادة بناء حاويات Docker"
else
    print_warning "Docker غير متاح، تم تخطي إعادة البناء"
fi

# إصلاح صلاحيات المجلدات
echo
print_info "إصلاح صلاحيات المجلدات..."
mkdir -p logs media backups staticfiles
chmod 755 logs media backups staticfiles 2>/dev/null || true
print_message "تم إصلاح صلاحيات المجلدات"

echo
echo "================================================================================"
echo "تم إصلاح جميع المشاكل الشائعة!"
echo "================================================================================"
echo
echo "الخطوات التالية:"
echo "  1. جرب تشغيل النظام مرة أخرى"
echo "  2. إذا استمرت المشاكل، راجع ملفات السجلات في مجلد logs/"
echo "  3. للمساعدة المتقدمة، شغّل: $PYTHON_CMD manage.py system_self_check"
echo