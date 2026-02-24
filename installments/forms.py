"""
Forms لنظام التقسيط الذكي
"""
from django import forms
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

from .models import (
    InstallmentPlan, InstallmentContract, Installment,
    InstallmentPayment, Guarantor
)
from partners.models import Customer
from payments.models import PaymentMethod


class InstallmentPlanForm(forms.ModelForm):
    """نموذج خطة التقسيط"""
    
    class Meta:
        model = InstallmentPlan
        fields = [
            'name', 'description', 'duration_months',
            'annual_interest_rate', 'admin_fee_type', 'admin_fee_value',
            'min_down_payment_percentage', 'min_amount', 'max_amount',
            'late_fee_type', 'late_fee_value', 'grace_period_days',
            'requires_guarantor', 'min_guarantors', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'duration_months': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 60}),
            'annual_interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'admin_fee_type': forms.Select(attrs={'class': 'form-select'}),
            'admin_fee_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_down_payment_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'late_fee_type': forms.Select(attrs={'class': 'form-select'}),
            'late_fee_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'grace_period_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'min_guarantors': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class InstallmentContractForm(forms.ModelForm):
    """نموذج عقد التقسيط"""
    
    class Meta:
        model = InstallmentContract
        fields = [
            'customer', 'plan', 'showroom', 'invoice',
            'principal_amount', 'down_payment', 'start_date',
            'national_id', 'national_id_image', 'address',
            'phone', 'alternative_phone', 'work_address', 'work_phone',
            'notes', 'customer_signature'
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select select2'}),
            'plan': forms.Select(attrs={'class': 'form-select', 'id': 'plan-select'}),
            'showroom': forms.Select(attrs={'class': 'form-select'}),
            'invoice': forms.Select(attrs={'class': 'form-select select2'}),
            'principal_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'id': 'principal-amount'
            }),
            'down_payment': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'id': 'down-payment'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'national_id': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'alternative_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'work_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'work_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plan'].queryset = InstallmentPlan.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        plan = cleaned_data.get('plan')
        principal_amount = cleaned_data.get('principal_amount')
        down_payment = cleaned_data.get('down_payment', Decimal('0'))
        
        if plan and principal_amount:
            # التحقق من الحد الأدنى
            if principal_amount < plan.min_amount:
                raise forms.ValidationError(
                    f'المبلغ أقل من الحد الأدنى المسموح ({plan.min_amount})'
                )
            
            # التحقق من الحد الأقصى
            if plan.max_amount and principal_amount > plan.max_amount:
                raise forms.ValidationError(
                    f'المبلغ أكبر من الحد الأقصى المسموح ({plan.max_amount})'
                )
            
            # التحقق من المقدم
            min_down = principal_amount * plan.min_down_payment_percentage / Decimal('100')
            if down_payment < min_down:
                raise forms.ValidationError(
                    f'المقدم أقل من الحد الأدنى المطلوب ({min_down})'
                )
        
        return cleaned_data


class GuarantorForm(forms.ModelForm):
    """نموذج الضامن"""
    
    class Meta:
        model = Guarantor
        fields = [
            'name', 'national_id', 'national_id_image',
            'phone', 'alternative_phone', 'address',
            'job_title', 'employer', 'work_address', 'work_phone',
            'monthly_income', 'relationship', 'relationship_details',
            'signature', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'national_id': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'alternative_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'employer': forms.TextInput(attrs={'class': 'form-control'}),
            'work_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'work_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'monthly_income': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'relationship': forms.Select(attrs={'class': 'form-select'}),
            'relationship_details': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class InstallmentPaymentForm(forms.Form):
    """نموذج تسجيل دفعة قسط"""
    
    amount = forms.DecimalField(
        label=_('المبلغ'),
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )
    
    payment_method = forms.ModelChoiceField(
        label=_('طريقة الدفع'),
        queryset=PaymentMethod.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    payment_reference = forms.CharField(
        label=_('مرجع الدفع'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    notes = forms.CharField(
        label=_('ملاحظات'),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


class ContractCalculatorForm(forms.Form):
    """نموذج حاسبة التقسيط"""
    
    plan = forms.ModelChoiceField(
        label=_('خطة التقسيط'),
        queryset=InstallmentPlan.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    amount = forms.DecimalField(
        label=_('المبلغ'),
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )
    
    down_payment = forms.DecimalField(
        label=_('المقدم'),
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0'),
        required=False,
        initial=Decimal('0'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )


class ContractFilterForm(forms.Form):
    """نموذج فلترة العقود"""
    
    STATUS_CHOICES = [('', 'الكل')] + list(InstallmentContract.CONTRACT_STATUS)
    
    q = forms.CharField(
        label=_('بحث'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'رقم العقد، اسم العميل، الهاتف...'
        })
    )
    
    status = forms.ChoiceField(
        label=_('الحالة'),
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    plan = forms.ModelChoiceField(
        label=_('خطة التقسيط'),
        queryset=InstallmentPlan.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        label=_('من تاريخ'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        label=_('إلى تاريخ'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


class BulkPaymentForm(forms.Form):
    """نموذج دفع مجمع"""
    
    contract = forms.ModelChoiceField(
        label=_('العقد'),
        queryset=InstallmentContract.objects.filter(status='active'),
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    
    amount = forms.DecimalField(
        label=_('المبلغ الإجمالي'),
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )
    
    payment_method = forms.ModelChoiceField(
        label=_('طريقة الدفع'),
        queryset=PaymentMethod.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    notes = forms.CharField(
        label=_('ملاحظات'),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )
