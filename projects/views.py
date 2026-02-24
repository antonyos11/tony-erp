"""
Views لإدارة المشاريع
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, Avg, F
from decimal import Decimal
from .models import (
    Project, ProjectType, ProjectCategory, ProjectAdjustment,
    BOQItem, Contractor, ContractorContract, ProjectLabour,
    LabourAttendance, ProjectExpense, ProjectInvoice
)


@login_required
def dashboard(request):
    """لوحة تحكم المشاريع"""
    projects = Project.objects.all()
    context = {
        'total_projects': projects.count(),
        'active_projects': projects.filter(status='in_progress').count(),
        'completed_projects': projects.filter(status='completed').count(),
        'total_budget': projects.aggregate(total=Sum('budget'))['total'] or 0,
        'recent_projects': projects[:5],
    }
    return render(request, 'projects/dashboard.html', context)


@login_required
def project_list(request):
    """قائمة المشاريع"""
    projects = Project.objects.select_related('project_type', 'category', 'manager').all()
    return render(request, 'projects/project_list.html', {'projects': projects})


@login_required
def project_create(request):
    """إنشاء مشروع جديد"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()

        if not name or not code:
            messages.error(request, 'الاسم والكود مطلوبان')
        elif Project.objects.filter(code=code).exists():
            messages.error(request, 'هذا الكود مستخدم مسبقاً')
        else:
            project = Project.objects.create(
                name=name,
                code=code,
                description=request.POST.get('description', ''),
                project_type_id=request.POST.get('project_type') or None,
                category_id=request.POST.get('category') or None,
                budget=Decimal(request.POST.get('budget', '0') or '0'),
                start_date=request.POST.get('start_date') or None,
                end_date=request.POST.get('end_date') or None,
                client_name=request.POST.get('client_name', ''),
                client_contact=request.POST.get('client_contact', ''),
                created_by=request.user
            )
            messages.success(request, 'تم إنشاء المشروع بنجاح')
            return redirect('projects:project_list')

    types = ProjectType.objects.filter(is_active=True)
    categories = ProjectCategory.objects.filter(is_active=True)
    return render(request, 'projects/project_form.html', {
        'title': 'إنشاء مشروع جديد',
        'types': types,
        'categories': categories
    })


@login_required
def project_detail(request, pk):
    """تفاصيل المشروع"""
    project = get_object_or_404(Project, pk=pk)
    boq_items = BOQItem.objects.filter(project=project)
    expenses = ProjectExpense.objects.filter(project=project)
    invoices = ProjectInvoice.objects.filter(project=project)
    labour = ProjectLabour.objects.filter(project=project)
    contracts = ContractorContract.objects.filter(project=project).select_related('contractor')
    adjustments = ProjectAdjustment.objects.filter(project=project)

    context = {
        'project': project,
        'boq_items': boq_items,
        'expenses': expenses,
        'invoices': invoices,
        'labour': labour,
        'contracts': contracts,
        'adjustments': adjustments,
        'total_expenses': expenses.aggregate(total=Sum('amount'))['total'] or 0,
        'total_invoices': invoices.aggregate(total=Sum('amount'))['total'] or 0,
        'total_boq': boq_items.aggregate(total=Sum('total_price'))['total'] or 0,
    }
    return render(request, 'projects/project_detail.html', context)


# ===== أنواع المشاريع =====
@login_required
def type_list(request):
    """قائمة أنواع المشاريع"""
    types = ProjectType.objects.all()
    return render(request, 'projects/types/list.html', {'types': types})


@login_required
def type_create(request):
    """إنشاء نوع مشروع"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        if name and code:
            ProjectType.objects.create(name=name, code=code, description=request.POST.get('description', ''))
            messages.success(request, 'تم إنشاء النوع بنجاح')
            return redirect('projects:type_list')
    return render(request, 'projects/types/form.html', {'title': 'إنشاء نوع جديد'})


# ===== تصنيفات المشاريع =====
@login_required
def category_list(request):
    """قائمة تصنيفات المشاريع"""
    categories = ProjectCategory.objects.all()
    return render(request, 'projects/categories/list.html', {'categories': categories})


@login_required
def category_create(request):
    """إنشاء تصنيف"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        parent_id = request.POST.get('parent') or None
        if name and code:
            ProjectCategory.objects.create(name=name, code=code, parent_id=parent_id)
            messages.success(request, 'تم إنشاء التصنيف بنجاح')
            return redirect('projects:category_list')
    parent_categories = ProjectCategory.objects.filter(is_active=True)
    return render(request, 'projects/categories/form.html', {
        'title': 'إنشاء تصنيف جديد',
        'parent_categories': parent_categories,
    })


