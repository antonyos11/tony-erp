# 🎯 دليل سريع لربط WhatsApp مع n8n و Tony ERP

## ✅ ما تم إنشاؤه:

### 1. تطبيق Django كامل (`whatsapp_ai`)
- ✅ Models للمحادثات والرسائل
- ✅ قاعدة معرفة للمنتجات
- ✅ API endpoints كاملة
- ✅ تسجيل تلقائي في CRM
- ✅ Admin Panel جاهز

### 2. Workflow n8n جاهز
- ✅ ملف JSON للاستيراد المباشر
- ✅ تكامل مع OpenAI
- ✅ معالجة رسائل WhatsApp
- ✅ تحليل ذكي للنوايا والمشاعر

### 3. وثائق شاملة
- ✅ دليل الإعداد الكامل
- ✅ أمثلة برمجية
- ✅ حل المشاكل

---

## 🚀 البدء السريع (5 دقائق):

### الخطوة 1: تأكد من تطبيق Migrations
```bash
cd /var/www/tony_erp
source venv/bin/activate
python manage.py migrate
```

### الخطوة 2: إنشاء Superuser (إذا لم يكن موجود)
```bash
python manage.py createsuperuser
```

### الخطوة 3: إضافة إعدادات WhatsApp
1. افتح: `http://your-domain/admin/whatsapp_ai/whatsappconfiguration/add/`
2. املأ:
   - الاسم: `إعدادات واتساب الرئيسية`
   - WhatsApp API URL: `https://graph.facebook.com/v18.0`
   - WhatsApp API Token: `[من Meta for Developers]`
   - Phone Number ID: `[من Meta]`
   - AI Provider: `OpenAI`
   - AI API Key: `[من OpenAI]`
   - ✅ إنشاء عميل تلقائياً
   - ✅ إنشاء فرصة بيع تلقائياً

### الخطوة 4: مزامنة المنتجات
```bash
python manage.py shell
```
```python
from whatsapp_ai.views import sync_products
from django.test import RequestFactory
request = RequestFactory().post('/sync/')
request.user = User.objects.get(username='admin')
sync_products(request)
```

### الخطوة 5: استيراد Workflow في n8n
1. افتح n8n
2. Import من: `/var/www/tony_erp/n8n_workflows/whatsapp_ai_workflow.json`
3. أضف Environment Variables
4. فعّل الـ Workflow

---

## 📡 API Endpoints الجاهزة:

| URL | الوظيفة |
|-----|---------|
| `GET /api/whatsapp-ai/ai/context/` | جلب المنتجات والـ system prompt للـ AI |
| `POST /api/whatsapp-ai/webhook/whatsapp/` | استقبال رسائل WhatsApp |
| `POST /api/whatsapp-ai/webhook/n8n-callback/` | استقبال نتائج AI من n8n |
| `GET /api/whatsapp-ai/conversations/` | عرض المحادثات |
| `POST /api/whatsapp-ai/sync/products/` | مزامنة المنتجات |
| `GET /api/whatsapp-ai/products-knowledge/search/?q=كلمة` | البحث في المنتجات |

---

## 💡 كيف يعمل النظام؟

```
📱 عميل → WhatsApp → Meta API
                ↓
        n8n Webhook يستقبل
                ↓
    n8n يحفظ في Tony ERP
                ↓
    n8n يجلب معلومات المنتجات
                ↓
        OpenAI يحلل ويرد
                ↓
    n8n يستخرج (منتجات، نية، مشاعر)
                ↓
    n8n يرسل التحليل للـ ERP
                ↓
    ERP يسجل في CRM تلقائياً (إذا احتمالية عالية)
                ↓
    n8n يرسل الرد للعميل عبر WhatsApp
```

---

## 🧪 اختبار سريع:

```bash
# اختبار API
curl -X POST http://your-domain/api/whatsapp-ai/webhook/whatsapp/ \
  -H "Content-Type: application/json" \
  -d '{
    "from_number": "+966501234567",
    "message_id": "test123",
    "text_body": "عندكم مراتب؟",
    "customer_name": "أحمد"
  }'
```

---

## 📊 مراقبة في Admin:

1. **المحادثات**: `/admin/whatsapp_ai/whatsappconversation/`
2. **الرسائل**: `/admin/whatsapp_ai/whatsappmessage/`
3. **المنتجات**: `/admin/whatsapp_ai/productknowledgebase/`
4. **الإعدادات**: `/admin/whatsapp_ai/whatsappconfiguration/`

---

## 🎨 تخصيص الردود:

عدّل System Prompt في الإعدادات:
```
أنت مساعد مبيعات ذكي لشركة [اسمك]

مهامك:
- الترحيب بالعملاء
- عرض المنتجات المناسبة
- الإجابة بدقة
- تشجيع الشراء

كن: ودوداً، سريعاً، ومفيداً
```

---

## 🔐 الأمان:

- ✅ Webhooks آمنة
- ✅ Token Authentication
- ✅ CSRF Protection
- ✅ API Keys مشفرة في DB

---

## 📁 الملفات المهمة:

```
whatsapp_ai/
├── models.py              # Models المحادثات والرسائل
├── views.py               # API Views
├── serializers.py         # Data Serializers
├── admin.py               # Admin Panel
└── urls.py               # API Routes

n8n_workflows/
└── whatsapp_ai_workflow.json  # Workflow جاهز

WHATSAPP_AI_SETUP_GUIDE.md     # الدليل الكامل
whatsapp_ai_examples.py         # أمثلة برمجية
```

---

## 🎯 الخطوات التالية:

1. ✅ **اختبر** الـ API محلياً
2. ✅ **أضف** بعض المنتجات في Knowledge Base
3. ✅ **استورد** Workflow في n8n
4. ✅ **اربط** WhatsApp Business API
5. ✅ **جرب** رسالة حقيقية
6. ✅ **راقب** النتائج في CRM

---

## 📞 تحتاج مساعدة؟

راجع:
1. [WHATSAPP_AI_SETUP_GUIDE.md](WHATSAPP_AI_SETUP_GUIDE.md) - الدليل الكامل
2. [whatsapp_ai_examples.py](whatsapp_ai_examples.py) - أمثلة برمجية
3. Admin Panel - للمراقبة والتحكم

---

**🎉 مبروك! النظام جاهز 100%**

كل ما تحتاجه هو:
- ✅ WhatsApp Business API Token
- ✅ OpenAI API Key  
- ✅ n8n Instance

ثم ابدأ الاستقبال التلقائي للعملاء! 🚀
