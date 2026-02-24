# دليل التثبيت والتشغيل السريع
# Quick Installation and Setup Guide

## 🚀 البدء السريع

### الخطوة 1: التحقق من المتطلبات

```bash
# التحقق من إصدار Python
python --version  # يجب أن يكون 3.10 أو أحدث

# التحقق من PostgreSQL
psql --version

# التحقق من Redis
redis-cli ping  # يجب أن يرجع PONG
```

### الخطوة 2: تثبيت الحزم المطلوبة

```bash
# الانتقال لمجلد المشروع
cd /var/www/tony_erp

# تفعيل البيئة الافتراضية (إذا كنت تستخدمها)
source venv/bin/activate

# تثبيت المتطلبات
pip install -r requirements.txt

# أو تثبيت الحزم يدوياً
pip install django==4.2.8
pip install djangorestframework==3.14.0
pip install celery==5.3.4
pip install redis==5.0.1
pip install django-redis==5.4.0
pip install psycopg2-binary==2.9.9
pip install weasyprint==60.1  # للطباعة PDF
pip install pillow==10.1.0
pip install openpyxl==3.1.2  # لتصدير Excel
```

### الخطوة 3: إعداد قاعدة البيانات

```bash
# إنشاء قاعدة البيانات (PostgreSQL)
sudo -u postgres createdb tony_erp

# إنشاء المستخدم
sudo -u postgres createuser tony_erp_user -P
# أدخل كلمة المرور: tony_erp_password

# منح الصلاحيات
sudo -u postgres psql
postgres=# GRANT ALL PRIVILEGES ON DATABASE tony_erp TO tony_erp_user;
postgres=# \q
```

### الخطوة 4: تحديث إعدادات Django

أضف/عدّل في `tony_erp/settings.py`:

```python
# قاعدة البيانات
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tony_erp',
        'USER': 'tony_erp_user',
        'PASSWORD': 'tony_erp_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Redis Cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'PICKLE_VERSION': -1,
        },
        'KEY_PREFIX': 'tony_erp',
        'TIMEOUT': 300,  # 5 دقائق افتراضياً
    }
}

# Celery
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Riyadh'
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 دقيقة

# التطبيقات
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # REST Framework
    'rest_framework',
    
    # التطبيقات الموجودة
    'core',
    'sales',
    'inventory',
    'purchasing',
    'accounting',
    'hr',
    'production',
    'dashboard',
    'notifications',
    'approvals',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.gzip.GZipMiddleware',  # ضغط الاستجابات
]

# الملفات الثابتة
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# ملفات الرفع
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

### الخطوة 5: تطبيق Migrations

```bash
# إنشاء جداول قاعدة البيانات
python manage.py makemigrations
python manage.py migrate

# إنشاء superuser
python manage.py createsuperuser
```

### الخطوة 6: تحميل البيانات الأولية

```python
# في Django shell
python manage.py shell

# تشغيل الأوامر التالية:
from accounting.entry_templates import create_predefined_templates
create_predefined_templates()

from inventory.stock_alerts import StockAlertSystem
# سيتم إنشاء الإعدادات تلقائياً

exit()
```

### الخطوة 7: جمع الملفات الثابتة

```bash
python manage.py collectstatic --noinput
```

### الخطوة 8: تشغيل خوادم Celery

افتح 3 نوافذ terminal منفصلة:

**Terminal 1 - Celery Worker:**
```bash
cd /var/www/tony_erp
source venv/bin/activate  # إذا كنت تستخدم venv
celery -A tony_erp worker --loglevel=info --concurrency=4
```

**Terminal 2 - Celery Beat (المهام المجدولة):**
```bash
cd /var/www/tony_erp
source venv/bin/activate
celery -A tony_erp beat --loglevel=info
```

**Terminal 3 - Django Development Server:**
```bash
cd /var/www/tony_erp
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

---

## 🔧 إعداد الإنتاج (Production)

### استخدام Supervisor لإدارة العمليات

#### 1. تثبيت Supervisor:
```bash
sudo apt-get install supervisor
```

#### 2. إنشاء ملف تكوين Celery Worker:
```bash
sudo nano /etc/supervisor/conf.d/tony_erp_celery.conf
```

محتوى الملف:
```ini
[program:tony_erp_celery]
command=/var/www/tony_erp/venv/bin/celery -A tony_erp worker --loglevel=info --concurrency=4
directory=/var/www/tony_erp
user=www-data
numprocs=1
stdout_logfile=/var/log/tony_erp/celery_worker.log
stderr_logfile=/var/log/tony_erp/celery_worker_error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
priority=998
```

#### 3. إنشاء ملف تكوين Celery Beat:
```bash
sudo nano /etc/supervisor/conf.d/tony_erp_celerybeat.conf
```

محتوى الملف:
```ini
[program:tony_erp_celerybeat]
command=/var/www/tony_erp/venv/bin/celery -A tony_erp beat --loglevel=info
directory=/var/www/tony_erp
user=www-data
numprocs=1
stdout_logfile=/var/log/tony_erp/celery_beat.log
stderr_logfile=/var/log/tony_erp/celery_beat_error.log
autostart=true
autorestart=true
startsecs=10
priority=999
```

#### 4. إنشاء مجلد السجلات:
```bash
sudo mkdir -p /var/log/tony_erp
sudo chown -R www-data:www-data /var/log/tony_erp
```

