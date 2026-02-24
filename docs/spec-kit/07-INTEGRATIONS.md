# 🔗 07 - التكاملات الخارجية

## 📋 نظرة عامة

يدعم النظام التكامل مع العديد من الأنظمة والخدمات الخارجية لتوفير تجربة متكاملة.

---

## 💳 بوابات الدفع

### 1. STC Pay
```python
# إعدادات STC Pay
STC_PAY_MERCHANT_ID = os.getenv('STC_PAY_MERCHANT_ID')
STC_PAY_API_KEY = os.getenv('STC_PAY_API_KEY')
STC_PAY_SECRET = os.getenv('STC_PAY_SECRET')
STC_PAY_ENVIRONMENT = 'production'  # or 'sandbox'
```

### 2. Mada/VISA/MasterCard
```python
# بوابة HyperPay
HYPERPAY_ENTITY_ID = os.getenv('HYPERPAY_ENTITY_ID')
HYPERPAY_ACCESS_TOKEN = os.getenv('HYPERPAY_ACCESS_TOKEN')
HYPERPAY_CHECKOUT_URL = 'https://oppwa.com/v1/checkouts'
```

### 3. Apple Pay / Google Pay
- دعم كامل عبر HyperPay
- تكامل مع نظام POS

---

## 📧 خدمات البريد والرسائل

### 1. البريد الإلكتروني

```python
# SMTP Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
```

**الخدمات المدعومة:**
- Gmail
- Outlook/Office 365
- Amazon SES
- SendGrid
- Mailgun

### 2. الرسائل القصيرة (SMS)

| المزود | المنطقة | المكتبة |
|--------|---------|---------|
| Twilio | عالمي | twilio |
| Unifonic | الشرق الأوسط | unifonic |
| Mobily | مصر | custom |
| MSEGAT | مصر | custom |

```python
# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
```

### 3. واتساب

```python
# WhatsApp Business API
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
WHATSAPP_PHONE_ID = os.getenv('WHATSAPP_PHONE_ID')
WHATSAPP_API_URL = 'https://graph.facebook.com/v17.0'
```

---

## 🛒 منصات التجارة الإلكترونية

### 1. WooCommerce

```python
# WooCommerce Integration
WOOCOMMERCE_STORE_URL = os.getenv('WOOCOMMERCE_URL')
WOOCOMMERCE_CONSUMER_KEY = os.getenv('WOOCOMMERCE_KEY')
WOOCOMMERCE_CONSUMER_SECRET = os.getenv('WOOCOMMERCE_SECRET')
WOOCOMMERCE_VERSION = 'wc/v3'
```

**المزامنة:**
- المنتجات (ثنائية الاتجاه)
- المخزون (ثنائية الاتجاه)
- الطلبات (من WooCommerce)
- العملاء (من WooCommerce)
- الفئات (ثنائية الاتجاه)

### 2. Shopify (قيد التطوير)

```python
# Shopify Integration
SHOPIFY_STORE_URL = os.getenv('SHOPIFY_URL')
SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
SHOPIFY_API_SECRET = os.getenv('SHOPIFY_API_SECRET')
```

### 3. Salla (قيد التطوير)

```python
# Salla Integration
SALLA_API_URL = 'https://api.salla.dev/admin/v2'
SALLA_ACCESS_TOKEN = os.getenv('SALLA_ACCESS_TOKEN')
```

---

## 📜 الفوترة الإلكترونية (ZATCA)

### المرحلة 1 - التوليد

```python
# ZATCA Phase 1
ZATCA_SELLER_NAME = os.getenv('ZATCA_SELLER_NAME')
ZATCA_VAT_NUMBER = os.getenv('ZATCA_VAT_NUMBER')
ZATCA_QR_ENABLED = True
```

### المرحلة 2 - التكامل

```python
# ZATCA Phase 2 Integration
ZATCA_API_URL = os.getenv('ZATCA_API_URL')
ZATCA_API_KEY = os.getenv('ZATCA_API_KEY')
ZATCA_API_SECRET = os.getenv('ZATCA_API_SECRET')
ZATCA_CERTIFICATE_PATH = os.getenv('ZATCA_CERTIFICATE_PATH')
ZATCA_PRIVATE_KEY_PATH = os.getenv('ZATCA_PRIVATE_KEY_PATH')

# Onboarding
ZATCA_DEVICE_SERIAL = os.getenv('ZATCA_DEVICE_SERIAL')
ZATCA_EGS_SERIAL = os.getenv('ZATCA_EGS_SERIAL')
```

**الميزات:**
- ✅ توليد QR Code
- ✅ توليد XML
- ✅ التوقيع الرقمي
- ✅ الإرسال للمنصة
- ✅ استلام الإجابة
- ✅ إعادة المحاولة التلقائية

---

## 🤖 الذكاء الاصطناعي

### 1. OpenAI

```python
# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = 'gpt-4'
OPENAI_MAX_TOKENS = 2000
```

**الاستخدامات:**
- المساعد الذكي
- تحليل البيانات
- توليد التقارير
- الترجمة

### 2. Anthropic (Claude)

```python
# Anthropic Configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ANTHROPIC_MODEL = 'claude-3-opus'
```

### 3. Google AI

```python
# Google Generative AI
GOOGLE_AI_API_KEY = os.getenv('GOOGLE_AI_API_KEY')
```

---

## 🏦 التكامل البنكي

### Open Banking API

```python
# Bank Integration
BANK_API_URL = os.getenv('BANK_API_URL')
BANK_CLIENT_ID = os.getenv('BANK_CLIENT_ID')
BANK_CLIENT_SECRET = os.getenv('BANK_CLIENT_SECRET')
```

**الميزات:**
- استيراد كشوفات الحساب
- المطابقة التلقائية
- التحويلات
- إشعارات الرصيد

