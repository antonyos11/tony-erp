# 🤖 WhatsApp AI Integration - نظام متكامل

## نظرة عامة

نظام ذكي يربط **WhatsApp Business** مع **الذكاء الصناعي (OpenAI)** و **Tony ERP** باستخدام **n8n**، لـ:

✅ الرد التلقائي على العملاء بذكاء
✅ تسجيل العملاء تلقائياً في CRM
✅ تتبع المحادثات والاهتمامات
✅ إنشاء فرص بيع تلقائياً

---

## 🎯 الميزات الرئيسية

### 1. الذكاء الصناعي
- رد تلقائي ذكي على رسائل العملاء
- فهم النوايا (شراء، استفسار، شكوى)
- تحليل المشاعر (إيجابي، سلبي، محايد)
- معرفة تفصيلية بكل المنتجات

### 2. تكامل CRM
- تسجيل عميل جديد تلقائياً
- حفظ الاهتمامات والمنتجات المطلوبة
- إنشاء فرصة بيع مع احتمالية
- تتبع كل التفاعلات

### 3. إدارة المحادثات
- حفظ كل الرسائل والمحادثات
- تحليل شامل لكل محادثة
- معرفة احتمالية التحويل
- تقارير وإحصائيات

### 4. قاعدة معرفة المنتجات
- معلومات تفصيلية عن كل منتج
- أسئلة شائعة مع الإجابات
- كلمات مفتاحية ذكية
- مزامنة تلقائية من المخزون

---

## 🛠️ البنية التقنية

```
┌─────────────────┐
│   WhatsApp      │
│   العميل        │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  WhatsApp       │
│  Business API   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│      n8n        │
│   Workflow      │
├─────────────────┤
│ 1. استقبال     │
│ 2. حفظ في ERP  │
│ 3. جلب منتجات  │
│ 4. معالجة AI   │
│ 5. تحليل       │
│ 6. تسجيل CRM   │
│ 7. إرسال رد    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   Tony ERP      │
│   + CRM         │
└─────────────────┘
```

---

## 📦 المكونات

### Backend (Django)
- **Models**: 4 نماذج (محادثات، رسائل، منتجات، إعدادات)
- **APIs**: 9 endpoints
- **Admin**: واجهة إدارة كاملة
- **Serializers**: معالجة البيانات
- **Views**: منطق العمل

### n8n Workflow
- استقبال رسائل WhatsApp
- معالجة بالذكاء الصناعي
- تحليل تلقائي
- إرسال الردود

### قاعدة البيانات
- محادثات الواتساب
- الرسائل
- قاعدة معرفة المنتجات
- إعدادات النظام

---

## 🚀 البدء

### 1. المتطلبات
- Django (مثبت مسبقاً)
- WhatsApp Business API Token
- OpenAI API Key
- n8n Instance

### 2. الإعداد
```bash
# Migrations (تم تطبيقها)
python manage.py migrate whatsapp_ai

# إضافة إعدادات في Admin
/admin/whatsapp_ai/whatsappconfiguration/add/

# مزامنة المنتجات
python manage.py shell
>>> from whatsapp_ai.views import sync_products
```

### 3. استيراد Workflow
- افتح n8n
- استورد: `n8n_workflows/whatsapp_ai_workflow.json`
- أضف Environment Variables

---

## 📚 الوثائق

| ملف | الوصف |
|-----|-------|
| [WHATSAPP_AI_SETUP_GUIDE.md](WHATSAPP_AI_SETUP_GUIDE.md) | دليل الإعداد الكامل والتفصيلي |
| [WHATSAPP_AI_QUICK_START.md](WHATSAPP_AI_QUICK_START.md) | البدء السريع في 5 دقائق |
| [WHATSAPP_AI_SUMMARY.md](WHATSAPP_AI_SUMMARY.md) | ملخص شامل للنظام |
| [whatsapp_ai_examples.py](whatsapp_ai_examples.py) | 10 أمثلة برمجية |

---

## 🔗 API Endpoints

### جلب معلومات للـ AI
```
GET /api/whatsapp-ai/ai/context/
```

### استقبال رسالة WhatsApp
```
POST /api/whatsapp-ai/webhook/whatsapp/
{
  "from_number": "+966501234567",
  "message_id": "msg_123",
  "text_body": "عندكم مراتب؟",
  "customer_name": "أحمد"
}
```

### استقبال نتيجة AI
```
POST /api/whatsapp-ai/webhook/n8n-callback/
{
  "conversation_id": 1,
  "ai_response": "نعم، لدينا...",
  "intent": "inquiry",
  "products": ["مرتبة سليب كومفورت"],
  "sentiment": "positive",
  "conversion_score": 0.7
}
```

