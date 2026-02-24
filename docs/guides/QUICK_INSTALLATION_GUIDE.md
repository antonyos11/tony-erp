# دليل التثبيت السريع - Tony ERP
## Quick Installation Guide

---

## 1. تفعيل التحسينات الأمنية 🔒

### الخطوة 1: تحديث ملف الإعدادات
افتح `accountant_pro/settings.py` وأضف:

```python
# في بداية الملف
import os

# تحديث MIDDLEWARE (أضف بعد SecurityMiddleware)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'security.security_middleware.SecurityHeadersMiddleware',
    'security.security_middleware.LoginRateLimitMiddleware',
    'security.security_middleware.SessionSecurityMiddleware',
    'security.security_middleware.AuditLogMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # ... باقي middleware
]

# محققات كلمات المرور
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'security.password_validators.ComplexPasswordValidator'},
    {'NAME': 'security.password_validators.NoCommonPasswordValidator'},
    {'NAME': 'security.password_validators.NoUserAttributePasswordValidator'},
    {'NAME': 'security.password_validators.PasswordHistoryValidator'},
]

# إعدادات الجلسات
SESSION_COOKIE_AGE = 7200  # ساعتين
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = not DEBUG  # True في الإنتاج
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# إعدادات CSRF
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
```

---

## 2. تفعيل المصادقة الثنائية (2FA) 🔐

### الخطوة 1: إضافة التطبيقات المطلوبة
في `accountant_pro/settings.py`:

```python
INSTALLED_APPS = [
    # ... التطبيقات الموجودة
    'django_otp',
    'django_otp.plugins.otp_totp',
    'security',
]
```

### الخطوة 2: تثبيت المكتبات
```bash
pip install django-otp qrcode pillow
```

### الخطوة 3: إنشاء Migrations
```bash
python manage.py migrate otp_totp
```

---

## 3. إعداد نظام الكاش (Redis) ⚡

### الخطوة 1: تثبيت Redis
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# تشغيل Redis
sudo systemctl start redis
sudo systemctl enable redis
```

### الخطوة 2: تثبيت المكتبات
```bash
pip install django-redis redis
```

### الخطوة 3: تحديث الإعدادات
في `accountant_pro/settings.py`:

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
        },
        'KEY_PREFIX': 'tony_erp',
        'TIMEOUT': 300,
    }
}
```

---

## 4. تحديث URLs 🔗

افتح `accountant_pro/urls.py` وأضف:

```python
from django.urls import path
from security.enhanced_login_views import (
    enhanced_login_view, 
    logout_view,
    settings_2fa_view, 
    generate_backup_codes_view
)
from monitoring.health_check import (
    health_check_view,
    readiness_check_view,
    liveness_check_view,
    metrics_view
)

urlpatterns = [
    # ... URLs الموجودة
    
    # Authentication URLs
    path('login/', enhanced_login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('settings/2fa/', settings_2fa_view, name='settings_2fa'),
    path('settings/2fa/backup-codes/', generate_backup_codes_view, name='generate_backup_codes'),
    
    # Health Check URLs
    path('health/', health_check_view, name='health_check'),
    path('readiness/', readiness_check_view, name='readiness_check'),
    path('liveness/', liveness_check_view, name='liveness_check'),
    path('metrics/', metrics_view, name='metrics'),
]
```

---

## 5. إنشاء Models المطلوبة 📊

أنشئ ملف `users/models_security.py`:

```python
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AuditLog(models.Model):
    """سجل التدقيق"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']


class PasswordHistory(models.Model):
    """تاريخ كلمات المرور"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'password_history'
        ordering = ['-created_at']


class BackupCode(models.Model):
    """رموز احتياطية للمصادقة الثنائية"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=255)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'backup_codes'
```

أضف إلى `users/models.py`:
```python
from .models_security import AuditLog, PasswordHistory, BackupCode
```

---

## 6. إنشاء Migrations وتطبيقها 🔄

```bash
# إنشاء migrations
python manage.py makemigrations users

# تطبيق migrations
python manage.py migrate

# للتأكد من تطبيق كل شيء
python manage.py migrate --run-syncdb
```

---

## 7. تثبيت المكتبات الإضافية 📦

```bash
# مكتبات المراقبة
pip install psutil

# تحديث requirements.txt
pip freeze > requirements.txt
```

---

## 8. اختبار التثبيت ✅

### اختبار 1: الصفحة الرئيسية
```bash
python manage.py runserver
# افتح: http://127.0.0.1:8000/login/
```

