# 📦 09 - المتطلبات والاعتماديات

## 📋 نظرة عامة

هذا الملف يوثق جميع المتطلبات والاعتماديات اللازمة لتشغيل النظام.

---

## 🐍 متطلبات Python

| المتطلب | الإصدار الأدنى | الإصدار الموصى |
|---------|----------------|-----------------|
| Python | 3.11 | 3.12+ |
| pip | 23.0 | 24.0+ |
| virtualenv | 20.0 | 20.0+ |

---

## 📚 المكتبات الأساسية (Core)

### Django و REST Framework

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| Django | 5.2.5 | إطار العمل الرئيسي |
| djangorestframework | 3.16.1 | REST API Framework |
| django-filter | 25.1 | فلترة الاستعلامات |
| django-cors-headers | 4.7.0 | دعم CORS |
| drf-spectacular | 0.28.0 | توثيق API (OpenAPI) |

### قاعدة البيانات

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| psycopg | 3.2.3 | PostgreSQL adapter |
| dj-database-url | 3.0.1 | تحليل DATABASE_URL |

### التخزين المؤقت والمهام

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| celery | 5.5.3 | قائمة المهام |
| redis | 6.4.0 | عميل Redis |
| django-redis | 5.4.0 | Django cache backend |
| flower | 2.0.1 | مراقبة Celery |
| django_celery_beat | - | جدولة المهام |

---

## 🔐 الأمان والمصادقة

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| djangorestframework-simplejwt | 5.5.1 | JWT Authentication |
| django-otp | 1.6.1 | المصادقة الثنائية |
| pyotp | 2.9.0 | TOTP/HOTP |
| django-ratelimit | 4.1.0 | تحديد الطلبات |
| django-csp | 3.8 | Content Security Policy |
| PyJWT | 2.9.0+ | JWT للـ QR |
| cryptography | 46.0.0 | التشفير |

---

## 🌐 الخوادم والاتصالات

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| gunicorn | 23.0.0 | WSGI Server |
| uvicorn | 0.32.0 | ASGI Server |
| daphne | 4.1.2 | Channels Server |
| channels | 4.1.0 | WebSocket |
| channels-redis | 4.2.0 | Channels backend |
| websockets | 14.0 | WebSocket |
| whitenoise | 6.9.0 | Static files |

---

## 📊 التقارير والتصدير

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| reportlab | 4.2.2 | PDF generation |
| openpyxl | 3.1.5 | Excel read/write |
| xlsxwriter | 3.2.0 | Excel write |
| pandas | 2.2.3 | تحليل البيانات |
| matplotlib | 3.9.2 | الرسوم البيانية |
| seaborn | 0.13.2 | تصور البيانات |
| plotly | 5.24.1 | الرسوم التفاعلية |

---

## 🖼️ الصور والباركود

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| pillow | 11.3.0 | معالجة الصور |
| qrcode | 8.2 | QR Code |
| python-barcode | 0.15.1 | Barcode generation |

---

## 🖨️ الطباعة

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| python-escpos | 3.1+ | طابعات ESC/POS |
| reportlab | 4.2.2 | طباعة PDF |

---

## 🌍 اللغة والترجمة

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| arabic-reshaper | 3.0.0 | تشكيل النص العربي |
| python-bidi | 0.4.2 | دعم RTL |

---

## 📅 التاريخ والوقت

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| python-dateutil | 2.9.0.post0 | معالجة التواريخ |
| pytz | 2024.2 | المناطق الزمنية |

---

## 🤖 الذكاء الاصطناعي

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| openai | 1.0.0+ | OpenAI API |
| anthropic | 0.7.0+ | Claude API |
| google-generativeai | 0.3.0+ | Gemini API |

---

## 🔔 الإشعارات

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| django-notifications-hq | 1.8.3 | نظام الإشعارات |
| pusher | 3.3.2 | Pusher real-time |

---

## 📜 ZATCA (الفوترة الإلكترونية)

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| cryptography | 46.0.0 | التشفير والتوقيع |
| lxml | 5.3.0 | معالجة XML |

---

## 🧪 التطوير والاختبار

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| django-debug-toolbar | 4.4.6 | شريط التصحيح |
| django-extensions | 3.2.3 | أوامر إضافية |
| coverage | 7.6.10 | تغطية الاختبارات |
| factory_boy | 3.3.0 | إنشاء بيانات اختبار |
| locust | 2.43.0 | اختبار الحمل |

---

## 📊 المراقبة

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| django-prometheus | 2.4.1 | Prometheus metrics |
| django-health-check | 3.18.3 | Health checks |
| psutil | 6.0.0 | مراقبة النظام |

