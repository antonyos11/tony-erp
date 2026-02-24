# 🤖 دليل إعداد WhatsApp AI مع n8n و Tony ERP

## 📋 نظرة عامة

هذا النظام يربط WhatsApp Business API مع نظام Tony ERP باستخدام n8n والذكاء الصناعي، ويقوم تلقائياً بـ:
- ✅ استقبال رسائل العملاء عبر WhatsApp
- ✅ الرد عليهم بذكاء صناعي مدرب على منتجاتك
- ✅ تسجيل العملاء تلقائياً في CRM
- ✅ إنشاء فرص بيع للعملاء المهتمين
- ✅ تتبع كل المحادثات والتفاعلات

---

## 🚀 خطوات الإعداد

### 1️⃣ تفعيل التطبيق في Django

أضف التطبيق في `settings.py`:

```python
INSTALLED_APPS = [
    # ... التطبيقات الأخرى
    'whatsapp_ai',
]
```

أضف الـ URLs في `urls.py` الرئيسي:

```python
urlpatterns = [
    # ... الروابط الأخرى
    path('api/whatsapp-ai/', include('whatsapp_ai.urls')),
]
```

---

### 2️⃣ تطبيق الـ Migrations

```bash
cd /var/www/tony_erp
source venv/bin/activate
python manage.py makemigrations whatsapp_ai
python manage.py migrate whatsapp_ai
```

---

### 3️⃣ إعداد WhatsApp Business API

#### أ) إنشاء حساب في Meta for Developers:
1. اذهب إلى https://developers.facebook.com/
2. أنشئ تطبيق جديد → اختر "Business"
3. أضف منتج "WhatsApp"
4. احصل على:
   - `Phone Number ID`
   - `WhatsApp Business Account ID`
   - `Access Token`

#### ب) تكوين Webhook:
1. في لوحة WhatsApp → Settings → Webhook
2. Callback URL: `https://your-n8n.com/webhook/whatsapp-incoming`
3. Verify Token: أي كلمة مرور تختارها
4. اشترك في: `messages`

---

### 4️⃣ إعداد n8n

#### أ) تثبيت n8n (إذا لم يكن مثبتاً):

```bash
# باستخدام npm
npm install -g n8n

# أو باستخدام Docker
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

#### ب) استيراد Workflow:
1. افتح n8n على `http://localhost:5678`
2. اذهب إلى Workflows → Import from File
3. اختر الملف: `n8n_workflows/whatsapp_ai_workflow.json`

#### ج) إعداد Environment Variables في n8n:

في n8n → Settings → Variables أضف:

```
TONY_ERP_URL=https://your-erp-domain.com
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_PHONE_ID=your_phone_number_id
WHATSAPP_TOKEN=your_whatsapp_access_token
OPENAI_API_KEY=your_openai_api_key
```

#### د) إعداد Credentials:
1. OpenAI API:
   - اذهب إلى Credentials → Add Credential
   - اختر "OpenAI"
   - أدخل API Key من https://platform.openai.com/

---

### 5️⃣ إعداد النظام في Admin Panel

1. اذهب إلى `/admin/whatsapp_ai/whatsappconfiguration/add/`

2. املأ البيانات:
   ```
   الاسم: إعدادات واتساب الرئيسية
   WhatsApp API URL: https://graph.facebook.com/v18.0
   WhatsApp API Token: [توكن من Meta]
   Phone Number ID: [معرّف الهاتف]
   n8n Webhook URL: https://your-n8n.com/webhook/whatsapp-incoming
   
   AI Provider: OpenAI
   AI API Key: [مفتاح OpenAI]
   AI Model: gpt-4
   
   System Prompt: [النص التعليمي للـ AI]
   
   ✅ إنشاء عميل تلقائياً
   ✅ إنشاء فرصة بيع تلقائياً
   ```

3. احفظ الإعدادات

---

### 6️⃣ مزامنة المنتجات

#### طريقة 1: من Admin Panel
1. اذهب إلى `/admin/whatsapp_ai/productknowledgebase/`
2. اختر Actions → "مزامنة من المخزون"
3. انقر Execute

