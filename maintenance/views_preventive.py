"""
واجهات عرض نظام الصيانة الوقائية
Preventive Maintenance Views

يوفر:
- لوحة تحكم الصيانة الوقائية
- إدارة الجداول
- التنبيهات والإشعارات
- التقارير والتحليلات
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
import json
import csv

from maintenance.models import (
    Machine, MaintenanceSchedule, MaintenanceRequest,
    MaintenanceType, MaintenanceRecord, MachineCategory
)
from maintenance.services.preventive_maintenance import (
    PreventiveMaintenanceScheduler,
    MaintenanceAnalytics,
    MaintenanceAlertManager
)
from hr.models import Employee


@login_required
def preventive_maintenance_dashboard(request):
    """
    لوحة التحكم الرئيسية للصيانة الوقائية
    
    عرض شامل:
    - الإحصائيات العامة
    - التنبيهات والإشعارات
    - الجداول المستحقة
    - حالة الماكينات
    """
    today = timezone.now().date()
    
    # إحصائيات عامة
    total_machines = Machine.objects.filter(status='operational').count()
    total_schedules = MaintenanceSchedule.objects.filter(is_active=True).count()
    
    # الصيانة المستحقة اليوم وخلال 7 أيام
    due_today = MaintenanceSchedule.objects.filter(
        is_active=True,
        next_due_date=today
    ).count()
    
    due_week = MaintenanceSchedule.objects.filter(
        is_active=True,
        next_due_date__gte=today,
        next_due_date__lte=today + timedelta(days=7)
    ).count()
    
    # الطلبات النشطة
    active_requests = MaintenanceRequest.objects.filter(
        status__in=['submitted', 'approved', 'in_progress']
    ).count()
    
    # التنبيهات
    alert_manager = MaintenanceAlertManager()
    alerts = alert_manager.generate_maintenance_alerts()
    
    critical_alerts = [a for a in alerts if a['severity'] == 'critical']
    high_alerts = [a for a in alerts if a['severity'] == 'high']
    
    # الماكينات حسب الحالة
    machines_by_condition = {
        'excellent': Machine.objects.filter(status='operational', condition='excellent').count(),
        'good': Machine.objects.filter(status='operational', condition='good').count(),
        'fair': Machine.objects.filter(status='operational', condition='fair').count(),
        'poor': Machine.objects.filter(status='operational', condition='poor').count(),
        'critical': Machine.objects.filter(status='operational', condition='critical').count(),
    }
    
    # الجداول المستحقة قريباً
    upcoming_schedules = MaintenanceSchedule.objects.filter(
        is_active=True,
        next_due_date__gte=today,
        next_due_date__lte=today + timedelta(days=30)
    ).select_related('machine', 'maintenance_type').order_by('next_due_date')[:10]
    
    # أحدث طلبات الصيانة
    recent_requests = MaintenanceRequest.objects.filter(
        status__in=['submitted', 'approved', 'in_progress']
    ).select_related('machine', 'maintenance_type').order_by('-request_date')[:10]
    
    context = {
        'stats': {
            'total_machines': total_machines,
            'total_schedules': total_schedules,
            'due_today': due_today,
            'due_week': due_week,
            'active_requests': active_requests,
            'critical_alerts': len(critical_alerts),
            'high_alerts': len(high_alerts),
        },
        'machines_by_condition': machines_by_condition,
        'alerts': alerts[:20],  # أول 20 تنبيه
        'upcoming_schedules': upcoming_schedules,
        'recent_requests': recent_requests,
        'page_title': 'لوحة التحكم - الصيانة الوقائية'
    }
    
    return render(request, 'maintenance/preventive/dashboard.html', context)


@login_required
def generate_maintenance_requests_view(request):
    """
    إنشاء طلبات صيانة تلقائية من الجداول المستحقة
    """
    if request.method == 'POST':
        advance_days = int(request.POST.get('advance_days', 7))
        
        scheduler = PreventiveMaintenanceScheduler()
        result = scheduler.generate_due_maintenance_requests(
            advance_days=advance_days
        )
        
        generated_count = result['statistics']['generated_requests']
        
        if generated_count > 0:
            messages.success(
                request,
                f'تم إنشاء {generated_count} طلب صيانة تلقائياً'
            )
        else:
            messages.info(request, 'لا توجد جداول مستحقة حالياً')
        
        return redirect('maintenance:preventive_dashboard')
    
    # GET: عرض صفحة التأكيد
    today = timezone.now().date()
    
    # الجداول المستحقة
    due_schedules = MaintenanceSchedule.objects.filter(
        is_active=True,
        next_due_date__lte=today + timedelta(days=7),
        auto_generate_requests=True
    ).select_related('machine', 'maintenance_type')
    
    context = {
        'due_schedules': due_schedules,
        'page_title': 'إنشاء طلبات صيانة تلقائية'
    }
    
    return render(request, 'maintenance/preventive/generate_requests.html', context)


@login_required
def maintenance_schedules_list(request):
    """
    قائمة جداول الصيانة الدورية
    """
    # الفلاتر
    machine_id = request.GET.get('machine')
    frequency = request.GET.get('frequency')
    status = request.GET.get('status', 'active')
    
    # بناء الاستعلام
    schedules = MaintenanceSchedule.objects.select_related(
        'machine', 'maintenance_type', 'assigned_to'
    )
    
    if status == 'active':
        schedules = schedules.filter(is_active=True)
    elif status == 'inactive':
        schedules = schedules.filter(is_active=False)
    
    if machine_id:
        schedules = schedules.filter(machine_id=machine_id)
    
    if frequency:
        schedules = schedules.filter(frequency=frequency)
    
    schedules = schedules.order_by('next_due_date')
    
    # للفلاتر
    machines = Machine.objects.filter(status='operational')
    
    context = {
        'schedules': schedules,
        'machines': machines,
        'selected_machine': machine_id,
        'selected_frequency': frequency,
        'selected_status': status,
        'page_title': 'جداول الصيانة الدورية'
    }
    
    return render(request, 'maintenance/preventive/schedules_list.html', context)


@login_required
def create_maintenance_schedule(request):
    """
    إنشاء جدولة صيانة جديدة
    """
    if request.method == 'POST':
        try:
            machine_id = request.POST.get('machine')
            maintenance_type_id = request.POST.get('maintenance_type')
            name = request.POST.get('name')
            frequency = request.POST.get('frequency')
            start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
            
            machine = Machine.objects.get(id=machine_id)
            maintenance_type = MaintenanceType.objects.get(id=maintenance_type_id)
            
            # حساب تاريخ الاستحقاق الأول
            scheduler = PreventiveMaintenanceScheduler()
            next_due_date = scheduler._calculate_next_due_date(
                start_date,
                frequency,
                int(request.POST.get('interval_days', 30))
            )
            
            schedule = MaintenanceSchedule.objects.create(
                name=name,
                machine=machine,
                maintenance_type=maintenance_type,
                frequency=frequency,
                interval_days=int(request.POST.get('interval_days', 30)),
                start_date=start_date,
                next_due_date=next_due_date,
                auto_generate_requests=request.POST.get('auto_generate') == 'on',
                advance_notice_days=int(request.POST.get('advance_notice_days', 7)),
                estimated_cost=Decimal(request.POST.get('estimated_cost', '0')),
                estimated_duration_hours=Decimal(request.POST.get('estimated_duration', '1')),
                assigned_to_id=request.POST.get('assigned_to') or None,
                description=request.POST.get('description', ''),
                checklist_template=request.POST.get('checklist', ''),
                created_by=request.user
            )
            
            messages.success(request, f'تم إنشاء الجدولة "{schedule.name}" بنجاح')
            return redirect('maintenance:schedules_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    # GET
    machines = Machine.objects.filter(status='operational')
    maintenance_types = MaintenanceType.objects.filter(is_active=True)
    employees = Employee.objects.filter(is_active=True)
    
    context = {
        'machines': machines,
        'maintenance_types': maintenance_types,
        'employees': employees,
        'page_title': 'إنشاء جدولة صيانة'
    }
    
    return render(request, 'maintenance/preventive/create_schedule.html', context)


@login_required
def machine_maintenance_history(request, machine_id):
    """
    تاريخ صيانة ماكينة محددة
    """
    machine = get_object_or_404(Machine, id=machine_id)
    
    # الفترة الزمنية
    period_days = int(request.GET.get('period_days', 90))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=period_days)
    
    # الحصول على التحليل
    analytics = MaintenanceAnalytics.get_machine_maintenance_history(
        machine, start_date, end_date
    )
    
    # حساب الكفاءة
    efficiency = MaintenanceAnalytics.calculate_maintenance_efficiency(
        machine, period_days
    )
    
    # الجداول النشطة للماكينة
    active_schedules = MaintenanceSchedule.objects.filter(
        machine=machine,
        is_active=True
    ).select_related('maintenance_type')
    
    # الطلبات النشطة
    active_requests = MaintenanceRequest.objects.filter(
        machine=machine,
        status__in=['submitted', 'approved', 'in_progress']
    ).select_related('maintenance_type')
    
    context = {
        'machine': machine,
        'analytics': analytics,
        'efficiency': efficiency,
        'active_schedules': active_schedules,
        'active_requests': active_requests,
        'period_days': period_days,
        'page_title': f'تاريخ صيانة {machine.name}'
    }
    
    return render(request, 'maintenance/preventive/machine_history.html', context)


@login_required
def maintenance_cost_report(request):
    """
    تقرير تكاليف الصيانة
    """
    # الفترة الزمنية
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    group_by = request.GET.get('group_by', 'machine')
    
    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        # الافتراضي: آخر 3 أشهر
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=90)
    
    # الحصول على التحليل
    analysis = MaintenanceAnalytics.get_maintenance_cost_analysis(
        start_date, end_date, group_by
    )
    
    # تحويل للرسم البياني
    chart_labels = list(analysis['grouped_data'].keys())
    chart_data = [
        float(analysis['grouped_data'][key]['total_cost'])
        for key in chart_labels
    ]
    
    context = {
        'analysis': analysis,
        'start_date': start_date,
        'end_date': end_date,
        'group_by': group_by,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'page_title': 'تقرير تكاليف الصيانة'
    }
    
    return render(request, 'maintenance/preventive/cost_report.html', context)


@login_required
def alerts_notifications_view(request):
    """
    عرض جميع التنبيهات والإشعارات
    """
    # إنشاء التنبيهات
    alert_manager = MaintenanceAlertManager()
    all_alerts = alert_manager.generate_maintenance_alerts()
    
    # الفلترة
    severity_filter = request.GET.get('severity')
    alert_type_filter = request.GET.get('type')
    
    if severity_filter:
        all_alerts = [a for a in all_alerts if a['severity'] == severity_filter]
    
    if alert_type_filter:
        all_alerts = [a for a in all_alerts if a['type'] == alert_type_filter]
    
    # إحصائيات
    alert_stats = {
        'total': len(all_alerts),
        'critical': len([a for a in all_alerts if a['severity'] == 'critical']),
        'high': len([a for a in all_alerts if a['severity'] == 'high']),
        'warning': len([a for a in all_alerts if a['severity'] == 'warning']),
    }
    
    context = {
        'alerts': all_alerts,
        'alert_stats': alert_stats,
        'severity_filter': severity_filter,
        'type_filter': alert_type_filter,
        'page_title': 'التنبيهات والإشعارات'
    }
    
    return render(request, 'maintenance/preventive/alerts.html', context)


@login_required
def machine_efficiency_report(request):
    """
    تقرير كفاءة الماكينات (OEE)
    """
    period_days = int(request.GET.get('period_days', 90))
    
    # حساب الكفاءة لكل ماكينة
    machines = Machine.objects.filter(status='operational')
    efficiency_data = []
    
    for machine in machines:
        efficiency = MaintenanceAnalytics.calculate_maintenance_efficiency(
            machine, period_days
        )
        efficiency_data.append(efficiency)
    
    # ترتيب حسب OEE (الأقل أولاً - يحتاج اهتمام)
    efficiency_data.sort(key=lambda e: e['oee_percent'])
    
    context = {
        'efficiency_data': efficiency_data,
        'period_days': period_days,
        'page_title': 'تقرير كفاءة الماكينات (OEE)'
    }
    
    return render(request, 'maintenance/preventive/efficiency_report.html', context)


@login_required
def export_cost_report_csv(request):
    """
    تصدير تقرير التكاليف إلى CSV
    """
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    group_by = request.GET.get('group_by', 'machine')
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    analysis = MaintenanceAnalytics.get_maintenance_cost_analysis(
        start_date, end_date, group_by
    )
    
    # إنشاء ملف CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="maintenance_costs_{start_date}_{end_date}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['تقرير تكاليف الصيانة'])
    writer.writerow([f'الفترة: {start_date} إلى {end_date}'])
    writer.writerow([])
    
    # العناوين
    if group_by == 'machine':
        writer.writerow(['الماكينة', 'عدد الصيانات', 'التكلفة الإجمالية', 'وقت التوقف (ساعات)'])
    else:
        writer.writerow(['التصنيف', 'عدد الصيانات', 'التكلفة الإجمالية'])
    
    # البيانات
    for key, value in analysis['grouped_data'].items():
        if group_by == 'machine':
            writer.writerow([
                key,
                value['count'],
                value['total_cost'],
                value.get('total_downtime', 0)
            ])
        else:
            writer.writerow([
                key,
                value['count'],
                value['total_cost']
            ])
    
    writer.writerow([])
    writer.writerow(['الإجمالي', analysis['total_records'], analysis['total_cost']])
    
    return response


@login_required
def update_schedule_status_ajax(request):
    """
    تحديث حالة جدولة (AJAX)
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            schedule_id = data.get('schedule_id')
            is_active = data.get('is_active')
            
            schedule = MaintenanceSchedule.objects.get(id=schedule_id)
            schedule.is_active = is_active
            schedule.save(update_fields=['is_active'])
            
            return JsonResponse({
                'success': True,
                'message': 'تم تحديث الحالة بنجاح'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'success': False}, status=400)
