# نظام الصلاحيات التفصيلي (Fine-Grained Permissions)

## نظرة عامة

هذا النظام يسمح لك بالتحكم **الدقيق جداً** في:
- ✅ **كل حقل** في الصفحة (مرئي/مخفي، قابل للتعديل/للقراءة فقط)
- ✅ **أقسام كاملة** في الصفحة (بطاقات، جداول، إلخ)
- ✅ **أزرار وعمليات** محددة
- ✅ **شروط مخصصة** لكل عنصر

---

## 📁 الملفات الجديدة

```
core/security/
└── fine_grained_permissions.py       ← النظام الكامل

core/templatetags/
└── fine_grained_perms.py             ← وسوم القوالب

templates/components/
├── conditional_field.html            ← قالب حقل
├── conditional_section.html          ← قالب قسم
└── action_button.html                ← قالب زر
```

---

## 🎯 الاستخدام الكامل

### 1. تعريف صلاحيات صفحة المنتج (مثال كامل)

```python
# في ملف مثل: inventory/page_permissions.py

from core.security.fine_grained_permissions import (
    PagePermissionConfig,
    FieldPermission,
    PageSection,
    ActionButton,
    FineGrainedPermissionService
)
from core.security.role_definitions import *

# إنشاء تكوين صفحة تفاصيل المنتج
product_detail_config = PagePermissionConfig(
    page_id='product_detail',
    title='تفاصيل الصنف',
    requires_permission='inventory.view'
)

# ===========================================================================
# الحقول - تحديد من يرى ويعدل كل حقل
# ===========================================================================

# 1. سعر التكلفة - حساس جداً!
product_detail_config.add_field(FieldPermission(
    field='cost_price',
    roles_allowed=[ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_INV_MANAGER],
    read_only_roles=[ROLE_INV_MANAGER],  # مدير المخزون يراه لكن لا يعدله
    hidden_for=[ROLE_SALES_STAFF, ROLE_CASHIER, ROLE_STORE_KEEPER],  # مخفي تماماً
))

# 2. سعر البيع - يراه الكل، لكن قلة تعدله
product_detail_config.add_field(FieldPermission(
    field='selling_price',
    roles_allowed=[],  # الكل يراه
    read_only_roles=[ROLE_SALES_STAFF, ROLE_CASHIER, ROLE_STORE_KEEPER],
))

# 3. هامش الربح - حساس
product_detail_config.add_field(FieldPermission(
    field='profit_margin',
    roles_allowed=[ROLE_OWNER, ROLE_FIN_MANAGER],
    hidden_for=[ROLE_SALES_STAFF, ROLE_SALES_MANAGER, ROLE_CASHIER],
))

# 4. الكمية المتاحة - الكل يراها
product_detail_config.add_field(FieldPermission(
    field='quantity',
    roles_allowed=[],  # الكل يراه
    read_only_roles=[ROLE_SALES_STAFF, ROLE_CASHIER],  # فقط المخزون يعدله
))

# 5. حد إعادة الطلب
product_detail_config.add_field(FieldPermission(
    field='reorder_level',
    roles_allowed=[ROLE_OWNER, ROLE_INV_MANAGER, ROLE_STORE_KEEPER],
    read_only_roles=[ROLE_STORE_KEEPER],
))

# 6. ملاحظات داخلية - لإدارة فقط
product_detail_config.add_field(FieldPermission(
    field='internal_notes',
    roles_allowed=[ROLE_OWNER, ROLE_INV_MANAGER],
    hidden_for=[ROLE_SALES_STAFF, ROLE_CASHIER],
))

# ===========================================================================
# الأقسام - أجزاء كاملة في الصفحة
# ===========================================================================

# قسم المعلومات المالية
product_detail_config.add_section(PageSection(
    section_id='financial_info',
    title='المعلومات المالية',
    roles_allowed=[ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_ACCOUNTANT],
    fields=['cost_price', 'profit_margin', 'total_cost', 'tax_info']
))

# قسم إحصائيات المبيعات
product_detail_config.add_section(PageSection(
    section_id='sales_stats',
    title='إحصائيات المبيعات',
    roles_allowed=[ROLE_OWNER, ROLE_SALES_MANAGER, ROLE_FIN_MANAGER],
))

# قسم حركات المخزون
product_detail_config.add_section(PageSection(
    section_id='stock_movements',
    title='حركات المخزون',
    roles_allowed=[ROLE_OWNER, ROLE_INV_MANAGER, ROLE_STORE_KEEPER],
))

# ===========================================================================
# العمليات/الأزرار - تحديد من يستطيع تنفيذ ماذا
# ===========================================================================

# زر تعديل
product_detail_config.add_action(ActionButton(
    action_id='edit',
    label='تعديل',
    url='#',
    roles_allowed=[ROLE_OWNER, ROLE_INV_MANAGER],
    requires_permission='inventory.change',
    icon='fas fa-edit'
))

# زر حذف - خطير!
product_detail_config.add_action(ActionButton(
    action_id='delete',
    label='حذف',
    url='#',
    roles_allowed=[ROLE_OWNER],
    requires_permission='inventory.delete',
    min_approval_level=5,  # يحتاج أعلى مستوى
    danger=True,
    icon='fas fa-trash',
    condition=lambda user, ctx: ctx.get('can_delete', False)  # شرط إضافي
))

# زر جرد
product_detail_config.add_action(ActionButton(
    action_id='inventory_count',
    label='جرد',
    url='#',
    roles_allowed=[ROLE_OWNER, ROLE_INV_MANAGER],
    requires_permission='inventory.approve',
    icon='fas fa-boxes'
))

# زر طباعة الباركود
product_detail_config.add_action(ActionButton(
    action_id='print_barcode',
    label='طباعة باركود',
    url='#',
    roles_allowed=[],  # الكل يستطيع
    icon='fas fa-barcode'
))

# تسجيل التكوين
FineGrainedPermissionService.register_page_config(product_detail_config)
```

