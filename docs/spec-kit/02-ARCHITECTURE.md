# 🏗️ 02 - البنية التقنية والمعمارية

## 📐 نمط التصميم

النظام مبني على نمط **MVT (Model-View-Template)** الخاص بـ Django مع طبقة **REST API** إضافية.

```
┌────────────────────────────────────────────────────────────┐
│                     طبقة العرض (Presentation)               │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Templates  │  │  REST API   │  │  WebSocket   │     │
│  │    (HTML)    │  │    (JSON)   │  │  (Channels)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
├────────────────────────────────────────────────────────────┤
│                     طبقة التحكم (Logic)                    │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    Views     │  │  ViewSets   │  │  Consumers   │     │
│  │   (Django)   │  │    (DRF)    │  │  (Channels)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
├────────────────────────────────────────────────────────────┤
│                   طبقة الخدمات (Services)                  │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Managers   │  │   Signals   │  │ Celery Tasks │     │
│  │              │  │             │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
├────────────────────────────────────────────────────────────┤
│                   طبقة البيانات (Data)                     │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    Models    │  │  QuerySets  │  │   Managers   │     │
│  │   (Django)   │  │             │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
├────────────────────────────────────────────────────────────┤
│                   طبقة التخزين (Storage)                   │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ PostgreSQL   │  │    Redis    │  │    Files     │     │
│  │   /SQLite    │  │   (Cache)   │  │   (Media)    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────────────────────────────────────────┘
```

---

## 📁 هيكل المشروع

```
tony_erp/
├── accountant_pro/           # إعدادات المشروع الرئيسية
│   ├── settings.py           # الإعدادات الأساسية
│   ├── settings_production.py # إعدادات الإنتاج
│   ├── urls.py               # URLs الرئيسية
│   └── wsgi.py / asgi.py     # خوادم WSGI/ASGI
│
├── core/                     # الوحدة الأساسية
│   ├── middleware/           # Middleware مخصص
│   ├── templatetags/         # Template Tags
│   ├── utils/                # أدوات مساعدة
│   └── context_processors/   # Context Processors
│
├── [79 Application Folders]/ # وحدات التطبيق
│   ├── models.py            # نماذج البيانات
│   ├── views.py             # منطق العرض
│   ├── urls.py              # مسارات URL
│   ├── admin.py             # لوحة الإدارة
│   ├── forms.py             # نماذج الإدخال
│   ├── serializers.py       # محولات API
│   ├── api_views.py         # واجهات API
│   └── templates/           # قوالب HTML
│
├── templates/               # قوالب عامة
│   ├── base.html           # القالب الأساسي
│   └── components/          # مكونات مشتركة
│
├── static/                  # ملفات ثابتة
│   ├── css/
│   ├── js/
│   └── images/
│
├── media/                   # ملفات المستخدمين
├── logs/                    # سجلات النظام
├── docs/                    # التوثيق
└── k8s/                     # Kubernetes manifests
```

---

## 🔄 سير تدفق الطلب (Request Flow)

```
[Client Request]
        │
        ▼
┌───────────────┐
│    Nginx      │ ◀── SSL Termination, Static Files
└───────┬───────┘
        │
        ▼
┌───────────────┐
│   Gunicorn    │ ◀── WSGI Server (HTTP)
│   / Daphne    │ ◀── ASGI Server (WebSocket)
└───────┬───────┘
        │
        ▼
┌───────────────────────────────────────┐
│           Django Middleware           │
├───────────────────────────────────────┤
│ • SecurityMiddleware                  │
│ • SessionMiddleware                   │
│ • AuthenticationMiddleware            │
│ • CSRFMiddleware                      │
│ • CorsMiddleware                      │
│ • CSPMiddleware                       │
│ • RateLimitMiddleware                 │
│ • PermissionMiddleware                │
│ • RequestTimingMiddleware             │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│            URL Router                  │
│      (5,300+ URL patterns)            │
└───────────────┬───────────────────────┘
                │
        ┌───────┴───────┐
        ▼               ▼
┌───────────────┐ ┌───────────────┐
│  Django Views │ │  DRF ViewSets │
└───────┬───────┘ └───────┬───────┘
        │                 │
        └────────┬────────┘
                 │
                 ▼
┌───────────────────────────────────────┐
│            Django ORM                  │
│         (629 Models)                   │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│           Database                     │
│    (PostgreSQL / SQLite)              │
└───────────────────────────────────────┘
```

---

## 🗄️ قاعدة البيانات

### الخيارات المدعومة

| قاعدة البيانات | الاستخدام | الوصف |
|----------------|----------|-------|
| **SQLite** | التطوير | ملف واحد، لا يحتاج إعداد |
| **PostgreSQL** | الإنتاج | أداء عالي، موثوقية |
| **MySQL** | اختياري | مدعوم لكن غير موصى |

### إحصائيات الجداول

- **عدد الموديلات:** 629
- **حجم قاعدة البيانات الحالية:** ~5.4MB
- **عدد الجداول:** ~650+ (مع جداول Django الداخلية)

---

## ⚡ التخزين المؤقت (Caching)

### استراتيجية التخزين المؤقت

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### مستويات التخزين المؤقت

1. **Database Query Cache** - استعلامات قاعدة البيانات
2. **View Cache** - صفحات كاملة
3. **Fragment Cache** - أجزاء من القوالب
4. **Session Cache** - جلسات المستخدمين
5. **API Response Cache** - ردود API

---

## 📬 قائمة المهام (Task Queue)

### Celery Configuration

```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
```

### أنواع المهام

| النوع | الأمثلة |
|-------|---------|
| **Immediate** | إرسال الإشعارات، تحديث المخزون |
| **Scheduled** | تقارير يومية، نسخ احتياطي |
| **Periodic** | فحص الضمانات، تجديد الاشتراكات |
| **Long-running** | تصدير البيانات، تحليلات AI |

---

## 🔌 WebSocket (Real-time)

### Django Channels

```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}
```

### الاستخدامات

- الدردشة الداخلية (Internal Chat)
- الإشعارات الفورية (Live Notifications)
- تحديثات POS (POS Updates)
- تتبع المواقع (Location Tracking)

---

## 🐳 Docker Architecture

### docker-compose.yml

```yaml
services:
  web:           # Django Application
  db:            # PostgreSQL Database
  redis:         # Cache & Message Broker
  celery:        # Task Workers
  celery-beat:   # Scheduled Tasks
  nginx:         # Reverse Proxy
  flower:        # Celery Monitoring
```

### Kubernetes Ready

```
k8s/
├── deployment.yaml
├── service.yaml
├── configmap.yaml
├── secrets.yaml
├── ingress.yaml
└── hpa.yaml
```

---

## 📊 المراقبة والأداء

### أدوات المراقبة

| الأداة | الغرض |
|--------|-------|
| **Prometheus** | جمع المقاييس |
| **Grafana** | لوحات المعلومات |
| **Flower** | مراقبة Celery |
| **Django Debug Toolbar** | تصحيح التطوير |

### مقاييس الأداء

- زمن استجابة الطلبات
- استخدام الذاكرة
- استعلامات قاعدة البيانات
- معدل الأخطاء

---

*الوثيقة التالية: [03-MODULES-CATALOG.md](03-MODULES-CATALOG.md)*
