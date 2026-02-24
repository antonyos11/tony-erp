# دليل الميزات الجديدة للنظام
# NEW FEATURES IMPLEMENTATION GUIDE

## نظرة عامة | Overview

تم إضافة **9 ميزات enterprise** احترافية شاملة للنظام:

### ✅ الميزات المكتملة | Completed Features

1. **نظام الوعد الذكي بالتسليم** - Smart Delivery Promise System
2. **نظام التتبع والاستدعاء** - Product Traceability & Recall System
3. **تحليل نقطة التعادل** - Break-Even Analysis System
4. **تقييم الموردين** - Supplier Evaluation & Rating System
5. **لوحة القيادة التنفيذية** - Executive Decision Cockpit
6. **منع الخسائر السعرية** - Loss Prevention & Price Validation
7. **API الموبايل** - Mobile API Layer
8. **نظام العلامة البيضاء** - White Label System (Multi-Tenancy)
9. **الكشف عن الشذوذات والتنبيهات الاستباقية** - Anomaly Detection & Proactive Alerts

---

## 1. نظام الوعد الذكي بالتسليم
**Smart Delivery Promise System**

### الموقع
```
production/services/delivery_promise.py
```

### الوصف
يحسب تاريخ التسليم المتوقع بناءً على:
- توفر المخزون
- سعة الإنتاج
- حمل مراكز العمل
- أولوية العميل (VIP)

### الاستخدام
```python
from production.services.delivery_promise import delivery_calculator

# حساب وعد التسليم لمنتج واحد
promise = delivery_calculator.calculate_promise(
    product_id=1,
    quantity=100,
    customer_priority='vip'
)

print(f"تاريخ التسليم المتوقع: {promise['delivery_date']}")
print(f"المصدر: {promise['source']}")  # 'stock' أو 'production'

# حساب جماعي
products = [
    {'product_id': 1, 'quantity': 100},
    {'product_id': 2, 'quantity': 50}
]
promises = delivery_calculator.bulk_calculate(products)
```

### المعادلات
- **إذا كان المخزون كافي**: `delivery_date = today + 1 day`
- **إذا احتاج إنتاج**: `delivery_date = today + production_time + safety_margin`
- **أولوية VIP**: تقليل 20% من الوقت

---

## 2. نظام التتبع والاستدعاء
**Product Traceability & Recall System**

### الموقع
```
quality_control/traceability.py
```

### الوصف
تتبع كامل من المواد الخام إلى العميل النهائي:
- تتبع رقم الدفعة (Batch)
- تتبع المورد
- تتبع الإنتاج
- تتبع المبيعات
- نظام استدعاء المنتجات

### الاستخدام
```python
from quality_control.traceability import traceability_service

# إنشاء تتبع من عملية شراء
traceability_service.create_trace_from_purchase(
    purchase_bill_id=1,
    batch_number='BATCH-2024-001'
)

# إنشاء تتبع من عملية إنتاج
traceability_service.create_trace_from_production(
    production_order_id=1,
    batch_number='PROD-2024-001'
)

# تتبع رحلة المنتج الكاملة
journey = traceability_service.trace_product_journey(
    product_id=1,
    batch_number='BATCH-2024-001'
)

# إنشاء أمر استدعاء
recall = traceability_service.create_recall_order(
    product_id=1,
    batch_number='BATCH-2024-001',
    reason='مشكلة جودة',
    severity='high'
)
```

### Models
- `ProductTraceability`: سجل التتبع
- `RecallOrder`: أمر الاستدعاء
- `RecallItem`: بنود الاستدعاء

---

## 3. تحليل نقطة التعادل
**Break-Even Analysis System**

### الموقع
```
accounting/break_even.py
```

### الوصف
تحليل شامل لنقطة التعادل:
- تحليل على مستوى المنتج
- تحليل على مستوى مركز التكلفة
- تحليل على مستوى الشركة
- تحليل متعدد المنتجات

