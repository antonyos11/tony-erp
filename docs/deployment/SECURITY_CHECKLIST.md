# قائمة فحص الأمان - Tony ERP
# Security Checklist for Tony ERP

## ✅ قائمة الفحص الأساسية

### 1. إعدادات الخادم
- [ ] تعطيل وضع التطوير (`DEBUG = False`)
- [ ] تكوين `ALLOWED_HOSTS` بشكل صحيح
- [ ] استخدام HTTPS في الإنتاج
- [ ] تكوين `SECURE_SSL_REDIRECT = True`
- [ ] تكوين `CSRF_COOKIE_SECURE = True`
- [ ] تكوين `SESSION_COOKIE_SECURE = True`

### 2. كلمات المرور
- [ ] تغيير كلمة المرور الافتراضية للمسؤول
- [ ] تطبيق سياسة كلمات مرور قوية
- [ ] تفعيل المصادقة الثنائية (2FA) للمسؤولين

### 3. قاعدة البيانات
- [ ] استخدام PostgreSQL في الإنتاج (ليس SQLite)
- [ ] تشفير الاتصال بقاعدة البيانات
- [ ] نسخ احتياطي منتظم
- [ ] صلاحيات محدودة لمستخدم قاعدة البيانات

### 4. SECRET_KEY
- [ ] استخدام مفتاح سري عشوائي وقوي
- [ ] عدم كشف المفتاح في الكود المصدري
- [ ] حفظه في متغيرات البيئة

### 5. CORS والـ APIs
- [ ] تقييد CORS_ALLOWED_ORIGINS
- [ ] استخدام Token Authentication للـ API
- [ ] تحديد معدل الطلبات (Rate Limiting)

### 6. الملفات والميديا
- [ ] فحص الملفات المرفوعة
- [ ] تقييد أنواع الملفات المسموحة
- [ ] استخدام مخزن ملفات آمن

### 7. الصلاحيات
- [ ] تطبيق مبدأ الحد الأدنى من الصلاحيات
- [ ] مراجعة صلاحيات المستخدمين دورياً
- [ ] تعطيل الحسابات غير المستخدمة

---

## 🔧 أوامر فحص سريعة

```bash
# فحص إعدادات Django
python manage.py check --deploy

# فحص الثغرات في الحزم
pip-audit

# فحص النظام الشامل
python manage.py system_self_check
```

---

## ⚠️ ملاحظات مهمة

1. **لا تستخدم SQLite في الإنتاج** - استخدم PostgreSQL أو MySQL
2. **لا تكشف DEBUG=True في الإنتاج** - يكشف معلومات حساسة
3. **غيّر كلمة المرور الافتراضية** - `superadmin/admin123` للتطوير فقط
4. **استخدم HTTPS دائماً** - لحماية البيانات المنقولة

---

## 📋 إعدادات الإنتاج الموصى بها

```python
# accountant_pro/settings.py

DEBUG = False
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']

# Security
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Cookies
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# Database (PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}
```
