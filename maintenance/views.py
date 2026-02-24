from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Avg, F
from django.utils import timezone
from django.template.loader import render_to_string
from datetime import datetime, timedelta
import json

from .models import (
    MachineCategory, Machine, MaintenanceType, SparePart, MaintenanceRequest,
    MaintenanceSchedule, MaintenanceRecord, SparePartUsage, MaintenanceChecklist
)
from .forms import (
    MachineForm, MachineCategoryForm, SparePartForm, MaintenanceTypeForm,
    MaintenanceRequestForm, MaintenanceScheduleForm, MaintenanceRecordForm
)


@login_required
def maintenance_dashboard(request):
    """الصفحة الرئيسية لنظام الصيانة"""
    
    # إحصائيات عامة
    total_machines = Machine.objects.filter(is_active=True).count()
    operational_machines = Machine.objects.filter(status='operational', is_active=True).count()
    machines_in_maintenance = Machine.objects.filter(status='maintenance', is_active=True).count()
    broken_machines = Machine.objects.filter(status='breakdown', is_active=True).count()
    
    # طلبات الصيانة
    pending_requests = MaintenanceRequest.objects.filter(status='submitted').count()
    in_progress_requests = MaintenanceRequest.objects.filter(status='in_progress').count()
    
    # الصيانة المتأخرة
    today = timezone.now().date()
    overdue_schedules = MaintenanceSchedule.objects.filter(
        next_due_date__lt=today, 
        is_active=True
    ).count()
    
    # الصيانة القادمة (خلال أسبوع)
    next_week = today + timedelta(days=7)
    upcoming_schedules = MaintenanceSchedule.objects.filter(
        next_due_date__lte=next_week,
        next_due_date__gte=today,
        is_active=True
    ).count()
    
    # قطع الغيار منخفضة المخزون
    low_stock_parts = SparePart.objects.filter(
        current_stock__lte=F('minimum_stock'),
        is_active=True
    ).count()
    
    # آخر 5 سجلات صيانة
    recent_records = MaintenanceRecord.objects.select_related('machine', 'maintenance_type', 'technician')[:5]
    
    # الصيانة المتأخرة (تفاصيل)
    overdue_maintenance = MaintenanceSchedule.objects.filter(
        next_due_date__lt=today,
        is_active=True
    ).select_related('machine', 'maintenance_type')[:10]
    
    # الماكينات التي تحتاج انتباه
    machines_need_attention = Machine.objects.filter(
        Q(condition__in=['poor', 'critical']) | Q(status='breakdown'),
        is_active=True
    ).select_related('category', 'location')[:10]
    
    # إحصائيات التكلفة (آخر 30 يوم)
    last_month = today - timedelta(days=30)
    maintenance_cost_last_month = MaintenanceRecord.objects.filter(
        start_datetime__date__gte=last_month
    ).aggregate(
        total=Sum('labor_cost') + Sum('parts_cost') + Sum('external_service_cost') + Sum('other_costs')
    )['total'] or 0
    
    context = {
        'total_machines': total_machines,
        'operational_machines': operational_machines,
        'machines_in_maintenance': machines_in_maintenance,
        'broken_machines': broken_machines,
        'pending_requests': pending_requests,
        'in_progress_requests': in_progress_requests,
        'overdue_schedules': overdue_schedules,
        'upcoming_schedules': upcoming_schedules,
        'low_stock_parts': low_stock_parts,
        'recent_records': recent_records,
        'overdue_maintenance': overdue_maintenance,
        'machines_need_attention': machines_need_attention,
        'maintenance_cost_last_month': maintenance_cost_last_month,
    }
    
    return render(request, 'maintenance/dashboard.html', context)


@login_required
def machine_list(request):
    """قائمة الماكينات"""
    
    machines = Machine.objects.filter(is_active=True).select_related(
        'category', 'location', 'work_center', 'responsible_employee'
    )
    
    # فلترة
    category = request.GET.get('category')
    status = request.GET.get('status')
    condition = request.GET.get('condition')
    location = request.GET.get('location')
    search = request.GET.get('search')
    
    if category:
        machines = machines.filter(category_id=category)
    if status:
        machines = machines.filter(status=status)
    if condition:
        machines = machines.filter(condition=condition)
    if location:
        machines = machines.filter(location_id=location)
    if search:
        machines = machines.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(manufacturer__icontains=search) |
            Q(model__icontains=search)
        )
    
    # ترتيب
    sort_by = request.GET.get('sort', 'code')
    machines = machines.order_by(sort_by)
    
    # التصفح
    paginator = Paginator(machines, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # للفلاتر
    categories = MachineCategory.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'current_category': category,
        'current_status': status,
        'current_condition': condition,
        'current_location': location,
        'current_search': search,
        'current_sort': sort_by,
    }
    
    return render(request, 'maintenance/machine_list.html', context)


