# ✅ قائمة مهام التفعيل - Tony ERP 2.0
## Activation Checklist

---

## 📋 المرحلة 1: التثبيت الأساسي (5 دقائق)

### ✅ 1.1 تثبيت المكتبات المطلوبة
```bash
cd /var/www/tony_erp
pip install django-otp qrcode pillow django-redis psutil
pip freeze > requirements.txt
```

**التحقق:**
```bash
python -c "import django_otp, qrcode, redis; print('✅ جميع المكتبات مثبتة')"
```

---

### ✅ 1.2 تحديث ملف الإعدادات

**الملف:** `accountant_pro/settings.py`

#### أ) إضافة Middleware (أضف بعد SecurityMiddleware)
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'security.security_middleware.SecurityHeadersMiddleware',
    'security.security_middleware.LoginRateLimitMiddleware',
    'security.security_middleware.SessionSecurityMiddleware',
    'security.security_middleware.AuditLogMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # ... باقي middleware
]
```

#### ب) إضافة التطبيقات
```python
INSTALLED_APPS = [
    # ... التطبيقات الموجودة
    'django_otp',
    'django_otp.plugins.otp_totp',
    'security',
    'performance',
    'monitoring',
]
```

#### ج) محققات كلمات المرور
```python
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'security.password_validators.ComplexPasswordValidator'},
    {'NAME': 'security.password_validators.NoCommonPasswordValidator'},
    {'NAME': 'security.password_validators.NoUserAttributePasswordValidator'},
    {'NAME': 'security.password_validators.PasswordHistoryValidator'},
]
```

#### د) إعدادات الجلسات
```python
SESSION_COOKIE_AGE = 7200  # ساعتين
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
```

#### هـ) إعدادات الكاش (إذا كان Redis متاح)
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'tony_erp',
        'TIMEOUT': 300,
    }
}
```

**التحقق:**
```bash
python manage.py check
```

---

### ✅ 1.3 تحديث URLs

**الملف:** `accountant_pro/urls.py`

```python
from django.urls import path
from security.enhanced_login_views import (
    enhanced_login_view, logout_view,
    settings_2fa_view, generate_backup_codes_view
)
from monitoring.health_check import (
    health_check_view, readiness_check_view,
    liveness_check_view, metrics_view
)

urlpatterns = [
    # ... URLs الموجودة
    
    # Authentication
    path('login/', enhanced_login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('settings/2fa/', settings_2fa_view, name='settings_2fa'),
    path('settings/2fa/backup-codes/', generate_backup_codes_view, name='generate_backup_codes'),
    
    # Health & Monitoring
    path('health/', health_check_view, name='health_check'),
    path('readiness/', readiness_check_view, name='readiness_check'),
    path('liveness/', liveness_check_view, name='liveness_check'),
    path('metrics/', metrics_view, name='metrics'),
    
    # ... باقي URLs
]
```

**التحقق:**
```bash
python manage.py show_urls | grep -E "(login|health|metrics)"
```

---

### ✅ 1.4 إنشاء Models

**الملف:** `users/models_security.py` (جديد)

```python
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AuditLog(models.Model):
    """سجل التدقيق"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        verbose_name = 'سجل تدقيق'
        verbose_name_plural = 'سجلات التدقيق'
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"


class PasswordHistory(models.Model):
    """تاريخ كلمات المرور"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_history')
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'password_history'
        ordering = ['-created_at']
        verbose_name = 'تاريخ كلمة مرور'
        verbose_name_plural = 'تاريخ كلمات المرور'


class BackupCode(models.Model):
    """رموز احتياطية للمصادقة الثنائية"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='backup_codes')
    code = models.CharField(max_length=255)
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'backup_codes'
        verbose_name = 'رمز احتياطي'
        verbose_name_plural = 'رموز احتياطية'
    
    def __str__(self):
        status = "مستخدم" if self.used else "جديد"
        return f"{self.user} - {status}"
```

**إضافة إلى:** `users/models.py`
```python
from .models_security import AuditLog, PasswordHistory, BackupCode
```

---

### ✅ 1.5 إنشاء وتطبيق Migrations

```bash
# إنشاء migrations
python manage.py makemigrations users

# عرض SQL الذي سيتم تنفيذه (اختياري)
python manage.py sqlmigrate users <migration_number>

# تطبيق migrations
python manage.py migrate

# التحقق
python manage.py showmigrations users
```

**التحقق من الجداول:**
```bash
python manage.py dbshell
\dt audit_logs
\dt password_history
\dt backup_codes
\q
```

---

## 📋 المرحلة 2: التكوين المتقدم (اختياري)

### ✅ 2.1 إعداد Redis (للكاش)

#### تثبيت Redis
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install redis-server

# تشغيل Redis
sudo systemctl start redis
sudo systemctl enable redis
```

**التحقق:**
```bash
redis-cli ping
# يجب أن يرد: PONG
```

---

### ✅ 2.2 اختبار الفحوصات الصحية

```bash
# تشغيل الخادم
python manage.py runserver

