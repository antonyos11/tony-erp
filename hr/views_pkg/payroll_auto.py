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

# حساب الرواتب التلقائي

# ============================================================================
# Auto Payroll Calculator Views
# ============================================================================

@login_required
@permission_required('hr.add_payroll', raise_exception=True)
def payroll_auto_calculate(request):
    """حساب تلقائي للرواتب"""
    from hr.payroll_calculator import bulk_calculate_payroll
    from datetime import date
    
    # Default to current month
    today = date.today()
    first_day = today.replace(day=1)
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    last_day = next_month - timedelta(days=1)
    
    if request.method == 'POST':
        try:
            period_start = date.fromisoformat(request.POST['period_start'])
            period_end = date.fromisoformat(request.POST['period_end'])
            
            # Calculate payroll
            results = bulk_calculate_payroll(period_start, period_end)
            
            messages.success(
                request,
                f'تم الحساب التلقائي: {results["created"]} جديد، {results["updated"]} محدّث، {results["failed"]} فشل'
            )
            
            if results['errors']:
                for error in results['errors'][:5]:  # Show first 5 errors
                    messages.warning(request, error)
            
            return redirect('hr:payroll_list')
        
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    # Get active employees count
    active_employees = Employee.objects.filter(status='active').count()
    
    context = {
        'period_start': first_day.isoformat(),
        'period_end': last_day.isoformat(),
        'active_employees': active_employees,
    }
    return render(request, 'hr/payroll_auto_calculate.html', context)


# === مفردات المرتب - البدلات والخصومات ===
