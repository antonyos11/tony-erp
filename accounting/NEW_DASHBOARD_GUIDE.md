# لوحة المحاسبة الجديدة - دليل الاستخدام

## نظرة عامة

تم إنشاء لوحة محاسبة جديدة ومحسّنة تعتمد على البنية المنظمة في `accounting_structure.py` مع نظام صلاحيات متقدم من `permissions.py`.

## المسار

```
/accounting/dashboard-new/
```

أو باستخدام اسم الـ URL:
```python
{% url 'accounting:dashboard_new' %}
```

## الميزات الرئيسية

### 1. أربعة تبويبات أفقية

#### 🔵 الأساسيات اليومية (أزرق #3b82f6)
- القيود المحاسبية
- الخزينة والبنوك
- دليل الحسابات

#### 🟢 الفواتير والحركة (أخضر #10b981)
- المبيعات والعملاء
- المشتريات والموردين
- الشيكات والبنوك

#### 🟠 المراجعة والتسويات (برتقالي #f59e0b)
- مراكز التكلفة
- الأصول الثابتة
- التسويات والإقفالات

#### 🟣 التقارير والميزانيات (بنفسجي #8b5cf6)
- القوائم المالية الأساسية
- التقارير التحليلية
- القروض والأدوات

### 2. نظام الأدوار (3 مستويات)

#### كاشير/مندوب (Cashier)
- يرى فقط: الأساسيات اليومية + الفواتير والحركة
- 12 شاشة متاحة

#### محاسب (Accountant)
- يرى جميع التبويبات الأربعة
- 55 شاشة متاحة

#### مدير مالي (CFO)
- يرى جميع التبويبات + الإعدادات المتقدمة
- 65 شاشة متاحة

### 3. تصفية ذكية حسب الصلاحيات

- كل عنصر في القائمة يُفحص مقابل:
  * دور المستخدم (roles)
  * صلاحيات Django (permissions)
  
- يتم إخفاء العناصر غير المتاحة تلقائياً

### 4. شارات (Badges) ديناميكية

#### شارات بالأرقام
- `draft_journal_count` - عدد القيود المسودة
- `pending_invoices_count` - الفواتير المعلقة
- `pending_purchase_count` - فواتير الشراء المعلقة
- `overdue_receivables_count` - الذمم المتأخرة
- `upcoming_payables_count` - الذمم القادمة
- `bank_reconcile_pending` - البنوك تحتاج تسوية

#### شارات حية (Live)
- تظهر كنقطة خضراء نابضة
- للعناصر التي تحتاج مراقبة مستمرة

### 5. بحث ذكي (Ctrl+K)

- بحث فوري في جميع العناصر
- يعمل عبر جميع التبويبات
- تفعيل بـ Ctrl+K

### 6. الاختصارات (Shortcuts)

بعض الشاشات تدعم اختصارات لوحة المفاتيح:
- `Ctrl+Alt+J` - قيد جديد
- `Ctrl+Alt+R` - سند قبض
- `Ctrl+Alt+P` - سند صرف
- `Ctrl+Alt+S` - كشف حساب عميل
- `Ctrl+K` - البحث

### 7. الإعدادات المتقدمة (CFO فقط)

قسم خاص في نهاية الصفحة يحتوي على:
- إعدادات عامة
- الحسابات الافتراضية
- إعدادات الضرائب
- السنة المالية
- قوالب القيود
- إصلاحات سريعة
- تشخيص النظام

## البنية التقنية

### الملفات المنشأة

1. **View**: `accounting/views.py`
   ```python
   @login_required
   def accounting_dashboard_new(request):
       # تصفية التبويبات والعناصر حسب دور المستخدم
   ```

2. **Template**: `accounting/templates/accounting/accounting_dashboard_new.html`
   - تصميم modern مع Bootstrap 5
   - دعم RTL كامل
   - أيقونات Bootstrap Icons

3. **Template Tags**: `accounting/templatetags/accounting_tags.py`
   - `get_item` - الوصول لعناصر القاموس
   - `has_badge` - التحقق من الشارات

