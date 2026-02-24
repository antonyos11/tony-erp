"""
Employee Loans Management Views
إدارة سلف الموظفين
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.http import HttpResponse
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from .models import EmployeeLoan, LoanInstallment, Employee, Payroll
from .forms import (
    EmployeeLoanForm, EmployeeLoanApprovalForm, 
    LoanInstallmentDeferForm, PayrollPrintForm
)


# === إدارة السلف ===

@login_required
@permission_required('hr.view_employeeloan', raise_exception=True)
def loans_dashboard(request):
    """لوحة تحكم السلف"""
    
    # إحصائيات
    total_loans = EmployeeLoan.objects.count()
    pending_loans = EmployeeLoan.objects.filter(status='pending').count()
    active_loans = EmployeeLoan.objects.filter(status__in=['approved', 'active']).count()
    completed_loans = EmployeeLoan.objects.filter(status='completed').count()
    
    # إجمالي المبالغ
    total_amount = EmployeeLoan.objects.filter(
        status__in=['approved', 'active', 'completed']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    total_paid = EmployeeLoan.objects.filter(
        status__in=['approved', 'active', 'completed']
    ).aggregate(total=Sum('paid_amount'))['total'] or Decimal('0')
    
    total_remaining = total_amount - total_paid
    
    # السلف الأخيرة
    recent_loans = EmployeeLoan.objects.select_related(
        'employee', 'approved_by'
    ).order_by('-created_at')[:10]
    
    # السلف المعلقة للموافقة
    pending_approvals = EmployeeLoan.objects.filter(
        status='pending'
    ).select_related('employee').order_by('request_date')[:5]
    
    context = {
        'total_loans': total_loans,
        'pending_loans': pending_loans,
        'active_loans': active_loans,
        'completed_loans': completed_loans,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'recent_loans': recent_loans,
        'pending_approvals': pending_approvals,
    }
    
    return render(request, 'hr/loans/dashboard.html', context)


@login_required
@permission_required('hr.view_employeeloan', raise_exception=True)
def loans_list(request):
    """قائمة السلف مع الفلترة"""
    
    loans = EmployeeLoan.objects.select_related(
        'employee', 'approved_by'
    ).all()
    
    # الفلترة
    status = request.GET.get('status')
    if status:
        loans = loans.filter(status=status)
    
    employee_id = request.GET.get('employee')
    if employee_id:
        loans = loans.filter(employee_id=employee_id)
    
    search = request.GET.get('search')
    if search:
        loans = loans.filter(
            Q(loan_number__icontains=search) |
            Q(employee__arabic_name__icontains=search) |
            Q(employee__first_name__icontains=search) |
            Q(employee__last_name__icontains=search)
        )
    
    loans = loans.order_by('-created_at')
    
    context = {
        'loans': loans,
        'employees': Employee.objects.filter(status='active'),
    }
    
    return render(request, 'hr/loans/list.html', context)


@login_required
def get_employee_loan_info(request, employee_id):
    """جلب معلومات الموظف والسلف النشطة - AJAX"""
    from django.http import JsonResponse
    
    try:
        employee = Employee.objects.select_related('department', 'position').get(id=employee_id)
        
        # السلفة النشطة
        active_loan = EmployeeLoan.objects.filter(
            employee=employee,
            status__in=['approved', 'active']
        ).first()
        
        # سجل السلف السابقة
        previous_loans = EmployeeLoan.objects.filter(
            employee=employee,
            status__in=['completed', 'rejected']
        ).order_by('-created_at')[:5]
        
        data = {
            'employee': {
                'id': employee.id,
                'name': employee.arabic_name,
                'employee_id': employee.employee_id,
                'department': employee.department.arabic_name,
                'position': employee.position.arabic_name,
                'basic_salary': str(employee.basic_salary),
                'hire_date': employee.hire_date.strftime('%Y-%m-%d'),
            },
            'active_loan': None,
            'previous_loans': []
        }
        
        if active_loan:
            paid_installments = active_loan.installments.filter(status='paid').count()
            pending_installments = active_loan.installments.filter(status='pending').count()
            
            data['active_loan'] = {
                'id': active_loan.id,
                'loan_number': active_loan.loan_number,
                'amount': str(active_loan.amount),
                'remaining_amount': str(active_loan.remaining_amount),
                'reason': active_loan.reason,
                'start_date': active_loan.start_date.strftime('%Y-%m-%d') if active_loan.start_date else None,
                'installments_count': active_loan.installments_count,
                'paid_installments': paid_installments,
                'pending_installments': pending_installments,
                'is_emergency': active_loan.is_emergency,
            }
        
        for loan in previous_loans:
            data['previous_loans'].append({
                'loan_number': loan.loan_number,
                'amount': str(loan.amount),
                'reason': loan.reason,
                'status': loan.get_status_display(),
                'created_at': loan.created_at.strftime('%Y-%m-%d'),
            })
        
        return JsonResponse(data)
        
    except Employee.DoesNotExist:
        return JsonResponse({'error': 'الموظف غير موجود'}, status=404)


@login_required
@permission_required('hr.add_employeeloan', raise_exception=True)
def loan_request(request):
    """طلب سلفة جديدة"""
    
    if request.method == 'POST':
        form = EmployeeLoanForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.created_by = request.user
            loan.status = 'pending'
            loan.save()
            
            # إنشاء الأقساط
            create_loan_installments(loan)
            
            messages.success(request, f'تم تقديم طلب السلفة رقم {loan.loan_number} بنجاح')
            return redirect('hr:loan_detail', pk=loan.pk)
    else:
        form = EmployeeLoanForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'hr/loans/request.html', context)


@login_required
@permission_required('hr.view_employeeloan', raise_exception=True)
def loan_detail(request, pk):
    """تفاصيل السلفة"""
    
    loan = get_object_or_404(
        EmployeeLoan.objects.select_related('employee', 'approved_by'),
        pk=pk
    )
    
    # الأقساط
    installments = loan.installments.all().order_by('installment_number')
    
    # عدد الأقساط المخصومة
    deducted_count = installments.filter(status='deducted').count()
    
    context = {
        'loan': loan,
        'installments': installments,
        'deducted_count': deducted_count,
    }
    
    return render(request, 'hr/loans/detail.html', context)


@login_required
@permission_required('hr.view_employeeloan', raise_exception=True)
def loan_receipt(request, pk):
    """طباعة إيصال السلفة"""
    
    loan = get_object_or_404(
        EmployeeLoan.objects.select_related('employee', 'employee__department', 'employee__position', 'approved_by'),
        pk=pk
    )
    
    # الأقساط
    installments = loan.installments.all().order_by('installment_number')
    
    # حساب القسط الشهري
    monthly_installment = loan.amount / loan.installments_count if loan.installments_count > 0 else 0
    
    context = {
        'loan': loan,
        'installments': installments,
        'monthly_installment': monthly_installment,
        'print_date': timezone.now(),
    }
    
    return render(request, 'hr/loans/receipt.html', context)


@login_required
@permission_required('hr.change_employeeloan', raise_exception=True)
def loan_approve(request, pk):
    """الموافقة على السلفة أو رفضها"""
    
    loan = get_object_or_404(EmployeeLoan, pk=pk)
    
    if loan.status != 'pending':
        messages.error(request, 'هذه السلفة تمت معالجتها بالفعل')
        return redirect('hr:loan_detail', pk=pk)
    
    if request.method == 'POST':
        form = EmployeeLoanApprovalForm(request.POST, instance=loan)
        if form.is_valid():
            action = request.POST.get('action')
            
            if action == 'approve':
                loan.status = 'approved'
                loan.approved_by = request.user.employee_profile
                loan.approved_at = timezone.now()
                loan.save()
                
                # إنشاء جدول الأقساط
                create_loan_installments(loan)
                
                messages.success(request, f'تمت الموافقة على السلفة رقم {loan.loan_number} وتم إنشاء جدول الأقساط')
            
            elif action == 'reject':
                loan.status = 'rejected'
                loan.rejection_reason = form.cleaned_data['rejection_reason']
                loan.save()
                
                messages.info(request, f'تم رفض السلفة رقم {loan.loan_number}')
            
            return redirect('hr:loan_detail', pk=pk)
    else:
        form = EmployeeLoanApprovalForm(instance=loan)
    
    context = {
        'loan': loan,
        'form': form,
    }
    
    return render(request, 'hr/loans/approve.html', context)


@login_required
@permission_required('hr.change_loaninstallment', raise_exception=True)
def installment_defer(request, pk):
    """تأجيل قسط السلفة"""
    
    installment = get_object_or_404(LoanInstallment, pk=pk)
    
    if installment.status != 'pending':
        messages.error(request, 'هذا القسط تمت معالجته بالفعل')
        return redirect('hr:loan_detail', pk=installment.loan.pk)
    
    if request.method == 'POST':
        form = LoanInstallmentDeferForm(request.POST)
        if form.is_valid():
            new_due_date = form.cleaned_data['new_due_date']
            reason = form.cleaned_data['reason']
            
            installment.defer_installment(new_due_date, reason)
            
            messages.success(
                request, 
                f'تم تأجيل القسط رقم {installment.installment_number} إلى {new_due_date}'
            )
            return redirect('hr:loan_detail', pk=installment.loan.pk)
    else:
        form = LoanInstallmentDeferForm()
    
    context = {
        'installment': installment,
        'form': form,
    }
    
    return render(request, 'hr/loans/defer_installment.html', context)


@login_required
def employee_loans(request, employee_id):
    """سلف موظف محدد"""
    
    employee = get_object_or_404(Employee, pk=employee_id)
    
    loans = EmployeeLoan.objects.filter(
        employee=employee
    ).order_by('-created_at')
    
    # إحصائيات
    total_loans = loans.count()
    active_loans = loans.filter(status__in=['approved', 'active']).count()
    total_borrowed = loans.filter(
        status__in=['approved', 'active', 'completed']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_paid = loans.filter(
        status__in=['approved', 'active', 'completed']
    ).aggregate(total=Sum('paid_amount'))['total'] or Decimal('0')
    
    context = {
        'employee': employee,
        'loans': loans,
        'total_loans': total_loans,
        'active_loans': active_loans,
        'total_borrowed': total_borrowed,
        'total_paid': total_paid,
        'total_remaining': total_borrowed - total_paid,
    }
    
    return render(request, 'hr/loans/employee_loans.html', context)


# === طباعة كشف الراتب الشامل ===

@login_required
@permission_required('hr.view_payroll', raise_exception=True)
def payroll_comprehensive_report(request):
    """كشف راتب شامل لجميع الموظفين مع كل التفاصيل"""
    
    if request.method == 'GET' and any(k in request.GET for k in ['period_start', 'period_end']):
        form = PayrollPrintForm(request.GET)
        if form.is_valid():
            period_start = form.cleaned_data.get('period_start')
            period_end = form.cleaned_data.get('period_end')
            department = form.cleaned_data.get('department')
            show_details = form.cleaned_data.get('include_details', False)
            
            # جلب كشوف الرواتب
            payrolls = Payroll.objects.filter(
                period_start__gte=period_start,
                period_end__lte=period_end,
                status__in=['calculated', 'approved', 'paid']
            ).select_related('employee', 'employee__department')
            
            if department:
                payrolls = payrolls.filter(employee__department=department)
            
            payrolls = payrolls.order_by('employee__department', 'employee__arabic_name')
            
            # تحضير البيانات
            payroll_data = []
            total_basic_salary = Decimal('0')
            total_allowances = Decimal('0')
            total_deductions = Decimal('0')
            total_loan_deduction = Decimal('0')
            total_net_salary = Decimal('0')
            
            for payroll in payrolls:
                allowances_total = (
                    payroll.housing_allowance + 
                    payroll.transportation_allowance + 
                    payroll.other_allowances
                )
                
                payroll_data.append({
                    'employee': payroll.employee,
                    'basic_salary': payroll.basic_salary,
                    'allowances_total': allowances_total,
                    'deductions_total': payroll.total_deductions,
                    'loan_deduction': Decimal('0'),
                    'net_salary': payroll.net_salary,
                })
                
                total_basic_salary += payroll.basic_salary
                total_allowances += allowances_total
                total_deductions += payroll.total_deductions
                total_net_salary += payroll.net_salary
            
            context = {
                'payroll_data': payroll_data,
                'total_basic_salary': total_basic_salary,
                'total_allowances': total_allowances,
                'total_deductions': total_deductions,
                'total_loan_deduction': total_loan_deduction,
                'total_net_salary': total_net_salary,
                'start_date': period_start,
                'end_date': period_end,
                'include_details': show_details,
                'form': form,
            }
            
            if request.GET.get('export_pdf'):
                return render_payroll_pdf(request, context)
            else:
                return render(request, 'hr/loans/comprehensive_report.html', context)
    
    # عرض النموذج الأولي
    today = date.today()
    first_day = today.replace(day=1)
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    last_day = next_month - timedelta(days=1)
    
    form = PayrollPrintForm(initial={
        'period_start': first_day,
        'period_end': last_day,
    })
    
    context = {
        'form': form,
    }
    
    return render(request, 'hr/loans/comprehensive_report_form.html', context)


# === وظائف مساعدة ===

def create_loan_installments(loan):
    """إنشاء الأقساط الشهرية للسلفة"""
    
    # حذف الأقساط القديمة إن وجدت
    loan.installments.all().delete()
    
    start_date = loan.start_deduction_date
    monthly_amount = loan.monthly_installment
    
    for i in range(loan.installments_count):
        due_date = start_date + relativedelta(months=i)
        
        # القسط الأخير قد يكون أقل بسبب التقريب
        if i == loan.installments_count - 1:
            # حساب المبلغ المتبقي
            paid_so_far = monthly_amount * i
            amount = loan.amount - paid_so_far
        else:
            amount = monthly_amount
        
        LoanInstallment.objects.create(
            loan=loan,
            installment_number=i + 1,
            amount=amount,
            due_date=due_date,
            status='pending'
        )


def render_payroll_pdf(request, context):
    """تصدير كشف الراتب كـ PDF"""
    from django.template.loader import render_to_string
    from weasyprint import HTML
    import tempfile
    
    html_string = render_to_string('hr/loans/comprehensive_report_pdf.html', context)
    html = HTML(string=html_string)
    
    result = html.write_pdf()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="payroll_report_{context["period_start"]}_{context["period_end"]}.pdf"'
    response.write(result)
    
    return response
