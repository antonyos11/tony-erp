# دليل استخدام القائمة الجانبية المنظمة
## Organized Sidebar Usage Guide

---

## نظرة عامة

تم تطوير نظام قائمة جانبية منظم ومتطور لنظام Tony ERB يعتمد على:
- **بنية موحدة** للبيانات في ملف مركزي
- **تقسيم واضح** إلى أقسام رئيسية ومجموعات فرعية
- **صلاحيات مدمجة** تلقائيًا
- **تجربة مستخدم محسّنة** مع حفظ الحالات

---

## البنية الأساسية

### الملفات الرئيسية

1. **`core/sidebar_config.py`** - تكوين القائمة الجانبية (نموذج البيانات)
2. **`core/sidebar_processor.py`** - معالج السياق (Context Processor)
3. **`templates/partials/_sidebar_organized.html`** - قالب العرض

---

## التقسيم الهرمي

```
├─ قسم رئيسي (Section)
│  ├─ عمليات يومية (Daily Operations)
│  │  ├─ عنصر 1
│  │  ├─ عنصر 2
│  │  └─ ...
│  ├─ تعريفات وإعدادات (Master Data)
│  │  ├─ عنصر 1
│  │  ├─ عنصر 2
│  │  └─ ...
│  └─ تقارير واستعلامات (Reports)
│     ├─ عنصر 1
│     ├─ عنصر 2
│     └─ ...
```

### الفئات الثلاث

- **`daily`** - عمليات يومية: الإجراءات المتكررة (إضافة فاتورة، قيد محاسبي، إلخ)
- **`master`** - تعريفات: البيانات الأساسية (العملاء، المنتجات، الحسابات، إلخ)
- **`reports`** - تقارير: التقارير والاستعلامات والتحليلات

---

## كيفية إضافة عنصر جديد

### مثال: إضافة شاشة "إدارة الخصومات" في قسم المبيعات

**الخطوة 1:** افتح ملف `core/sidebar_config.py`

**الخطوة 2:** ابحث عن القسم المناسب (مثلاً `sales`)

**الخطوة 3:** أضف العنصر في المكان المناسب:

```python
'sales': {
    'id': 'sales',
    'label': _('المبيعات'),
    'icon': 'bi-cart-check',
    'order': 2,
    'module': 'sales',
    'permissions': ['view', 'add', 'change'],
    'items': [
        # ... العناصر الموجودة ...
        
        # === إضافة عنصر جديد ===
        {
            'id': 'sales_discounts_manager',           # معرف فريد
            'label': _('إدارة الخصومات'),              # النص الظاهر
            'url': 'sales:discounts_manager',          # اسم الـ URL
            'icon': 'bi-percent',                      # أيقونة Bootstrap Icons
            'category': CATEGORY_MASTER,               # الفئة: daily, master, reports
            'permission': 'change',                    # الصلاحية المطلوبة
        },
        
        # ... باقي العناصر ...
    ]
}
```

**الخطوة 4:** احفظ الملف - التغييرات ستظهر فورًا!

---

## إضافة قسم رئيسي جديد

### مثال: إضافة قسم "المطاعم"

```python
'restaurants': {
    'id': 'restaurants',
    'label': _('المطاعم'),
    'icon': 'bi-shop',
    'order': 14,  # الترتيب في القائمة
    'module': 'restaurants',  # اسم الوحدة في نظام الصلاحيات
    'permissions': ['view', 'add', 'change'],
    'items': [
        # === عمليات يومية ===
        {
            'id': 'restaurants_orders',
            'label': _('طلبات المطعم'),
            'url': 'restaurants:orders_list',
            'icon': 'bi-receipt',
            'category': CATEGORY_DAILY,
            'permission': 'view',
        },
        {
            'id': 'restaurants_new_order',
            'label': _('طلب جديد'),
            'url': 'restaurants:order_create',
            'icon': 'bi-plus-circle',
            'category': CATEGORY_DAILY,
            'permission': 'add',
        },
        
        # === تعريفات ===
        {
            'id': 'restaurants_menu',
            'label': _('قائمة الطعام'),
            'url': 'restaurants:menu_list',
            'icon': 'bi-card-list',
            'category': CATEGORY_MASTER,
            'permission': 'view',
        },
        {
            'id': 'restaurants_tables',
            'label': _('الطاولات'),
            'url': 'restaurants:tables_list',
            'icon': 'bi-grid-3x3',
            'category': CATEGORY_MASTER,
            'permission': 'view',
        },
        
        # === تقارير ===
        {
            'id': 'restaurants_sales_report',
            'label': _('تقرير المبيعات'),
            'url': 'restaurants:sales_report',
            'icon': 'bi-graph-up',
            'category': CATEGORY_REPORTS,
            'permission': 'view',
        },
    ]
}
```

