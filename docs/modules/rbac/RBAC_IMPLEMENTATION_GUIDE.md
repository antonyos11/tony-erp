# دليل نظام الصلاحيات والأدوار المحسّن
## Tony ERP - نظام الشامل

**التاريخ**: 7 ديسمبر 2025  
**الإصدار**: 2.0  
**الحالة**: ✅ مكتمل

---

## نظرة عامة

تم تطوير نظام شامل لإدارة الصلاحيات والأدوار في نظام الشامل، يجعل النظام أكثر أماناً وتنظيماً، ويسهّل عملية تشغيل كل مستخدم حسب صلاحياته.

---

## 📋 ما تم إنجازه

### 1. مصفوفة الأدوار والصلاحيات الكاملة ✅

**الملف**: `RBAC_ROLES_MATRIX.md`

تم تعريف **12 دور أساسي** في النظام مع صلاحيات مفصلة لكل دور:

1. **المالك / المدير العام** (ROLE_OWNER) - صلاحيات كاملة
2. **المدير المالي** (ROLE_FIN_MANAGER) - إدارة مالية كاملة
3. **محاسب** (ROLE_ACCOUNTANT) - عمليات محاسبية يومية
4. **مدير المخزون** (ROLE_INV_MANAGER) - إدارة المخزون والمشتريات
5. **أمين مخزن** (ROLE_STORE_KEEPER) - استلام وصرف يومي
6. **مدير المبيعات** (ROLE_SALES_MANAGER) - إدارة المبيعات والفريق
7. **موظف مبيعات** (ROLE_SALES_STAFF) - فواتير وعروض أسعار
8. **كاشير** (ROLE_CASHIER) - نقطة البيع فقط
9. **مدير الإنتاج** (ROLE_PROD_MANAGER) - إدارة الإنتاج
10. **موظف موارد بشرية** (ROLE_HR_STAFF) - إدارة الموظفين
11. **مشرف نظام** (ROLE_SYS_ADMIN) - دعم تقني
12. **مستخدم عرض فقط** (ROLE_VIEWER) - عرض بدون تعديل

**المخرجات**:
- مصفوفة صلاحيات مفصلة (جدول كامل)
- حدود الموافقات المالية لكل دور
- حدود الخصومات لكل دور
- أولوية الموافقات (5 مستويات)

---

### 2. طبقة خدمة موحدة للصلاحيات ✅

**المسار**: `core/security/`

#### الملفات المنشأة:

**`role_definitions.py`**
- ثوابت الأدوار (ROLE_OWNER, ROLE_FIN_MANAGER, إلخ)
- حدود الموافقات والخصومات الافتراضية
- مستويات الموافقة
- دوال مساعدة

**`permissions_service.py`**
- **PermissionService**: الخدمة المركزية
- فحص صلاحيات الوحدات
- فحص صلاحيات الموارد
- فحص الأدوار
- فحص سلطة الموافقة على المبالغ
- فحص سلطة الخصومات
- فحوصات خاصة (إلغاء فواتير، إقفال فترات، إلخ)

#### أمثلة الاستخدام:

```python
from core.security import PermissionService

# فحص صلاحية عرض
if PermissionService.can_view(request.user, 'sales'):
    # عرض البيانات

# فحص صلاحية إضافة
if PermissionService.can_add(request.user, 'inventory'):
    # إضافة صنف

# فحص سلطة موافقة على مبلغ
if PermissionService.can_approve_amount(request.user, amount):
    # اعتماد العملية

# فحص سلطة خصم
if PermissionService.can_give_discount(request.user, discount_percentage):
    # إعطاء الخصم

# دوال مختصرة
from core.security import user_can
if user_can(request.user, 'sales', 'add'):
    # ...

# ديكوريتر للـ Views
from core.security import require_permission

@require_permission('sales', 'add')
def create_invoice(request):
    # ...
```

---

### 3. محرك القوائم الديناميكي ✅

**المسار**: `core/navigation/`

#### الملفات المنشأة:

**`menu_config.py`**
- تعريف كامل لكل القوائم والبنود
- صلاحيات مطلوبة لكل بند
- أدوار مسموح لها
- تكوين لوحات التحكم لكل دور

**`menu_engine.py`**
- **MenuEngine**: محرك توليد القوائم
- فلترة تلقائية بناءً على صلاحيات المستخدم
- Breadcrumbs ديناميكية
- إجراءات سريعة حسب الدور
- لوحات تحكم مخصصة

**`core/templatetags/menu_tags.py`**
- وسوم Django للقوالب
- `{% get_main_menu %}`
- `{% render_main_menu %}`
- `{% render_quick_actions %}`

