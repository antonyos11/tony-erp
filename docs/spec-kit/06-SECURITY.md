# 🔐 06 - الأمان والحماية

## 📋 نظرة عامة

يتبع النظام أفضل ممارسات الأمان لحماية البيانات والمستخدمين، مع دعم معايير الامتثال المختلفة.

---

## 🔒 طبقات الأمان

```
┌─────────────────────────────────────────────────────────────┐
│                    الطبقة 1: الشبكة                          │
│     • Firewall • SSL/TLS • DDoS Protection                  │
├─────────────────────────────────────────────────────────────┤
│                    الطبقة 2: التطبيق                         │
│     • WAF • Rate Limiting • Input Validation                │
├─────────────────────────────────────────────────────────────┤
│                    الطبقة 3: المصادقة                        │
│     • JWT • 2FA/MFA • Session Management                    │
├─────────────────────────────────────────────────────────────┤
│                    الطبقة 4: التفويض                         │
│     • RBAC • Permission System • Resource Control           │
├─────────────────────────────────────────────────────────────┤
│                    الطبقة 5: البيانات                        │
│     • Encryption • Hashing • Audit Logging                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 المصادقة (Authentication)

### 1. JWT (JSON Web Tokens)

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
}
```

### 2. المصادقة الثنائية (2FA)

| الطريقة | الوصف | المكتبة |
|---------|-------|---------|
| **TOTP** | تطبيقات مثل Google Authenticator | django-otp |
| **SMS** | رمز عبر الرسائل القصيرة | Twilio |
| **Email** | رمز عبر البريد الإلكتروني | Django Email |
| **Backup Codes** | رموز احتياطية | django-otp |

### 3. إدارة الجلسات

```python
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

---

## 👥 التفويض (Authorization)

### نظام الأدوار (RBAC)

```
┌──────────────────────────────────────────────────────────┐
│                    Super Admin                            │
│                 (صلاحيات كاملة)                           │
└────────────────────────┬─────────────────────────────────┘
                         │
           ┌─────────────┼─────────────┐
           │             │             │
           ▼             ▼             ▼
     ┌──────────┐  ┌──────────┐  ┌──────────┐
     │  Admin   │  │  Admin   │  │  Admin   │
     │ المبيعات │  │ المحاسبة │  │   HR     │
     └────┬─────┘  └────┬─────┘  └────┬─────┘
          │             │             │
    ┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐
    │  Manager  │ │  Manager  │ │  Manager  │
    └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
          │             │             │
    ┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐
    │   User    │ │   User    │ │   User    │
    └───────────┘ └───────────┘ └───────────┘
```

### أنواع الصلاحيات

| النوع | الوصف | المثال |
|-------|-------|--------|
| **Module Permission** | صلاحية الوصول للوحدة | `can_access_sales` |
| **CRUD Permission** | عمليات CRUD | `can_create_invoice` |
| **Field Permission** | صلاحية على الحقل | `can_view_cost_price` |
| **Record Permission** | صلاحية على السجل | `can_view_own_invoices` |

### نموذج الصلاحيات

```python
class ModulePermission(models.Model):
    role = ForeignKey(UserRole)
    module = CharField()
    can_view = BooleanField()
    can_create = BooleanField()
    can_edit = BooleanField()
    can_delete = BooleanField()
    can_export = BooleanField()
    can_approve = BooleanField()
