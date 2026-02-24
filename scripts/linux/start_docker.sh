#!/bin/bash
# Tony ERP - تشغيل النظام بـ Docker

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
echo "Tony ERP - تشغيل النظام بـ Docker"
echo "================================================================================"
echo

# التحقق من وجود Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker غير مثبت أو غير متاح. يرجى تثبيت Docker أولاً"
fi

# التحقق من وجود Docker Compose
if ! docker compose version &> /dev/null; then
    print_error "Docker Compose غير متاح. يرجى تثبيت إصدار حديث من Docker"
fi

print_message "Docker متوفر:"
docker --version
docker compose version

# التحقق من وجود ملف .env
if [ ! -f ".env" ]; then
    print_info "إنشاء ملف الإعدادات..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
    print_message "تم إنشاء ملف .env من .env.example"
    else
        print_error "لم يتم العثور على .env.example"
    fi
fi

# إيقاف الخدمات المشتغلة (إن وجدت)
print_info "إيقاف الخدمات السابقة..."
docker compose down >/dev/null 2>&1

# بناء وتشغيل الخدمات
echo
print_info "بناء وتشغيل خدمات Docker..."
echo "هذا قد يستغرق عدة دقائق في المرة الأولى..."
echo

docker compose up --build -d || print_error "خطأ في تشغيل Docker Compose"

# انتظار حتى يصبح النظام جاهزاً
print_info "انتظار بدء الخدمات..."
sleep 30

# فحص حالة الخدمات
print_info "فحص حالة الخدمات..."
docker compose ps

# انتظار حتى يصبح النظام متاحاً
print_info "فحص توفر النظام..."
retries=0
max_retries=12

while [ $retries -lt $max_retries ]; do
    if curl -s http://127.0.0.1:8000/health/ready/ >/dev/null 2>&1; then
        print_message "النظام متاح ويعمل"
        break
    fi
    
    retries=$((retries + 1))
    echo "انتظار... ($retries/$max_retries)"
    sleep 5
done

if [ $retries -eq $max_retries ]; then
    print_warning "النظام قد لا يكون جاهزاً بعد"
    echo "تحقق من السجلات: docker compose logs web"
fi

echo
echo "================================================================================"
echo "تم تشغيل Tony ERP بنجاح باستخدام Docker!"
echo "================================================================================"
echo
echo "النظام متاح على: http://127.0.0.1:8000"
echo "اسم المستخدم: superadmin"
echo "كلمة المرور: admin123"
echo
echo "روابط مفيدة:"
echo "   - لوحة الإدارة: http://127.0.0.1:8000/admin/"
echo "   - واجهة API: http://127.0.0.1:8000/api/docs/"
echo "   - مراقب Flower: http://127.0.0.1:5555"
echo "   - حالة النظام: http://127.0.0.1:8000/health/ready/"
echo
echo "أوامر مفيدة:"
echo "   - عرض السجلات: docker compose logs -f web"
echo "   - إيقاف النظام: docker compose down"
echo "   - إعادة تشغيل: docker compose restart"
echo "   - فحص الحاويات: docker compose ps"
echo
echo "================================================================================"

# فتح المتصفح
print_info "فتح المتصفح..."
sleep 3

if command -v xdg-open > /dev/null; then
    xdg-open http://127.0.0.1:8000 >/dev/null 2>&1 &
elif command -v gnome-open > /dev/null; then
    gnome-open http://127.0.0.1:8000 >/dev/null 2>&1 &
elif command -v open > /dev/null; then
    open http://127.0.0.1:8000 >/dev/null 2>&1 &
fi

echo
echo "النظام يعمل في الخلفية. لإيقافه، شغّل: docker compose down"
echo "لعرض السجلات المباشرة، شغّل: docker compose logs -f web"
echo