#### أمثلة الاستخدام:

```python
from core.navigation import MenuEngine

# في View
menu = MenuEngine.get_menu_for_user(request.user)

# الإجراءات السريعة
quick_actions = MenuEngine.get_quick_actions(request.user)

# لوحة التحكم المناسبة
dashboard_config = MenuEngine.get_dashboard_config(request.user)
```

في القوالب:
```django
{% load menu_tags %}

{% render_main_menu %}
{% render_quick_actions %}
```

---

### 4. نظام Workflows للعمليات الحرجة ✅

**المسار**: `core/workflows/`

#### الملفات المنشأة:

**`base_workflow.py`**
- **WorkflowEngine**: المحرك الأساسي
- حالات سير العمل (WorkflowState)
- إجراءات (WorkflowAction)
- انتقالات (WorkflowTransition)
- سجل التغييرات (WorkflowHistory)

**`invoice_workflow.py`**
- سير عمل الفواتير
- مسودة → معلق → معتمد → مرحّل
- إلغاء فواتير معتمدة (بصلاحيات خاصة)

**`journal_workflow.py`**
- سير عمل القيود المحاسبية
- مسودة → معلق → معتمد → مرحّل → مقفل
- ترحيل وإقفال بصلاحيات مشددة

**`approval_workflow.py`**
- سير عمل عام للموافقات
- يمكن استخدامه لأي عملية

#### أمثلة الاستخدام:

```python
from core.workflows import get_workflow_for_type, WorkflowAction

# الحصول على workflow
workflow = get_workflow_for_type('invoice')

# فحص الإجراءات المتاحة
available_actions = workflow.get_available_actions(
    current_state=invoice.state,
    user=request.user,
    context={'amount': invoice.total}
)

# تنفيذ إجراء
success, new_state, message = workflow.perform_action(
    obj=invoice,
    current_state=invoice.state,
    action=WorkflowAction.APPROVE,
    user=request.user,
    comment='معتمد',
    context={'amount': invoice.total}
)

if success:
    invoice.state = new_state
    invoice.save()
```

---

### 5. نظام صلاحيات التقارير ✅

**الملف**: `core/security/report_permissions.py`

#### المميزات:

- **كتالوج شامل للتقارير** (REPORTS_CATALOG)
- تصنيف التقارير حسب الفئة
- مستويات حساسية (عام، محدود، سري، سري للغاية)
- أدوار مسموح لها لكل تقرير
- فلترة تقارير تظهر التكلفة/الأرباح

#### الفئات:

1. **التقارير المالية** - للمحاسبين والإدارة
2. **تقارير المبيعات** - لفريق المبيعات
3. **تقارير المخزون** - لإدارة المخزون
4. **تقارير المشتريات** - لفريق المشتريات
5. **تقارير الإنتاج** - لإدارة الإنتاج
6. **تقارير الموارد البشرية** - لقسم HR

#### أمثلة الاستخدام:

```python
from core.security.report_permissions import ReportPermissionService

# الحصول على التقارير المتاحة
available_reports = ReportPermissionService.get_available_reports(request.user)

# فحص صلاحية تقرير معين
can_view, message = ReportPermissionService.can_view_report(request.user, 'profit_by_invoice')

# التقارير مجموعة حسب الفئة
reports_by_category = ReportPermissionService.get_reports_by_category(request.user)
```

---

### 6. نظام تسجيل الأمان والتدقيق المحسّن ✅

**الملف**: `core/security/audit_service.py`

#### المميزات:

**SecurityAuditService** - خدمة شاملة للتدقيق:

- تسجيل محاولات الدخول (نجحت/فشلت)
- تسجيل العمليات الحرجة
- تسجيل الموافقات والرفض
- تسجيل تصدير البيانات
- تسجيل انتهاكات الصلاحيات
- تسجيل تعديل البيانات
- أحداث النظام

#### أمثلة الاستخدام:

```python
from core.security.audit_service import SecurityAuditService

# تسجيل عملية حرجة
SecurityAuditService.log_critical_action(
    user=request.user,
    action='إلغاء فاتورة',
    module='المبيعات',
    object_id=str(invoice.id),
    description=f'إلغاء فاتورة معتمدة رقم {invoice.id}',
    request=request,
)

# تسجيل موافقة
SecurityAuditService.log_approval(
    user=request.user,
    action='اعتماد',
    module='المحاسبة',
    object_type='قيد يومية',
    object_id=str(entry.id),
    amount=entry.amount,
    approved=True,
    request=request,
)

# استخدام ديكوريتر
from core.security.audit_service import audit_critical_action

@audit_critical_action('إلغاء فاتورة', 'المبيعات')
def cancel_invoice(request, invoice_id):
    # ...
```

