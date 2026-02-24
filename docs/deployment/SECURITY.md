# سياسة الأمان (مبدئي)

## الأهداف
- تعزيز المصادقة (إمكانية تفعيل 2FA عبر django-otp موجود فعلاً)
- ضبط الجلسات المتزامنة لكل مستخدم
- تسجيل محاولات الدخول الفاشلة والتنبيهات (SecurityAlert)
- تمهيد لتفعيل Rate Limiting (اقتراح استخدام django-ratelimit لاحقاً)

## ما هو موجود
- OTP Middleware مفعّل
- نماذج: SecurityAlert, UserActivity, UserSession
- إعداد: users.middleware.SecurityMiddleware
- محدد معدل بسيط (DEV فقط): core.middleware.SimpleRateLimitMiddleware
- سياسات كلمات مرور (Min Length 10 + Validators قياسية)

## تحسينات قادمة
1. إضافة قيود محاولات تسجيل الدخول (Lockout مؤقت)
2. إضافة سياسة كلمة مرور (طول وتعقيد + انتهاء صلاحية)
3. إضافة Rate Limit لنقاط حساسة (/api/* , /login)
4. تفعيل إشعارات بريد (لاحقاً) عند تنبيه أمني حرج
5. استبدال المحدد البسيط ب Redis + django-ratelimit في الإنتاج

## متغيرات بيئة مقترحة
```
SECURITY_MAX_FAILED_LOGINS=5
SECURITY_LOCK_MINUTES=15
RATE_LIMIT_LOGIN=5/m
RATE_LIMIT_API_DEFAULT=100/m
```

## سجل التعديلات
- 2025-09-15: إنشاء الملف المبدئي.
