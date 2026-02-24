# Smart Pricing - التسعير الذكي بالذكاء الاصطناعي

## 🎯 نظرة عامة

نظام تسعير ذكي مدعوم بالذكاء الاصطناعي يقوم تلقائياً بـ:
- ✅ تسعير المنتجات المخصصة حسب المواصفات
- ✅ حساب التكاليف بدقة (مواد خام + عمالة + إضافية)
- ✅ إنشاء عروض أسعار فورية
- ✅ ترشيح أفضل خط إنتاج بالذكاء الاصطناعي
- ✅ صرف المواد الخام آلياً من المستودع

---

## 📋 المكونات الرئيسية

### 1. PricingRule - قاعدة التسعير
قاعدة قابلة للتخصيص تحدد كيفية حساب السعر

**الخصائص:**
- طريقة التسعير: ثابت، تكلفة+هامش، حسب السوق، AI ديناميكي
- معاملات الحجم: صغير (0.8)، متوسط (1.0)، كبير (1.3)، ضخم (1.6)
- معاملات التعقيد: بسيط (1.0)، متوسط (1.2)، معقد (1.5)
- هامش الربح: أدنى، مستهدف، أقصى
- خصم كمية: حد الخصم ونسبته

**مثال:**
```python
rule = PricingRule.objects.create(
    name="قاعدة الأثاث المخصص",
    method="ai_dynamic",
    target_profit_margin=25.0,
    quantity_discount_threshold=100,
    quantity_discount_rate=5.0,
    use_ai_pricing=True
)
```

---

### 2. SmartQuote - عرض السعر الذكي
عرض سعر يُحسب تلقائياً بناءً على المواصفات

**المواصفات:**
- اسم المنتج ووصفه
- الكمية المطلوبة
- المقاس: small, medium, large, xlarge
- التعقيد: simple, medium, complex
- الأبعاد (اختياري): عرض، طول، عمق، وزن

**التسعير:**
- تكلفة المواد الخام (تلقائي أو يدوي)
- تكلفة العمالة (30% من المواد افتراضياً)
- تكاليف إضافية (15% افتراضياً)
- هامش الربح (من القاعدة)
- خصم الكمية (تلقائي)

**مثال:**
```python
from smart_pricing.models import SmartQuote, PricingRule

# إنشاء عرض سعر
quote = SmartQuote.objects.create(
    customer=customer,
    product_name="طاولة خشبية مخصصة",
    description="طاولة 6 مقاعد، خشب زان",
    quantity=50,
    size="large",
    complexity="medium",
    width=200.00,  # cm
    height=90.00,
    depth=100.00,
    pricing_rule=rule
)

# حساب السعر تلقائياً
quote.calculate_price()

print(f"التكلفة الإجمالية: {quote.total_cost} ج.م")
print(f"سعر الوحدة: {quote.unit_price} ج.م")
print(f"السعر الإجمالي: {quote.total_price} ج.م")
print(f"الخصم: {quote.quantity_discount}%")
print(f"السعر النهائي: {quote.final_price} ج.م")
```

---

### 3. ProductionLineAI - محرك الذكاء الاصطناعي

يرشح أفضل خط إنتاج بناءً على:
- التكلفة المتوقعة
- الوقت المطلوب
- السعة المتاحة
- جودة الإنتاج (من السجل التاريخي)

**معايير التقييم:**
- درجة التكلفة (40%)
- درجة الوقت (30%)
- مطابقة السعة (20%)
- درجة الجودة (10%)

**مثال:**
```python
from smart_pricing.ai_engine import auto_recommend_production_line

# ترشيح أفضل 3 خطوط إنتاج
recommendations = auto_recommend_production_line(quote)

# أفضل خط
best = recommendations[0]
print(f"الخط المُرشح: {best.work_center.name}")
print(f"التكلفة المتوقعة: {best.estimated_cost} ج.م")
print(f"الوقت المتوقع: {best.estimated_time} ساعة")
print(f"مطابقة السعة: {best.capacity_match}%")
print(f"درجة الجودة: {best.quality_score}/100")
print(f"درجة الترشيح: {best.recommendation_score}/100")
print(f"ملاحظات: {best.notes}")

# استخدام الخط المُرشح
production_order.work_center = best.work_center
production_order.save()
```

