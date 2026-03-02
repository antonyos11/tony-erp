"""
واجهات الموارد البشرية — RITA ERP
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView,
    TemplateView, View, FormView,
)

from apps.core.models import Branch
from apps.core.mixins import apply_branch_filter, BranchCreateMixin
from apps.hr.models import (
    Department, JobTitle, Employee, Attendance,
    LeaveRequest, LeaveBalance, Penalty, SalaryAdvance,
    Payroll, PayrollLine, ProductionPieceWork,
)
from apps.hr.services.payroll_engine import PayrollEngine


# ══════════════════════════════════════════════════════
# Forms
# ══════════════════════════════════════════════════════

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'user', 'employee_number', 'full_name_ar', 'full_name_en',
            'national_id', 'date_of_birth', 'gender', 'marital_status',
            'phone', 'phone2', 'address', 'governorate',
            'emergency_contact', 'emergency_phone',
            'branch', 'department', 'job_title', 'employment_type',
            'hire_date', 'contract_end_date', 'direct_manager',
            'basic_salary', 'housing_allowance', 'transport_allowance',
            'food_allowance', 'other_allowances',
            'social_insurance_number', 'social_insurance_deduction',
            'tax_deduction', 'bank_name', 'bank_account',
            'daily_rate', 'piece_rate', 'production_line',
            'is_active', 'termination_date', 'termination_reason', 'photo',
        ]
        widgets = {f: forms.TextInput(attrs={'class': 'form-control'}) for f in [
            'employee_number', 'full_name_ar', 'full_name_en', 'national_id',
            'phone', 'phone2', 'governorate', 'emergency_contact', 'emergency_phone',
            'social_insurance_number', 'bank_name', 'bank_account',
        ]}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _select = {'class': 'form-select'}
        _num = {'class': 'form-control', 'step': '0.01'}
        _date = {'class': 'form-control', 'type': 'date'}
        for f in ['user', 'gender', 'marital_status', 'branch', 'department',
                  'job_title', 'employment_type', 'direct_manager', 'production_line']:
            self.fields[f].widget.attrs.update(_select)
        for f in ['basic_salary', 'housing_allowance', 'transport_allowance',
                  'food_allowance', 'other_allowances', 'social_insurance_deduction',
                  'tax_deduction', 'daily_rate', 'piece_rate']:
            self.fields[f].widget = forms.NumberInput(attrs=_num)
        for f in ['date_of_birth', 'hire_date', 'contract_end_date', 'termination_date']:
            self.fields[f].widget = forms.DateInput(attrs=_date)
        self.fields['address'].widget = forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
        self.fields['termination_reason'].widget = forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
        self.fields['photo'].widget = forms.FileInput(attrs={'class': 'form-control'})
        for fname, fobj in self.fields.items():
            if isinstance(fobj, forms.BooleanField):
                fobj.widget.attrs['class'] = 'form-check-input'


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'status', 'check_in', 'check_out',
                  'overtime_hours', 'late_minutes', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'check_in': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'overtime_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
            'late_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'days_count', 'reason']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'days_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PenaltyForm(forms.ModelForm):
    class Meta:
        model = Penalty
        fields = ['employee', 'penalty_type', 'date', 'amount', 'days', 'reason', 'approved_by']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'penalty_type': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'days': forms.NumberInput(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'approved_by': forms.Select(attrs={'class': 'form-select'}),
        }


class SalaryAdvanceForm(forms.ModelForm):
    class Meta:
        model = SalaryAdvance
        fields = ['employee', 'date', 'amount', 'reason', 'deduction_months',
                  'monthly_deduction', 'remaining_amount']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'deduction_months': forms.NumberInput(attrs={'class': 'form-control'}),
            'monthly_deduction': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'remaining_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class PayrollCalculateForm(forms.Form):
    MONTHS = [(i, f"{i:02d}") for i in range(1, 13)]
    month = forms.ChoiceField(choices=MONTHS, label="الشهر",
                              widget=forms.Select(attrs={'class': 'form-select'}))
    year = forms.IntegerField(min_value=2000, max_value=2100, initial=timezone.now().year,
                              label="السنة",
                              widget=forms.NumberInput(attrs={'class': 'form-control'}))
    branch = forms.ModelChoiceField(queryset=Branch.objects.all(), label="الفرع",
                                    widget=forms.Select(attrs={'class': 'form-select'}))


class AttendanceBulkForm(forms.Form):
    date = forms.DateField(label="التاريخ",
                           widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    branch = forms.ModelChoiceField(queryset=Branch.objects.all(), label="الفرع",
                                    widget=forms.Select(attrs={'class': 'form-select'}))
    department = forms.ModelChoiceField(queryset=Department.objects.filter(is_active=True),
                                        required=False, label="القسم",
                                        widget=forms.Select(attrs={'class': 'form-select'}))


class PieceWorkForm(forms.ModelForm):
    class Meta:
        model = ProductionPieceWork
        fields = ['employee', 'date', 'production_order', 'product', 'quantity', 'rate', 'total', 'is_approved']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'production_order': forms.Select(attrs={'class': 'form-select'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# ══════════════════════════════════════════════════════
# Employee Views
# ══════════════════════════════════════════════════════

class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = 'hr/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 30

    def get_queryset(self):
        qs = Employee.objects.select_related('branch', 'department', 'job_title').order_by('employee_number')
        qs = apply_branch_filter(qs, self.request)
        q = self.request.GET.get('q', '')
        branch_id = self.request.GET.get('branch', '')
        dept_id = self.request.GET.get('department', '')
        emp_type = self.request.GET.get('employment_type', '')
        is_active = self.request.GET.get('is_active', '')

        if q:
            qs = qs.filter(
                Q(full_name_ar__icontains=q) | Q(employee_number__icontains=q) |
                Q(national_id__icontains=q) | Q(phone__icontains=q)
            )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        if emp_type:
            qs = qs.filter(employment_type=emp_type)
        if is_active in ('1', '0'):
            qs = qs.filter(is_active=(is_active == '1'))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['branches'] = Branch.objects.all()
        ctx['departments'] = Department.objects.filter(is_active=True)
        ctx['employment_types'] = Employee.EMPLOYMENT_TYPES
        ctx['total_count'] = self.get_queryset().count()
        return ctx


class EmployeeCreateView(LoginRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    success_url = reverse_lazy('hr:employee_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "تم إضافة الموظف بنجاح")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'إضافة موظف جديد'
        ctx['action'] = 'create'
        return ctx


class EmployeeDetailView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = 'hr/employee_detail.html'
    context_object_name = 'employee'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        emp = self.object
        ctx['attendances'] = emp.attendances.order_by('-date')[:30]
        ctx['leave_requests'] = emp.leave_requests.order_by('-start_date')[:10]
        ctx['payroll_lines'] = emp.payrollline_set.select_related('payroll').order_by(
            '-payroll__year', '-payroll__month')[:12]
        ctx['penalties'] = emp.penalties.order_by('-date')[:10]
        ctx['advances'] = emp.advances.order_by('-date')[:10]
        ctx['leave_balance'] = emp.leave_balances.filter(year=timezone.now().year).first()
        return ctx


class EmployeeUpdateView(LoginRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'

    def get_success_url(self):
        return reverse_lazy('hr:employee_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "تم تحديث بيانات الموظف")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'تعديل: {self.object.full_name_ar}'
        ctx['action'] = 'update'
        return ctx


# ══════════════════════════════════════════════════════
# Attendance Views
# ══════════════════════════════════════════════════════

class AttendanceListView(LoginRequiredMixin, ListView):
    model = Attendance
    template_name = 'hr/attendance_list.html'
    context_object_name = 'attendances'
    paginate_by = 50

    def get_queryset(self):
        qs = Attendance.objects.select_related('employee', 'employee__branch').order_by('-date')
        emp_id = self.request.GET.get('employee', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        branch_id = self.request.GET.get('branch', '')
        status = self.request.GET.get('status', '')

        if emp_id:
            qs = qs.filter(employee_id=emp_id)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if branch_id:
            qs = qs.filter(employee__branch_id=branch_id)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['employees'] = Employee.objects.filter(is_active=True).order_by('full_name_ar')
        ctx['branches'] = Branch.objects.all()
        ctx['statuses'] = Attendance.ATTENDANCE_STATUSES
        return ctx


class AttendanceBulkCreateView(LoginRequiredMixin, FormView):
    template_name = 'hr/attendance_bulk_form.html'
    form_class = AttendanceBulkForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        branch_id = self.request.GET.get('branch', '')
        dept_id = self.request.GET.get('department', '')
        date = self.request.GET.get('date', timezone.now().date())
        employees = Employee.objects.filter(is_active=True)
        if branch_id:
            employees = employees.filter(branch_id=branch_id)
        if dept_id:
            employees = employees.filter(department_id=dept_id)
        ctx['employees'] = employees.select_related('department', 'job_title')
        ctx['statuses'] = Attendance.ATTENDANCE_STATUSES
        ctx['branches'] = Branch.objects.all()
        ctx['departments'] = Department.objects.filter(is_active=True)
        ctx['selected_date'] = date
        return ctx

    def post(self, request, *args, **kwargs):
        date_val = request.POST.get('date')
        employee_ids = request.POST.getlist('employee_ids')
        created = 0
        for emp_id in employee_ids:
            status = request.POST.get(f'status_{emp_id}', 'present')
            check_in = request.POST.get(f'check_in_{emp_id}') or None
            check_out = request.POST.get(f'check_out_{emp_id}') or None
            overtime = request.POST.get(f'overtime_{emp_id}', 0) or 0
            late_min = request.POST.get(f'late_{emp_id}', 0) or 0
            Attendance.objects.update_or_create(
                employee_id=emp_id, date=date_val,
                defaults={
                    'status': status,
                    'check_in': check_in,
                    'check_out': check_out,
                    'overtime_hours': overtime,
                    'late_minutes': late_min,
                    'created_by': request.user,
                    'updated_by': request.user,
                }
            )
            created += 1
        messages.success(request, f"تم تسجيل الحضور لـ {created} موظف")
        return redirect('hr:attendance_list')


# ══════════════════════════════════════════════════════
# Leave Views
# ══════════════════════════════════════════════════════

class LeaveRequestListView(LoginRequiredMixin, ListView):
    model = LeaveRequest
    template_name = 'hr/leave_list.html'
    context_object_name = 'leaves'
    paginate_by = 30

    def get_queryset(self):
        qs = LeaveRequest.objects.select_related('employee').order_by('-start_date')
        status = self.request.GET.get('status', '')
        emp_id = self.request.GET.get('employee', '')
        if status:
            qs = qs.filter(status=status)
        if emp_id:
            qs = qs.filter(employee_id=emp_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['employees'] = Employee.objects.filter(is_active=True).order_by('full_name_ar')
        return ctx


class LeaveRequestCreateView(LoginRequiredMixin, CreateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'hr/leave_form.html'
    success_url = reverse_lazy('hr:leave_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "تم تقديم طلب الإجازة")
        return super().form_valid(form)


class LeaveApproveView(LoginRequiredMixin, View):
    template_name = 'hr/leave_approve.html'

    def get(self, request, pk):
        leave = get_object_or_404(LeaveRequest, pk=pk)
        return render_template(request, self.template_name, {'leave': leave})

    def post(self, request, pk):
        leave = get_object_or_404(LeaveRequest, pk=pk)
        action = request.POST.get('action')
        if action == 'approve':
            leave.status = 'approved'
            leave.approved_by = request.user
            leave.approved_at = timezone.now()
            leave.save()
            messages.success(request, "تم اعتماد الإجازة")
        elif action == 'reject':
            leave.status = 'rejected'
            leave.rejection_reason = request.POST.get('rejection_reason', '')
            leave.save()
            messages.warning(request, "تم رفض طلب الإجازة")
        return redirect('hr:leave_list')


# ══════════════════════════════════════════════════════
# Penalty Views
# ══════════════════════════════════════════════════════

class PenaltyListView(LoginRequiredMixin, ListView):
    model = Penalty
    template_name = 'hr/penalty_list.html'
    context_object_name = 'penalties'
    paginate_by = 30

    def get_queryset(self):
        qs = Penalty.objects.select_related('employee').order_by('-date')
        emp_id = self.request.GET.get('employee', '')
        ptype = self.request.GET.get('penalty_type', '')
        if emp_id:
            qs = qs.filter(employee_id=emp_id)
        if ptype:
            qs = qs.filter(penalty_type=ptype)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['employees'] = Employee.objects.filter(is_active=True).order_by('full_name_ar')
        ctx['penalty_types'] = Penalty.PENALTY_TYPES
        return ctx


class PenaltyCreateView(LoginRequiredMixin, CreateView):
    model = Penalty
    form_class = PenaltyForm
    template_name = 'hr/penalty_form.html'
    success_url = reverse_lazy('hr:penalty_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "تم الحفظ بنجاح")
        return super().form_valid(form)


# ══════════════════════════════════════════════════════
# Salary Advance Views
# ══════════════════════════════════════════════════════

class SalaryAdvanceListView(LoginRequiredMixin, ListView):
    model = SalaryAdvance
    template_name = 'hr/advance_list.html'
    context_object_name = 'advances'
    paginate_by = 30

    def get_queryset(self):
        qs = SalaryAdvance.objects.select_related('employee').order_by('-date')
        emp_id = self.request.GET.get('employee', '')
        status = self.request.GET.get('status', '')
        if emp_id:
            qs = qs.filter(employee_id=emp_id)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['employees'] = Employee.objects.filter(is_active=True).order_by('full_name_ar')
        return ctx


class SalaryAdvanceCreateView(LoginRequiredMixin, CreateView):
    model = SalaryAdvance
    form_class = SalaryAdvanceForm
    template_name = 'hr/advance_form.html'
    success_url = reverse_lazy('hr:advance_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "تم تسجيل السلفة بنجاح")
        return super().form_valid(form)


# ══════════════════════════════════════════════════════
# Payroll Views
# ══════════════════════════════════════════════════════

class PayrollListView(LoginRequiredMixin, ListView):
    model = Payroll
    template_name = 'hr/payroll_list.html'
    context_object_name = 'payrolls'
    paginate_by = 20

    def get_queryset(self):
        qs = Payroll.objects.select_related('branch').order_by('-year', '-month')
        qs = apply_branch_filter(qs, self.request)
        branch_id = self.request.GET.get('branch', '')
        status = self.request.GET.get('status', '')
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['branches'] = Branch.objects.all()
        ctx['statuses'] = Payroll.PAYROLL_STATUSES
        return ctx


class PayrollCalculateView(LoginRequiredMixin, FormView):
    template_name = 'hr/payroll_calculate.html'
    form_class = PayrollCalculateForm

    def form_valid(self, form):
        month = int(form.cleaned_data['month'])
        year = form.cleaned_data['year']
        branch = form.cleaned_data['branch']
        try:
            payroll = PayrollEngine.calculate_payroll(month, year, branch, user=self.request.user)
            messages.success(self.request, f"تم حساب مسيّر رواتب {month}/{year} — {payroll.lines.count()} موظف")
            return redirect('hr:payroll_detail', pk=payroll.pk)
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)


class PayrollDetailView(LoginRequiredMixin, DetailView):
    model = Payroll
    template_name = 'hr/payroll_detail.html'
    context_object_name = 'payroll'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['lines'] = self.object.lines.select_related('employee').order_by('employee__employee_number')
        return ctx


class PayrollApproveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        payroll = get_object_or_404(Payroll, pk=pk)
        try:
            PayrollEngine.approve_payroll(payroll, user=request.user)
            messages.success(request, "تم اعتماد المسيّر")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('hr:payroll_detail', pk=pk)


class PayrollPayView(LoginRequiredMixin, View):
    def post(self, request, pk):
        payroll = get_object_or_404(Payroll, pk=pk)
        try:
            PayrollEngine.pay_payroll(payroll, user=request.user)
            messages.success(request, "تم صرف الرواتب وإنشاء القيد المحاسبي")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('hr:payroll_detail', pk=pk)


class PayslipView(LoginRequiredMixin, DetailView):
    model = PayrollLine
    template_name = 'hr/payslip.html'
    context_object_name = 'line'

    def get_object(self):
        return get_object_or_404(
            PayrollLine,
            payroll_id=self.kwargs['pk'],
            employee_id=self.kwargs['employee_pk'],
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['payroll'] = self.object.payroll
        ctx['employee'] = self.object.employee
        return ctx


# ══════════════════════════════════════════════════════
# Department Views
# ══════════════════════════════════════════════════════

class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'hr/department_list.html'
    context_object_name = 'departments'

    def get_queryset(self):
        return Department.objects.select_related('branch', 'manager').order_by('name')


# ══════════════════════════════════════════════════════
# Piece Work Views
# ══════════════════════════════════════════════════════

class PieceWorkListView(LoginRequiredMixin, ListView):
    model = ProductionPieceWork
    template_name = 'hr/piece_work_list.html'
    context_object_name = 'piece_works'
    paginate_by = 30

    def get_queryset(self):
        qs = ProductionPieceWork.objects.select_related('employee', 'product').order_by('-date')
        emp_id = self.request.GET.get('employee', '')
        is_approved = self.request.GET.get('is_approved', '')
        if emp_id:
            qs = qs.filter(employee_id=emp_id)
        if is_approved in ('1', '0'):
            qs = qs.filter(is_approved=(is_approved == '1'))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['employees'] = Employee.objects.filter(is_active=True, employment_type='production')
        return ctx


class PieceWorkCreateView(LoginRequiredMixin, CreateView):
    model = ProductionPieceWork
    form_class = PieceWorkForm
    template_name = 'hr/piece_work_form.html'
    success_url = reverse_lazy('hr:piece_work_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "تم تسجيل عمل القطعة")
        return super().form_valid(form)


# Helper for class-based views that need render
from django.shortcuts import render as django_render


def render_template(request, template, context):
    return django_render(request, template, context)


# Patch LeaveApproveView.get to use render
LeaveApproveView.get = lambda self, request, pk: django_render(
    request,
    'hr/leave_approve.html',
    {'leave': get_object_or_404(LeaveRequest, pk=pk)}
)


# ══════════════════════════════════════════════════════
# Sprint 20 — إنهاء خدمة موظف
# ══════════════════════════════════════════════════════

class EmployeeTerminateView(LoginRequiredMixin, View):
    """إنهاء خدمة موظف"""
    def get(self, request, pk):
        from apps.hr.models import Employee
        from django.shortcuts import render
        employee = get_object_or_404(Employee, pk=pk)
        return render(request, 'hr/employee_terminate.html', {
            'title': f'إنهاء خدمة: {employee.full_name_ar}',
            'employee': employee,
        })

    def post(self, request, pk):
        from apps.hr.models import Employee
        employee = get_object_or_404(Employee, pk=pk)
        termination_date = request.POST.get('termination_date')
        reason = request.POST.get('reason', '')

        employee.status = 'terminated'
        employee.termination_date = termination_date
        employee.termination_reason = reason
        employee.save()

        # تعطيل حساب المستخدم المرتبط
        try:
            if hasattr(employee, 'user') and employee.user:
                employee.user.is_active = False
                employee.user.save()
        except Exception:
            pass

        from django.contrib import messages
        messages.success(request, f'تم إنهاء خدمة الموظف {employee.full_name_ar}')
        return redirect('hr:employee_detail', pk=pk)
