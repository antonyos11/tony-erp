#!/bin/bash
# ===============================================================================
# سكريبت إعداد السيرفر وتثبيت Tony ERP
# قم بتشغيل هذا السكريبت على الـ VPS بعد الاتصال عبر SSH
# ===============================================================================

set -e  # إيقاف عند أي خطأ

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║       🚀 Tony ERP - سكريبت الإعداد التلقائي للسيرفر              ║"
echo "╚══════════════════════════════════════════════════════════════════╝"

# ألوان للتنسيق
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# متغيرات
PROJECT_DIR="/var/www/tony_erp"
VENV_DIR="$PROJECT_DIR/venv"
DB_NAME="tony_erp"
DB_USER="tony"
DOMAIN=""  # سيتم طلبها من المستخدم

# دالة الطباعة
print_step() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} ${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} ${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} ${RED}✗${NC} $1"
}

# ===============================================================================
# الخطوة 1: جمع المعلومات
# ===============================================================================
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}                    الخطوة 1: جمع المعلومات                     ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

read -p "أدخل الدومين (أو اتركه فارغاً لاستخدام IP): " DOMAIN
read -p "أدخل كلمة مرور قاعدة البيانات: " -s DB_PASSWORD
echo ""
read -p "أدخل البريد الإلكتروني (لشهادة SSL): " EMAIL

# ===============================================================================
# الخطوة 2: تحديث النظام
# ===============================================================================
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}                   الخطوة 2: تحديث النظام                       ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

print_step "تحديث قوائم الحزم..."
apt update -qq

print_step "ترقية الحزم المثبتة..."
apt upgrade -y -qq

# ===============================================================================
# الخطوة 3: تثبيت الحزم المطلوبة
# ===============================================================================
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}                  الخطوة 3: تثبيت الحزم                         ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

print_step "تثبيت Python و أدوات التطوير..."
apt install -y -qq python3 python3-pip python3-venv python3-dev build-essential

print_step "تثبيت PostgreSQL..."
apt install -y -qq postgresql postgresql-contrib libpq-dev

print_step "تثبيت Nginx..."
apt install -y -qq nginx

print_step "تثبيت Redis..."
apt install -y -qq redis-server

print_step "تثبيت أدوات إضافية..."
apt install -y -qq git curl wget htop supervisor certbot python3-certbot-nginx \
    libffi-dev libssl-dev libjpeg-dev zlib1g-dev libfreetype6-dev

print_step "تفعيل الخدمات..."
systemctl enable postgresql nginx redis-server
systemctl start postgresql nginx redis-server

# ===============================================================================
# الخطوة 4: إعداد قاعدة البيانات
# ===============================================================================
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}                الخطوة 4: إعداد قاعدة البيانات                  ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

print_step "إنشاء قاعدة البيانات والمستخدم..."
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || print_warning "قاعدة البيانات موجودة مسبقاً"
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || print_warning "المستخدم موجود مسبقاً"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET timezone TO 'Africa/Cairo';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# ===============================================================================
# الخطوة 5: إعداد مجلد المشروع
# ===============================================================================
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}                 الخطوة 5: إعداد مجلد المشروع                   ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

print_step "إنشاء مجلد المشروع..."
mkdir -p $PROJECT_DIR
mkdir -p $PROJECT_DIR/media
mkdir -p $PROJECT_DIR/logs
mkdir -p $PROJECT_DIR/staticfiles

print_step "إعداد الصلاحيات..."
chown -R www-data:www-data $PROJECT_DIR

echo ""
print_warning "الآن قم برفع ملفات المشروع إلى: $PROJECT_DIR"
print_warning "يمكنك استخدام: scp -r app/* root@YOUR_IP:$PROJECT_DIR/"
read -p "اضغط Enter بعد رفع الملفات للمتابعة..."

# ===============================================================================
# الخطوة 6: إعداد البيئة الافتراضية
# ===============================================================================
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}               الخطوة 6: إعداد البيئة الافتراضية                ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

cd $PROJECT_DIR

print_step "إنشاء البيئة الافتراضية..."
python3 -m venv venv

print_step "تفعيل البيئة..."
source venv/bin/activate

print_step "تحديث pip..."
pip install --upgrade pip setuptools wheel -q

print_step "تثبيت المتطلبات..."
pip install -r requirements.txt -q

print_step "تثبيت Gunicorn..."
pip install gunicorn psycopg2-binary -q

# ===============================================================================
# الخطوة 7: إنشاء ملف البيئة
# ===============================================================================
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}                 الخطوة 7: إنشاء ملف البيئة                     ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

# توليد مفتاح سري
SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
JWT_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")

# تحديد ALLOWED_HOSTS
if [ -z "$DOMAIN" ]; then
    SERVER_IP=$(curl -s ifconfig.me)
    ALLOWED_HOSTS="localhost,127.0.0.1,$SERVER_IP"
else
    ALLOWED_HOSTS="$DOMAIN,www.$DOMAIN,localhost,127.0.0.1"
fi

print_step "إنشاء ملف .env..."
cat > $PROJECT_DIR/.env << EOF
# ===============================================================================
# Tony ERP - إعدادات الإنتاج
# تم إنشاؤه تلقائياً: $(date)
# ===============================================================================