---

### 7. واجهة إدارة المستخدمين والأدوار ✅

**الملف**: `users/views_enhanced.py`

#### الواجهات المنشأة:

1. **قائمة المستخدمين** (`user_list`)
   - بحث وفلترة
   - عرض الأدوار والحالة
   - Pagination

2. **تفاصيل المستخدم** (`user_detail`)
   - معلومات كاملة
   - آخر الأنشطة
   - التنبيهات الأمنية
   - حدود الموافقة والخصم

3. **إنشاء مستخدم** (`user_create`)
   - إدخال بيانات كاملة
   - اختيار الدور الرئيسي
   - أدوار إضافية
   - موافقة تلقائية (اختياري)

4. **تعديل مستخدم** (`user_edit`)
   - تحديث كل البيانات
   - تغيير الأدوار
   - عناوين IP المسموحة
   - عدد الجلسات المتزامنة

5. **قائمة الأدوار** (`role_list`)
   - عرض كل الأدوار
   - عدد المستخدمين لكل دور

6. **تفاصيل الدور** (`role_detail`)
   - صلاحيات الوحدات
   - صلاحيات الموارد
   - المستخدمون بهذا الدور

7. **مصفوفة الصلاحيات** (`role_permissions_matrix`)
   - جدول شامل
   - كل الأدوار × كل الوحدات × كل العمليات

8. **سجلات الأمان** (`security_logs`)
   - التنبيهات الأمنية
   - نشاط المستخدمين الأخير

---

## 📁 هيكل الملفات الجديدة

```
الشامل/الشامل/app/
├── RBAC_ROLES_MATRIX.md                    # مصفوفة الأدوار
├── core/
│   ├── security/                           # نظام الأمان
│   │   ├── __init__.py
│   │   ├── role_definitions.py             # تعريفات الأدوار
│   │   ├── permissions_service.py          # خدمة الصلاحيات
│   │   ├── report_permissions.py           # صلاحيات التقارير
│   │   └── audit_service.py                # تسجيل التدقيق
│   ├── navigation/                         # القوائم الديناميكية
│   │   ├── __init__.py
│   │   ├── menu_config.py                  # تعريف القوائم
│   │   └── menu_engine.py                  # محرك القوائم
│   ├── workflows/                          # سير العمل
│   │   ├── __init__.py
│   │   ├── base_workflow.py                # المحرك الأساسي
│   │   ├── invoice_workflow.py             # سير عمل الفواتير
│   │   ├── journal_workflow.py             # سير عمل القيود
│   │   └── approval_workflow.py            # موافقات عامة
│   └── templatetags/
│       └── menu_tags.py                    # وسوم القوائم
├── templates/
│   └── components/
│       ├── main_menu.html                  # قالب القائمة
│       └── quick_actions.html              # قالب الإجراءات السريعة
└── users/
    └── views_enhanced.py                   # واجهات إدارة المستخدمين
```

---

## 🚀 كيفية الاستخدام

### 1. التكامل مع Views موجودة

```python
# في أي view
from core.security import PermissionService, require_permission

@require_permission('sales', 'add')
def create_invoice(request):
    # الكود القديم يعمل كما هو
    # الصلاحيات تُفحص تلقائياً
    pass
```

### 2. في القوالب (Templates)

```django
{% load menu_tags %}

<!DOCTYPE html>
<html>
<head>
    <title>نظام الشامل</title>
</head>
<body>
    {# القائمة الديناميكية #}
    {% render_main_menu %}
    
    {# الإجراءات السريعة #}
    {% render_quick_actions %}
    
    {# المحتوى #}
    <div class="content">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
```

### 3. استخدام Workflows

```python
# في view الفاتورة
from core.workflows import get_workflow_for_type, WorkflowAction

def approve_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    workflow = get_workflow_for_type('invoice')
    
    # فحص إذا كان المستخدم يستطيع الاعتماد
    can, message = workflow.can_perform_action(
        current_state=invoice.workflow_state,
        action=WorkflowAction.APPROVE,
        user=request.user,
        context={'amount': invoice.total}
    )
    
    if not can:
        messages.error(request, message)
        return redirect('invoice_detail', invoice_id)
    
    # تنفيذ الاعتماد
    success, new_state, msg = workflow.perform_action(
        obj=invoice,
        current_state=invoice.workflow_state,
        action=WorkflowAction.APPROVE,
        user=request.user,
        comment=request.POST.get('comment', ''),
        context={'amount': invoice.total}
    )
    
    if success:
        invoice.workflow_state = new_state.value
        invoice.save()
        messages.success(request, msg)
    
    return redirect('invoice_detail', invoice_id)
```