---

### 4. AutoMaterialRelease - صرف المواد الآلي

يُنشأ تلقائياً عند الموافقة على أمر إنتاج

**الميزات:**
- تحديد المواد المطلوبة تلقائياً
- حساب الكميات من BOM
- صرف من المستودع المحدد
- تسجيل التكاليف

**مثال:**
```python
from smart_pricing.models import AutoMaterialRelease

# إنشاء أمر صرف آلي
release = AutoMaterialRelease.objects.create(
    production_order=order,
    warehouse=warehouse,
    auto_generated=True,
    status='pending'
)

# إضافة المواد
from smart_pricing.models import MaterialReleaseItem
MaterialReleaseItem.objects.create(
    release=release,
    material=material,
    required_quantity=100.0,
    unit_cost=10.00
)

# الموافقة والصرف
release.status = 'approved'
release.save()

# تنفيذ الصرف
release.status = 'released'
release.released_at = timezone.now()
release.released_by = user
release.save()
```

---

## 🔌 REST API

### Endpoints

```
GET    /api/smart-pricing/rules/           # قائمة قواعد التسعير
POST   /api/smart-pricing/rules/           # إنشاء قاعدة
GET    /api/smart-pricing/rules/:id/       # تفاصيل قاعدة

GET    /api/smart-pricing/quotes/          # قائمة عروض الأسعار
POST   /api/smart-pricing/quotes/          # إنشاء عرض سعر
GET    /api/smart-pricing/quotes/:id/      # تفاصيل عرض
POST   /api/smart-pricing/quotes/:id/calculate/   # حساب السعر

GET    /api/smart-pricing/recommendations/ # ترشيحات خطوط الإنتاج
POST   /api/smart-pricing/recommendations/recommend/  # ترشيح تلقائي

GET    /api/smart-pricing/releases/        # أوامر الصرف
POST   /api/smart-pricing/releases/:id/approve/      # الموافقة
POST   /api/smart-pricing/releases/:id/execute/      # التنفيذ
```

### مثال API

```bash
# إنشاء عرض سعر
curl -X POST http://localhost:8000/api/smart-pricing/quotes/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer": 1,
    "product_name": "طاولة خشبية",
    "quantity": 50,
    "size": "large",
    "complexity": "medium",
    "pricing_rule": 1
  }'

# حساب السعر
curl -X POST http://localhost:8000/api/smart-pricing/quotes/1/calculate/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# ترشيح خط الإنتاج
curl -X POST http://localhost:8000/api/smart-pricing/recommendations/recommend/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"quote_id": 1}'
```

---

## 🎨 لوحة الإدارة

### الوصول
```
http://localhost:8000/admin/smart_pricing/
```

### الإجراءات المتاحة (Bulk Actions)
1. **حساب الأسعار تلقائياً** - لعروض الأسعار المحددة
2. **ترشيح خطوط الإنتاج** - بالذكاء الاصطناعي

---

## ⚙️ الإعداد

### 1. إضافة للـ INSTALLED_APPS
```python
# settings.py
INSTALLED_APPS = [
    # ...
    'smart_pricing',
]
```

### 2. تشغيل Migrations
```bash
python manage.py makemigrations smart_pricing
python manage.py migrate smart_pricing
```

### 3. إنشاء قاعدة تسعير افتراضية
```python
python manage.py shell

from smart_pricing.models import PricingRule
PricingRule.objects.create(
    name="قاعدة عامة",
    method="cost_plus",
    target_profit_margin=25.0,
    quantity_discount_threshold=50,
    quantity_discount_rate=5.0,
    is_active=True
)
```

---

## 🧪 الاختبار