```

---

## 🛡️ حماية الويب

### 1. Content Security Policy (CSP)

```python
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "fonts.googleapis.com")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "fonts.gstatic.com")
CSP_CONNECT_SRC = ("'self'", "wss:")
```

### 2. Security Headers

```python
# HSTS
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Other Headers
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
```

### 3. CORS Configuration

```python
CORS_ALLOWED_ORIGINS = [
    "https://app.domain.com",
    "https://admin.domain.com",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
```

### 4. CSRF Protection

```python
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_TRUSTED_ORIGINS = ['https://domain.com']
```

---

## ⏱️ Rate Limiting

### إعدادات التحديد

```python
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_KEY_PREFIX = 'rl'

# التحديدات
RATELIMIT_RULES = {
    'login': '5/m',          # 5 محاولات/دقيقة
    'api': '100/m',          # 100 طلب/دقيقة
    'reports': '10/m',       # 10 تقارير/دقيقة
    'export': '5/m',         # 5 تصديرات/دقيقة
    'password_reset': '3/h', # 3 محاولات/ساعة
}
```

### Middleware

```python
MIDDLEWARE = [
    ...
    'core.middleware.SimpleRateLimitMiddleware',
    ...
]
```

---

## 📝 تسجيل الأحداث (Audit Logging)

### ما يتم تسجيله

| الحدث | التفاصيل |
|-------|----------|
| تسجيل الدخول | المستخدم، الوقت، IP، الجهاز |
| تسجيل الخروج | المستخدم، الوقت، نوع الخروج |
| عمليات CRUD | المستخدم، الموديل، السجل، القيم |
| تغيير الصلاحيات | من، لمن، الصلاحيات |
| تصدير البيانات | المستخدم، نوع البيانات، الكمية |
| محاولات فاشلة | المستخدم/IP، النوع، السبب |

### نموذج السجل

```python
class AuditLog(models.Model):
    user = ForeignKey(User)
    action = CharField()  # create, update, delete, login, etc.
    model_name = CharField()
    object_id = CharField()
    old_values = JSONField()
    new_values = JSONField()
    ip_address = GenericIPAddressField()
    user_agent = TextField()
    timestamp = DateTimeField(auto_now_add=True)
```

---

## 🔔 تنبيهات الأمان

### أنواع التنبيهات

| النوع | الوصف | الإجراء |
|-------|-------|---------|
| **محاولات دخول فاشلة** | أكثر من 5 محاولات | قفل الحساب مؤقتاً |
| **تسجيل دخول من جهاز جديد** | جهاز غير معروف | إشعار للمستخدم |
| **تسجيل دخول من موقع جديد** | IP غير معتاد | طلب تأكيد |
| **تغيير كلمة المرور** | تغيير ناجح | إشعار للمستخدم |
| **وصول في وقت غير معتاد** | خارج ساعات العمل | تسجيل وإشعار |

### نموذج التنبيه

```python
class SecurityAlert(models.Model):
    user = ForeignKey(User)
    alert_type = CharField()
    severity = CharField()  # low, medium, high, critical
    message = TextField()
    ip_address = GenericIPAddressField()
    is_resolved = BooleanField()
    created_at = DateTimeField()
```

---

## 🔐 تشفير البيانات

### البيانات المشفرة

| البيانات | نوع التشفير |
|----------|-------------|
| كلمات المرور | PBKDF2 + SHA256 |
| رموز API | HMAC-SHA256 |
| بيانات الدفع | AES-256 |
| الملفات الحساسة | AES-256-GCM |
| الاتصالات | TLS 1.3 |

### إعدادات كلمة المرور

```python
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
```

---

## ✅ قائمة فحص الأمان

### قبل النشر

- [ ] تغيير `SECRET_KEY`
- [ ] تعطيل `DEBUG`
- [ ] تحديث `ALLOWED_HOSTS`
- [ ] تفعيل HTTPS
- [ ] تفعيل HSTS
- [ ] تكوين CSP
- [ ] تفعيل Rate Limiting
- [ ] مراجعة الصلاحيات
- [ ] تكوين النسخ الاحتياطي
- [ ] تفعيل المراقبة

### دوري

- [ ] تحديث المكتبات
- [ ] مراجعة سجلات الأمان
- [ ] اختبار الاختراق
- [ ] تدريب المستخدمين
- [ ] مراجعة الصلاحيات
- [ ] تجديد الشهادات

---

## 📜 الامتثال

### المعايير المدعومة

| المعيار | الوصف | الحالة |
|---------|-------|--------|
| **ZATCA** | الفوترة الإلكترونية | ✅ مطابق |
| **GDPR** | حماية البيانات الأوروبية | ✅ جاهز |
| **PCI DSS** | أمان بطاقات الدفع | ⚠️ جزئي |
| **ISO 27001** | أمان المعلومات | ⚠️ جزئي |

---

*الوثيقة التالية: [07-INTEGRATIONS.md](07-INTEGRATIONS.md)*