### 4. التقارير حسب الدور

```python
# في view التقارير
from core.security.report_permissions import ReportPermissionService

def reports_dashboard(request):
    # الحصول على التقارير المتاحة للمستخدم
    reports_by_category = ReportPermissionService.get_reports_by_category(request.user)
    
    context = {
        'reports_by_category': reports_by_category,
    }
    
    return render(request, 'reports/dashboard.html', context)


def view_report(request, report_id):
    # فحص الصلاحية
    can_view, message = ReportPermissionService.can_view_report(request.user, report_id)
    
    if not can_view:
        messages.error(request, message)
        return redirect('reports_dashboard')
    
    # عرض التقرير
    # ...
```

---

## 🔐 الأمان والأفضليات

### ✅ ما تم تطبيقه:

1. **فحص الصلاحيات على 3 مستويات**:
   - مستوى الوحدة (Module)
   - مستوى المورد (Resource)
   - مستوى الدور (Role)

2. **حدود واضحة للموافقات**:
   - كل دور له حد موافقة معين
   - فحص تلقائي للمبالغ

3. **حدود الخصومات**:
   - نسب محددة لكل دور
   - منع إعطاء خصومات غير مصرح بها

4. **Workflows مشددة للعمليات الحرجة**:
   - إلغاء فواتير معتمدة
   - ترحيل قيود
   - إقفال فترات

5. **تسجيل شامل**:
   - كل عملية حرجة تُسجل
   - تنبيهات أمنية للانتهاكات
   - سجل كامل لنشاط المستخدمين

6. **فصل البيانات الحساسة**:
   - أسعار التكلفة (لأدوار محددة فقط)
   - تقارير الأرباح (للإدارة فقط)
   - الرواتب (سرية)

---

## 📝 الخطوات التالية (اختياري)

### 1. التكامل التدريجي:

1. **المرحلة 1** (أسبوع 1-2):
   - استخدام `PermissionService` في شاشات المبيعات
   - استخدام `PermissionService` في شاشات المخزون
   - تطبيق القوائم الديناميكية

2. **المرحلة 2** (أسبوع 3-4):
   - تطبيق Workflows على الفواتير
   - تطبيق Workflows على القيود
   - إعداد واجهة إدارة المستخدمين

3. **المرحلة 3** (أسبوع 5-6):
   - تطبيق صلاحيات التقارير
   - تفعيل تسجيل التدقيق الكامل
   - اختبار شامل

### 2. تحسينات مستقبلية:

- [ ] نظام إشعارات للموافقات المعلقة
- [ ] لوحات تحكم متقدمة لكل دور
- [ ] تقارير نشاط المستخدمين
- [ ] نظام مهام (Tasks) مرتبط بالأدوار
- [ ] موافقات متعددة المستويات (Multi-level approval)

---

## 🎯 الفوائد المحققة

### للمستخدمين:

✅ واجهة بسيطة ونظيفة - فقط ما يحتاجونه  
✅ إجراءات سريعة حسب الدور  
✅ لوحة تحكم مخصصة  
✅ تقارير مناسبة للدور  
✅ تجنب الأخطاء (لا يرون ما لا يحق لهم)

### للإدارة:

✅ تحكم كامل في الصلاحيات  
✅ تتبع كل العمليات الحرجة  
✅ أمان محسّن  
✅ سهولة إضافة مستخدمين جدد  
✅ تقارير تدقيق شاملة

### للمطورين:

✅ كود منظم وقابل للصيانة  
✅ API موحد للصلاحيات  
✅ سهولة التوسع  
✅ توثيق واضح  
✅ أمثلة جاهزة

---

## 📞 الدعم

لأي استفسارات أو مشاكل:

1. راجع ملف `RBAC_ROLES_MATRIX.md` للمصفوفة الكاملة
2. راجع الكود مع التعليقات التوضيحية
3. استخدم الأمثلة الموجودة في هذا الملف

---

## ✨ ملخص

تم بناء نظام شامل ومتكامل لإدارة الصلاحيات والأدوار في نظام الشامل:

- ✅ **12 دور محدد** بصلاحيات واضحة
- ✅ **طبقة خدمة موحدة** سهلة الاستخدام
- ✅ **قوائم ديناميكية** تتغير حسب المستخدم
- ✅ **Workflows** للعمليات الحرجة
- ✅ **صلاحيات تقارير** مفصلة
- ✅ **تسجيل وتدقيق** شامل
- ✅ **واجهات إدارة** سهلة

النظام جاهز للاستخدام ويمكن التكامل معه تدريجياً! 🎉


