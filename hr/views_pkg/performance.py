from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg, F, Max, Min
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import os
from functools import wraps

from hr.models import (
    Employee, Department, JobPosition, AttendanceRecord, WorkSchedule,
    LeaveRequest, LeaveType, Payroll, PerformanceReview, TrainingProgram,
    TrainingEnrollment, JobVacancy, JobApplication, HRSettings,
    PerformanceTarget, TargetCategory, TargetProgress, TeamTarget,
    TeamTargetMembership, PerformanceMetric, EmployeeMetricValue,
    WeekendDay, PublicHoliday, EmployeeAbsence,
    AllowanceType, DeductionType, EmployeeAllowance, EmployeeDeduction, PayrollItem
)
from accounting.models import JournalEntry, JournalEntryItem
from hr.forms import (
    ComplaintForm, DisciplinaryActionForm, HSEIncidentForm,
    HSEInspectionForm, HSETrainingForm,
    LeaveRequestForm, PerformanceReviewQuickForm, TrainingProgramForm,
    JobVacancyForm, JobApplicationQuickForm, PerformanceTargetQuickForm,
    TeamTargetQuickForm, AttendanceRecordQuickForm
)

# تقييم الأداء والأهداف

# === تقييم الأداء ===

@login_required
@permission_required('hr.view_performancereview', raise_exception=True)
def performance_dashboard(request):
    """لوحة تحكم تقييم الأداء"""
    from django.db.models import Avg
    avg_performance = 0
    try:
        avg_perf = PerformanceReview.objects.filter(status='approved', overall_rating__isnull=False).aggregate(avg=Avg('overall_rating'))
        if avg_perf['avg']:
            # تحويل من مقياس 5 إلى نسبة مئوية
            avg_performance = round((avg_perf['avg'] / 5) * 100, 1)
    except Exception:
        avg_performance = 0

    # بيانات الرسم البياني الحقيقية
    approved_reviews = PerformanceReview.objects.filter(
        status='approved',
        overall_rating__isnull=False
    )
    chart_data = {
        'excellent': approved_reviews.filter(overall_rating__gte=4.5).count(),
        'very_good': approved_reviews.filter(overall_rating__gte=3.5, overall_rating__lt=4.5).count(),
        'good': approved_reviews.filter(overall_rating__gte=2.5, overall_rating__lt=3.5).count(),
        'needs_improvement': approved_reviews.filter(overall_rating__gte=1.5, overall_rating__lt=2.5).count(),
        'poor': approved_reviews.filter(overall_rating__lt=1.5).count(),
    }

    context = {
        'pending_reviews': PerformanceReview.objects.filter(status='draft').count(),
        'completed_reviews': PerformanceReview.objects.filter(status='approved').count(),
        'recent_reviews': PerformanceReview.objects.select_related('employee', 'reviewer').order_by('-created_at')[:10],
        'avg_performance': avg_performance,
        'chart_data': chart_data,
    }
    return render(request, 'hr/performance_dashboard.html', context)

@login_required
def performance_review_list(request):
    """قائمة تقييمات الأداء"""
    reviews = PerformanceReview.objects.select_related('employee', 'reviewer').order_by('-review_period_end')
    form = PerformanceReviewQuickForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request,'تم إضافة تقييم أداء')
        return redirect('hr:performance_review_list')
    context = {'reviews': reviews,'form': form}
    return render(request, 'hr/performance_review_list.html', context)

@login_required
def performance_review_create(request):
    """إنشاء تقييم أداء"""
    if request.method == 'POST':
        # منطق إنشاء التقييم
        messages.success(request, 'تم إنشاء تقييم الأداء بنجاح')
        return redirect('hr:performance_review_list')
    
    context = {
        'employees': Employee.objects.filter(status='active'),
        'rating_choices': PerformanceReview.RATING_CHOICES,
    }
    return render(request, 'hr/performance_review_form.html', context)

@login_required
def performance_review_detail(request, pk):
    """تفاصيل تقييم الأداء"""
    review = get_object_or_404(PerformanceReview, pk=pk)
    context = {'review': review}
    return render(request, 'hr/performance_review_detail.html', context)

# === نظام الأهداف والتارجت المتطور ===