@login_required
def machine_detail(request, pk):
    """تفاصيل الماكينة"""
    
    machine = get_object_or_404(Machine, pk=pk, is_active=True)
    
    # آخر سجلات الصيانة
    maintenance_records = MaintenanceRecord.objects.filter(
        machine=machine
    ).select_related('maintenance_type', 'technician').order_by('-start_datetime')[:10]
    
    # طلبات الصيانة النشطة
    active_requests = MaintenanceRequest.objects.filter(
        machine=machine,
        status__in=['submitted', 'approved', 'in_progress']
    ).select_related('maintenance_type', 'assigned_to').order_by('-request_date')
    
    # جدولة الصيانة
    maintenance_schedules = MaintenanceSchedule.objects.filter(
        machine=machine,
        is_active=True
    ).select_related('maintenance_type').order_by('next_due_date')
    
    # قطع الغيار المتوافقة
    # استخدام الاستعلام المباشر لتفادي مشاكل المحلل مع علاقات الرجوع
    compatible_parts = SparePart.objects.filter(compatible_machines=machine, is_active=True)[:10]
    
    # إحصائيات
    total_maintenance_cost = maintenance_records.aggregate(
        total=Sum('labor_cost') + Sum('parts_cost') + Sum('external_service_cost') + Sum('other_costs')
    )['total'] or 0
    
    avg_maintenance_duration = maintenance_records.aggregate(
        avg=Avg('actual_duration_hours')
    )['avg'] or 0
    
    context = {
        'machine': machine,
        'maintenance_records': maintenance_records,
        'active_requests': active_requests,
        'maintenance_schedules': maintenance_schedules,
        'compatible_parts': compatible_parts,
        'total_maintenance_cost': total_maintenance_cost,
        'avg_maintenance_duration': avg_maintenance_duration,
    }
    
    return render(request, 'maintenance/machine_detail.html', context)


@login_required
def machine_add(request):
    """إضافة ماكينة جديدة"""
    
    if request.method == 'POST':
        form = MachineForm(request.POST)
        if form.is_valid():
            machine = form.save(commit=False)
            machine.created_by = request.user
            machine.save()
            form.save_m2m()
            messages.success(request, 'تم إضافة الماكينة بنجاح')
            return redirect('maintenance:machine_detail', pk=machine.pk)
    else:
        form = MachineForm()
    
    return render(request, 'maintenance/machine_form.html', {'form': form, 'title': 'إضافة ماكينة جديدة'})


@login_required
def machine_edit(request, pk):
    """تعديل الماكينة"""
    
    machine = get_object_or_404(Machine, pk=pk, is_active=True)
    
    if request.method == 'POST':
        form = MachineForm(request.POST, instance=machine)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث بيانات الماكينة بنجاح')
            return redirect('maintenance:machine_detail', pk=machine.pk)
    else:
        form = MachineForm(instance=machine)
    
    return render(request, 'maintenance/machine_form.html', {
        'form': form, 
        'machine': machine,
        'title': f'تعديل {machine.name}'
    })


@login_required
def spare_part_list(request):
    """قائمة قطع الغيار"""
    
    parts = SparePart.objects.filter(is_active=True).select_related('storage_location')
    
    # فلترة
    category = request.GET.get('category')
    stock_status = request.GET.get('stock_status')
    location = request.GET.get('location')
    search = request.GET.get('search')
    
    if category:
        parts = parts.filter(category=category)
    if stock_status:
        if stock_status == 'low':
            parts = parts.filter(current_stock__lte=F('minimum_stock'))
        elif stock_status == 'out':
            parts = parts.filter(current_stock=0)
        elif stock_status == 'reorder':
            parts = parts.filter(current_stock__lte=F('reorder_point'))
    if location:
        parts = parts.filter(storage_location_id=location)
    if search:
        parts = parts.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(manufacturer__icontains=search) |
            Q(part_number__icontains=search)
        )
    
    # ترتيب
    sort_by = request.GET.get('sort', 'code')
    parts = parts.order_by(sort_by)
    
    # التصفح
    paginator = Paginator(parts, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'current_category': category,
        'current_stock_status': stock_status,
        'current_location': location,
        'current_search': search,
        'current_sort': sort_by,
    }
    
    return render(request, 'maintenance/spare_part_list.html', context)


@login_required
def spare_part_detail(request, pk):
    """تفاصيل قطعة الغيار"""
    
    part = get_object_or_404(SparePart, pk=pk, is_active=True)
    
    # الماكينات المتوافقة
    compatible_machines = part.compatible_machines.filter(is_active=True)
    
    # آخر استخدامات
    recent_usage = SparePartUsage.objects.filter(
        spare_part=part
    ).select_related(
        'maintenance_record__machine', 
        'maintenance_record__technician'
    ).order_by('-created_at')[:10]
    
    # إحصائيات الاستخدام
    usage_stats = SparePartUsage.objects.filter(spare_part=part).aggregate(
        total_used=Sum('quantity_used'),
        total_cost=Sum('total_cost'),
        usage_count=Count('id')
    )
    
    context = {
        'part': part,
        'compatible_machines': compatible_machines,
        'recent_usage': recent_usage,
        'usage_stats': usage_stats,
    }
    
    return render(request, 'maintenance/spare_part_detail.html', context)