# ===== التعديلات =====
@login_required
def adjustment_list(request):
    """قائمة التعديلات"""
    adjustments = ProjectAdjustment.objects.select_related('project').all()
    return render(request, 'projects/adjustments/list.html', {'adjustments': adjustments})


# ===== جدول الكميات =====
@login_required
def boq_list(request):
    """جدول الكميات"""
    project_id = request.GET.get('project')
    items = BOQItem.objects.select_related('project').all()
    if project_id:
        items = items.filter(project_id=project_id)
    projects = Project.objects.all()
    return render(request, 'projects/boq/list.html', {'items': items, 'projects': projects})


# ===== المقاولين =====
@login_required
def contractor_list(request):
    """قائمة المقاولين"""
    contractors = Contractor.objects.annotate(
        contract_count=Count('contracts'),
        total_amount=Sum('contracts__amount')
    ).all()
    return render(request, 'projects/contractors/list.html', {'contractors': contractors})


@login_required
def contractor_create(request):
    """إنشاء مقاول"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        if name and code:
            Contractor.objects.create(
                name=name,
                code=code,
                specialty=request.POST.get('specialty', ''),
                phone=request.POST.get('phone', ''),
                email=request.POST.get('email', ''),
                address=request.POST.get('address', ''),
                tax_number=request.POST.get('tax_number', ''),
            )
            messages.success(request, 'تم إنشاء المقاول بنجاح')
            return redirect('projects:contractor_list')
    return render(request, 'projects/contractors/form.html', {'title': 'إضافة مقاول جديد'})


@login_required
def contractor_contracts(request):
    """عقود المقاولين"""
    contracts = ContractorContract.objects.select_related('project', 'contractor').all()
    return render(request, 'projects/contractors/contracts.html', {'contracts': contracts})


@login_required
def contractor_statements(request):
    """مستخلصات المقاولين"""
    contracts = ContractorContract.objects.select_related('project', 'contractor').all()
    contractors = Contractor.objects.filter(is_active=True)
    return render(request, 'projects/contractors/statements.html', {
        'contracts': contracts,
        'contractors': contractors,
    })


# ===== العمالة =====
@login_required
def labour_list(request):
    """قائمة العمالة"""
    labour = ProjectLabour.objects.select_related('project').all()
    return render(request, 'projects/labour/list.html', {'labour': labour})


@login_required
def labour_attendance(request):
    """سجل الحضور"""
    attendance = LabourAttendance.objects.select_related('labour', 'labour__project').all()[:100]
    return render(request, 'projects/labour/attendance.html', {'attendance': attendance})


@login_required
def labour_attendance_create(request):
    """تسجيل حضور"""
    if request.method == 'POST':
        labour_id = request.POST.get('labour')
        date = request.POST.get('date')
        hours_worked = request.POST.get('hours_worked', 8)
        overtime_hours = request.POST.get('overtime_hours', 0)
        notes = request.POST.get('notes', '')

        try:
            labour = ProjectLabour.objects.get(id=labour_id)
            LabourAttendance.objects.create(
                labour=labour,
                date=date,
                hours_worked=Decimal(str(hours_worked)),
                overtime_hours=Decimal(str(overtime_hours)),
                notes=notes
            )
            messages.success(request, 'تم تسجيل الحضور بنجاح')
        except ProjectLabour.DoesNotExist:
            messages.error(request, 'العامل غير موجود')
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
        return redirect('projects:labour_attendance')
    labour = ProjectLabour.objects.filter(is_active=True).select_related('project')
    return render(request, 'projects/labour/attendance_form.html', {'labour': labour})


@login_required
def labour_attendance_report(request):
    """تقرير الحضور"""
    # فلترة حسب المشروع أو العامل
    project_id = request.GET.get('project')
    labour_id = request.GET.get('labour')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    attendance = LabourAttendance.objects.select_related('labour', 'labour__project').all()

    if project_id:
        attendance = attendance.filter(labour__project_id=project_id)
    if labour_id:
        attendance = attendance.filter(labour_id=labour_id)
    if date_from:
        attendance = attendance.filter(date__gte=date_from)
    if date_to:
        attendance = attendance.filter(date__lte=date_to)

    # إحصائيات
    total_hours = attendance.aggregate(total=Sum('hours_worked'))['total'] or 0
    total_overtime = attendance.aggregate(total=Sum('overtime_hours'))['total'] or 0
    total_records = attendance.count()

    # ملخص لكل عامل
    labour_summary = attendance.values(
        'labour__id', 'labour__name', 'labour__job_title', 'labour__daily_rate', 'labour__project__name'
    ).annotate(
        total_hours=Sum('hours_worked'),
        total_overtime=Sum('overtime_hours'),
        days_count=Count('id'),
    ).order_by('-total_hours')

    projects = Project.objects.all()
    labour_list_qs = ProjectLabour.objects.filter(is_active=True).select_related('project')

    context = {
        'attendance': attendance[:200],
        'total_hours': total_hours,
        'total_overtime': total_overtime,
        'total_records': total_records,
        'labour_summary': labour_summary,
        'projects': projects,
        'labour_list': labour_list_qs,
    }
    return render(request, 'projects/labour/attendance_report.html', context)


# ===== المالية =====
@login_required
def finance_mandates(request):
    """الاعتمادات المالية"""
    projects = Project.objects.all()
    total_budget = projects.aggregate(total=Sum('budget'))['total'] or 0
    total_actual = projects.aggregate(total=Sum('actual_cost'))['total'] or 0
    total_expenses = ProjectExpense.objects.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'projects': projects,
        'total_budget': total_budget,
        'total_actual': total_actual,
        'total_expenses': total_expenses,
    }
    return render(request, 'projects/finance/mandates.html', context)


@login_required
def finance_expenses(request):
    """المصروفات"""
    expenses = ProjectExpense.objects.select_related('project').all()
    projects = Project.objects.all()
    total = expenses.aggregate(total=Sum('amount'))['total'] or 0

    # فلترة
    project_id = request.GET.get('project')
    expense_type = request.GET.get('expense_type')
    if project_id:
        expenses = expenses.filter(project_id=project_id)
    if expense_type:
        expenses = expenses.filter(expense_type=expense_type)

    context = {
        'expenses': expenses,
        'projects': projects,
        'total': total,
    }
    return render(request, 'projects/finance/expenses.html', context)


@login_required
def finance_invoices(request):
    """الفواتير"""
    invoices = ProjectInvoice.objects.select_related('project').all()
    projects = Project.objects.all()
    total = invoices.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'invoices': invoices,
        'projects': projects,
        'total': total,
    }
    return render(request, 'projects/finance/invoices.html', context)


# ===== التقارير =====
@login_required
def reports_overview(request):
    """نظرة عامة على التقارير"""
    projects = Project.objects.all()
    total_projects = projects.count()
    active_projects = projects.filter(status='in_progress').count()
    completed_projects = projects.filter(status='completed').count()
    on_hold_projects = projects.filter(status='on_hold').count()

    total_budget = projects.aggregate(total=Sum('budget'))['total'] or 0
    total_actual = projects.aggregate(total=Sum('actual_cost'))['total'] or 0
    total_expenses = ProjectExpense.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_invoices = ProjectInvoice.objects.aggregate(total=Sum('amount'))['total'] or 0

    total_contractors = Contractor.objects.count()
    total_labour = ProjectLabour.objects.count()
    total_contracts = ContractorContract.objects.count()

    context = {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'on_hold_projects': on_hold_projects,
        'total_budget': total_budget,
        'total_actual': total_actual,
        'total_expenses': total_expenses,
        'total_invoices': total_invoices,
        'total_contractors': total_contractors,
        'total_labour': total_labour,
        'total_contracts': total_contracts,
        'projects': projects,
    }
    return render(request, 'projects/reports/overview.html', context)


@login_required
def reports_stats(request):
    """إحصائيات المشاريع"""
    projects = Project.objects.all()

    by_status = projects.values('status').annotate(count=Count('id')).order_by('status')
    by_type = projects.values('project_type__name').annotate(count=Count('id')).order_by('-count')
    by_category = projects.values('category__name').annotate(count=Count('id')).order_by('-count')

    total_budget = projects.aggregate(total=Sum('budget'))['total'] or 0
    total_actual = projects.aggregate(total=Sum('actual_cost'))['total'] or 0
    avg_progress = projects.aggregate(avg=Avg('progress'))['avg'] or 0

    context = {
        'projects': projects,
        'by_status': by_status,
        'by_type': by_type,
        'by_category': by_category,
        'total_budget': total_budget,
        'total_actual': total_actual,
        'avg_progress': avg_progress,
    }
    return render(request, 'projects/reports/stats.html', context)


@login_required
def reports_progress(request):
    """تقرير التقدم"""
    projects = Project.objects.select_related('project_type', 'category').all()
    return render(request, 'projects/reports/progress.html', {'projects': projects})


@login_required
def reports_costs(request):
    """تقرير التكاليف"""
    projects = Project.objects.all()
    expenses = ProjectExpense.objects.select_related('project').all()

    # ملخص حسب نوع المصروف
    by_type = expenses.values('expense_type').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')

    # ملخص حسب المشروع
    by_project = expenses.values('project__name', 'project__code', 'project__budget').annotate(
        total_spent=Sum('amount'),
        expense_count=Count('id')
    ).order_by('-total_spent')

    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    total_budget = projects.aggregate(total=Sum('budget'))['total'] or 0

    context = {
        'projects': projects,
        'expenses': expenses[:100],
        'by_type': by_type,
        'by_project': by_project,
        'total_expenses': total_expenses,
        'total_budget': total_budget,
    }
    return render(request, 'projects/reports/costs.html', context)


@login_required
def reports_contractors(request):
    """تقرير المقاولين"""
    contractors = Contractor.objects.annotate(
        contract_count=Count('contracts'),
        total_amount=Sum('contracts__amount'),
    )
    return render(request, 'projects/reports/contractors.html', {'contractors': contractors})


@login_required
def reports_labour_statements(request):
    """كشوف العمالة"""
    labour = ProjectLabour.objects.select_related('project').all()
    projects = Project.objects.all()

    # ملخص لكل عامل مع ساعات الحضور
    labour_data = []
    for worker in labour:
        attendance = LabourAttendance.objects.filter(labour=worker)
        total_hours = attendance.aggregate(total=Sum('hours_worked'))['total'] or 0
        total_overtime = attendance.aggregate(total=Sum('overtime_hours'))['total'] or 0
        days_count = attendance.count()
        total_wage = float(worker.daily_rate) * float(days_count)
        labour_data.append({
            'worker': worker,
            'total_hours': total_hours,
            'total_overtime': total_overtime,
            'days_count': days_count,
            'total_wage': total_wage,
        })

    total_wages = sum(item['total_wage'] for item in labour_data)

    context = {
        'labour_data': labour_data,
        'projects': projects,
        'total_workers': labour.count(),
        'total_wages': total_wages,
    }
    return render(request, 'projects/reports/labour_statements.html', context)


# ===== خطط المشاريع =====
@login_required
def project_plans(request):
    """خطط المشاريع"""
    projects = Project.objects.select_related('project_type', 'category', 'manager').all()
    return render(request, 'projects/plans/list.html', {'projects': projects})


# ===== كميات المشاريع =====
@login_required
def project_quantities(request):
    """كميات المشاريع"""
    project_id = request.GET.get('project')
    items = BOQItem.objects.select_related('project').all()
    if project_id:
        items = items.filter(project_id=project_id)

    projects = Project.objects.all()
    total_quantity = items.aggregate(total=Sum('total_price'))['total'] or 0

    context = {
        'items': items,
        'projects': projects,
        'total_quantity': total_quantity,
    }
    return render(request, 'projects/quantities/list.html', context)


# ===== مستخلصات المالك =====
@login_required
def owner_statements(request):
    """مستخلصات المالك"""
    invoices = ProjectInvoice.objects.select_related('project').all()
    projects = Project.objects.all()
    total = invoices.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'invoices': invoices,
        'projects': projects,
        'total': total,
    }
    return render(request, 'projects/owner_statements/list.html', context)


# ===== أوامر الشراء =====
@login_required
def purchase_orders(request):
    """أوامر الشراء"""
    # أوامر الشراء تعتمد على مصروفات المواد
    expenses = ProjectExpense.objects.select_related('project').filter(
        expense_type='material'
    )
    projects = Project.objects.all()
    total = expenses.aggregate(total=Sum('amount'))['total'] or 0

    # كل المصروفات كأوامر شراء
    all_expenses = ProjectExpense.objects.select_related('project').all()

    context = {
        'expenses': all_expenses,
        'material_expenses': expenses,
        'projects': projects,
        'total': total,
    }
    return render(request, 'projects/purchase_orders/list.html', context)


# ===== التقديرات =====
@login_required
def estimations(request):
    """التقديرات"""
    projects = Project.objects.all()
    boq_items = BOQItem.objects.select_related('project').all()

    # ملخص حسب المشروع
    project_estimates = projects.annotate(
        boq_total=Sum('boq_items__total_price'),
        boq_count=Count('boq_items'),
    )

    total_estimates = boq_items.aggregate(total=Sum('total_price'))['total'] or 0

    context = {
        'projects': project_estimates,
        'boq_items': boq_items[:100],
        'total_estimates': total_estimates,
    }
    return render(request, 'projects/estimations/list.html', context)


# ===== العقود =====
@login_required
def contracts(request):
    """العقود"""
    contracts_qs = ContractorContract.objects.select_related('project', 'contractor').all()
    projects = Project.objects.all()
    total = contracts_qs.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'contracts': contracts_qs,
        'projects': projects,
        'total': total,
    }
    return render(request, 'projects/contracts/list.html', context)