#### طريقة 2: عبر API
```bash
curl -X POST https://your-erp.com/api/whatsapp-ai/sync/products/ \
  -H "Authorization: Token YOUR_API_TOKEN"
```

#### طريقة 3: إضافة يدوية
يمكنك إضافة منتجات يدوياً مع معلومات مخصصة للـ AI:
- الأسئلة الشائعة
- الكلمات المفتاحية
- معلومات إضافية

---

## 🔗 كيف يعمل النظام؟

```
1. عميل يرسل رسالة عبر WhatsApp
         ↓
2. WhatsApp API يرسل Webhook إلى n8n
         ↓
3. n8n يحفظ الرسالة في Tony ERP
         ↓
4. n8n يجلب معلومات المنتجات من ERP
         ↓
5. n8n يرسل الرسالة + المنتجات للـ AI
         ↓
6. AI يحلل ويرد بذكاء
         ↓
7. n8n يحلل الرد ويستخرج:
   - المنتجات المذكورة
   - النية (شراء، استفسار، إلخ)
   - المشاعر (إيجابي، سلبي)
   - احتمالية الشراء
         ↓
8. n8n يرسل التحليل لـ ERP
         ↓
9. ERP يحفظ التحليل ويسجل العميل في CRM (إذا احتمالية عالية)
         ↓
10. n8n يرسل الرد للعميل عبر WhatsApp
```

---

## 📊 مراقبة المحادثات

### في Admin Panel:

#### عرض المحادثات:
`/admin/whatsapp_ai/whatsappconversation/`

يمكنك:
- رؤية كل المحادثات النشطة
- قراءة الرسائل
- معرفة احتمالية الشراء
- تحويل المحادثة إلى عميل يدوياً

#### عرض التحليلات:
كل محادثة تحتوي على:
- ✅ عدد الرسائل
- ✅ المنتجات المهتم بها
- ✅ تحليل المشاعر
- ✅ احتمالية التحويل

---

## 🔐 الأمان

### التأكد من صحة Webhooks:

أضف في `settings.py`:

```python
# للتحقق من WhatsApp Webhooks
WHATSAPP_VERIFY_TOKEN = 'your_secret_verify_token'
```

عدل `views.py`:

```python
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def whatsapp_webhook(request):
    if request.method == 'GET':
        # Webhook verification
        verify_token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        if verify_token == settings.WHATSAPP_VERIFY_TOKEN:
            return Response(int(challenge))
        return Response('Verification failed', status=403)
    
    # ... باقي الكود
```

---

## 🧪 اختبار النظام

### 1. اختبار من Postman:

```bash
POST https://your-erp.com/api/whatsapp-ai/webhook/whatsapp/

Body (JSON):
{
  "from_number": "+966501234567",
  "message_id": "test_msg_123",
  "message_type": "text",
  "text_body": "السلام عليكم، عندكم مراتب؟",
  "customer_name": "أحمد محمد"
}
```

### 2. اختبار من WhatsApp:
- أرسل رسالة لرقم واتساب Business
- انتظر الرد الذكي
- تحقق من Admin Panel

### 3. التحقق من CRM:
اذهب إلى `/admin/crm/customer/` وتأكد من إنشاء العميل تلقائياً

---

## 📱 أمثلة على المحادثات

### مثال 1: استفسار عن منتج
```
العميل: عندكم مراتب طبية؟
AI: مرحباً! نعم، لدينا مجموعة ممتازة من المراتب الطبية:
     1. مرتبة سليب كومفورت الطبية - 2500 ج.م
     2. مرتبة أورثو ميديكال - 3200 ج.م
     هل تريد تفاصيل أكثر عن أي منهما؟

→ يسجل في CRM: عميل محتمل، اهتمام بالمراتب الطبية
```