@login_required
def maintenance_request_list(request):
    """قائمة طلبات الصيانة"""
    
    requests = MaintenanceRequest.objects.select_related(
        'machine', 'maintenance_type', 'requested_by', 'assigned_to'
    )
    
    # فلترة
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    machine = request.GET.get('machine')
    assigned_to = request.GET.get('assigned_to')
    search = request.GET.get('search')
    
    if status:
        requests = requests.filter(status=status)
    if priority:
        requests = requests.filter(priority=priority)
    if machine:
        requests = requests.filter(machine_id=machine)
    if assigned_to:
        requests = requests.filter(assigned_to_id=assigned_to)
    if search:
        requests = requests.filter(
            Q(title__icontains=search) |
            Q(request_number__icontains=search) |
            Q(machine__name__icontains=search)
        )
    
    # ترتيب
    sort_by = request.GET.get('sort', '-request_date')
    requests = requests.order_by(sort_by)
    
    # التصفح
    paginator = Paginator(requests, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إحصائيات الحالات للبطاقات العلوية
    pending_count = MaintenanceRequest.objects.filter(status='submitted').count()
    approved_count = MaintenanceRequest.objects.filter(status='approved').count()
    in_progress_count = MaintenanceRequest.objects.filter(status='in_progress').count()
    completed_count = MaintenanceRequest.objects.filter(status='completed').count()

    context = {
        'page_obj': page_obj,
        'current_status': status,
        'current_priority': priority,
        'current_machine': machine,
        'current_assigned_to': assigned_to,
        'current_search': search,
        'current_sort': sort_by,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
    }
    
    return render(request, 'maintenance/maintenance_request_list.html', context)


@login_required
def maintenance_request_detail(request, pk):
    """تفاصيل طلب الصيانة"""
    
    maintenance_request = get_object_or_404(MaintenanceRequest, pk=pk)
    
    # سجلات الصيانة المرتبطة
    maintenance_records = MaintenanceRecord.objects.filter(
        maintenance_request=maintenance_request
    ).select_related('technician').order_by('-start_datetime')
    
    context = {
        'maintenance_request': maintenance_request,
        'maintenance_records': maintenance_records,
    }
    
    return render(request, 'maintenance/maintenance_request_detail.html', context)


@login_required
def maintenance_schedule_list(request):
    """قائمة جدولة الصيانة"""
    
    schedules = MaintenanceSchedule.objects.filter(is_active=True).select_related(
        'machine', 'maintenance_type', 'assigned_to'
    )
    
    # فلترة
    status = request.GET.get('status')  # due, upcoming, normal
    machine = request.GET.get('machine')
    maintenance_type = request.GET.get('maintenance_type')
    
    today = timezone.now().date()
    if status == 'due':
        schedules = schedules.filter(next_due_date__lt=today)
    elif status == 'upcoming':
        next_week = today + timedelta(days=7)
        schedules = schedules.filter(next_due_date__lte=next_week, next_due_date__gte=today)
    
    if machine:
        schedules = schedules.filter(machine_id=machine)
    if maintenance_type:
        schedules = schedules.filter(maintenance_type_id=maintenance_type)
    
    # ترتيب
    schedules = schedules.order_by('next_due_date')
    
    # التصفح
    paginator = Paginator(schedules, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'current_status': status,
        'current_machine': machine,
        'current_maintenance_type': maintenance_type,
    }
    
    return render(request, 'maintenance/maintenance_schedule_list.html', context)


@login_required
def maintenance_record_list(request):
    """قائمة سجلات الصيانة"""
    
    records = MaintenanceRecord.objects.select_related(
        'machine', 'maintenance_type', 'technician', 'maintenance_request'
    )
    
    # فلترة
    status = request.GET.get('status')
    result = request.GET.get('result')
    machine = request.GET.get('machine')
    technician = request.GET.get('technician')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if status:
        records = records.filter(status=status)
    if result:
        records = records.filter(result=result)
    if machine:
        records = records.filter(machine_id=machine)
    if technician:
        records = records.filter(technician_id=technician)
    if date_from:
        records = records.filter(start_datetime__date__gte=date_from)
    if date_to:
        records = records.filter(start_datetime__date__lte=date_to)
    
    # ترتيب
    records = records.order_by('-start_datetime')
    
    # التصفح
    paginator = Paginator(records, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'current_status': status,
        'current_result': result,
        'current_machine': machine,
        'current_technician': technician,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'maintenance/maintenance_record_list.html', context)


@login_required
def maintenance_record_detail(request, pk):
    """تفاصيل سجل الصيانة"""
    
    record = get_object_or_404(MaintenanceRecord, pk=pk)
    
    # قطع الغيار المستخدمة
    spare_parts_used = SparePartUsage.objects.filter(
        maintenance_record=record
    ).select_related('spare_part')
    
    context = {
        'record': record,
        'spare_parts_used': spare_parts_used,
    }
    
    return render(request, 'maintenance/maintenance_record_detail.html', context)


@login_required
def maintenance_alerts(request):
    """التنبيهات والتذكيرات"""
    
    today = timezone.now().date()
    
    # الصيانة المتأخرة
    overdue_maintenance = MaintenanceSchedule.objects.filter(
        next_due_date__lt=today,
        is_active=True
    ).select_related('machine', 'maintenance_type')
    
    # الصيانة القادمة (خلال أسبوع)
    next_week = today + timedelta(days=7)
    upcoming_maintenance = MaintenanceSchedule.objects.filter(
        next_due_date__lte=next_week,
        next_due_date__gte=today,
        is_active=True
    ).select_related('machine', 'maintenance_type')
    
    # قطع الغيار منخفضة المخزون
    from django.db.models import F
    low_stock_parts = SparePart.objects.filter(
        current_stock__lte=F('minimum_stock'),
        is_active=True
    ).select_related('storage_location')
    
    # قطع الغيار نفدت
    out_of_stock_parts = SparePart.objects.filter(
        current_stock=0,
        is_active=True
    ).select_related('storage_location')
    
    # الماكينات في حالة سيئة
    critical_machines = Machine.objects.filter(
        condition__in=['poor', 'critical'],
        is_active=True
    ).select_related('category', 'location')
    
    # الماكينات المعطلة
    broken_machines = Machine.objects.filter(
        status='breakdown',
        is_active=True
    ).select_related('category', 'location')
    
    context = {
        'overdue_maintenance': overdue_maintenance,
        'upcoming_maintenance': upcoming_maintenance,
        'low_stock_parts': low_stock_parts,
        'out_of_stock_parts': out_of_stock_parts,
        'critical_machines': critical_machines,
        'broken_machines': broken_machines,
    }
    
    return render(request, 'maintenance/maintenance_alerts.html', context)


@login_required
def maintenance_reports(request):
    """تقارير الصيانة"""
    
    # إحصائيات عامة
    total_machines = Machine.objects.filter(is_active=True).count()
    total_requests = MaintenanceRequest.objects.count()
    completed_requests = MaintenanceRequest.objects.filter(status='completed').count()
    
    # تكاليف الصيانة (آخر 12 شهر)
    last_year = timezone.now().date() - timedelta(days=365)
    maintenance_costs = MaintenanceRecord.objects.filter(
        start_datetime__date__gte=last_year
    ).values(
        'start_datetime__year', 'start_datetime__month'
    ).annotate(
        total_cost=Sum('labor_cost') + Sum('parts_cost') + Sum('external_service_cost') + Sum('other_costs')
    ).order_by('start_datetime__year', 'start_datetime__month')
    
    context = {
        'total_machines': total_machines,
        'total_requests': total_requests,
        'completed_requests': completed_requests,
        'maintenance_costs': list(maintenance_costs),
    }
    
    return render(request, 'maintenance/maintenance_reports.html', context)


# واجهات API بسيطة
@login_required
def api_machine_search(request):
    """البحث في الماكينات - API"""
    
    query = request.GET.get('q', '')
    machines = Machine.objects.filter(
        Q(name__icontains=query) | Q(code__icontains=query),
        is_active=True
    )[:10]
    
    data = [
        {
            'id': machine.pk,
            'name': machine.name,
            'code': machine.code,
            'category': machine.category.name if machine.category else '',
        }
        for machine in machines
    ]
    
    return JsonResponse(data, safe=False)


@login_required
def api_spare_part_search(request):
    """البحث في قطع الغيار - API"""
    
    query = request.GET.get('q', '')
    parts = SparePart.objects.filter(
        Q(name__icontains=query) | Q(code__icontains=query),
        is_active=True
    )[:10]
    
    data = [
        {
            'id': part.pk,
            'name': part.name,
            'code': part.code,
            'current_stock': float(part.current_stock),
            'unit_cost': float(part.unit_cost),
        }
        for part in parts
    ]
    
    return JsonResponse(data, safe=False)


@login_required
def machine_category_list(request):
    """قائمة فئات الماكينات"""
    categories = MachineCategory.objects.all().order_by('code')
    
    # فلترة
    search = request.GET.get('search')
    if search:
        categories = categories.filter(
            Q(name__icontains=search) | Q(code__icontains=search)
        )
    
    paginator = Paginator(categories, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'title': 'فئات الماكينات'
    }
    return render(request, 'maintenance/machine_category_list.html', context)

@login_required
def machine_category_add(request):
    """إضافة فئة ماكينة"""
    if request.method == 'POST':
        form = MachineCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة الفئة بنجاح')
            return redirect('maintenance:machine_category_list')
    else:
        form = MachineCategoryForm()
    
    return render(request, 'maintenance/machine_category_form.html', {
        'form': form,
        'title': 'إضافة فئة ماكينة'
    })

@login_required
def machine_category_edit(request, pk):
    """تعديل فئة الماكينة"""
    category = get_object_or_404(MachineCategory, pk=pk)
    if request.method == 'POST':
        form = MachineCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الفئة بنجاح')
            return redirect('maintenance:machine_category_list')
    else:
        form = MachineCategoryForm(instance=category)
    
    return render(request, 'maintenance/machine_category_form.html', {
        'form': form,
        'title': 'تعديل فئة الماكينة',
        'object': category
    })

@login_required
def machine_category_delete(request, pk):
    """حذف فئة الماكينة"""
    category = get_object_or_404(MachineCategory, pk=pk)
    if request.method == 'POST':
        if category.machines.exists():
            messages.error(request, 'لا يمكن حذف الفئة لأنها مرتبطة بماكينات')
        else:
            category.delete()
            messages.success(request, 'تم حذف الفئة بنجاح')
    return redirect('maintenance:machine_category_list')

@login_required
def machine_delete(request, pk):
    """حذف الماكينة"""
    machine = get_object_or_404(Machine, pk=pk)
    if request.method == 'POST':
        machine.is_active = False # Soft delete usually safer
        machine.save()
        messages.success(request, 'تم حذف الماكينة بنجاح (نقلت للأرشيف)')
        return redirect('maintenance:machine_list')
    return render(request, 'maintenance/machine_confirm_delete.html', {'machine': machine})

def machine_qr_code(request, pk):
    return render(request, 'maintenance/coming_soon.html', {'title': 'رمز QR للماكينة'})

@login_required
def spare_part_add(request):
    """إضافة قطعة غيار"""
    if request.method == 'POST':
        form = SparePartForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة قطعة الغيار بنجاح')
            return redirect('maintenance:spare_part_list')
    else:
        form = SparePartForm()
    
    return render(request, 'maintenance/spare_part_form.html', {
        'form': form,
        'title': 'إضافة قطعة غيار'
    })

@login_required
def spare_part_edit(request, pk):
    """تعديل قطعة غيار"""
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == 'POST':
        form = SparePartForm(request.POST, instance=part)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث قطعة الغيار بنجاح')
            return redirect('maintenance:spare_part_list')
    else:
        form = SparePartForm(instance=part)
    
    return render(request, 'maintenance/spare_part_form.html', {
        'form': form,
        'title': 'تعديل قطعة غيار',
        'object': part
    })

@login_required
def spare_part_delete(request, pk):
    """حذف قطعة غيار"""
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == 'POST':
        part.is_active = False  # Soft delete
        part.save()
        messages.success(request, 'تم حذف قطعة الغيار بنجاح')
    return redirect('maintenance:spare_part_list')

def spare_part_low_stock(request):
    """عرض قطع الغيار منخفضة المخزون باستخدام نفس قائمة القطع مع فلتر جاهز."""
    from django.urls import reverse
    qs = request.GET.copy()
    qs['stock_status'] = 'low'
    # نحتفظ بباقي معاملات الرابط (مثل البحث/الترتيب) إن وُجدت
    target = f"{reverse('maintenance:spare_part_list')}?{qs.urlencode()}"
    return redirect(target)

@login_required
def maintenance_type_list(request):
    """قائمة أنواع الصيانة"""
    types = MaintenanceType.objects.all().order_by('code')
    
    context = {
        'types': types,
        'title': 'أنواع الصيانة'
    }
    return render(request, 'maintenance/maintenance_type_list.html', context)

@login_required
def maintenance_type_add(request):
    """إضافة نوع صيانة"""
    if request.method == 'POST':
        form = MaintenanceTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة نوع الصيانة بنجاح')
            return redirect('maintenance:maintenance_type_list')
    else:
        form = MaintenanceTypeForm()
    
    return render(request, 'maintenance/maintenance_type_form.html', {
        'form': form,
        'title': 'إضافة نوع صيانة'
    })

@login_required
def maintenance_type_edit(request, pk):
    """تعديل نوع الصيانة"""
    m_type = get_object_or_404(MaintenanceType, pk=pk)
    if request.method == 'POST':
        form = MaintenanceTypeForm(request.POST, instance=m_type)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث نوع الصيانة بنجاح')
            return redirect('maintenance:maintenance_type_list')
    else:
        form = MaintenanceTypeForm(instance=m_type)
    
    return render(request, 'maintenance/maintenance_type_form.html', {
        'form': form,
        'title': 'تعديل نوع الصيانة',
        'object': m_type
    })

@login_required
def maintenance_request_add(request):
    """إضافة طلب صيانة جديد"""
    if request.method == 'POST':
        form = MaintenanceRequestForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.requested_by = request.user
            # عند إنشاء الطلب نجعله "مقدم" افتراضياً
            if not obj.status or obj.status == 'draft':
                obj.status = 'submitted'
            obj.save()
            messages.success(request, 'تم إنشاء طلب الصيانة بنجاح')
            return redirect('maintenance:maintenance_request_detail', pk=obj.pk)
    else:
        initial = {}
        machine_id = request.GET.get('machine')
        if machine_id:
            initial['machine'] = machine_id
        form = MaintenanceRequestForm(initial=initial)

    return render(request, 'maintenance/maintenance_request_form.html', {
        'form': form,
        'title': 'إضافة طلب صيانة'
    })

@login_required
def maintenance_request_detail(request, pk):
    """تفاصيل طلب الصيانة"""
    m_request = get_object_or_404(MaintenanceRequest, pk=pk)
    return render(request, 'maintenance/maintenance_request_detail.html', {
        'request': m_request,
        'title': f'تفاصيل الطلب: {m_request.request_number}'
    })

@login_required
def maintenance_request_edit(request, pk):
    """تعديل طلب الصيانة"""
    m_request = get_object_or_404(MaintenanceRequest, pk=pk)
    
    # تحقق من الصلاحيات والحالة (مثلاً لا يمكن تعديل طلب مكتمل)
    if m_request.status in ['completed', 'cancelled', 'rejected']:
        messages.error(request, 'لا يمكن تعديل طلب في هذه الحالة')
        return redirect('maintenance:maintenance_request_detail', pk=pk)

    if request.method == 'POST':
        form = MaintenanceRequestForm(request.POST, instance=m_request)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تعديل الطلب بنجاح')
            return redirect('maintenance:maintenance_request_detail', pk=pk)
    else:
        form = MaintenanceRequestForm(instance=m_request)
    
    return render(request, 'maintenance/maintenance_request_form.html', {
        'form': form,
        'title': 'تعديل طلب الصيانة',
        'object': m_request
    })

@login_required
def maintenance_request_approve(request, pk):
    """الموافقة على طلب الصيانة"""
    m_request = get_object_or_404(MaintenanceRequest, pk=pk)
    if request.method == 'POST':
        if m_request.status in ['draft', 'submitted']:
            m_request.status = 'approved'
            m_request.approved_by = request.user
            m_request.approved_date = timezone.now()
            m_request.save()
            messages.success(request, 'تمت الموافقة على الطلب')
        else:
            messages.warning(request, 'الطلب ليس في حالة تسمح بالموافقة')
    return redirect('maintenance:maintenance_request_detail', pk=pk)

@login_required
def maintenance_request_start(request, pk):
    """بدء تنفيذ طلب الصيانة"""
    m_request = get_object_or_404(MaintenanceRequest, pk=pk)
    if request.method == 'POST':
        if m_request.status == 'approved':
            m_request.status = 'in_progress'
            m_request.started_date = timezone.now()
            m_request.save()
            
            # إنشاء سجل صيانة أولي
            MaintenanceRecord.objects.create(
                maintenance_request=m_request,
                machine=m_request.machine,
                maintenance_type=m_request.maintenance_type,
                start_datetime=timezone.now(),
                status='in_progress',
                technician=m_request.assigned_to,
                work_performed='تم بدء العمل بناءً على الطلب',
                created_by=request.user
            )
            messages.success(request, 'تم بدء تنفيذ الطلب وإنشاء سجل صيانة')
        else:
            messages.warning(request, 'يجب الموافقة على الطلب أولاً')
    return redirect('maintenance:maintenance_request_detail', pk=pk)

@login_required
def maintenance_request_complete(request, pk):
    """إنهاء طلب الصيانة"""
    m_request = get_object_or_404(MaintenanceRequest, pk=pk)
    if request.method == 'POST':
        if m_request.status == 'in_progress':
            m_request.status = 'completed'
            m_request.completed_date = timezone.now()
            m_request.save()
            
            # تحديث السجلات المرتبطة إذا لزم الأمر
            m_request.maintenance_records.filter(status='in_progress').update(
                status='completed', 
                end_datetime=timezone.now()
            )
            messages.success(request, 'تم إكمال الطلب بنجاح')
        else:
            messages.warning(request, 'الطلب يجب أن يكون قيد التنفيذ لإكماله')
    return redirect('maintenance:maintenance_request_detail', pk=pk)

@login_required
def maintenance_request_cancel(request, pk):
    """إلغاء طلب الصيانة"""
    m_request = get_object_or_404(MaintenanceRequest, pk=pk)
    if request.method == 'POST':
        reason = request.POST.get('cancellation_reason', '')
        if m_request.status not in ['completed']:
            m_request.status = 'cancelled'
            m_request.cancellation_reason = reason
            m_request.save()
            messages.success(request, 'تم إلغاء الطلب')
        else:
            messages.error(request, 'لا يمكن إلغاء طلب مكتمل')
    return redirect('maintenance:maintenance_request_detail', pk=pk)

@login_required
def maintenance_schedule_add(request):
    """إضافة جدولة صيانة جديدة (نموذج مبسّط يعمل الآن)."""
    if request.method == 'POST':
        form = MaintenanceScheduleForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            # تعيين افتراضات آمنة إن لزم
            if not getattr(obj, 'is_active', True) is True:
                obj.is_active = True
            # إذا كان next_due_date فارغاً ونوع التكرار يحدد ذلك، نحاول حسابه لاحقاً (تركه كما هو حالياً)
            obj.save()
            messages.success(request, 'تم إنشاء جدولة الصيانة بنجاح')
            return redirect('maintenance:maintenance_schedule_list')
    else:
        initial = {}
        machine_id = request.GET.get('machine')
        if machine_id:
            initial['machine'] = machine_id
        form = MaintenanceScheduleForm(initial=initial)

    return render(request, 'maintenance/maintenance_schedule_form.html', {
        'form': form,
        'title': 'إضافة جدولة صيانة'
    })

@login_required
def maintenance_schedule_detail(request, pk):
    """تفاصيل جدولة الصيانة"""
    schedule = get_object_or_404(MaintenanceSchedule, pk=pk)
    return render(request, 'maintenance/maintenance_schedule_detail.html', {
        'schedule': schedule,
        'title': f'جدولة الصيانة: {schedule.name}'
    })

@login_required
def maintenance_schedule_edit(request, pk):
    """تعديل جدولة الصيانة"""
    schedule = get_object_or_404(MaintenanceSchedule, pk=pk)
    if request.method == 'POST':
        form = MaintenanceScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تعديل الجدولة بنجاح')
            return redirect('maintenance:maintenance_schedule_detail', pk=pk)
    else:
        form = MaintenanceScheduleForm(instance=schedule)
    
    return render(request, 'maintenance/maintenance_schedule_form.html', {
        'form': form,
        'title': 'تعديل جدولة الصيانة',
        'object': schedule
    })

@login_required
def generate_maintenance_requests(request):
    """إنشاء طلبات الصيانة التلقائية من الجداول المستحقة"""
    today = timezone.now().date()
    # Schedules due today or earlier, active, auto-generate enabled
    schedules = MaintenanceSchedule.objects.filter(
        next_due_date__lte=today,
        is_active=True,
        auto_generate_requests=True
    )
    
    generated_count = 0
    for schedule in schedules:
        # Check if a request already exists for this schedule for this due date (to avoid duplicates)
        active_request = MaintenanceRequest.objects.filter(
            machine=schedule.machine,
            maintenance_type=schedule.maintenance_type,
            status__in=['draft', 'submitted', 'approved', 'in_progress']
        ).exists()
        
        if not active_request:
            MaintenanceRequest.objects.create(
                machine=schedule.machine,
                maintenance_type=schedule.maintenance_type,
                title=f"صيانة مجدولة: {schedule.name}",
                description=f"صيانة دورية تم إنشاؤها تلقائياً من الجدول {schedule.name}\n{schedule.description}",
                priority='normal',
                requested_by=request.user,
                requested_completion_date=timezone.now().date() + timezone.timedelta(days=3),
                assigned_to=schedule.assigned_to,
                estimated_cost=schedule.estimated_cost,
                estimated_duration_hours=schedule.estimated_duration_hours,
                status='submitted'
            )
            
            # Update schedule
            schedule.last_generated_date = today
            schedule.next_due_date = schedule.calculate_next_due_date()
            schedule.save()
            generated_count += 1
    
    if generated_count > 0:
        messages.success(request, f'تم إنشاء {generated_count} طلب صيانة تلقائي بنجاح')
    else:
        messages.info(request, 'لا توجد جداول مستحقة للصيانة اليوم')
        
    return redirect('maintenance:maintenance_schedule_list')

@login_required
def maintenance_record_add(request):
    """إضافة سجل صيانة"""
    if request.method == 'POST':
        form = MaintenanceRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.created_by = request.user
            record.save()
            form.save_m2m()
            messages.success(request, 'تم إضافة سجل الصيانة بنجاح')
            # Redirect to request detail if linked, otherwise dashboard or list
            if record.maintenance_request:
                return redirect('maintenance:maintenance_request_detail', pk=record.maintenance_request.pk)
            return redirect('maintenance:dashboard')
    else:
        initial = {}
        request_id = request.GET.get('request')
        if request_id:
            m_request = get_object_or_404(MaintenanceRequest, pk=request_id)
            initial['maintenance_request'] = m_request
            initial['machine'] = m_request.machine
            initial['maintenance_type'] = m_request.maintenance_type
            initial['technician'] = m_request.assigned_to 
            initial['start_datetime'] = m_request.started_date
            
        form = MaintenanceRecordForm(initial=initial)
    
    return render(request, 'maintenance/maintenance_record_form.html', {
        'form': form,
        'title': 'إضافة سجل صيانة'
    })

@login_required
def maintenance_record_edit(request, pk):
    """تعديل سجل الصيانة"""
    record = get_object_or_404(MaintenanceRecord, pk=pk)
    if request.method == 'POST':
        form = MaintenanceRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تعديل سجل الصيانة بنجاح')
            if record.maintenance_request:
                return redirect('maintenance:maintenance_request_detail', pk=record.maintenance_request.pk)
            return redirect('maintenance:dashboard')
    else:
        form = MaintenanceRecordForm(instance=record)
    
    return render(request, 'maintenance/maintenance_record_form.html', {
        'form': form,
        'title': 'تعديل سجل الصيانة',
        'object': record
    })

@login_required
def maintenance_record_print(request, pk):
    """طباعة سجل الصيانة"""
    record = get_object_or_404(MaintenanceRecord, pk=pk)
    return render(request, 'maintenance/maintenance_record_print.html', {'record': record})

@login_required
def maintenance_checklist_list(request):
    """قائمة قوائم الفحص"""
    checklists = MaintenanceChecklist.objects.all().order_by('name')
    return render(request, 'maintenance/maintenance_checklist_list.html', {
        'checklists': checklists,
        'title': 'قوائم فحص الصيانة'
    })

@login_required
def maintenance_checklist_add(request):
    """إضافة قائمة فحص"""
    if request.method == 'POST':
        form = MaintenanceChecklistForm(request.POST)
        if form.is_valid():
            checklist = form.save(commit=False)
            checklist.created_by = request.user
            checklist.save()
            messages.success(request, 'تم إضافة قائمة الفحص بنجاح')
            return redirect('maintenance:maintenance_checklist_list')
    else:
        form = MaintenanceChecklistForm()
    
    return render(request, 'maintenance/maintenance_checklist_form.html', {
        'form': form,
        'title': 'إضافة قائمة فحص'
    })

@login_required
def maintenance_checklist_edit(request, pk):
    """تعديل قائمة الفحص"""
    checklist = get_object_or_404(MaintenanceChecklist, pk=pk)
    if request.method == 'POST':
        form = MaintenanceChecklistForm(request.POST, instance=checklist)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تعديل قائمة الفحص بنجاح')
            return redirect('maintenance:maintenance_checklist_list')
    else:
        form = MaintenanceChecklistForm(instance=checklist)
    
    return render(request, 'maintenance/maintenance_checklist_form.html', {
        'form': form,
        'title': 'تعديل قائمة الفحص',
        'object': checklist
    })

@login_required
def machine_maintenance_history(request, machine_id):
    """سجل تاريخ صيانة الماكينة"""
    machine = get_object_or_404(Machine, pk=machine_id)
    records = machine.maintenance_records.order_by('-start_datetime')
    
    return render(request, 'maintenance/machine_maintenance_history.html', {
        'machine': machine,
        'records': records,
        'title': f'سجل صيانة: {machine.name}'
    })

@login_required
def maintenance_performance_report(request):
    """تقرير أداء الصيانة (KPIs)"""
    # Simple KPI dashboard
    total_requests = MaintenanceRequest.objects.count()
    completed_requests = MaintenanceRequest.objects.filter(status='completed').count()
    completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
    
    # Average completion time
    from django.db.models import F, Avg
    # Only for completed requests with dates
    avg_duration_delta = MaintenanceRequest.objects.filter(
        status='completed', 
        completed_date__isnull=False, 
        started_date__isnull=False
    ).annotate(
        duration=F('completed_date') - F('started_date')
    ).aggregate(avg=Avg('duration'))['avg']
    
    avg_duration_hours = 0
    if avg_duration_delta:
        avg_duration_hours = avg_duration_delta.total_seconds() / 3600
    
    context = {
        'total_requests': total_requests,
        'completed_requests': completed_requests,
        'completion_rate': round(completion_rate, 1),
        'avg_duration_hours': round(avg_duration_hours, 1),
        'title': 'تقرير أداء الصيانة'
    }
    return render(request, 'maintenance/maintenance_performance_report.html', context)

@login_required
def spare_parts_usage_report(request):
    """تقرير استخدام قطع الغيار"""
    usage = SparePartUsage.objects.select_related('spare_part', 'maintenance_record').order_by('-created_at')
    
    # Summary by part
    from django.db.models import Sum
    summary = SparePartUsage.objects.values('spare_part__name', 'spare_part__code').annotate(
        total_qty=Sum('quantity_used'),
        total_cost=Sum('total_cost')
    ).order_by('-total_cost')
    
    return render(request, 'maintenance/spare_parts_usage_report.html', {
        'usage': usage,
        'summary': summary,
        'title': 'تقرير استخدام قطع الغيار'
    })

def overdue_maintenance(request):
    return render(request, 'maintenance/coming_soon.html', {'title': 'الصيانة المتأخرة'})

def upcoming_maintenance(request):
    return render(request, 'maintenance/coming_soon.html', {'title': 'الصيانة القادمة'})

def api_maintenance_calendar(request):
    return JsonResponse({'message': 'قيد التطوير'}, safe=False)

@login_required
def maintenance_cost_analysis(request):
    """تحليل تكاليف الصيانة"""
    # تجميع التكاليف حسب نوع الصيانة
    by_type = MaintenanceRecord.objects.values('maintenance_type__name').annotate(
        total=Sum('labor_cost') + Sum('parts_cost') + Sum('external_service_cost') + Sum('other_costs')
    ).order_by('-total')
    
    # تجميع التكاليف حسب الماكينة (أغلى 10)
    by_machine = MaintenanceRecord.objects.values('machine__name').annotate(
        total=Sum('labor_cost') + Sum('parts_cost') + Sum('external_service_cost') + Sum('other_costs')
    ).order_by('-total')[:10]
    
    context = {
        'by_type': list(by_type),
        'by_machine': list(by_machine),
        'title': 'تحليل تكاليف الصيانة'
    }
    return render(request, 'maintenance/maintenance_cost_analysis.html', context)