```python
# tests/test_smart_pricing.py
from django.test import TestCase
from smart_pricing.models import SmartQuote, PricingRule

class SmartQuoteTestCase(TestCase):
    def setUp(self):
        self.rule = PricingRule.objects.create(
            name="Test Rule",
            method="cost_plus",
            target_profit_margin=25.0
        )
    
    def test_calculate_price(self):
        quote = SmartQuote.objects.create(
            product_name="Test Product",
            quantity=100,
            size="medium",
            complexity="simple",
            pricing_rule=self.rule
        )
        
        result = quote.calculate_price()
        
        self.assertTrue(result)
        self.assertGreater(quote.final_price, 0)
        self.assertEqual(quote.status, 'ready')
```

---

## 📊 سيناريو كامل

```python
from smart_pricing.models import PricingRule, SmartQuote
from smart_pricing.ai_engine import auto_recommend_production_line
from crm.models import Customer

# 1. إعداد قاعدة التسعير
rule = PricingRule.objects.create(
    name="قاعدة الأثاث الفاخر",
    method="ai_dynamic",
    target_profit_margin=30.0,
    quantity_discount_threshold=20,
    quantity_discount_rate=10.0,
    use_ai_pricing=True
)

# 2. عميل يطلب عرض سعر
customer = Customer.objects.get(name="شركة المثال")

# 3. إنشاء عرض سعر
quote = SmartQuote.objects.create(
    customer=customer,
    product_name="طاولة اجتماعات فاخرة",
    description="طاولة 12 مقعد، خشب ماهوجني، تشطيب لامع",
    quantity=25,
    size="xlarge",
    complexity="complex",
    width=400.00,
    height=80.00,
    depth=150.00,
    pricing_rule=rule
)

# 4. حساب السعر تلقائياً
quote.calculate_price()

print(f"""
عرض السعر: {quote.quote_number}
المنتج: {quote.product_name}
الكمية: {quote.quantity}
---
تكلفة المواد: {quote.raw_material_cost} ج.م
تكلفة العمالة: {quote.labor_cost} ج.م
تكاليف إضافية: {quote.overhead_cost} ج.م
التكلفة الإجمالية: {quote.total_cost} ج.م
هامش الربح: {quote.profit_margin}%
السعر قبل الخصم: {quote.total_price} ج.م
خصم الكمية: {quote.quantity_discount}%
السعر النهائي: {quote.final_price} ج.م
""")

# 5. ترشيح أفضل خط إنتاج
recommendations = auto_recommend_production_line(quote)

print("\nخطوط الإنتاج المُرشحة:")
for i, rec in enumerate(recommendations, 1):
    print(f"""
{i}. {rec.work_center.name}
   التكلفة: {rec.estimated_cost} ج.م
   الوقت: {rec.estimated_time} ساعة
   السعة: {rec.capacity_match}%
   الجودة: {rec.quality_score}/100
   الدرجة: {rec.recommendation_score}/100
   {rec.notes}
""")

# 6. اختيار الخط الأفضل
best_line = recommendations[0].work_center

# 7. إرسال العرض للعميل
quote.status = 'sent'
quote.save()
```

---

## 🎯 الفوائد

1. **توفير الوقت:** حساب تلقائي بدلاً من الحساب اليدوي
2. **دقة أعلى:** معادلات محسوبة بدقة
3. **قرارات ذكية:** اختيار خط الإنتاج الأمثل
4. **أتمتة كاملة:** من العرض إلى صرف المواد
5. **مرونة:** قواعد قابلة للتخصيص لكل فئة منتجات

---

## 📝 ملاحظات

- يمكن تخصيص معاملات الحساب لكل قاعدة
- يدعم حساب السعر يدوياً أو تلقائياً
- يحفظ سجل كامل للترشيحات
- يتكامل مع نظام الإنتاج والمخزون

---

**📅 آخر تحديث:** 4 يناير 2026  
**📖 الإصدار:** 1.0.0