### مثال 2: استفسار عن السعر والشراء
```
العميل: كم سعر مرتبة سليب كومفورت؟
AI: مرتبة سليب كومفورت الطبية سعرها 2500 ج.م فقط!
    تتميز بـ:
    - طبقة ميموري فوم طبية
    - دعم العمود الفقري
    - ضمان 10 سنوات
    
العميل: تمام، أبغى واحدة مقاس كينج
AI: ممتاز! مقاس الكينج متوفر. 
    هل تريد طلبها الآن؟ يمكننا التوصيل خلال 48 ساعة.

→ يسجل في CRM: عميل محتمل جداً (احتمالية 90%)
→ يُنشئ فرصة بيع تلقائياً
```

---

## 🎨 تخصيص الردود

عدل System Prompt في Admin:

```
أنت مساعد مبيعات محترف لشركة [اسم شركتك] المتخصصة في [المجال].

أسلوبك:
- ودود ومهذب
- احترافي وسريع
- تجيب بدقة ووضوح
- تشجع على الشراء بلطف

قواعد:
1. رحب بالعميل بحرارة
2. اعرض المنتجات المناسبة فقط
3. اذكر الأسعار بوضوح
4. أجب على الأسئلة بدقة
5. اسأل إذا يريد المساعدة في الطلب

تذكر: هدفك مساعدة العميل وتحقيق البيع بطريقة طبيعية.
```

---

## 📈 التقارير والتحليلات

### الحصول على إحصائيات:

```python
# في Django shell
from whatsapp_ai.models import WhatsAppConversation

# إجمالي المحادثات
total = WhatsAppConversation.objects.count()

# المحادثات النشطة
active = WhatsAppConversation.objects.filter(status='active').count()

# العملاء المحولين
converted = WhatsAppConversation.objects.filter(status='converted').count()

# معدل التحويل
conversion_rate = (converted / total) * 100 if total > 0 else 0

print(f"معدل التحويل: {conversion_rate:.1f}%")
```

---

## 🔧 استكشاف الأخطاء

### المشكلة: الـ AI لا يرد
- تأكد من OpenAI API Key صحيح
- تحقق من رصيد OpenAI
- راجع logs في n8n

### المشكلة: WhatsApp لا يرسل
- تأكد من WhatsApp Token صالح
- تحقق من Webhook URL
- راجع WhatsApp Dashboard

### المشكلة: العملاء لا يسجلون في CRM
- تأكد من تفعيل "إنشاء عميل تلقائياً"
- تحقق من احتمالية التحويل (يجب أن تكون >= 0.5)
- راجع logs في ERP

---

## 🌐 API Endpoints المتاحة

| Endpoint | Method | الوصف |
|----------|--------|-------|
| `/api/whatsapp-ai/webhook/whatsapp/` | POST | استقبال رسائل WhatsApp |
| `/api/whatsapp-ai/webhook/n8n-callback/` | POST | استقبال تحليل AI من n8n |
| `/api/whatsapp-ai/ai/context/` | GET | جلب معلومات المنتجات للـ AI |
| `/api/whatsapp-ai/sync/products/` | POST | مزامنة المنتجات |
| `/api/whatsapp-ai/conversations/` | GET | عرض المحادثات |
| `/api/whatsapp-ai/products-knowledge/` | GET | قاعدة معرفة المنتجات |

---

## 💡 نصائح للنجاح

1. **اختبر جيداً** قبل الإطلاق
2. **راقب المحادثات** الأولى يدوياً
3. **حسّن System Prompt** بناءً على النتائج
4. **أضف أسئلة شائعة** للمنتجات
5. **تابع معدل التحويل** واضبط الإعدادات

---

## 🎯 الخطوات التالية

بعد الإعداد الأساسي، يمكنك:
- ✅ إضافة ردود تلقائية لساعات العمل
- ✅ إرسال عروض تسويقية للعملاء
- ✅ إنشاء تقارير تحليلية
- ✅ ربط مع أنظمة الشحن
- ✅ إضافة payment links في الردود

---

## 📞 الدعم

إذا واجهت أي مشكلة:
1. راجع الـ logs في `/var/log/tony_erp/`
2. تحقق من n8n execution logs
3. راجع WhatsApp Business Dashboard

---

**🎉 مبروك! نظامك جاهز للعمل الآن!**
