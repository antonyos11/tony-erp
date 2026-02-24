# تشغيل الإنتاج: PostgreSQL + Redis

هذا الدليل يوضح تهيئة Tony ERP على بيئة إنتاج باستخدام PostgreSQL وRedis عبر Docker Compose.

## المتطلبات
- Docker Desktop
- ملف بيئة إنتاج: `.env.prod` (انسخ من `.env.prod.example`)

## الخطوات السريعة
1) انسخ القالب:
```
copy .env.prod.example .env.prod
```
2) عدّل `.env.prod` وضع القيم الصحيحة (SECRET_KEY, PROD_ALLOWED_HOSTS, كلمات مرور DB).
3) شغّل الخدمات:
```
docker compose --env-file .env.prod up -d --build
```
4) أول تشغيل سيقوم بـ migrate و collectstatic ثم يبدأ Gunicorn على المنفذ 8000.

## المتغيرات المهمة
- DJANGO_SETTINGS_MODULE=accountant_pro.settings_prod (مُفعّل داخل docker-compose)
- PROD_ALLOWED_HOSTS=example.com,www.example.com
- REDIS_URL=redis://redis:6379/1
- DATABASE_URL (اختياري)، أو POSTGRES_* + DB_ENGINE=postgresql

## خدمات المكدس
- db: PostgreSQL 15، منفذ 5432
- redis: Redis 7، منفذ 6379
- web: Django + Gunicorn على 8000
- celery_worker, celery_beat: للمهام الخلفية
- flower: مراقبة Celery على 5555

## ملاحظات الأمان
- استخدم HTTPS أمام Nginx (ملف nginx.conf اختياري).
- عيّن مفاتيح قوية وتحقق من قيم HSTS.

## استكشاف الأخطاء
- `docker compose logs -f web`
- تأكد من صحة ALLOWED_HOSTS و CORS.