### الاستخدام
```python
from accounting.break_even import breakeven_analyzer

# تحليل منتج واحد
result = breakeven_analyzer.calculate_product_breakeven(
    product_id=1,
    selling_price=100
)

print(f"نقطة التعادل: {result['breakeven_units']} وحدة")
print(f"التكلفة المتغيرة: {result['variable_cost_per_unit']}")
print(f"التكلفة الثابتة: {result['fixed_costs']}")
print(f"هامش المساهمة: {result['contribution_margin']}")

# تحليل مركز تكلفة
cc_result = breakeven_analyzer.calculate_cost_center_breakeven(
    cost_center_id=1,
    period_months=12
)

# تحليل الشركة كاملة
company_result = breakeven_analyzer.calculate_company_breakeven(
    period_months=12
)
```

### المعادلات
```
Contribution Margin = Selling Price - Variable Cost
Break-Even Units = Fixed Costs / Contribution Margin
Break-Even Revenue = Break-Even Units × Selling Price
Safety Margin = (Current Sales - Break-Even Sales) / Current Sales × 100%
```

---

## 4. تقييم الموردين
**Supplier Evaluation & Rating System**

### الموقع
```
purchases/supplier_evaluation.py
```

### الوصف
تقييم تلقائي للموردين بناءً على:
- الأسعار (40%)
- الجودة (40%)
- التسليم (20%)
- نظام تصنيف A-F

### الاستخدام
```python
from purchases.supplier_evaluation import supplier_evaluation_service

# تقييم تلقائي
evaluation = supplier_evaluation_service.auto_evaluate_supplier(
    supplier_id=1,
    evaluation_period_months=6
)

print(f"التقييم النهائي: {evaluation.overall_score}/100")
print(f"التصنيف: {evaluation.grade}")

# اقتراح مورد بديل
alternative = supplier_evaluation_service.suggest_alternative_supplier(
    current_supplier_id=1,
    product_id=1
)

if alternative:
    print(f"المورد البديل: {alternative['supplier'].name}")
    print(f"نسبة التحسين: {alternative['improvement']}")
```

### معايير التقييم
- **A** (90-100): ممتاز
- **B** (80-89): جيد جداً
- **C** (70-79): جيد
- **D** (60-69): مقبول
- **F** (<60): ضعيف

---

## 5. لوحة القيادة التنفيذية
**Executive Decision Cockpit**

### الموقع
```
monitoring/executive_dashboard.py
```

### الوصف
ملخص تنفيذي شامل مع:
- نظرة عامة على الأعمال
- KPIs مالية
- مؤشرات تشغيلية
- تحليل المبيعات
- مؤشرات المخزون
- مؤشرات الموارد البشرية
- مؤشرات الجودة
- تنبيهات حرجة
- توصيات استراتيجية

### الاستخدام
```python
from monitoring.executive_dashboard import executive_dashboard

# الحصول على الملخص التنفيذي
summary = executive_dashboard.get_executive_summary(period_months=1)

print(f"الإيرادات: {summary['overview']['total_revenue']}")
print(f"الربح: {summary['overview']['profit']}")
print(f"هامش الربح: {summary['financial_kpis']['profit_margin']}%")
print(f"معدل دوران المخزون: {summary['inventory_kpis']['turnover_ratio']}")

# توليد توصيات استراتيجية
recommendations = executive_dashboard.generate_strategic_recommendations(
    period_months=3
)

for rec in recommendations:
    print(f"- {rec.title}: {rec.description}")
```

---

## 6. منع الخسائر السعرية
**Loss Prevention & Price Validation**

### الموقع
```
smart_pricing/validators.py
```

### الوصف
منع بيع المنتجات بأقل من التكلفة:
- التحقق من السعر مقابل التكلفة
- فرض هامش ربح أدنى
- صلاحيات تجاوز للمدير
- تحليل مخاطر التسعير