### اختبار 2: Health Check
```bash
# في terminal آخر
curl http://127.0.0.1:8000/health/
```

يجب أن تحصل على:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-03T...",
  "checks": {
    "database": {"status": "healthy"},
    "cache": {"status": "healthy"},
    ...
  }
}
```

### اختبار 3: تسجيل الدخول
1. افتح المتصفح على `/login/`
2. سجل الدخول باسم مستخدم وكلمة مرور
3. تحقق من التصميم الجديد

---

## 9. تفعيل المصادقة الثنائية لمستخدم 👤

### من Django Shell:
```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from security.two_factor_auth import TwoFactorAuthManager

User = get_user_model()

# احصل على المستخدم
user = User.objects.get(username='admin')

# فعّل المصادقة الثنائية
device, qr_code = TwoFactorAuthManager.enable_2fa(user)

# اطبع QR code URL (يمكنك فتحه في متصفح)
print(qr_code)

# أو احصل على المفتاح السري مباشرة
print(f"Secret Key: {device.key}")
```

---

## 10. إعداد بيئة الإنتاج 🚀

### في `.env`:
```bash
# الأمان
DEBUG=False
SECRET_KEY=your-very-long-random-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# قاعدة البيانات
DATABASE_URL=postgresql://user:password@localhost:5432/tony_erp

# Redis
REDIS_URL=redis://127.0.0.1:6379/1

# HTTPS
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### تجميع الملفات الثابتة:
```bash
python manage.py collectstatic --noinput
```

---

## 11. إعداد Nginx (اختياري) 🌐

أنشئ ملف `/etc/nginx/sites-available/tony_erp`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /var/www/tony_erp/staticfiles/;
    }
    
    location /media/ {
        alias /var/www/tony_erp/media/;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/tony_erp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 12. إعداد Systemd Service ⚙️

أنشئ `/etc/systemd/system/tony_erp.service`:

```ini
[Unit]
Description=Tony ERP Application
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/tony_erp
Environment="PATH=/var/www/tony_erp/venv/bin"
ExecStart=/var/www/tony_erp/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --access-logfile /var/log/tony_erp/access.log \
    --error-logfile /var/log/tony_erp/error.log \
    accountant_pro.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# إنشاء مجلد السجلات
sudo mkdir -p /var/log/tony_erp
sudo chown www-data:www-data /var/log/tony_erp

# تفعيل الخدمة
sudo systemctl daemon-reload
sudo systemctl enable tony_erp
sudo systemctl start tony_erp
sudo systemctl status tony_erp
```

---

## 13. الصيانة الدورية 🔧

### النسخ الاحتياطي اليومي:
```bash
# أضف إلى crontab
crontab -e

# أضف هذا السطر:
0 2 * * * /var/www/tony_erp/backup.sh
```

### تنظيف الجلسات القديمة:
```bash
python manage.py clearsessions
```

### تنظيف سجلات التدقيق القديمة (أكثر من 90 يوم):
```bash
python manage.py shell
```
```python
from datetime import timedelta
from django.utils import timezone
from users.models import AuditLog

cutoff_date = timezone.now() - timedelta(days=90)
AuditLog.objects.filter(timestamp__lt=cutoff_date).delete()
```

---

## 14. استكشاف الأخطاء 🔍

### المشكلة: Redis لا يعمل
```bash
# تحقق من حالة Redis
sudo systemctl status redis

# أعد تشغيله
sudo systemctl restart redis
```

### المشكلة: خطأ في Migrations
```bash
# إعادة تعيين migrations
python manage.py migrate --fake users zero
python manage.py migrate users
```

### المشكلة: صفحة تسجيل الدخول لا تظهر
```bash
# تأكد من تجميع الملفات الثابتة
python manage.py collectstatic --noinput

# تحقق من المسارات في settings
python manage.py findstatic css/style.css
```

---

## 15. الأوامر المفيدة 🛠️

```bash
# إنشاء مستخدم إداري
python manage.py createsuperuser

# تشغيل الخادم للتطوير
python manage.py runserver

# تشغيل الاختبارات
pytest

# فحص الأخطاء
python manage.py check

# عرض URLs
python manage.py show_urls
```

---

**✅ التثبيت مكتمل!**

للمساعدة، راجع:
- 📚 [DEVELOPMENT_PLAN_IMPLEMENTATION.md](DEVELOPMENT_PLAN_IMPLEMENTATION.md)
- 🔒 [SECURITY.md](SECURITY.md)
- 📖 [README.md](README.md)
