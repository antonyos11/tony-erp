# 🔧 دليل الصيانة والتطوير

## 📋 الملفات الرئيسية

### خدمات التسعير
```
showrooms/
├── models.py                    # ShowroomPricingRule Model
├── services/
│   ├── __init__.py
│   └── pricing_service.py       # ShowroomPricingService
└── admin.py                     # ShowroomPricingRuleAdmin UI
```

### خدمات الإنتاج
```
production/
├── services/
│   └── auto_order_service.py    # AutoProductionOrderService
└── (signals activated in pos/signals.py)
```

### خدمات الرسائل
```
notifications/
├── messaging_service.py         # AutoMessagingService
├── services.py                  # Helper functions
└── models.py                    # Notification Model
```

### الإعدادات والاختبارات
```
config/
└── auto_features_settings.py    # Central Configuration

tests/
└── tests_auto_features.py       # 11 Unit Tests
```

---

## 🔍 المفاهيم الأساسية

### 1. ShowroomPricingRule
**الموقع:** `showrooms/models.py`

```python
# الحقول الرئيسية:
- showroom: ForeignKey
- product: ForeignKey
- adjustment_type: choice (fixed, percentage, markup, discount)
- adjustment_value: Decimal
- valid_from: datetime
- valid_until: datetime
- created_by: User
```

### 2. ShowroomPricingService
**الموقع:** `showrooms/services/pricing_service.py`

```python
# الدوال الرئيسية:
- get_product_price(product_id, showroom_id, quantity)
- bulk_get_prices(products, showroom_id)
- create_pricing_rule(data)
- bulk_create_pricing_rules(rules)
```

### 3. AutoProductionOrderService
**الموقع:** `production/services/auto_order_service.py`

```python
# الدوال الرئيسية:
- check_and_create_order(product, quantity, showroom, ...)
- check_stock_availability(product, location)
- estimate_delivery_date(product)
- calculate_production_quantity(required, min_stock)
```

### 4. AutoMessagingService
**الموقع:** `notifications/messaging_service.py`

```python
# الدوال الرئيسية:
- send_message(phone, message, channel, ...)
- send_order_confirmation(pos_order)
- send_production_ready(production_order)
- send_payment_reminder(installment)

# القنوات المدعومة:
- SMS (via Twilio)
- WhatsApp (via Twilio)
- Internal Notifications
```

---

## 🧪 الاختبارات

### تشغيل جميع الاختبارات
```bash
cd /var/www/tony_erp
python3 manage.py test tests.tests_auto_features -v 2
```

### تشغيل اختبار واحد
```bash
python3 manage.py test tests.tests_auto_features.ShowroomPricingTests.test_fixed_price_rule -v 2
```

### مثال من الاختبار
```python
def test_fixed_price_rule(self):
    """اختبار قاعدة السعر الثابت"""
    # الخطوة 1: إنشاء بيانات تجريبية
    showroom = Showroom.objects.create(...)
    product = Product.objects.create(...)
    
    # الخطوة 2: إنشاء قاعدة سعر
    rule = ShowroomPricingRule.objects.create(
        showroom=showroom,
        product=product,
        adjustment_type='fixed',
        adjustment_value=100.00
    )
    
    # الخطوة 3: الحصول على السعر
    service = ShowroomPricingService()
    price = service.get_product_price(product.id, showroom.id)
    
    # الخطوة 4: التحقق
    self.assertEqual(price, 100.00)
```

---

## 📝 كيفية إضافة ميزة جديدة

### 1. إضافة قالب رسالة جديد

**ملف:** `notifications/messaging_service.py`

```python
TEMPLATES = {
    'new_template': {
        'ar': 'نص عربي {variable}',
        'en': 'English text {variable}',
        'whatsapp': True,
        'sms': True,
        'category': 'orders'
    }
}
```

### 2. إضافة نوع تسعير جديد

**ملف:** `showrooms/models.py`

```python
ADJUSTMENT_TYPES = [
    ('fixed', 'سعر ثابت'),
    ('percentage', 'نسبة مئوية'),
    ('markup', 'هامش'),
    ('discount', 'خصم'),
    ('custom', 'مخصص'),  # نوع جديد
]
```

ثم في `ShowroomPricingService`:

```python
@staticmethod
def _apply_custom_adjustment(base_price, rule):
    """تطبيق تسعير مخصص"""
    # منطق التسعير الخاص بك
    return calculated_price
```