### الاستخدام
```python
from smart_pricing.validators import price_validator, loss_prevention_service

# التحقق من سعر بيع
validation = price_validator.validate_selling_price(
    product_id=1,
    selling_price=80,
    quantity=10
)

if not validation['is_valid']:
    print(f"تحذير: {validation['warning']}")
    print(f"الحد الأدنى: {validation['min_acceptable_price']}")
    print(f"السعر الموصى به: {validation['recommended_price']}")

# التحقق الجماعي
items = [
    {'product_id': 1, 'selling_price': 80, 'quantity': 10},
    {'product_id': 2, 'selling_price': 50, 'quantity': 5}
]
bulk_validation = price_validator.validate_bulk_prices(items)

# تحليل مخاطر
risks = loss_prevention_service.analyze_pricing_risks(period_months=3)
```

### القواعد
```
Min Price (No Override) = Cost × 1.05  (هامش 5%)
Min Price (With Override) = Cost × 1.15  (هامش 15%)
Recommended Price = Cost × (1 + Default Markup %)
```

---

## 7. API الموبايل
**Mobile API Layer**

### الموقع
```
api/mobile/
  ├── auth.py          # المصادقة JWT
  ├── dashboard.py     # لوحة التحكم
  ├── pos.py           # نقطة البيع
  ├── inventory.py     # المخزون
  └── production.py    # الإنتاج
```

### Endpoints

#### Authentication
```
POST /api/mobile/auth/login/
POST /api/mobile/auth/logout/
POST /api/mobile/auth/refresh/
GET  /api/mobile/auth/profile/
PUT  /api/mobile/auth/update_profile/
POST /api/mobile/auth/change_password/
```

#### Dashboard
```
GET /api/mobile/dashboard/summary/
GET /api/mobile/dashboard/quick_stats/
```

#### POS
```
GET  /api/mobile/pos/products/
POST /api/mobile/pos/create_sale/
POST /api/mobile/pos/check_stock/
GET  /api/mobile/pos/recent_sales/
```

#### Inventory
```
GET  /api/mobile/inventory/stock_levels/
POST /api/mobile/inventory/adjust_stock/
POST /api/mobile/inventory/physical_count/
POST /api/mobile/inventory/barcode_scan/
```

#### Production
```
GET  /api/mobile/production/active_orders/
GET  /api/mobile/production/order_details/
POST /api/mobile/production/start_production/
POST /api/mobile/production/record_progress/
POST /api/mobile/production/report_issue/
```

### مثال استخدام
```bash
# تسجيل الدخول
curl -X POST http://domain/api/mobile/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Response
{
  "success": true,
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  },
  "user": {...}
}

# استخدام Access Token
curl -X GET http://domain/api/mobile/dashboard/summary/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

---

## 8. نظام العلامة البيضاء
**White Label System (Multi-Tenancy)**

### الموقع
```
core/white_label/
  ├── models.py        # Tenant, TenantBranding, TenantSettings
  ├── middleware.py    # TenantMiddleware
  ├── utils.py         # أدوات مساعدة
  └── admin.py         # لوحة التحكم
```

### الميزات
- تعدد المستأجرين (Multi-Tenancy)
- عزل كامل للبيانات
- تخصيص العلامة التجارية (شعار، ألوان، خطوط)
- إعدادات مخصصة لكل عميل
- دعم نطاقات متعددة
- حدود استخدام قابلة للتخصيص

### Models

#### Tenant
```python
- name, slug, domain
- company_name, tax_id
- subscription_plan, subscription_end
- max_users, max_branches, max_products
- enabled_modules
- timezone, language, currency
```

#### TenantBranding
```python
- logo, logo_dark, favicon
- primary_color, secondary_color, accent_color
- font_family
- app_title, tagline
- login_background
- custom_css, custom_js
```

#### TenantSettings
```python
- invoice_prefix, tax_rate
- allow_negative_stock
- default_markup
- require_po_approval
- email_notifications
- api_enabled
```

### الاستخدام
```python
from core.white_label.utils import get_current_tenant, is_feature_enabled

# الحصول على المستأجر الحالي
tenant = get_current_tenant()