---

### 2. في View

```python
# في inventory/views.py

from django.shortcuts import render, get_object_or_404
from core.security.fine_grained_permissions import FineGrainedPermissionService
from .models import Product
from .page_permissions import product_detail_config  # استيراد التكوين

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # فحص الوصول للصفحة
    can_access, message = product_detail_config.can_access_page(request.user)
    if not can_access:
        messages.error(request, message)
        return redirect('product_list')
    
    # الحصول على الحقول المرئية
    visible_fields = product_detail_config.get_visible_fields(request.user)
    
    # الحصول على الحقول القابلة للتعديل
    editable_fields = product_detail_config.get_editable_fields(request.user)
    
    # الحصول على الأقسام المرئية
    visible_sections = product_detail_config.get_visible_sections(request.user)
    
    # الحصول على العمليات المتاحة
    available_actions = product_detail_config.get_available_actions(
        request.user,
        context={'can_delete': product.quantity == 0}  # مثال: فقط إذا كانت الكمية صفر
    )
    
    # فلترة بيانات المنتج بناءً على الصلاحيات
    filtered_product_data = FineGrainedPermissionService.filter_model_fields(
        request.user,
        'product_detail',
        product
    )
    
    context = {
        'product': product,
        'filtered_data': filtered_product_data,
        'visible_fields': visible_fields,
        'editable_fields': editable_fields,
        'visible_sections': visible_sections,
        'available_actions': available_actions,
    }
    
    return render(request, 'inventory/product_detail.html', context)
```

---

### 3. في Template