---

## خيارات العنصر (Item Options)

| الحقل | الوصف | مطلوب | مثال |
|------|-------|-------|------|
| `id` | معرف فريد للعنصر | ✓ | `'sales_invoice_create'` |
| `label` | النص الظاهر للمستخدم | ✓ | `_('فاتورة جديدة')` |
| `url` | اسم URL أو مسار مطلق | ✓ | `'sales:invoice_create'` أو `'/sales/invoices/'` |
| `icon` | أيقونة Bootstrap Icons | ✓ | `'bi-file-earmark-plus'` |
| `category` | الفئة | ✓ | `CATEGORY_DAILY` |
| `permission` | الصلاحية المطلوبة | ✓ | `'view'`, `'add'`, `'change'` |
| `resource` | صلاحية مورد محدد | - | `'invoice_create'` |
| `badge_key` | مفتاح الشارة (Badge) | - | `'unposted_journal_entries_count'` |
| `module_permission` | صلاحية خاصة | - | `('core', 'view_auditlog')` |

---

## إضافة شارات (Badges)

### مثال: عرض عدد المهام المعلقة

**الخطوة 1:** أضف `badge_key` للعنصر:

```python
{
    'id': 'tasks_pending',
    'label': _('المهام المعلقة'),
    'url': 'tasks:pending_list',
    'icon': 'bi-clock',
    'category': CATEGORY_DAILY,
    'permission': 'view',
    'badge_key': 'pending_tasks_count',  # ← إضافة هذا
}
```

**الخطوة 2:** أضف دالة في `core/context_processors.py` لحساب العدد:

```python
_pending_tasks_cache = {'value': 0, 'ts': None}

def _pending_tasks_count():
    from tasks.models import Task
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    
    # استخدام الكاش لمدة دقيقة
    if _pending_tasks_cache['ts'] and (now - _pending_tasks_cache['ts']) < timedelta(seconds=60):
        return _pending_tasks_cache['value']
    
    count = Task.objects.filter(status='pending').count()
    _pending_tasks_cache['value'] = count
    _pending_tasks_cache['ts'] = now
    return count
```

**الخطوة 3:** أضف العدد في `system_info` context processor:

```python
def system_info(request):
    return {
        # ... الحقول الموجودة ...
        'pending_tasks_count': (_pending_tasks_count() if request.user.is_authenticated else 0),
    }
```

**الخطوة 4:** أضف عرض الشارة في القالب `_sidebar_organized.html`:

```html
{% if item.badge_key == 'pending_tasks_count' and pending_tasks_count %}
  <span class="badge bg-warning text-dark ms-auto">{{ pending_tasks_count }}</span>
{% endif %}
```

---

## الأيقونات المتاحة

استخدم أيقونات **Bootstrap Icons**: https://icons.getbootstrap.com/

### أيقونات شائعة:

- **عمليات يومية:**
  - `bi-plus-circle` - إضافة جديد
  - `bi-list-check` - قوائم
  - `bi-file-earmark-plus` - مستند جديد
  - `bi-cash-coin` - نقدي
  - `bi-arrow-repeat` - تحديث

- **تعريفات:**
  - `bi-people` - أشخاص
  - `bi-building` - مباني
  - `bi-gear` - إعدادات
  - `bi-tag` - وسوم
  - `bi-box-seam` - منتجات

- **تقارير:**
  - `bi-graph-up` - تقارير
  - `bi-clipboard-data` - بيانات
  - `bi-bar-chart` - رسوم بيانية
  - `bi-file-text` - مستندات
  - `bi-calculator` - حسابات

---

## نظام الصلاحيات

الاسليدر يدعم نظام الصلاحيات تلقائيًا:

### مستويات الصلاحيات:

1. **صلاحيات الوحدة** (Module Permissions):
   ```python
   'permission': 'view'  # أو 'add', 'change', 'delete'
   ```

2. **صلاحيات الموارد** (Resource Permissions):
   ```python
   'resource': 'invoice_create',
   'permission': 'add'
   ```

3. **صلاحيات خاصة** (Custom Permissions):
   ```python
   'module_permission': ('core', 'view_auditlog')
   ```

### إخفاء العناصر تلقائيًا:

العناصر التي لا يملك المستخدم صلاحية الوصول لها **تُخفى تلقائيًا** ولا تظهر في القائمة.

