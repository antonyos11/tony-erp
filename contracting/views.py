"""
Views for Contracting App - واجهات نظام المقاولات
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q, Avg
from django.db.models.functions import TruncMonth, TruncDate
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from decimal import Decimal

from .models import (
    ContractingProject, ContractingWorker, ContractingAttendance,
    ContractingMaterial, ContractingEquipment, ContractingExpense,
    ContractingReceipt, ContractingContract
)
from .forms import (
    ProjectForm, WorkerForm, AttendanceForm, MaterialForm,
    EquipmentForm, ExpenseForm, ReceiptForm, ContractForm
)


# ==================== Dashboard ====================

@login_required
def dashboard(request):
    """لوحة تحكم المقاولات"""
    
    # إحصائيات عامة
    total_projects = ContractingProject.objects.count()
    active_projects = ContractingProject.objects.filter(status='active').count()
    total_workers = ContractingWorker.objects.filter(is_active=True).count()
    total_equipment = ContractingEquipment.objects.filter(status='available').count()
    
    # إجماليات مالية
    total_expenses = ContractingExpense.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_receipts = ContractingReceipt.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # آخر المشاريع
    recent_projects = ContractingProject.objects.order_by('-created_at')[:5]
    
    # المشاريع النشطة مع التقدم
    active_projects_list = ContractingProject.objects.filter(status='active').order_by('-progress_percentage')[:5]
    
    # حضور اليوم
    today = timezone.now().date()
    today_attendance = ContractingAttendance.objects.filter(date=today).count()
    today_present = ContractingAttendance.objects.filter(date=today, status='present').count()
    
    context = {
        'page_title': _('لوحة تحكم المقاولات'),
        'total_projects': total_projects,
        'active_projects': active_projects,
        'total_workers': total_workers,
        'total_equipment': total_equipment,
        'total_expenses': total_expenses,
        'total_receipts': total_receipts,
        'profit_loss': total_receipts - total_expenses,
        'recent_projects': recent_projects,
        'active_projects_list': active_projects_list,
        'today_attendance': today_attendance,
        'today_present': today_present,
    }
    return render(request, 'contracting/dashboard.html', context)


# ==================== Projects ====================

@login_required
def project_list(request):
    """قائمة المشاريع"""
    projects = ContractingProject.objects.all()
    
    # البحث والفلترة
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    if search:
        projects = projects.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(client_name__icontains=search)
        )
    
    if status:
        projects = projects.filter(status=status)
    
    # الترقيم
    paginator = Paginator(projects, 20)
    page = request.GET.get('page', 1)
    projects = paginator.get_page(page)
    
    context = {
        'page_title': _('قائمة المشاريع'),
        'projects': projects,
        'search': search,
        'current_status': status,
        'status_choices': ContractingProject.STATUS_CHOICES,
    }
    return render(request, 'contracting/project_list.html', context)


@login_required
def project_create(request):
    """إنشاء مشروع جديد"""
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            messages.success(request, _('تم إنشاء المشروع بنجاح'))
            return redirect('contracting:project_list')
    else:
        form = ProjectForm()
    
    context = {
        'page_title': _('مشروع جديد'),
        'form': form,
    }
    return render(request, 'contracting/project_form.html', context)


@login_required
def project_detail(request, pk):
    """تفاصيل المشروع"""
    project = get_object_or_404(ContractingProject, pk=pk)
    
    context = {
        'page_title': project.name,
        'project': project,
        'workers': project.workers.all()[:10],
        'expenses': project.expenses.all()[:10],
        'receipts': project.receipts.all()[:10],
        'contracts': project.contracts.all(),
    }
    return render(request, 'contracting/project_detail.html', context)


@login_required
def project_edit(request, pk):
    """تعديل المشروع"""
    project = get_object_or_404(ContractingProject, pk=pk)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث المشروع بنجاح'))
            return redirect('contracting:project_detail', pk=pk)
    else:
        form = ProjectForm(instance=project)
    
    context = {
        'page_title': _('تعديل المشروع'),
        'form': form,
        'project': project,
    }
    return render(request, 'contracting/project_form.html', context)


# ==================== Workers ====================

@login_required
def worker_list(request):
    """قائمة العمال"""
    workers = ContractingWorker.objects.all()
    
    search = request.GET.get('search', '')
    if search:
        workers = workers.filter(
            Q(name__icontains=search) |
            Q(national_id__icontains=search) |
            Q(job_title__icontains=search)
        )
    
    active_only = request.GET.get('active', '')
    if active_only == '1':
        workers = workers.filter(is_active=True)
    
    paginator = Paginator(workers, 20)
    page = request.GET.get('page', 1)
    workers = paginator.get_page(page)
    
    context = {
        'page_title': _('قائمة العمال'),
        'workers': workers,
        'search': search,
    }
    return render(request, 'contracting/worker_list.html', context)


@login_required
def worker_create(request):
    """إضافة عامل جديد"""
    if request.method == 'POST':
        form = WorkerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة العامل بنجاح'))
            return redirect('contracting:worker_list')
    else:
        form = WorkerForm()
    
    context = {
        'page_title': _('عامل جديد'),
        'form': form,
    }
    return render(request, 'contracting/worker_form.html', context)


@login_required
def worker_detail(request, pk):
    """تفاصيل العامل"""
    worker = get_object_or_404(ContractingWorker, pk=pk)
    
    attendance_records = worker.attendance_records.order_by('-date')[:30]
    
    context = {
        'page_title': worker.name,
        'worker': worker,
        'attendance_records': attendance_records,
    }
    return render(request, 'contracting/worker_detail.html', context)


# ==================== Attendance ====================

@login_required
def attendance_list(request):
    """سجلات الحضور والانصراف"""
    records = ContractingAttendance.objects.select_related('worker', 'project').all()
    
    date_filter = request.GET.get('date', '')
    project_filter = request.GET.get('project', '')
    
    if date_filter:
        records = records.filter(date=date_filter)
    else:
        # افتراضياً عرض اليوم
        records = records.filter(date=timezone.now().date())
    
    if project_filter:
        records = records.filter(project_id=project_filter)
    
    paginator = Paginator(records, 50)
    page = request.GET.get('page', 1)
    records = paginator.get_page(page)
    
    projects = ContractingProject.objects.filter(status='active')
    
    context = {
        'page_title': _('الحضور والانصراف'),
        'records': records,
        'projects': projects,
        'date_filter': date_filter or timezone.now().date().isoformat(),
        'project_filter': project_filter,
    }
    return render(request, 'contracting/attendance_list.html', context)


@login_required
def attendance_create(request):
    """تسجيل حضور"""
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.created_by = request.user
            attendance.save()
            messages.success(request, _('تم تسجيل الحضور بنجاح'))
            return redirect('contracting:attendance_list')
    else:
        form = AttendanceForm()
    
    context = {
        'page_title': _('تسجيل حضور'),
        'form': form,
    }
    return render(request, 'contracting/attendance_form.html', context)


@login_required
def attendance_report(request):
    """تقرير الحضور"""
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    project_id = request.GET.get('project', '')
    
    records = ContractingAttendance.objects.select_related('worker', 'project')
    
    if from_date:
        records = records.filter(date__gte=from_date)
    if to_date:
        records = records.filter(date__lte=to_date)
    if project_id:
        records = records.filter(project_id=project_id)
    
    # إحصائيات
    summary = records.aggregate(
        total_records=Count('id'),
        present_count=Count('id', filter=Q(status='present')),
        absent_count=Count('id', filter=Q(status='absent')),
        total_wages=Sum('total_wage'),
        total_hours=Sum('hours_worked'),
    )
    
    # تجميع حسب العامل
    worker_summary = records.values('worker__name').annotate(
        days_present=Count('id', filter=Q(status='present')),
        total_wages=Sum('total_wage'),
    ).order_by('-total_wages')
    
    projects = ContractingProject.objects.filter(status='active')
    
    context = {
        'page_title': _('تقرير الحضور'),
        'records': records[:100],
        'summary': summary,
        'worker_summary': worker_summary,
        'projects': projects,
        'from_date': from_date,
        'to_date': to_date,
        'project_id': project_id,
    }
    return render(request, 'contracting/attendance_report.html', context)


# ==================== Materials ====================

@login_required
def material_list(request):
    """قائمة المواد"""
    materials = ContractingMaterial.objects.all()
    
    search = request.GET.get('search', '')
    if search:
        materials = materials.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search)
        )
    
    paginator = Paginator(materials, 20)
    page = request.GET.get('page', 1)
    materials = paginator.get_page(page)
    
    context = {
        'page_title': _('قائمة المواد'),
        'materials': materials,
        'search': search,
    }
    return render(request, 'contracting/material_list.html', context)


@login_required
def material_create(request):
    """إضافة مادة جديدة"""
    if request.method == 'POST':
        form = MaterialForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة المادة بنجاح'))
            return redirect('contracting:material_list')
    else:
        form = MaterialForm()
    
    context = {
        'page_title': _('إضافة مادة'),
        'form': form,
    }
    return render(request, 'contracting/material_form.html', context)


# ==================== Equipment ====================

@login_required
def equipment_list(request):
    """قائمة المعدات"""
    equipment = ContractingEquipment.objects.all()
    
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    if search:
        equipment = equipment.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search)
        )
    
    if status:
        equipment = equipment.filter(status=status)
    
    paginator = Paginator(equipment, 20)
    page = request.GET.get('page', 1)
    equipment = paginator.get_page(page)
    
    context = {
        'page_title': _('قائمة المعدات'),
        'equipment': equipment,
        'search': search,
        'current_status': status,
        'status_choices': ContractingEquipment.STATUS_CHOICES,
    }
    return render(request, 'contracting/equipment_list.html', context)


@login_required
def equipment_create(request):
    """إضافة معدة جديدة"""
    if request.method == 'POST':
        form = EquipmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة المعدة بنجاح'))
            return redirect('contracting:equipment_list')
    else:
        form = EquipmentForm()
    
    context = {
        'page_title': _('إضافة معدة'),
        'form': form,
    }
    return render(request, 'contracting/equipment_form.html', context)


# ==================== Expenses ====================

@login_required
def expense_list(request):
    """قائمة المصروفات"""
    expenses = ContractingExpense.objects.select_related('project').all()
    
    project_filter = request.GET.get('project', '')
    expense_type = request.GET.get('type', '')
    
    if project_filter:
        expenses = expenses.filter(project_id=project_filter)
    if expense_type:
        expenses = expenses.filter(expense_type=expense_type)
    
    paginator = Paginator(expenses, 20)
    page = request.GET.get('page', 1)
    expenses = paginator.get_page(page)
    
    projects = ContractingProject.objects.all()
    
    context = {
        'page_title': _('المصروفات'),
        'expenses': expenses,
        'projects': projects,
        'project_filter': project_filter,
        'expense_type': expense_type,
        'type_choices': ContractingExpense.EXPENSE_TYPE_CHOICES,
    }
    return render(request, 'contracting/expense_list.html', context)


@login_required
def expense_create(request):
    """إضافة مصروف"""
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            messages.success(request, _('تم إضافة المصروف بنجاح'))
            return redirect('contracting:expense_list')
    else:
        form = ExpenseForm()
    
    context = {
        'page_title': _('إضافة مصروف'),
        'form': form,
    }
    return render(request, 'contracting/expense_form.html', context)


# ==================== Receipts ====================

@login_required
def receipt_list(request):
    """قائمة المقبوضات"""
    receipts = ContractingReceipt.objects.select_related('project').all()
    
    project_filter = request.GET.get('project', '')
    
    if project_filter:
        receipts = receipts.filter(project_id=project_filter)
    
    paginator = Paginator(receipts, 20)
    page = request.GET.get('page', 1)
    receipts = paginator.get_page(page)
    
    projects = ContractingProject.objects.all()
    
    context = {
        'page_title': _('المقبوضات'),
        'receipts': receipts,
        'projects': projects,
        'project_filter': project_filter,
    }
    return render(request, 'contracting/receipt_list.html', context)


@login_required
def receipt_create(request):
    """إضافة مقبوض"""
    if request.method == 'POST':
        form = ReceiptForm(request.POST)
        if form.is_valid():
            receipt = form.save(commit=False)
            receipt.created_by = request.user
            receipt.save()
            messages.success(request, _('تم إضافة المقبوض بنجاح'))
            return redirect('contracting:receipt_list')
    else:
        form = ReceiptForm()
    
    context = {
        'page_title': _('إضافة مقبوض'),
        'form': form,
    }
    return render(request, 'contracting/receipt_form.html', context)


# ==================== Contracts ====================

@login_required
def contract_list(request):
    """قائمة العقود"""
    contracts = ContractingContract.objects.select_related('project').all()
    
    project_filter = request.GET.get('project', '')
    status = request.GET.get('status', '')
    
    if project_filter:
        contracts = contracts.filter(project_id=project_filter)
    if status:
        contracts = contracts.filter(status=status)
    
    paginator = Paginator(contracts, 20)
    page = request.GET.get('page', 1)
    contracts = paginator.get_page(page)
    
    projects = ContractingProject.objects.all()
    
    context = {
        'page_title': _('العقود'),
        'contracts': contracts,
        'projects': projects,
        'project_filter': project_filter,
        'current_status': status,
        'status_choices': ContractingContract.STATUS_CHOICES,
    }
    return render(request, 'contracting/contract_list.html', context)


@login_required
def contract_create(request):
    """إنشاء عقد جديد"""
    if request.method == 'POST':
        form = ContractForm(request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.created_by = request.user
            contract.save()
            messages.success(request, _('تم إنشاء العقد بنجاح'))
            return redirect('contracting:contract_list')
    else:
        form = ContractForm()
    
    context = {
        'page_title': _('عقد جديد'),
        'form': form,
    }
    return render(request, 'contracting/contract_form.html', context)


@login_required
def contract_detail(request, pk):
    """تفاصيل العقد"""
    contract = get_object_or_404(ContractingContract, pk=pk)
    
    context = {
        'page_title': contract.title,
        'contract': contract,
    }
    return render(request, 'contracting/contract_detail.html', context)


# ==================== Reports ====================

@login_required
def reports_dashboard(request):
    """لوحة التقارير"""
    
    # إجماليات المشاريع
    projects_stats = ContractingProject.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(status='active')),
        completed=Count('id', filter=Q(status='completed')),
        total_value=Sum('contract_value'),
    )
    
    # إجماليات مالية
    financial_stats = {
        'total_expenses': ContractingExpense.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'total_receipts': ContractingReceipt.objects.aggregate(total=Sum('amount'))['total'] or 0,
    }
    financial_stats['profit_loss'] = financial_stats['total_receipts'] - financial_stats['total_expenses']
    
    # إحصائيات العمال
    workers_stats = ContractingWorker.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(is_active=True)),
    )
    
    context = {
        'page_title': _('تقارير المقاولات'),
        'projects_stats': projects_stats,
        'financial_stats': financial_stats,
        'workers_stats': workers_stats,
    }
    return render(request, 'contracting/reports_dashboard.html', context)


@login_required
def daily_report(request):
    """التقرير اليومي"""
    date = request.GET.get('date', timezone.now().date().isoformat())
    
    # حضور اليوم
    attendance = ContractingAttendance.objects.filter(date=date).select_related('worker', 'project')
    
    attendance_summary = attendance.aggregate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
        absent=Count('id', filter=Q(status='absent')),
        total_wages=Sum('total_wage'),
    )
    
    # مصروفات اليوم
    expenses = ContractingExpense.objects.filter(date=date)
    expenses_total = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    # مقبوضات اليوم
    receipts = ContractingReceipt.objects.filter(date=date)
    receipts_total = receipts.aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'page_title': _('التقرير اليومي'),
        'date': date,
        'attendance': attendance,
        'attendance_summary': attendance_summary,
        'expenses': expenses,
        'expenses_total': expenses_total,
        'receipts': receipts,
        'receipts_total': receipts_total,
    }
    return render(request, 'contracting/daily_report.html', context)


@login_required
def customers_report(request):
    """تقرير تحليل العملاء"""
    
    # تجميع المشاريع حسب العميل
    customers = ContractingProject.objects.values('client_name').annotate(
        projects_count=Count('id'),
        total_value=Sum('contract_value'),
        total_expenses=Sum('expenses__amount'),
        total_receipts=Sum('receipts__amount'),
    ).order_by('-total_value')
    
    context = {
        'page_title': _('تحليل العملاء'),
        'customers': customers,
    }
    return render(request, 'contracting/customers_report.html', context)
