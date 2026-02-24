# 🏢 Tony ERP Enterprise - دليل التنصيب للشركات الكبيرة

## 📋 المتطلبات

### الحد الأدنى للسيرفر
| المكون | الحد الأدنى | الموصى به للشركات الكبيرة |
|--------|-------------|---------------------------|
| CPU | 4 cores | 16+ cores |
| RAM | 8 GB | 64+ GB |
| Storage | 100 GB SSD | 1+ TB NVMe SSD |
| Network | 100 Mbps | 1+ Gbps |

### البرمجيات المطلوبة
- Docker 24.0+
- Docker Compose 2.20+
- PostgreSQL 15+ (عبر Docker أو مستقل)
- Redis 7+
- Nginx (اختياري - موجود في Docker)

---

## 🚀 التنصيب السريع

### 1. استنساخ المشروع
```bash
git clone https://github.com/your-repo/tony-erp.git
cd tony-erp
```

### 2. إعداد ملف البيئة
```bash
cp .env.enterprise.example .env
nano .env  # عدّل القيم
```

### 3. تشغيل النظام
```bash
# التشغيل الأساسي
docker-compose -f docker-compose.enterprise.yml up -d

# مع أدوات الإدارة (pgAdmin)
docker-compose -f docker-compose.enterprise.yml --profile admin up -d

# مع أدوات المراقبة (Prometheus + Grafana)
docker-compose -f docker-compose.enterprise.yml --profile monitoring up -d
```

### 4. إنشاء المستخدم الأول
```bash
docker-compose -f docker-compose.enterprise.yml exec web python manage.py createsuperuser
```

---

## 🏗️ البنية التحتية

```
                    ┌─────────────────────────────────┐
                    │           Load Balancer         │
                    │       (Nginx / AWS ALB)         │
                    └───────────────┬─────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
    ┌─────┴─────┐            ┌─────┴─────┐            ┌─────┴─────┐
    │  Web App  │            │  Web App  │            │  Web App  │
    │  (Django) │            │  (Django) │            │  (Django) │
    └─────┬─────┘            └─────┬─────┘            └─────┬─────┘
          │                         │                         │
          └─────────────────────────┼─────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
    ┌─────┴─────┐            ┌─────┴─────┐            ┌─────┴─────┐
    │PostgreSQL │            │   Redis   │            │  Celery   │
    │  (Primary)│            │  (Cache)  │            │ (Workers) │
    └───────────┘            └───────────┘            └───────────┘
```

---

## ⚙️ الإعدادات المهمة

### قاعدة البيانات (PostgreSQL)
```env
DB_ENGINE=postgresql
DB_NAME=tony_erp
DB_USER=tony_erp
DB_PASSWORD=كلمة-مرور-قوية-جداً
DB_HOST=db
DB_PORT=5432
```

### التخزين المؤقت (Redis)
```env
REDIS_URL=redis://redis:6379/0
```

### المهام الخلفية (Celery)
```env
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

---

## 📊 المراقبة والأداء

### Flower (مراقبة Celery)
```
http://your-server:5555
```

### Grafana (لوحة تحكم الأداء)
```
http://your-server:3000
```

### pgAdmin (إدارة قاعدة البيانات)
```
http://your-server:5050
```

---

## 🔒 الأمان

### 1. تغيير كلمات المرور الافتراضية
```bash
# قاعدة البيانات
DB_PASSWORD=كلمة-مرور-معقدة

# Redis (إذا كان مكشوف)
REDIS_PASSWORD=كلمة-مرور-redis

# Secret Key
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
```

### 2. شهادات SSL
```bash
# Let's Encrypt
certbot certonly --webroot -w /var/www/html -d yourdomain.com

# نسخ الشهادات
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./ssl/
```

### 3. Firewall
```bash
# السماح فقط للمنافذ الضرورية
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 5432/tcp  # PostgreSQL - داخلي فقط
ufw deny 6379/tcp  # Redis - داخلي فقط
```

---

## 📈 التوسع (Scaling)

### التوسع الأفقي
```bash
# زيادة عدد نسخ Web
docker-compose -f docker-compose.enterprise.yml up -d --scale web=4

# زيادة عدد Workers
docker-compose -f docker-compose.enterprise.yml up -d --scale celery_worker=4
```

### Kubernetes (للمؤسسات الكبيرة جداً)
انظر ملف `kubernetes/` للتفاصيل.

---

## 💾 النسخ الاحتياطي

### نسخ يومي تلقائي
النسخ الاحتياطي يعمل تلقائياً عبر Celery Beat في الساعة 3:00 صباحاً.

### نسخ يدوي
```bash
# قاعدة البيانات
docker-compose exec db pg_dump -U tony_erp tony_erp > backup_$(date +%Y%m%d).sql

# الملفات
tar -czf media_$(date +%Y%m%d).tar.gz media/
```

### استعادة
```bash
# قاعدة البيانات
cat backup_20240101.sql | docker-compose exec -T db psql -U tony_erp tony_erp

# الملفات
tar -xzf media_20240101.tar.gz
```

---

## 🛠️ الصيانة

### تحديث النظام
```bash
# إيقاف النظام
docker-compose -f docker-compose.enterprise.yml down

# سحب التحديثات
git pull

# إعادة البناء والتشغيل
docker-compose -f docker-compose.enterprise.yml up -d --build
```

### تنظيف الـ Cache
```bash
docker-compose exec web python manage.py clear_cache
```

### عرض السجلات
```bash
# كل الخدمات
docker-compose logs -f

# خدمة معينة
docker-compose logs -f web
docker-compose logs -f celery_worker
```

---

## 📞 الدعم الفني

للدعم الفني للشركات الكبيرة:
- 📧 Email: enterprise@tonyerp.com
- 📱 Phone: +966-XX-XXX-XXXX
- 🌐 Portal: https://support.tonyerp.com

---

## ✅ قائمة التحقق قبل الإنتاج

- [ ] تغيير `SECRET_KEY`
- [ ] تعيين `DEBUG=0`
- [ ] تكوين شهادات SSL
- [ ] تعيين `ALLOWED_HOSTS`
- [ ] تكوين البريد الإلكتروني
- [ ] تفعيل النسخ الاحتياطي التلقائي
- [ ] تكوين المراقبة (Monitoring)
- [ ] اختبار الاستعادة من النسخ الاحتياطي
- [ ] تحديد صلاحيات المستخدمين
- [ ] تفعيل Rate Limiting
- [ ] مراجعة إعدادات الأمان