```django
{% extends "base.html" %}
{% load fine_grained_perms %}

{% block content %}
<div class="product-detail">
    <h1>{{ product.name }}</h1>
    
    {# ==================================================================== #}
    {# استخدام وسوم للحقول الفردية #}
    {# ==================================================================== #}
    
    <div class="basic-info">
        {# حقل عادي - يظهر للكل #}
        <div class="form-group">
            <label>اسم المنتج</label>
            <input type="text" value="{{ product.name }}" class="form-control">
        </div>
        
        {# حقل محمي - سعر التكلفة #}
        {% can_view_field 'product_detail' 'cost_price' as can_view_cost %}
        {% if can_view_cost %}
            {% can_edit_field 'product_detail' 'cost_price' as can_edit_cost %}
            <div class="form-group">
                <label>سعر التكلفة</label>
                {% if can_edit_cost %}
                    <input type="number" name="cost_price" value="{{ product.cost_price }}" class="form-control">
                {% else %}
                    <span class="form-control-plaintext">{{ product.cost_price }} جنيه (للقراءة فقط)</span>
                {% endif %}
            </div>
        {% endif %}
        
        {# استخدام مكون جاهز #}
        {% render_field 'product_detail' 'selling_price' 'سعر البيع' product.selling_price 'currency' %}
        {% render_field 'product_detail' 'profit_margin' 'هامش الربح %' product.profit_margin 'text' %}
    </div>
    
    {# ==================================================================== #}
    {# الأقسام - أجزاء كاملة تظهر أو تختفي #}
    {# ==================================================================== #}
    
    {# قسم المعلومات المالية #}
    {% can_view_section 'product_detail' 'financial_info' as can_view_financial %}
    {% if can_view_financial %}
        <div class="card mt-3">
            <div class="card-header bg-success text-white">
                <h5>💰 المعلومات المالية</h5>
            </div>
            <div class="card-body">
                <table class="table">
                    {% can_view_field 'product_detail' 'cost_price' as show_cost %}
                    {% if show_cost %}
                        <tr>
                            <td>سعر التكلفة</td>
                            <td>{{ product.cost_price }} جنيه</td>
                        </tr>
                    {% endif %}
                    
                    {% can_view_field 'product_detail' 'profit_margin' as show_margin %}
                    {% if show_margin %}
                        <tr>
                            <td>هامش الربح</td>
                            <td>{{ product.profit_margin }}%</td>
                        </tr>
                    {% endif %}
                    
                    <tr>
                        <td>إجمالي القيمة في المخزون</td>
                        {% can_view_field 'product_detail' 'cost_price' as show_total_cost %}
                        {% if show_total_cost %}
                            <td>{{ product.total_value }} جنيه</td>
                        {% else %}
                            <td>---</td>
                        {% endif %}
                    </tr>
                </table>
            </div>
        </div>
    {% endif %}
    
    {# قسم إحصائيات المبيعات #}
    {% can_view_section 'product_detail' 'sales_stats' as can_view_sales %}
    {% if can_view_sales %}
        <div class="card mt-3">
            <div class="card-header bg-primary text-white">
                <h5>📊 إحصائيات المبيعات</h5>
            </div>
            <div class="card-body">
                <p>المبيعات هذا الشهر: {{ product.sales_this_month }}</p>
                <p>المبيعات السنة: {{ product.sales_this_year }}</p>
            </div>
        </div>
    {% endif %}
    
    {# قسم حركات المخزون #}
    {% can_view_section 'product_detail' 'stock_movements' as can_view_movements %}
    {% if can_view_movements %}
        <div class="card mt-3">
            <div class="card-header bg-info text-white">
                <h5>📦 حركات المخزون</h5>
            </div>
            <div class="card-body">
                {# جدول الحركات #}
            </div>
        </div>
    {% endif %}
    
    {# ==================================================================== #}
    {# الأزرار/العمليات - تظهر أو تختفي حسب الصلاحيات #}
    {# ==================================================================== #}
    
    <div class="actions mt-4">
        {# طريقة 1: فحص يدوي #}
        {% can_execute_action 'product_detail' 'edit' as can_edit %}
        {% if can_edit %}
            <a href="{% url 'product_edit' product.id %}" class="btn btn-primary">
                <i class="fas fa-edit"></i> تعديل
            </a>
        {% endif %}
        
        {# طريقة 2: استخدام مكون جاهز #}
        {% render_action_button 'product_detail' 'delete' 'حذف' '#' 'btn-danger' 'fas fa-trash' %}
        {% render_action_button 'product_detail' 'inventory_count' 'جرد' '#' 'btn-warning' 'fas fa-boxes' %}
        {% render_action_button 'product_detail' 'print_barcode' 'طباعة باركود' '#' 'btn-info' 'fas fa-barcode' %}
    </div>
    
    {# ==================================================================== #}
    {# الحصول على قوائم #}
    {# ==================================================================== #}
    
    {% get_visible_fields 'product_detail' as my_visible_fields %}
    <div class="debug-info">
        <h6>الحقول المرئية لي:</h6>
        <ul>
            {% for field in my_visible_fields %}
                <li>{{ field }}</li>
            {% endfor %}
        </ul>
    </div>
    
    {% get_available_actions 'product_detail' as my_actions %}
    <div class="debug-info">
        <h6>العمليات المتاحة لي:</h6>
        <ul>
            {% for action in my_actions %}
                <li>{{ action.label }}</li>
            {% endfor %}
        </ul>
    </div>
</div>
{% endblock %}
```