### البحث في المنتجات
```
GET /api/whatsapp-ai/products-knowledge/search/?q=مرتبة
```

### عرض المحادثات
```
GET /api/whatsapp-ai/conversations/
GET /api/whatsapp-ai/conversations/?status=active
```

### تحويل لعميل CRM
```
POST /api/whatsapp-ai/conversations/{id}/convert_to_customer/
```

---

## 🎨 أمثلة

### استفسار بسيط
```
العميل: السلام عليكم
AI: وعليكم السلام! كيف يمكنني مساعدتك اليوم؟

→ تسجيل: محادثة جديدة، احتمالية 30%
```

### استفسار مع اهتمام
```
العميل: عندكم مراتب طبية؟
AI: نعم! لدينا مراتب طبية ممتازة:
    1. سليب كومفورت - 2500 ج.م
    2. أورثو ميديكال - 3200 ج.م
    أيهما يناسبك؟

→ تسجيل: منتجات مهتم بها، احتمالية 60%
```

### نية شراء
```
العميل: أبغى مرتبة سليب كومفورت مقاس كينج
AI: ممتاز! مرتبة سليب كومفورت مقاس كينج متوفرة.
    السعر: 2500 ج.م
    هل تريد إتمام الطلب؟

→ تسجيل: احتمالية 90%
→ إنشاء: عميل CRM + فرصة بيع تلقائياً! ✨
```

---

## 📊 Admin Panel

### المحادثات
```
/admin/whatsapp_ai/whatsappconversation/

- عرض كل المحادثات
- فلترة حسب الحالة
- رؤية احتمالية الشراء
- تحويل يدوي لـ CRM
```

### الرسائل
```
/admin/whatsapp_ai/whatsappmessage/

- كل الرسائل الواردة والصادرة
- تحليل النوايا
- الكيانات المستخرجة
```

### قاعدة المعرفة
```
/admin/whatsapp_ai/productknowledgebase/

- إضافة منتجات يدوياً
- مزامنة من المخزون
- إضافة أسئلة شائعة
- تعديل الكلمات المفتاحية
```

### الإعدادات
```
/admin/whatsapp_ai/whatsappconfiguration/

- WhatsApp API Settings
- OpenAI Settings
- System Prompt
- CRM Auto-creation
- Business Hours
```

---

## 🧪 الاختبار

### اختبار سريع
```bash
./test_whatsapp_ai.sh
```

### اختبار يدوي
```bash
curl -X POST http://localhost:8000/api/whatsapp-ai/webhook/whatsapp/ \
  -H "Content-Type: application/json" \
  -d '{
    "from_number": "+966501234567",
    "message_id": "test_123",
    "text_body": "عندكم مراتب؟"
  }'
```

---

## 🔐 الأمان

- ✅ Token Authentication
- ✅ CSRF Protection
- ✅ Webhook Verification
- ✅ Encrypted API Keys
- ✅ Permission Classes

---

## 📈 الإحصائيات

يمكنك الحصول على:
- إجمالي المحادثات
- المحادثات النشطة
- معدل التحويل
- المنتجات الأكثر طلباً
- احتمالية الشراء المتوسطة

```python
from whatsapp_ai.models import WhatsAppConversation

total = WhatsAppConversation.objects.count()
active = WhatsAppConversation.objects.filter(status='active').count()
converted = WhatsAppConversation.objects.filter(status='converted').count()

conversion_rate = (converted / total) * 100 if total > 0 else 0
print(f"معدل التحويل: {conversion_rate:.1f}%")
```

---

## 🎯 الخطوات التالية

1. ✅ أضف WhatsApp Business API Token
2. ✅ أضف OpenAI API Key
3. ✅ زامن المنتجات من المخزون
4. ✅ استورد Workflow في n8n
5. ✅ اختبر برسالة حقيقية
6. ✅ راقب النتائج في CRM

---

## 💬 أمثلة برمجية

راجع [whatsapp_ai_examples.py](whatsapp_ai_examples.py) لـ:
- جلب context للـ AI
- إرسال رسائل
- البحث في المنتجات
- عرض المحادثات
- تحويل لعميل CRM
- سيناريو كامل

---

## 🌟 الميزات المتقدمة

- ساعات العمل
- رسائل خارج أوقات العمل
- تحليل المشاعر
- استخراج الكيانات
- تصنيف النوايا
- احتمالية التحويل
- ملخص المحادثات تلقائياً

---

## 📝 الترخيص

جزء من نظام Tony ERP

---

## 🤝 المساهمة

النظام جاهز ويعمل. يمكن تخصيصه حسب الحاجة.

---

**مبروك! النظام جاهز 100% 🎉**

ابدأ الآن باستقبال العملاء عبر WhatsApp تلقائياً! 🚀