# التحقق من تفعيل ميزة
if is_feature_enabled('production'):
    # تنفيذ كود الإنتاج
    pass

# الحصول على إعداد
setting = get_tenant_setting('invoice_prefix', 'INV')
```

### Middleware Setup
```python
# في settings.py
MIDDLEWARE = [
    ...
    'core.white_label.middleware.TenantMiddleware',
    'core.white_label.middleware.TenantDataIsolationMiddleware',
    'core.white_label.middleware.TenantThemeMiddleware',
    ...
]

TEMPLATES = [{
    'OPTIONS': {
        'context_processors': [
            ...
            'core.white_label.utils.tenant_context_processor',
        ]
    }
}]
```

---

## 9. الكشف عن الشذوذات والتنبيهات الاستباقية
**Anomaly Detection & Proactive Alerts**

### الموقع
```
monitoring/anomaly_detection.py
monitoring/tasks_anomaly.py
monitoring/admin_anomaly.py
```

### الوصف
نظام ذكي يكتشف:
- **الشذوذات**: أنماط غير طبيعية في البيانات
- **التنبيهات الاستباقية**: مشاكل متوقعة قبل حدوثها

### أنواع الشذوذات

#### 1. شذوذات المبيعات
- انخفاض حاد في المبيعات
- مبيعات غير عادية لمنتج معين
- نشاط في توقيت غير معتاد
- تركز عالي على عميل واحد

#### 2. شذوذات المخزون
- تغيرات غير مبررة
- معدل دوران غير طبيعي
- فروقات جرد كبيرة

#### 3. شذوذات الإنتاج
- تأخيرات متكررة
- معدل عيوب مرتفع
- كفاءة منخفضة

#### 4. شذوذات مالية
- نفقات غير عادية
- تدفق نقدي سلبي

### أنواع التحذيرات الاستباقية
- نفاد مخزون متوقع
- حمل زائد متوقع على الإنتاج
- مشكلة تدفق نقدي متوقعة
- خطر فوات موعد
- اتجاه جودة سلبي
- تجاوز تكلفة متوقع

### الاستخدام
```python
from monitoring.anomaly_detection import anomaly_detector, proactive_warner

# تشغيل الكشف عن الشذوذات
results = anomaly_detector.run_all_detections()

for category, alerts in results.items():
    print(f"{category}: {len(alerts)} تنبيه")
    for alert in alerts:
        print(f"  - {alert.title}")

# تشغيل التنبؤات
warnings = proactive_warner.run_all_predictions()

for category, warns in warnings.items():
    print(f"{category}: {len(warns)} تحذير")
    for warning in warns:
        print(f"  - {warning.title}")
        print(f"    التاريخ المتوقع: {warning.predicted_date}")
        print(f"    مستوى الثقة: {warning.confidence_level}%")
```

### Celery Tasks (تلقائي)
```python
# يتم تشغيلها تلقائياً:
- run_anomaly_detection()         # كل ساعة
- run_proactive_predictions()     # كل 6 ساعات
- cleanup_old_alerts()            # يومياً
- send_daily_anomaly_report()     # يومياً 8 صباحاً
```

---

## التكامل والإعداد
**Integration & Setup**

### 1. إضافة إلى INSTALLED_APPS
```python
# في settings.py
INSTALLED_APPS = [
    ...
    'rest_framework',
    'rest_framework_simplejwt',
    'core.white_label',
]
```

### 2. URLs
```python
# في urls.py الرئيسي
urlpatterns = [
    ...
    path('api/mobile/', include('api.mobile.urls')),
]
```

### 3. Migrations
```bash
python manage.py makemigrations quality_control
python manage.py makemigrations purchases
python manage.py makemigrations monitoring
python manage.py makemigrations white_label

python manage.py migrate
```

### 4. Admin Registration
```python
# في monitoring/admin.py
from .admin_anomaly import AnomalyAlertAdmin, ProactiveWarningAdmin

