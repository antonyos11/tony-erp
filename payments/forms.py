"""
نماذج تطبيق المدفوعات والقروض
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import PaymentMethod, Loan, PaymentTransaction, LoanInstallment
from partners.models import Partner
from decimal import Decimal


class PaymentMethodForm(forms.ModelForm):
    """نموذج طريقة الدفع"""
    
    class Meta:
        model = PaymentMethod
        fields = ['name', 'type', 'account_number', 'bank_name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم طريقة الدفع'
            }),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الحساب (اختياري)'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم البنك (اختياري)'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'name': 'اسم طريقة الدفع',
            'type': 'نوع الدفع',
            'account_number': 'رقم الحساب',
            'bank_name': 'اسم البنك',
            'is_active': 'نشط'
        }


class LoanForm(forms.ModelForm):
    """نموذج القرض"""
    
    borrower = forms.ModelChoiceField(
        queryset=Partner.objects.filter(partner_type='customer', is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='المقترض'
    )
    
    class Meta:
        model = Loan
        fields = [
            'loan_number', 'borrower', 'loan_type', 'principal_amount',
            'interest_rate', 'duration_months', 'start_date', 'notes'
        ]
        widgets = {
            'loan_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم القرض'
            }),
            'loan_type': forms.Select(attrs={'class': 'form-select'}),
            'principal_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'interest_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'duration_months': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '12'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات إضافية'
            })
        }
        labels = {
            'loan_number': 'رقم القرض',
            'borrower': 'المقترض',
            'loan_type': 'نوع القرض',
            'principal_amount': 'مبلغ القرض',
            'interest_rate': 'معدل الفائدة %',
            'duration_months': 'مدة القرض (شهر)',
            'start_date': 'تاريخ البدء',
            'notes': 'ملاحظات'
        }
    
    def clean_loan_number(self):
        """التحقق من عدم تكرار رقم القرض"""
        loan_number = self.cleaned_data['loan_number']
        if Loan.objects.filter(loan_number=loan_number).exists():
            if not self.instance.pk or self.instance.loan_number != loan_number:
                raise ValidationError('رقم القرض موجود مسبقاً')
        return loan_number
    
    def clean_principal_amount(self):
        """التحقق من مبلغ القرض"""
        amount = self.cleaned_data['principal_amount']
        if amount <= 0:
            raise ValidationError('يجب أن يكون مبلغ القرض أكبر من صفر')
        return amount
    
    def clean_interest_rate(self):
        """التحقق من معدل الفائدة"""
        rate = self.cleaned_data['interest_rate']
        if rate < 0 or rate > 100:
            raise ValidationError('معدل الفائدة يجب أن يكون بين 0 و 100')
        return rate
    
    def clean_duration_months(self):
        """التحقق من مدة القرض"""
        duration = self.cleaned_data['duration_months']
        if duration < 1 or duration > 360:  # 30 سنة كحد أقصى
            raise ValidationError('مدة القرض يجب أن تكون بين 1 و 360 شهر')
        return duration
    
    def save(self, commit=True):
        """حفظ القرض مع حساب القسط الشهري"""
        loan = super().save(commit=False)
        
        # حساب القسط الشهري
        principal = loan.principal_amount
        monthly_rate = loan.interest_rate / 100 / 12
        num_payments = loan.duration_months
        
        if monthly_rate > 0:
            # صيغة حساب القسط مع الفائدة
            loan.monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
        else:
            # قرض بدون فوائد
            loan.monthly_payment = principal / num_payments
        
        # حساب تاريخ النهاية
        from dateutil.relativedelta import relativedelta
        loan.end_date = loan.start_date + relativedelta(months=num_payments)
        
        if commit:
            loan.save()
        return loan


class PaymentForm(forms.Form):
    """نموذج الدفع"""
    
    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        label='المبلغ'
    )
    
    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='طريقة الدفع'
    )
    
    reference_number = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'رقم المرجع (اختياري)'
        }),
        label='رقم المرجع'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'ملاحظات إضافية'
        }),
        label='ملاحظات'
    )
    
    def clean_amount(self):
        """التحقق من المبلغ"""
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise ValidationError('يجب أن يكون المبلغ أكبر من صفر')
        return amount


class LoanSearchForm(forms.Form):
    """نموذج البحث في القروض"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'البحث برقم القرض أو اسم المقترض...'
        }),
        label='البحث'
    )
    
    status = forms.ChoiceField(
        choices=[('', 'جميع الحالات')] + Loan.LOAN_STATUS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='الحالة'
    )
    
    loan_type = forms.ChoiceField(
        choices=[('', 'جميع الأنواع')] + Loan.LOAN_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='نوع القرض'
    )
    
    borrower = forms.ModelChoiceField(
        queryset=Partner.objects.filter(partner_type='customer', is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='المقترض'
    )


class InstallmentSearchForm(forms.Form):
    """نموذج البحث في الأقساط"""
    
    status = forms.ChoiceField(
        choices=[('', 'جميع الحالات')] + LoanInstallment.INSTALLMENT_STATUS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='حالة القسط'
    )
    
    overdue = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='الأقساط المتأخرة فقط'
    )
    
    borrower = forms.ModelChoiceField(
        queryset=Partner.objects.filter(partner_type='customer', is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='المقترض'
    )