@login_required
def targets_dashboard(request):
    """لوحة تحكم الأهداف والتارجت"""

    
    # إحصائيات عامة
    total_active_targets = PerformanceTarget.objects.filter(status='active').count()
    completed_targets = PerformanceTarget.objects.filter(status='completed').count()
    overdue_targets = PerformanceTarget.objects.filter(
        status='active',
        end_date__lt=timezone.now().date()
    ).count()
    
    # الأهداف الشخصية للمستخدم الحالي (إذا كان موظف)
    user_targets = []
    if hasattr(request.user, 'employee_profile'):
        user_targets = PerformanceTarget.objects.filter(
            employee=request.user.employee_profile,
            status__in=['active', 'completed']
        ).order_by('-start_date')[:5]
    
    # أهداف الفريق
    team_targets = TeamTarget.objects.filter(status='active').order_by('-start_date')[:5]
    
    # إحصائيات الإنجاز
    achievement_stats = []
    for target in PerformanceTarget.objects.filter(status='active')[:10]:
        achievement_stats.append({
            'target': target,
            'percentage': target.achievement_percentage,
            'level': target.performance_level
        })
    
    context = {
        'total_active_targets': total_active_targets,
        'completed_targets': completed_targets,
        'overdue_targets': overdue_targets,
        'user_targets': user_targets,
        'team_targets': team_targets,
        'achievement_stats': achievement_stats,
        'target_categories': TargetCategory.objects.filter(is_active=True)
    }
    
    return render(request, 'hr/targets_dashboard.html', context)


@login_required
def targets_list(request):
    """قائمة الأهداف"""
    from django.db.models import Q
    qs = PerformanceTarget.objects.select_related('employee', 'category')
    search = request.GET.get('search')
    if search:
        qs = qs.filter(
            Q(title__icontains=search) |
            Q(employee__arabic_name__icontains=search) |
            Q(category__name__icontains=search)
        )
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    category = request.GET.get('category')
    if category:
        qs = qs.filter(category_id=category)
    form = PerformanceTargetQuickForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.assigned_by = request.user
        obj.save()
        messages.success(request,'تم إنشاء هدف')
        return redirect('hr:targets_list')
    context = {
        'targets': qs.order_by('-start_date'),
        'status_choices': PerformanceTarget.STATUS_CHOICES,
        'target_categories': TargetCategory.objects.filter(is_active=True),
        'form': form,
        'search_query': search,
        'status_filter': status,
        'category_filter': category,
    }
    return render(request, 'hr/targets_list.html', context)


@login_required
def target_create(request):
    """إنشاء هدف جديد"""
    
    if request.method == 'POST':
        try:
            target = PerformanceTarget.objects.create(
                employee_id=request.POST.get('employee'),
                category_id=request.POST.get('category'),
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                target_period=request.POST.get('target_period'),
                target_type=request.POST.get('target_type'),
                target_value=request.POST.get('target_value'),
                unit=request.POST.get('unit', 'عدد'),
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date'),
                weight=request.POST.get('weight', 100),
                priority=request.POST.get('priority', 'medium'),
                min_acceptable=request.POST.get('min_acceptable') or None,
                excellence_threshold=request.POST.get('excellence_threshold') or None,
                reward_amount=request.POST.get('reward_amount', 0),
                assigned_by=request.user
            )
            messages.success(request, 'تم إنشاء الهدف بنجاح!')
            return redirect('hr:targets_list')
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'employees': Employee.objects.filter(status='active'),
        'categories': TargetCategory.objects.filter(is_active=True),
        'target_periods': PerformanceTarget.TARGET_PERIODS,
        'target_types': PerformanceTarget.TARGET_TYPES,
        'priority_choices': [('low', 'منخفضة'), ('medium', 'متوسطة'), 
                           ('high', 'عالية'), ('critical', 'حرجة')]
    }
    
    return render(request, 'hr/target_form.html', context)


@login_required
def target_detail(request, pk):
    """تفاصيل الهدف"""

    
    target = get_object_or_404(PerformanceTarget, pk=pk)
    
    # سجل التقدم
    progress_history = TargetProgress.objects.filter(target=target).order_by('-timestamp')[:10]
    
    context = {
        'target': target,
        'progress_history': progress_history,
        'can_edit': request.user.is_superuser or request.user == target.assigned_by
    }
    
    return render(request, 'hr/target_detail.html', context)