4. **URL**: `accounting/urls.py`
   ```python
   path('dashboard-new/', views.accounting_dashboard_new, name='dashboard_new'),
   ```

### البيانات المصدرية

#### من `accounting_structure.py`:
- `ACCOUNTING_TABS` - تعريف التبويبات
- `ACCOUNTING_STRUCTURE` - بنية العناصر
- `ACCOUNTING_ADVANCED_SETTINGS` - الإعدادات المتقدمة
- `get_user_accounting_tabs()` - التبويبات المتاحة للمستخدم
- `filter_items_by_user()` - تصفية العناصر

#### من `permissions.py`:
- `AccountingRoles` - أدوار المحاسبة الثلاثة
- `get_user_accounting_role()` - دور المستخدم الحالي
- `ROLE_PERMISSIONS` - صلاحيات كل دور

## التصميم

### الألوان
```css
--primary-blue: #3b82f6     /* التبويب الأول */
--primary-green: #10b981    /* التبويب الثاني */
--primary-orange: #f59e0b   /* التبويب الثالث */
--primary-purple: #8b5cf6   /* التبويب الرابع */
```

### المميزات البصرية
- Header gradient بنفسجي
- Cards مع shadow وhover effects
- تبويبات ملونة حسب القسم
- أيقونات واضحة لكل عنصر
- Responsive design كامل

## الاستخدام المستقبلي

### إضافة عنصر جديد

في `accounting_structure.py`:
```python
{
    'id': 'my_new_item',
    'label': _('عنصر جديد'),
    'url': 'accounting:my_view',
    'icon': 'bi-star',
    'roles': ['accountant', 'cfo'],
    'permissions': ['accounting.my_permission'],
    'badge_key': 'my_badge_count',  # اختياري
    'shortcut': 'Ctrl+Alt+N',        # اختياري
}
```

### إضافة شارة جديدة

في `views.py` دالة `calculate_dashboard_badges()`:
```python
badges['my_badge_count'] = MyModel.objects.filter(status='pending').count()
```

## الفرق عن اللوحة القديمة

| الميزة | القديمة | الجديدة ✅ |
|--------|---------|-----------|
| البنية | ثابتة في Template | ديناميكية من `accounting_structure.py` |
| الصلاحيات | يدوية في Template | تلقائية من نظام الأدوار |
| التبويبات | قائمة جانبية | 4 تبويبات أفقية ملونة |
| البحث | غير موجود | بحث ذكي + Ctrl+K |
| الشارات | يدوية | ديناميكية من database |
| الاختصارات | غير موجودة | دعم كامل |
| RTL | جزئي | كامل |
| التصميم | قديم | Modern + Animations |

## الاختبار

### كـ كاشير:
1. سجل دخول بمستخدم له دور `accounting_cashier`
2. افتح `/accounting/dashboard-new/`
3. يجب أن ترى تبويبين فقط

### كـ محاسب:
1. سجل دخول بمستخدم له دور `accounting_accountant`
2. افتح `/accounting/dashboard-new/`
3. يجب أن ترى 4 تبويبات

### كـ مدير مالي:
1. سجل دخول بمستخدم له دور `accounting_cfo`
2. افتح `/accounting/dashboard-new/`
3. يجب أن ترى 4 تبويبات + الإعدادات المتقدمة

## الصيانة

### إضافة تبويب جديد

في `accounting_structure.py`:
```python
ACCOUNTING_TABS['new_tab'] = {
    'id': 'new_tab',
    'label': _('تبويب جديد'),
    'icon': 'bi-star',
    'color': '#ec4899',  # وردي
    'order': 5,
}

ACCOUNTING_STRUCTURE['new_tab'] = {
    'groups': [...]
}
```

### تحديث الصلاحيات

في `permissions.py`:
```python
ROLE_PERMISSIONS[AccountingRoles.CASHIER].append('accounting.new_permission')
```

ثم تشغيل:
```python
from accounting.permissions import create_accounting_roles
create_accounting_roles()
```

---

تم الإنشاء: ديسمبر 2025
المطور: Tony ERP Team