# Django الأساسية
DJANGO_SECRET_KEY=$SECRET_KEY
DEBUG=0
ENVIRONMENT=production

# المضيفات المسموحة
ALLOWED_HOSTS=$ALLOWED_HOSTS

# قاعدة البيانات PostgreSQL
DB_ENGINE=postgresql
POSTGRES_DB=$DB_NAME
POSTGRES_USER=$DB_USER
POSTGRES_PASSWORD=$DB_PASSWORD
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME

# Redis
REDIS_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# الأمان
SECURE_SSL_REDIRECT=0
SECURE_HSTS_SECONDS=0

# JWT
JWT_SECRET_KEY=$JWT_KEY
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# اللغة والمنطقة
LANGUAGE_CODE=ar
TIME_ZONE=Africa/Cairo

# النسخ الاحتياطي
AUTO_BACKUP_ENABLED=1
BACKUP_SCHEDULE_HOUR=3
BACKUP_RETENTION_DAYS=30

# الملفات
MAX_UPLOAD_SIZE_MB=25
EOF

# ===============================================================================
# الخطوة 8: تهيئة Django
# ===============================================================================
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}                   الخطوة 8: تهيئة Django                       ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

source venv/bin/activate

print_step "تطبيق الهجرات..."
python manage.py migrate --noinput

print_step "تجميع الملفات الثابتة..."
python manage.py collectstatic --noinput

print_step "إنشاء مستخدم admin..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell
print_warning "تم إنشاء مستخدم admin بكلمة مرور: admin123 - غيّرها فوراً!"

# ===============================================================================
# الخطوة 9: إعداد Gunicorn
# ===============================================================================
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}                  الخطوة 9: إعداد Gunicorn                      ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

print_step "إنشاء مجلد السجلات..."
mkdir -p /var/log/gunicorn
chown www-data:www-data /var/log/gunicorn

print_step "إنشاء ملف خدمة Gunicorn..."
cat > /etc/systemd/system/gunicorn.service << EOF
[Unit]
Description=Gunicorn daemon for Tony ERP
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/gunicorn \\
    --workers 3 \\
    --bind 127.0.0.1:8000 \\
    --timeout 300 \\
    --access-logfile /var/log/gunicorn/access.log \\
    --error-logfile /var/log/gunicorn/error.log \\
    accountant_pro.wsgi:application

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

print_step "تفعيل خدمة Gunicorn..."
systemctl daemon-reload
systemctl enable gunicorn
systemctl start gunicorn

# ===============================================================================
# الخطوة 10: إعداد Nginx
# ===============================================================================
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}                   الخطوة 10: إعداد Nginx                       ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

# تحديد server_name
if [ -z "$DOMAIN" ]; then
    SERVER_NAME=$(curl -s ifconfig.me)
else
    SERVER_NAME="$DOMAIN www.$DOMAIN"
fi

print_step "إنشاء ملف إعداد Nginx..."
cat > /etc/nginx/sites-available/tony_erp << EOF
server {
    listen 80;
    server_name $SERVER_NAME;

    access_log /var/log/nginx/tony_erp_access.log;
    error_log /var/log/nginx/tony_erp_error.log;

    client_max_body_size 100M;

    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }
}
EOF

print_step "تفعيل الموقع..."
ln -sf /etc/nginx/sites-available/tony_erp /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

print_step "اختبار إعداد Nginx..."
nginx -t

print_step "إعادة تشغيل Nginx..."
systemctl restart nginx

# ===============================================================================
# الخطوة 11: إعداد الصلاحيات النهائية
# ===============================================================================
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}              الخطوة 11: إعداد الصلاحيات النهائية               ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

print_step "تحديث صلاحيات الملفات..."
chown -R www-data:www-data $PROJECT_DIR
chmod -R 755 $PROJECT_DIR
chmod -R 775 $PROJECT_DIR/media
chmod -R 775 $PROJECT_DIR/logs

# ===============================================================================
# الخطوة 12: إعداد الجدار الناري
# ===============================================================================
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}               الخطوة 12: إعداد الجدار الناري                  ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

print_step "تفعيل UFW..."
ufw allow 22
ufw allow 80
ufw allow 443
echo "y" | ufw enable

# ===============================================================================
# النتيجة النهائية
# ===============================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ تم الإعداد بنجاح!                          ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

if [ -z "$DOMAIN" ]; then
    echo -e "${GREEN}🌐 الموقع متاح الآن على: http://$(curl -s ifconfig.me)${NC}"
else
    echo -e "${GREEN}🌐 الموقع متاح الآن على: http://$DOMAIN${NC}"
fi

echo ""
echo "📋 معلومات تسجيل الدخول:"
echo "   • المستخدم: admin"
echo "   • كلمة المرور: admin123"
echo "   ⚠️  غيّر كلمة المرور فوراً!"
echo ""
echo "🔧 أوامر مفيدة:"
echo "   • حالة الخدمات: systemctl status gunicorn nginx"
echo "   • سجلات Gunicorn: tail -f /var/log/gunicorn/error.log"
echo "   • سجلات Nginx: tail -f /var/log/nginx/tony_erp_error.log"
echo "   • إعادة التشغيل: systemctl restart gunicorn nginx"
echo ""

if [ -n "$DOMAIN" ]; then
    echo "🔐 لتفعيل SSL، شغّل:"
    echo "   sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
