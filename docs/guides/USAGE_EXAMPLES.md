# 🚀 مثال سريع - كيف تستخدم الميزات الجديدة

## في أي View:

```python
# في أول الملف
from core.security import PermissionService, require_permission
from core.security.role_definitions import ROLE_OWNER, ROLE_SALES_MANAGER

# استخدام ديكوريتر
@require_permission('sales', 'add')
def create_invoice(request):
    """فقط من لديه صلاحية إضافة في المبيعات يدخل هنا"""
    # كودك العادي
    pass

# فحص يدوي
def approve_invoice(request, invoice_id):
    # فحص الصلاحية
    if not PermissionService.can_approve(request.user, 'sales'):
        messages.error(request, 'ليس لديك صلاحية الاعتماد')
        return redirect('invoice_list')
    
    # فحص المبلغ
    invoice = Invoice.objects.get(id=invoice_id)
    if not PermissionService.can_approve_amount(request.user, invoice.total):
        messages.error(request, 'المبلغ يتجاوز سلطتك')
        return redirect('invoice_detail', invoice_id)
    
    # اعتماد الفاتورة
    invoice.status = 'approved'
    invoice.save()
    
    # تسجيل العملية
    from core.security.audit_service import SecurityAuditService
    SecurityAuditService.log_approval(
        user=request.user,
        action='اعتماد',
        module='المبيعات',
        object_type='فاتورة',
        object_id=str(invoice.id),
        amount=invoice.total,
        approved=True,
        request=request
    )
    
    return redirect('invoice_detail', invoice_id)

# فحص دور
def financial_report(request):
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_FIN_MANAGER)):
        messages.error(request, 'هذا التقرير للإدارة فقط')
        return redirect('dashboard')
    
    # عرض التقرير
    pass
```

---

## في Templates:

```django
{% load menu_tags %}

<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <title>نظام الشامل</title>
</head>
<body>
    {# القائمة الديناميكية - تتغير حسب المستخدم #}
    {% render_main_menu %}
    
    {# الإجراءات السريعة #}
    <div class="dashboard">
        {% render_quick_actions %}
    </div>
    
    {# المحتوى #}
    <div class="content">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
```

---

## استخدام Workflows:

```python
from core.workflows import get_workflow_for_type, WorkflowAction

def process_invoice_action(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    action = request.POST.get('action')  # 'approve', 'reject', 'cancel'
    
    # الحصول على workflow
    workflow = get_workflow_for_type('invoice')
    
    # تحويل action من string إلى enum
    workflow_action = WorkflowAction.APPROVE if action == 'approve' else \
                      WorkflowAction.REJECT if action == 'reject' else \
                      WorkflowAction.CANCEL
    
    # فحص إذا المستخدم يستطيع
    can, message = workflow.can_perform_action(
        current_state=invoice.workflow_state,
        action=workflow_action,
        user=request.user,
        context={'amount': invoice.total}
    )
    
    if not can:
        messages.error(request, message)
        return redirect('invoice_detail', invoice_id)
    
    # تنفيذ الإجراء
    success, new_state, msg = workflow.perform_action(
        obj=invoice,
        current_state=invoice.workflow_state,
        action=workflow_action,
        user=request.user,
        comment=request.POST.get('comment', ''),
        context={'amount': invoice.total}
    )
    
    if success:
        invoice.workflow_state = new_state.value
        invoice.save()
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    
    return redirect('invoice_detail', invoice_id)
```

---

## صلاحيات التقارير:

```python
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

## 📌 ملخص سريع:

### للصلاحيات:
```python
from core.security import PermissionService
PermissionService.can_add(user, 'sales')
PermissionService.can_approve_amount(user, amount)
```

### للقوائم:
```python
from core.navigation import MenuEngine
menu = MenuEngine.get_menu_for_user(user)
```

### للـ Workflows:
```python
from core.workflows import get_workflow_for_type
workflow = get_workflow_for_type('invoice')
```

### للتقارير:
```python
from core.security.report_permissions import ReportPermissionService
reports = ReportPermissionService.get_available_reports(user)
```

### للتدقيق:
```python
from core.security.audit_service import SecurityAuditService
SecurityAuditService.log_critical_action(...)
```

---

**كل شيء جاهز للاستخدام! 🎉**


