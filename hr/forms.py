from django import forms
from .models import (
    Complaint, DisciplinaryAction, HSEIncident, HSEInspection, HSETraining,
    LeaveRequest, PerformanceReview, TrainingProgram, JobVacancy, JobApplication,
    PerformanceTarget, TeamTarget, AttendanceRecord, LeaveType, TargetCategory, Employee,
    EmployeeLoan, LoanInstallment
)

class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['employee','subject','description','status']

class DisciplinaryActionForm(forms.ModelForm):
    class Meta:
        model = DisciplinaryAction
        fields = ['employee','action_type','description','date']
        widgets = {
            'date': forms.DateInput(attrs={'type':'date'})
        }

class HSEIncidentForm(forms.ModelForm):
    class Meta:
        model = HSEIncident
        fields = ['date','description','employee','department','status']
        widgets = {
            'date': forms.DateInput(attrs={'type':'date'})
        }

class HSEInspectionForm(forms.ModelForm):
    class Meta:
        model = HSEInspection
        fields = ['date','location','findings','actions']
        widgets = {
            'date': forms.DateInput(attrs={'type':'date'})
        }

class HSETrainingForm(forms.ModelForm):
    class Meta:
        model = HSETraining
        fields = ['title','date','participants','status']
        widgets = {
            'date': forms.DateInput(attrs={'type':'date'}),
            'participants': forms.SelectMultiple(attrs={'size':6})
        }

# === نماذج إضافية لباقي صفحات HR ===

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'replacement_employee', 'supporting_documents']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'يرجى ذكر سبب الإجازة بوضوح...'}),
            'replacement_employee': forms.Select(attrs={'class': 'form-select'}),
            'supporting_documents': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'leave_type': 'نوع الإجازة',
            'start_date': 'تاريخ البداية',
            'end_date': 'تاريخ النهاية',
            'reason': 'السبب',
            'replacement_employee': 'الموظف البديل (اختياري)',
            'supporting_documents': 'مستندات داعمة (اختياري)',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تخصيص حقل الموظف البديل ليعرض الموظفين النشطين فقط
        if 'replacement_employee' in self.fields:
            self.fields['replacement_employee'].queryset = Employee.objects.filter(status='active').order_by('first_name')
            self.fields['replacement_employee'].empty_label = "--- اختر موظفاً بديلاً ---"
            
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError('تاريخ النهاية لا يجب أن يسبق تاريخ البداية.')
        return cleaned_data

class PerformanceReviewQuickForm(forms.ModelForm):
    class Meta:
        model = PerformanceReview
        fields = [
            'employee','reviewer','review_period_start','review_period_end',
            'quality_of_work','productivity','communication','teamwork','punctuality','initiative',
            'strengths','areas_for_improvement','goals_for_next_period','reviewer_comments'
        ]
        widgets = {
            'review_period_start': forms.DateInput(attrs={'type':'date'}),
            'review_period_end': forms.DateInput(attrs={'type':'date'}),
            'strengths': forms.Textarea(attrs={'rows':2}),
            'areas_for_improvement': forms.Textarea(attrs={'rows':2}),
            'goals_for_next_period': forms.Textarea(attrs={'rows':2}),
            'reviewer_comments': forms.Textarea(attrs={'rows':2}),
        }

class TrainingProgramForm(forms.ModelForm):
    class Meta:
        model = TrainingProgram
        fields = ['title','provider','start_date','end_date','duration_hours','location','cost','max_participants','description']
        widgets = {
            'start_date': forms.DateInput(attrs={'type':'date'}),
            'end_date': forms.DateInput(attrs={'type':'date'}),
            'description': forms.Textarea(attrs={'rows':3}),
        }

class JobVacancyForm(forms.ModelForm):
    class Meta:
        model = JobVacancy
        fields = ['position','title','description','requirements','number_of_positions','salary_range_min','salary_range_max','posting_date','closing_date','status']
        widgets = {
            'posting_date': forms.DateInput(attrs={'type':'date'}),
            'closing_date': forms.DateInput(attrs={'type':'date'}),
            'description': forms.Textarea(attrs={'rows':3}),
            'requirements': forms.Textarea(attrs={'rows':3}),
        }

class JobApplicationQuickForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['vacancy','first_name','last_name','email','phone','cv_file','status']

class PerformanceTargetQuickForm(forms.ModelForm):
    class Meta:
        model = PerformanceTarget
        fields = ['employee','category','title','target_period','target_type','target_value','unit','start_date','end_date','priority','weight']
        widgets = {
            'start_date': forms.DateInput(attrs={'type':'date'}),
            'end_date': forms.DateInput(attrs={'type':'date'}),
        }

class TeamTargetQuickForm(forms.ModelForm):
    class Meta:
        model = TeamTarget
        fields = ['team_name','department','category','title','target_value','unit','start_date','end_date','status']
        widgets = {
            'start_date': forms.DateInput(attrs={'type':'date'}),
            'end_date': forms.DateInput(attrs={'type':'date'}),
        }

class AttendanceRecordQuickForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ['employee','date','time','record_type','source','notes']
        widgets = {
            'date': forms.DateInput(attrs={'type':'date'}),
            'time': forms.TimeInput(attrs={'type':'time'}),
            'notes': forms.Textarea(attrs={'rows':2}),
        }


# === نماذج سلف الموظفين ===

class EmployeeLoanForm(forms.ModelForm):
    """نموذج طلب سلفة جديدة"""
    class Meta:
        model = EmployeeLoan
        fields = [
            'employee', 'amount', 'reason', 'installments_count',
            'start_deduction_date', 'is_emergency', 'notes'
        ]
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'start_deduction_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'installments_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'is_emergency': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'employee': 'الموظف',
            'amount': 'مبلغ السلفة',
            'reason': 'سبب طلب السلفة',
            'installments_count': 'عدد الأقساط (بالشهور)',
            'start_deduction_date': 'تاريخ بدء الخصم',
            'is_emergency': 'سلفة طارئة',
            'notes': 'ملاحظات',
        }


class EmployeeLoanApprovalForm(forms.ModelForm):
    """نموذج الموافقة على السلفة أو رفضها"""
    action = forms.ChoiceField(
        choices=[('approve', 'الموافقة'), ('reject', 'الرفض')],
        widget=forms.RadioSelect,
        label='الإجراء'
    )
    
    class Meta:
        model = EmployeeLoan
        fields = ['rejection_reason']
        widgets = {
            'rejection_reason': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control',
                'placeholder': 'أدخل سبب الرفض (إن وجد)'
            }),
        }
        labels = {
            'rejection_reason': 'سبب الرفض',
        }


class LoanInstallmentDeferForm(forms.Form):
    """نموذج تأجيل قسط السلفة"""
    new_due_date = forms.DateField(
        label='التاريخ الجديد للاستحقاق',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text='اختر التاريخ الذي سيتم فيه خصم القسط'
    )
    reason = forms.CharField(
        label='سبب التأجيل',
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        help_text='أدخل سبب تأجيل القسط'
    )


class PayrollPrintForm(forms.Form):
    """نموذج طباعة كشف الرواتب الشامل"""
    period_start = forms.DateField(
        label='من تاريخ',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    period_end = forms.DateField(
        label='إلى تاريخ',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    department = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        label='القسم',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='جميع الأقسام'
    )
    include_details = forms.BooleanField(
        required=False,
        initial=True,
        label='تضمين التفاصيل',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='عرض تفاصيل البدلات والخصومات'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Department
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