# في terminal آخر، اختبر:
curl http://127.0.0.1:8000/health/
curl http://127.0.0.1:8000/readiness/
curl http://127.0.0.1:8000/liveness/
curl http://127.0.0.1:8000/metrics/
```

**النتيجة المتوقعة:**
```json
{
  "status": "healthy",
  "timestamp": "...",
  "checks": {
    "database": {"status": "healthy"},
    "cache": {"status": "healthy"},
    ...
  }
}
```

---

### ✅ 2.3 اختبار صفحة تسجيل الدخول

1. افتح المتصفح: `http://127.0.0.1:8000/login/`
2. تحقق من:
   - ✅ التصميم الجديد يظهر
   - ✅ الألوان والـ gradient صحيحة
   - ✅ زر إظهار/إخفاء كلمة المرور يعمل
   - ✅ رسائل الخطأ تظهر بشكل صحيح

---

## 📋 المرحلة 3: الاختبارات (مُوصى به)

### ✅ 3.1 تثبيت pytest
```bash
pip install pytest pytest-django pytest-cov
```

### ✅ 3.2 تشغيل الاختبارات
```bash
# تشغيل جميع الاختبارات
pytest

# تشغيل اختبارات الأمان فقط
pytest tests/test_security.py -v

# تشغيل مع تقرير التغطية
pytest --cov=. --cov-report=html
```

---

## 📋 المرحلة 4: التفعيل الإنتاجي (للسيرفر)

### ✅ 4.1 تحديث متغيرات البيئة

**الملف:** `.env`
```bash
# الأمان
DEBUG=False
SECRET_KEY=<توليد مفتاح سري قوي هنا>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# قاعدة البيانات
DATABASE_URL=postgresql://user:password@localhost:5432/tony_erp

# Redis
REDIS_URL=redis://127.0.0.1:6379/1

# HTTPS
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

---

### ✅ 4.2 تجميع الملفات الثابتة
```bash
python manage.py collectstatic --noinput
```

---

### ✅ 4.3 إعداد Gunicorn (مُوصى به)

#### تثبيت
```bash
pip install gunicorn
```

#### التشغيل
```bash
gunicorn accountant_pro.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile /var/log/tony_erp/access.log \
    --error-logfile /var/log/tony_erp/error.log
```

---

## 📋 المرحلة 5: التحقق النهائي

### ✅ 5.1 قائمة التحقق النهائية

- [ ] جميع المكتبات مثبتة
- [ ] settings.py محدّث
- [ ] urls.py محدّث
- [ ] Models موجودة
- [ ] Migrations مطبقة
- [ ] Redis يعمل (اختياري)
- [ ] صفحة تسجيل الدخول تعمل
- [ ] Health checks تعمل
- [ ] الاختبارات تنجح
- [ ] الملفات الثابتة مجمعة (للإنتاج)

---

### ✅ 5.2 اختبار شامل

```bash
# 1. تحقق من الأخطاء
python manage.py check --deploy

# 2. اختبر قاعدة البيانات
python manage.py dbshell
SELECT COUNT(*) FROM audit_logs;
\q

# 3. اختبر الكاش (إذا كان Redis)
python manage.py shell
from django.core.cache import cache
cache.set('test', 'value', 10)
print(cache.get('test'))
exit()

# 4. اختبر صفحة تسجيل الدخول
curl -I http://127.0.0.1:8000/login/

# 5. اختبر Health Check
curl http://127.0.0.1:8000/health/ | python -m json.tool
```

---

## 🎉 النجاح!

إذا مرت جميع الاختبارات:

```
✅ التثبيت الأساسي - مكتمل
✅ التكوين المتقدم - مكتمل  
✅ الاختبارات - نجحت
✅ التفعيل الإنتاجي - جاهز
✅ التحقق النهائي - تم
```

**🚀 نظام Tony ERP 2.0 جاهز للاستخدام!**

---

## 📞 في حالة وجود مشاكل

### مشكلة: Redis لا يعمل
```bash
sudo systemctl status redis
sudo systemctl restart redis
```

### مشكلة: Migrations تفشل
```bash
python manage.py migrate --fake users zero
python manage.py migrate users
```

### مشكلة: صفحة تسجيل الدخول لا تظهر
```bash
python manage.py collectstatic --clear --noinput
python manage.py collectstatic --noinput
```

### مشكلة: Import Errors
```bash
pip install --upgrade -r requirements.txt
python manage.py check
```

---

## 📚 المراجع

- [دليل التثبيت الكامل](QUICK_INSTALLATION_GUIDE.md)
- [خطة التطوير](DEVELOPMENT_PLAN_IMPLEMENTATION.md)
- [الملخص](IMPLEMENTATION_SUMMARY.md)

---

**آخر تحديث:** 3 يناير 2026  
**الإصدار:** 2.0.0