@login_required
def target_update_progress(request, pk):
    """تحديث تقدم الهدف"""

    
    target = get_object_or_404(PerformanceTarget, pk=pk)
    
    if request.method == 'POST':
        try:
            new_value = float(request.POST.get('new_value', 0))
            notes = request.POST.get('notes', '')
            
            target.update_progress(new_value, notes, request.user)
            
            messages.success(request, 'تم تحديث التقدم بنجاح!')
            return redirect('hr:target_detail', pk=pk)
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    return redirect('hr:target_detail', pk=pk)


@login_required
def employee_targets(request, employee_id):
    """أهداف موظف معين"""

    
    employee = get_object_or_404(Employee, pk=employee_id)
    targets = PerformanceTarget.objects.filter(employee=employee).order_by('-start_date')
    
    # إحصائيات الموظف
    active_targets = targets.filter(status='active').count()
    completed_targets = targets.filter(status='completed').count()
    overdue_targets = targets.filter(status='active', end_date__lt=timezone.now().date()).count()
    
    # متوسط الإنجاز
    avg_achievement = 0
    if targets.exists():
        total_achievement = sum([t.achievement_percentage for t in targets])
        avg_achievement = total_achievement / targets.count()
    
    context = {
        'employee': employee,
        'targets': targets,
        'active_targets': active_targets,
        'completed_targets': completed_targets,
        'overdue_targets': overdue_targets,
        'avg_achievement': round(avg_achievement, 2)
    }
    
    return render(request, 'hr/employee_targets.html', context)


@login_required
def team_targets_list(request):
    """قائمة أهداف الفرق"""
    team_targets = TeamTarget.objects.select_related('department', 'category')
    search = request.GET.get('search')
    if search:
        team_targets = team_targets.filter(
            Q(title__icontains=search) |
            Q(team_name__icontains=search) |
            Q(department__name__icontains=search)
        )
    form = TeamTargetQuickForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request,'تم إضافة هدف فريق')
        return redirect('hr:team_targets_list')
    context = {
        'team_targets': team_targets.order_by('-start_date'),
        'form': form,
        'search_query': search,
    }
    return render(request, 'hr/team_targets_list.html', context)


@login_required
def performance_analytics(request):
    """تحليلات الأداء المتقدمة"""
    from django.db.models import Avg, Count
    
    # تحليل الأهداف حسب الفئة
    category_stats = []

    for category in TargetCategory.objects.filter(is_active=True):
        targets = PerformanceTarget.objects.filter(category=category, status='active')
        if targets.exists():
            avg_achievement = sum([t.achievement_percentage for t in targets]) / targets.count()
            category_stats.append({
                'category': category,
                'total_targets': targets.count(),
                'avg_achievement': round(avg_achievement, 2),
                'completed_count': targets.filter(status='completed').count()
            })
    
    # أفضل الموظفين أداءً
    top_performers = []
    for employee in Employee.objects.filter(status='active')[:10]:
        targets = PerformanceTarget.objects.filter(employee=employee, status__in=['active', 'completed'])
        if targets.exists():
            avg_achievement = sum([t.achievement_percentage for t in targets]) / targets.count()
            top_performers.append({
                'employee': employee,
                'avg_achievement': round(avg_achievement, 2),
                'total_targets': targets.count(),
                'completed_targets': targets.filter(status='completed').count()
            })
    
    # ترتيب حسب الأداء
    top_performers.sort(key=lambda x: x['avg_achievement'], reverse=True)
    top_performers = top_performers[:10]
    
    # إحصائيات شهرية
    from datetime import datetime, timedelta
    monthly_stats = []
    for i in range(6):  # آخر 6 شهور
        month_date = timezone.now().date().replace(day=1) - timedelta(days=30*i)
        month_targets = PerformanceTarget.objects.filter(
            start_date__year=month_date.year,
            start_date__month=month_date.month
        )
        
        monthly_stats.append({
            'month': month_date.strftime('%Y-%m'),
            'total_targets': month_targets.count(),
            'completed_targets': month_targets.filter(status='completed').count(),
            'avg_achievement': round(sum([t.achievement_percentage for t in month_targets]) / month_targets.count() if month_targets.exists() else 0, 2)
        })
    
    context = {
        'category_stats': category_stats,
        'top_performers': top_performers,
        'monthly_stats': monthly_stats[::-1],  # عكس الترتيب لأحدث أولاً
        'total_metrics': PerformanceMetric.objects.filter(is_active=True).count(),
        'total_measurements': EmployeeMetricValue.objects.count()
    }
    
    return render(request, 'hr/performance_analytics.html', context)


# === التدريب والتطوير ===