---

## 🎯 أمثلة سيناريوهات واقعية

### سيناريو 1: صفحة الفاتورة

```python
# تعريف صلاحيات صفحة الفاتورة
invoice_config = PagePermissionConfig(
    page_id='invoice_detail',
    title='تفاصيل الفاتورة',
    requires_permission='sales.view'
)

# الحقول
invoice_config.add_field(FieldPermission(
    field='discount_percentage',
    roles_allowed=[ROLE_OWNER, ROLE_SALES_MANAGER, ROLE_SALES_STAFF],
    read_only_roles=[ROLE_SALES_STAFF],  # يرى لكن لا يعدل
    condition=lambda user: PermissionService.get_max_discount_percentage(user) > 0
))

invoice_config.add_field(FieldPermission(
    field='notes',
    roles_allowed=[],  # الكل يراه
))

# الأقسام
invoice_config.add_section(PageSection(
    section_id='payment_terms',
    title='شروط الدفع',
    roles_allowed=[ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_SALES_MANAGER],
))

# العمليات
invoice_config.add_action(ActionButton(
    action_id='approve',
    label='اعتماد',
    roles_allowed=[ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_SALES_MANAGER],
    requires_permission='sales.approve',
    min_approval_level=3,
    icon='fas fa-check',
    condition=lambda user, ctx: PermissionService.can_approve_amount(user, ctx.get('amount', 0))
))

invoice_config.add_action(ActionButton(
    action_id='cancel',
    label='إلغاء',
    roles_allowed=[ROLE_OWNER, ROLE_FIN_MANAGER],
    min_approval_level=4,
    danger=True,
    icon='fas fa-times',
))

FineGrainedPermissionService.register_page_config(invoice_config)
```

---

### سيناريو 2: صفحة الموظف

```python
employee_config = PagePermissionConfig(
    page_id='employee_detail',
    title='تفاصيل الموظف',
    requires_permission='hr.view'
)

# معلومات الراتب - حساسة جداً
employee_config.add_field(FieldPermission(
    field='salary',
    roles_allowed=[ROLE_OWNER, ROLE_FIN_MANAGER],
    hidden_for=[ROLE_HR_STAFF],  # حتى HR لا يرى الراتب!
))

employee_config.add_field(FieldPermission(
    field='social_insurance_number',
    roles_allowed=[ROLE_OWNER, ROLE_HR_STAFF],
))

# قسم البيانات المالية
employee_config.add_section(PageSection(
    section_id='financial_data',
    title='البيانات المالية',
    roles_allowed=[ROLE_OWNER, ROLE_FIN_MANAGER],
    fields=['salary', 'bonuses', 'deductions']
))

FineGrainedPermissionService.register_page_config(employee_config)
```

---

## ✨ المميزات

✅ **تحكم دقيق** - على مستوى كل حقل  
✅ **أقسام ديناميكية** - أجزاء كاملة تظهر/تختفي  
✅ **أزرار ذكية** - تظهر فقط للمسموح لهم  
✅ **شروط مخصصة** - منطق معقد حسب الحاجة  
✅ **سهل الاستخدام** - وسوم بسيطة في Templates  
✅ **قابل للتوسع** - أضف المزيد حسب الحاجة

---

## 📚 الملفات للقراءة

1. `fine_grained_permissions.py` - الكود الرئيسي
2. `fine_grained_perms.py` - وسوم القوالب
3. هذا الملف - الدليل الكامل

**الآن لديك تحكم كامل في كل شيء في كل صفحة! 🎉**


