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

# لوحة التحكم الرئيسية

# === لوحات التحكم الرئيسية ===

@login_required
def hr_dashboard(request):
    """لوحة تحكم الموارد البشرية الرئيسية"""
    context = {
        'total_employees': Employee.objects.filter(status='active').count(),
        'departments_count': Department.objects.count(),
        'pending_leaves': LeaveRequest.objects.filter(status='pending').count(),
        'today_attendance': AttendanceRecord.objects.filter(
            date=date.today(), 
            record_type='check_in'
        ).count(),
        'recent_hires': Employee.objects.filter(
            hire_date__gte=date.today() - timedelta(days=30)
        ).order_by('-hire_date')[:5],
        'pending_reviews': PerformanceReview.objects.filter(status='draft').count(),
        'active_trainings': TrainingProgram.objects.filter(
            start_date__lte=date.today(),
            end_date__gte=date.today()
        ).count(),
    }
    return render(request, 'hr/dashboard.html', context)

# === إدارة الموظفين ===