---

## حفظ حالة الطي/الفتح

الاسليدر يحفظ حالة الأقسام المطوية/المفتوحة في `localStorage` تلقائيًا:

- عند **فتح** قسم → يُحفظ في المتصفح
- عند **طي** قسم → يُحفظ في المتصفح
- عند العودة للصفحة → تُستعاد الحالة السابقة

**ملاحظة:** الأقسام التي تحتوي على عنصر نشط (active) تُفتح تلقائيًا حتى لو كانت مطوية سابقًا.

---

## تفعيل الاسليدر المنظم

### الخطوة 1: تسجيل Context Processor

في `settings.py`:

```python
TEMPLATES = [
    {
        'OPTIONS': {
            'context_processors': [
                # ... الموجودة ...
                'core.sidebar_processor.sidebar_menu',  # ← إضافة هذا
            ],
        },
    },
]
```

### الخطوة 2: استبدال القالب

في `templates/base.html` أو `templates/base_v2.html`:

```html
{# استبدل هذا: #}
{% include 'partials/_sidebar.html' %}

{# بهذا: #}
{% include 'partials/_sidebar_organized.html' %}
```

### الخطوة 3: إعادة تشغيل السيرفر

```bash
python manage.py runserver
```

---

## استكشاف الأخطاء

### المشكلة: العناصر لا تظهر

**الحل:**
1. تأكد من أن المستخدم لديه الصلاحية المطلوبة
2. تحقق من أن `module` في القسم يطابق اسم الوحدة في نظام الصلاحيات
3. تأكد من أن `url` صحيح ومسجل في `urls.py`

### المشكلة: الشارات (Badges) لا تظهر

**الحل:**
1. تأكد من إضافة `badge_key` في تكوين العنصر
2. تأكد من إضافة القيمة في context processor
3. تأكد من إضافة عرض الشارة في القالب

### المشكلة: الأيقونات لا تظهر

**الحل:**
1. تأكد من أن اسم الأيقونة صحيح (مثل `'bi-graph-up'`)
2. تأكد من تحميل Bootstrap Icons في الصفحة
3. جرّب أيقونة بديلة من https://icons.getbootstrap.com/

---

## أمثلة عملية

### مثال 1: إضافة قسم فرعي للتقارير في المحاسبة

```python
{
    'id': 'accounting_profitability_report',
    'label': _('تقرير الربحية'),
    'url': 'accounting:profitability_report',
    'icon': 'bi-currency-dollar',
    'category': CATEGORY_REPORTS,  # ← تقرير
    'permission': 'view',
}
```

### مثال 2: إضافة عملية يومية في المخزون

```python
{
    'id': 'inventory_quick_adjustment',
    'label': _('تعديل سريع للمخزون'),
    'url': 'inventory:quick_adjustment',
    'icon': 'bi-lightning',
    'category': CATEGORY_DAILY,  # ← عملية يومية
    'permission': 'change',
}
```

### مثال 3: إضافة تعريف جديد في الموارد البشرية

```python
{
    'id': 'hr_skills_list',
    'label': _('المهارات'),
    'url': 'hr:skills_list',
    'icon': 'bi-award',
    'category': CATEGORY_MASTER,  # ← تعريف
    'permission': 'view',
}
```

---

## نصائح وأفضل الممارسات

### ✅ افعل:

1. **استخدم أسماء واضحة** للـ `id` و `label`
2. **اختر الفئة المناسبة** (daily/master/reports)
3. **استخدم أيقونات معبرة** تناسب الوظيفة
4. **اختبر الصلاحيات** مع مستخدمين مختلفين
5. **حافظ على الترتيب المنطقي** في `order`

### ❌ لا تفعل:

1. **لا تكرر** نفس `id` في عناصر مختلفة
2. **لا تضع** كل شيء في فئة واحدة
3. **لا تنسَ** تحديد `permission` المناسبة
4. **لا تستخدم** مسارات URL معطلة
5. **لا تُفرط** في عدد العناصر في قسم واحد (10-15 عنصر كحد أقصى)

---

## الدعم والمساعدة

للمزيد من المساعدة:
- راجع ملف `core/sidebar_config.py` للأمثلة الكاملة
- راجع ملف `core/sidebar_processor.py` لفهم معالجة الصلاحيات
- راجع قالب `templates/partials/_sidebar_organized.html` لفهم العرض

---

**تم إنشاء هذا الدليل بواسطة:** فريق تطوير Tony ERB  
**آخر تحديث:** 2025