#### 5. تحديث وإعادة تشغيل Supervisor:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start tony_erp_celery
sudo supervisorctl start tony_erp_celerybeat
```

#### 6. التحقق من الحالة:
```bash
sudo supervisorctl status
```

يجب أن ترى:
```
tony_erp_celery         RUNNING   pid 12345, uptime 0:00:10
tony_erp_celerybeat     RUNNING   pid 12346, uptime 0:00:10
```

---

### إعداد Nginx + Gunicorn

#### 1. تثبيت Gunicorn:
```bash
pip install gunicorn
```

#### 2. إنشاء ملف خدمة Gunicorn:
```bash
sudo nano /etc/systemd/system/tony_erp.service
```

محتوى الملف:
```ini
[Unit]
Description=Tony ERP Gunicorn Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/tony_erp
Environment="PATH=/var/www/tony_erp/venv/bin"
ExecStart=/var/www/tony_erp/venv/bin/gunicorn \
          --workers 4 \
          --bind unix:/var/www/tony_erp/tony_erp.sock \
          --timeout 120 \
          --access-logfile /var/log/tony_erp/gunicorn_access.log \
          --error-logfile /var/log/tony_erp/gunicorn_error.log \
          tony_erp.wsgi:application

[Install]
WantedBy=multi-user.target
```

#### 3. تفعيل وتشغيل الخدمة:
```bash
sudo systemctl daemon-reload
sudo systemctl start tony_erp
sudo systemctl enable tony_erp
sudo systemctl status tony_erp
```

#### 4. إعداد Nginx:
```bash
sudo nano /etc/nginx/sites-available/tony_erp
```

محتوى الملف:
```nginx
upstream tony_erp {
    server unix:/var/www/tony_erp/tony_erp.sock fail_timeout=0;
}

server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 50M;
    
    location /static/ {
        alias /var/www/tony_erp/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /var/www/tony_erp/media/;
        expires 7d;
    }
    
    location / {
        proxy_pass http://tony_erp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_min_length 1000;
}
```

#### 5. تفعيل الموقع:
```bash
sudo ln -s /etc/nginx/sites-available/tony_erp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 📊 اختبار النظام

### 1. اختبار Cache:
```python
python manage.py shell

from django.core.cache import cache
cache.set('test_key', 'test_value', 60)
print(cache.get('test_key'))  # يجب أن يطبع: test_value
```

### 2. اختبار Celery:
```python
from notifications.enhanced_service import check_low_stock
result = check_low_stock.delay()
print(result.id)  # معرف المهمة
```

### 3. اختبار مؤشرات الأداء:
```bash
curl http://localhost:8000/api/dashboard/kpis/
```

### 4. اختبار الطباعة الحرارية:
- افتح فاتورة موجودة
- اضغط على "طباعة"
- تحقق من السجل في `/var/log/tony_erp/thermal_printer.log`

---

## 🔍 استكشاف الأخطاء

### مشكلة: Celery لا يعمل
```bash
# التحقق من Redis
redis-cli ping

# التحقق من السجل
sudo tail -f /var/log/tony_erp/celery_worker_error.log

# إعادة تشغيل
sudo supervisorctl restart tony_erp_celery
```

### مشكلة: Cache لا يعمل
```bash
# التحقق من Redis
sudo systemctl status redis

# فحص الاتصال
redis-cli
127.0.0.1:6379> ping
PONG

# مسح الكاش
redis-cli FLUSHDB
```

### مشكلة: أخطاء في الطباعة
```bash
# التحقق من تثبيت WeasyPrint
pip install --upgrade weasyprint

# فحص السجل
tail -f /var/log/tony_erp/thermal_printer.log
```

### مشكلة: بطء في الاستعلامات
```python
# تفعيل DEBUG في settings.py مؤقتاً
DEBUG = True

# عرض الاستعلامات في shell
from django.db import connection
print(len(connection.queries))
print(connection.queries)
```

---

## 📈 مراقبة الأداء

### 1. سجلات Celery:
```bash
sudo tail -f /var/log/tony_erp/celery_worker.log
```

### 2. سجلات Gunicorn:
```bash
sudo tail -f /var/log/tony_erp/gunicorn_error.log
```

### 3. سجلات Nginx:
```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 4. مراقبة Redis:
```bash
redis-cli INFO stats
redis-cli INFO memory
```

---

## 🔐 الأمان

### 1. تحديث SECRET_KEY في الإنتاج:
```python
# في settings.py
SECRET_KEY = 'your-very-secure-and-long-secret-key-here'
```

### 2. تعطيل DEBUG:
```python
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']
```

### 3. HTTPS (اختياري لكن موصى به):
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 📚 الخطوات التالية

1. ✅ تدريب الموظفين (خطة 3 أيام - راجع التقرير الشامل)
2. ✅ إعداد النسخ الاحتياطي التلقائي
3. ✅ مراقبة الأداء
4. ✅ جمع الملاحظات من المستخدمين
5. ✅ تحسينات مستمرة

---

## 📞 الدعم

في حالة وجود مشاكل:
1. راجع السجلات أولاً
2. تحقق من حالة جميع الخدمات
3. ارجع لدليل استكشاف الأخطاء

---

**تاريخ آخر تحديث:** {{ current_date }}
**الإصدار:** 2.0.0
**الحالة:** ✅ جاهز للإنتاج