---

## 🎨 واجهة المستخدم

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| django-crispy-forms | 2.5 | نماذج Bootstrap |
| crispy-bootstrap5 | 2025.6 | Bootstrap 5 template |

---

## 🌐 الاتصالات الخارجية

| المكتبة | الإصدار | الوصف |
|---------|---------|-------|
| requests | 2.32.3 | HTTP Client |
| python-dotenv | 1.1.1 | متغيرات البيئة |

---

## 📦 requirements.txt الكامل

```txt
# Core Django dependencies
Django==5.2.5
djangorestframework==3.16.1
django-filter==25.1
django-cors-headers==4.7.0

# Database
psycopg[binary]==3.2.3
dj-database-url==3.0.1

# Environment management
python-dotenv==1.1.1

# API Documentation
drf-spectacular==0.28.0

# Authentication
djangorestframework-simplejwt==5.5.1
django-otp==1.6.1
qrcode==8.2
pillow==11.3.0

# Task queue and caching
celery==5.5.3
redis==6.4.0
django-redis==5.4.0
flower==2.0.1

# Static files
whitenoise==6.9.0

# File handling
openpyxl==3.1.5
xlsxwriter==3.2.0
reportlab==4.2.2

# Date and time
python-dateutil==2.9.0.post0

# Image processing
python-barcode==0.15.1

# Security
django-ratelimit==4.1.0
django-csp==3.8
django-health-check==3.18.3

# Monitoring & Testing
django-prometheus==2.4.1
locust==2.43.0

# ZATCA Integration
cryptography==46.0.0
lxml==5.3.0

# Development tools
django-debug-toolbar==4.4.6
django-extensions==3.2.3

# Forms UI
django-crispy-forms==2.5
crispy-bootstrap5==2025.6

# Production server
gunicorn==23.0.0
uvicorn==0.32.0

# WebSocket support
channels==4.1.0
channels-redis==4.2.0
websockets==14.0
daphne==4.1.2

# Notifications
django-notifications-hq==1.8.3
pusher==3.3.2

# Excel/PDF export
pandas==2.2.3
matplotlib==3.9.2
seaborn==0.13.2
plotly==5.24.1

# Utilities
requests==2.32.3
pytz==2024.2
arabic-reshaper==3.0.0
python-bidi==0.4.2
psutil==6.0.0
coverage==7.6.10
factory_boy==3.3.0

# Printing
python-escpos>=3.1

# Authentication
PyJWT>=2.9.0
pyotp==2.9.0

# AI
openai>=1.0.0
anthropic>=0.7.0
google-generativeai>=0.3.0
```

---

## 🔧 متطلبات النظام

### Linux (Ubuntu/Debian)

```bash
# تحديث النظام
sudo apt update && sudo apt upgrade -y

# تثبيت Python
sudo apt install python3.11 python3.11-venv python3-pip -y

# متطلبات PostgreSQL
sudo apt install libpq-dev -y

# متطلبات الصور
sudo apt install libjpeg-dev zlib1g-dev libpng-dev -y

# متطلبات PDF
sudo apt install libfreetype6-dev -y

# Redis
sudo apt install redis-server -y
```

### Windows

```powershell
# تثبيت Python من python.org
# تثبيت Visual C++ Build Tools

# تثبيت Redis (WSL أو Docker)
wsl --install
# أو
docker run -d -p 6379:6379 redis:alpine
```

### macOS

```bash
# Homebrew
brew install python@3.11
brew install postgresql
brew install redis
brew services start redis
```

---

## 📈 موارد الخادم الموصى بها

### التطوير

| المورد | الحد الأدنى |
|--------|-------------|
| CPU | 2 cores |
| RAM | 4 GB |
| Storage | 10 GB |

### الإنتاج (صغير)

| المورد | الموصى |
|--------|--------|
| CPU | 4 cores |
| RAM | 8 GB |
| Storage | 50 GB SSD |

### الإنتاج (كبير)

| المورد | الموصى |
|--------|--------|
| CPU | 8+ cores |
| RAM | 16+ GB |
| Storage | 200+ GB SSD |
| Database | PostgreSQL منفصل |
| Cache | Redis منفصل |

---

## 🔄 تحديث المكتبات

```bash
# عرض المكتبات القديمة
pip list --outdated

# تحديث مكتبة معينة
pip install --upgrade django

# تحديث جميع المكتبات (بحذر!)
pip install --upgrade -r requirements.txt

# إنشاء requirements.txt جديد
pip freeze > requirements.txt
```

---

*الوثيقة التالية: [10-DATABASE-SCHEMA.md](10-DATABASE-SCHEMA.md)*