# في core/white_label/admin.py تم التسجيل بالفعل
```

### 5. Celery Setup
```python
# في accountant_pro/celery.py
from celery.schedules import crontab

app.conf.beat_schedule = {
    'anomaly-detection-hourly': {
        'task': 'monitoring.tasks_anomaly.run_anomaly_detection',
        'schedule': crontab(minute=0),
    },
    'proactive-predictions-6h': {
        'task': 'monitoring.tasks_anomaly.run_proactive_predictions',
        'schedule': crontab(minute=0, hour='*/6'),
    },
}
```

---

## الأداء والتحسين
**Performance & Optimization**

### 1. Database Indexes
تم إضافة indexes على:
- `anomaly_alerts`: (category, severity, status), (detected_at)
- `tenant`: (slug), (domain)
- `tenant_domains`: (domain)

### 2. Query Optimization
- استخدام `select_related()` و `prefetch_related()`
- Aggregation في قاعدة البيانات
- حد أقصى للنتائج في الحلقات

### 3. Caching (موصى به)
```python
from django.core.cache import cache

# Cache للملخص التنفيذي
summary = cache.get('executive_summary')
if not summary:
    summary = executive_dashboard.get_executive_summary()
    cache.set('executive_summary', summary, 300)  # 5 دقائق
```

---

## الأمان
**Security**

### 1. Mobile API
- JWT Authentication
- Token expiry
- Refresh tokens
- Permission checks

### 2. White Label
- Data isolation بين المستأجرين
- Domain validation
- Subscription checks

### 3. Anomaly Detection
- Role-based access
- Audit trail
- Email notifications للأحداث الحرجة

---

## الاختبار
**Testing**

### Unit Tests Example
```python
from django.test import TestCase
from production.services.delivery_promise import delivery_calculator

class DeliveryPromiseTests(TestCase):
    def test_calculate_promise_from_stock(self):
        # إعداد
        product = Product.objects.create(...)
        Stock.objects.create(product=product, quantity=100)
        
        # تنفيذ
        result = delivery_calculator.calculate_promise(product.id, 50)
        
        # تحقق
        self.assertEqual(result['source'], 'stock')
        self.assertIsNotNone(result['delivery_date'])
```

---

## الصيانة
**Maintenance**

### 1. مراقبة الأداء
```bash
# فحص Celery tasks
celery -A accountant_pro inspect active

# فحص logs
tail -f logs/anomaly_detection.log
```

### 2. Database Cleanup
```bash
# تشغيل cleanup يدوياً
python manage.py shell
>>> from monitoring.tasks_anomaly import cleanup_old_alerts
>>> cleanup_old_alerts()
```

### 3. Backup
نسخ احتياطي للجداول الجديدة:
- `anomaly_alerts`
- `proactive_warnings`
- `tenants`
- `tenant_branding`
- `tenant_settings`
- `product_traceability`
- `recall_orders`
- `supplier_evaluations`

---

## الدعم والتوثيق
**Support & Documentation**

### موارد إضافية
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Simple JWT](https://django-rest-framework-simplejwt.readthedocs.io/)
- [Celery](https://docs.celeryproject.org/)
- [Statistical Analysis](https://docs.python.org/3/library/statistics.html)

### تواصل
لأي استفسارات أو مشاكل، يرجى الرجوع إلى:
- التوثيق الداخلي في كل ملف
- Comments في الكود
- Docstrings للدوال والكلاسات

---

## الخلاصة
**Summary**

تم إضافة 9 ميزات enterprise شاملة واحترافية:
✅ الوعد الذكي بالتسليم
✅ التتبع والاستدعاء
✅ تحليل نقطة التعادل
✅ تقييم الموردين
✅ لوحة القيادة التنفيذية
✅ منع الخسائر السعرية
✅ Mobile API كامل
✅ نظام العلامة البيضاء (Multi-Tenancy)
✅ الكشف عن الشذوذات والتنبيهات الاستباقية

**جميع الأنظمة جاهزة للإنتاج** ✨