---

## 📊 التحليلات والمراقبة

### 1. Prometheus

```python
# Prometheus Metrics
PROMETHEUS_METRICS_EXPORT_PORT = 8001
PROMETHEUS_METRICS_EXPORT_PORT_RANGE = (8001, 8099)
```

### 2. Grafana

- لوحات معلومات جاهزة
- تنبيهات مخصصة
- تقارير أداء

### 3. Sentry (Error Tracking)

```python
# Sentry Configuration
import sentry_sdk
sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    traces_sample_rate=1.0,
    environment=os.getenv('ENVIRONMENT', 'production'),
)
```

---

## 🖨️ الطباعة

### 1. طابعات حرارية (ESC/POS)

```python
# ESC/POS Printers
ESCPOS_PRINTER_IP = os.getenv('ESCPOS_PRINTER_IP')
ESCPOS_PRINTER_PORT = int(os.getenv('ESCPOS_PRINTER_PORT', 9100))
```

**الطابعات المدعومة:**
- Epson TM series
- Star TSP series
- XPrinter
- POS-80

### 2. طابعات الباركود (ZPL)

```python
# Zebra Printers
ZPL_PRINTER_IP = os.getenv('ZPL_PRINTER_IP')
ZPL_PRINTER_PORT = 9100
```

**الطابعات المدعومة:**
- Zebra GK/GC series
- Zebra ZD series
- TSC

### 3. طابعات PDF

```python
# PDF Generation
WKHTMLTOPDF_PATH = '/usr/bin/wkhtmltopdf'
REPORTLAB_FONT = 'arabic'
```

---

## 🚚 شركات الشحن

### 1. Aramex

```python
# Aramex Integration
ARAMEX_ACCOUNT_NUMBER = os.getenv('ARAMEX_ACCOUNT_NUMBER')
ARAMEX_USERNAME = os.getenv('ARAMEX_USERNAME')
ARAMEX_PASSWORD = os.getenv('ARAMEX_PASSWORD')
ARAMEX_API_URL = 'https://ws.aramex.net'
```

### 2. SMSA

```python
# SMSA Integration
SMSA_PASSKEY = os.getenv('SMSA_PASSKEY')
SMSA_API_URL = 'https://sam.smsaexpress.com'
```

### 3. DHL

```python
# DHL Integration
DHL_API_KEY = os.getenv('DHL_API_KEY')
DHL_SECRET = os.getenv('DHL_SECRET')
DHL_ACCOUNT = os.getenv('DHL_ACCOUNT')
```

---

## ☁️ التخزين السحابي

### 1. Amazon S3

```python
# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_S3_BUCKET')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION', 'me-south-1')
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
```

### 2. Google Cloud Storage

```python
# GCS Configuration
GS_BUCKET_NAME = os.getenv('GCS_BUCKET')
GS_PROJECT_ID = os.getenv('GCS_PROJECT')
DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
```

### 3. DigitalOcean Spaces

```python
# DO Spaces
AWS_S3_ENDPOINT_URL = 'https://fra1.digitaloceanspaces.com'
```

---

## 📱 تطبيقات الموبايل

### Push Notifications

```python
# Firebase Cloud Messaging
FCM_SERVER_KEY = os.getenv('FCM_SERVER_KEY')
FCM_API_URL = 'https://fcm.googleapis.com/fcm/send'

# Apple Push Notification
APNS_KEY_ID = os.getenv('APNS_KEY_ID')
APNS_TEAM_ID = os.getenv('APNS_TEAM_ID')
```

### Pusher (Real-time)

```python
# Pusher Configuration
PUSHER_APP_ID = os.getenv('PUSHER_APP_ID')
PUSHER_KEY = os.getenv('PUSHER_KEY')
PUSHER_SECRET = os.getenv('PUSHER_SECRET')
PUSHER_CLUSTER = os.getenv('PUSHER_CLUSTER', 'eu')
```

---

## 🔗 خريطة التكاملات

```
                              ┌─────────────────┐
                              │   Tony ERP      │
                              └────────┬────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │              │               │               │              │
        ▼              ▼               ▼               ▼              ▼
   ┌─────────┐   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
   │ Payment │   │  E-com  │    │  ZATCA  │    │   AI    │    │ Storage │
   │ Gateway │   │ Platform│    │  eFatoora│   │ Services│    │  Cloud  │
   └─────────┘   └─────────┘    └─────────┘    └─────────┘    └─────────┘
       │              │               │               │              │
   ┌───┴───┐     ┌───┴───┐      ┌────┴────┐    ┌────┴────┐    ┌───┴───┐
   │STC Pay│     │WooComm│      │ Phase 1 │    │ OpenAI  │    │  S3   │
   │Mada   │     │Shopify│      │ Phase 2 │    │ Claude  │    │ GCS   │
   │Apple  │     │Salla  │      │         │    │ Gemini  │    │       │
   └───────┘     └───────┘      └─────────┘    └─────────┘    └───────┘
```

---

## ⚙️ إعداد التكاملات

### متغيرات البيئة المطلوبة

```bash
# .env file

# ZATCA
ZATCA_SELLER_NAME=اسم_الشركة
ZATCA_VAT_NUMBER=300000000000003

# WooCommerce
WOOCOMMERCE_URL=https://store.com
WOOCOMMERCE_KEY=ck_xxxxx
WOOCOMMERCE_SECRET=cs_xxxxx

# AI
OPENAI_API_KEY=sk-xxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxx

# SMS
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_PHONE_NUMBER=+1234567890

# Cloud Storage
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=xxxxx
AWS_S3_BUCKET=my-bucket
```

---

*الوثيقة التالية: [08-DEPLOYMENT.md](08-DEPLOYMENT.md)*