---

## 🔄 التكامل مع الأنظمة الأخرى

### تكامل POS
```python
# ملف: pos/signals.py
@receiver(post_save, sender=POSOrder)
def check_production_on_pos_order(sender, instance, created, **kwargs):
    # 1. فحص المخزون
    # 2. إنشاء أوامر إنتاج
    # 3. إرسال رسائل العملاء
```

### تكامل Production
```python
# عند انتهاء الإنتاج:
production_order.status = 'completed'
production_order.save()

# سيتم تلقائياً:
# 1. إرسال إشعار
# 2. تحديث المخزون
# 3. إبلاغ العملاء
```

---

## 🐛 استكشاف الأخطاء

### المشكلة: الأسعار لا تُحسب بشكل صحيح

**الحل:**
1. تحقق من وجود قاعدة سعر نشطة:
```python
from showrooms.models import ShowroomPricingRule
rules = ShowroomPricingRule.objects.filter(
    showroom=showroom,
    product=product,
    valid_from__lte=now,
    valid_until__gte=now
)
```

2. تحقق من النوع والقيمة:
```python
for rule in rules:
    print(f"Type: {rule.adjustment_type}")
    print(f"Value: {rule.adjustment_value}")
```

### المشكلة: الرسائل لا تُرسل

**الحل:**
1. تحقق من الإعدادات:
```python
from django.conf import settings
print(settings.AUTO_MESSAGING_SETTINGS)
```

2. تحقق من بيانات Twilio:
```python
from notifications.messaging_service import AutoMessagingService
result = AutoMessagingService.is_enabled('sms')
print(f"SMS Enabled: {result}")
```

3. شغّل الاختبار:
```bash
python3 manage.py test tests.tests_auto_features.MessagingServiceTests -v 2
```

### المشكلة: أوامر الإنتاج لا تُنشأ تلقائياً

**الحل:**
1. تحقق من الإعدادات:
```python
from django.conf import settings
print(settings.AUTO_PRODUCTION_SETTINGS['ENABLED'])
```

2. تحقق من السجلات:
```bash
tail -f logs/django.log | grep production
```

3. اختبر يدويأً:
```python
from production.services.auto_order_service import AutoProductionOrderService
result = AutoProductionOrderService.check_and_create_order(
    product=product,
    quantity=10,
    showroom=showroom,
    location=location
)
print(result)
```

---

## 📈 المراقبة والتقارير

### عدد القواعس السعرية
```python
from showrooms.models import ShowroomPricingRule
total = ShowroomPricingRule.objects.count()
by_showroom = ShowroomPricingRule.objects.values('showroom').annotate(
    count=Count('id')
)
```

### أوامر الإنتاج المُنشأة تلقائياً
```python
from production.models import ProductionOrder
auto_orders = ProductionOrder.objects.filter(
    reference__startswith='POS-'
).count()
```

### الرسائل المُرسلة
```python
from notifications.models import Notification
total = Notification.objects.count()
by_level = Notification.objects.values('level').annotate(
    count=Count('id')
)
```

---

## 🔐 أمان البيانات

### حماية بيانات Twilio
```python
# لا تخزن بيانات Twilio في الكود
# استخدم environment variables:

import os
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
```

### Permissions التسعير
```python
# المستخدم يجب أن يكون من موظفي المعرض
# أضيفت حماية تلقائية:

created_by = request.user  # يُضاف تلقائياً
```

---

## 📊 أفضل الممارسات

1. **استخدم الخدمات مباشرة**
   ```python
   from showrooms.services.pricing_service import ShowroomPricingService
   # ❌ لا تستعلم المتغيرات مباشرة
   # ✅ استخدم الخدمة
   ```

2. **اختبر التغييرات**
   ```bash
   python3 manage.py test tests.tests_auto_features -v 2
   ```

3. **وثّق التغييرات**
   - أضف docstrings
   - أضف تعليقات للمنطق المعقد

4. **تحقق من الأداء**
   - استخدم `select_related`/`prefetch_related`
   - تجنب queries في حلقات

---

## 📚 مراجع إضافية

- [Django Signals Documentation](https://docs.djangoproject.com/en/stable/topics/signals/)
- [DRF Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [Twilio Python SDK](https://www.twilio.com/docs/python/install)

---

**آخر تحديث:** 2026-01-05
