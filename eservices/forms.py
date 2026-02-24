"""
نماذج إدخال الخدمات الإلكترونية - Tony ERP
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    ServiceCategory, ServiceProvider, EService, MobileOperator,
    RechargePackage, BillType, MoneyTransfer
)


class ServiceCategoryForm(forms.ModelForm):
    """نموذج فئة الخدمة"""
    class Meta:
        model = ServiceCategory
        fields = ['name', 'code', 'icon', 'description', 'is_active', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'bi-gear'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ServiceProviderForm(forms.ModelForm):
    """نموذج مزود الخدمة"""
    class Meta:
        model = ServiceProvider
        fields = [
            'name', 'code', 'logo', 'description', 'website',
            'api_endpoint', 'api_key', 'api_secret', 'is_active', 'commission_rate'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'api_endpoint': forms.URLInput(attrs={'class': 'form-control'}),
            'api_key': forms.TextInput(attrs={'class': 'form-control'}),
            'api_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class EServiceForm(forms.ModelForm):
    """نموذج الخدمة الإلكترونية"""
    class Meta:
        model = EService
        fields = [
            'name', 'code', 'category', 'provider', 'service_type',
            'description', 'icon', 'base_fee', 'percentage_fee',
            'min_amount', 'max_amount', 'requires_account',
            'requires_verification', 'is_active', 'is_featured'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'provider': forms.Select(attrs={'class': 'form-select'}),
            'service_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icon': forms.TextInput(attrs={'class': 'form-control'}),
            'base_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'percentage_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'requires_account': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_verification': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class MobileOperatorForm(forms.ModelForm):
    """نموذج مشغل الاتصالات"""
    class Meta:
        model = MobileOperator
        fields = ['name', 'code', 'logo', 'prefixes', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'prefixes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '010,011,012'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class RechargePackageForm(forms.ModelForm):
    """نموذج باقة الشحن"""
    class Meta:
        model = RechargePackage
        fields = ['operator', 'name', 'amount', 'bonus', 'validity_days', 'is_active', 'order']
        widgets = {
            'operator': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bonus': forms.TextInput(attrs={'class': 'form-control'}),
            'validity_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class BillTypeForm(forms.ModelForm):
    """نموذج نوع الفاتورة"""
    class Meta:
        model = BillType
        fields = ['name', 'code', 'icon', 'provider', 'service_fee', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'icon': forms.TextInput(attrs={'class': 'form-control'}),
            'provider': forms.Select(attrs={'class': 'form-select'}),
            'service_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class MobileRechargeForm(forms.Form):
    """نموذج شحن الرصيد"""
    operator = forms.ModelChoiceField(
        queryset=MobileOperator.objects.filter(is_active=True),
        label=_('المشغل'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    mobile_number = forms.CharField(
        label=_('رقم الجوال'),
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '01xxxxxxxxx'})
    )
    amount = forms.DecimalField(
        label=_('المبلغ'),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    package = forms.ModelChoiceField(
        queryset=RechargePackage.objects.filter(is_active=True),
        label=_('الباقة'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class BillPaymentForm(forms.Form):
    """نموذج دفع الفاتورة"""
    bill_type = forms.ModelChoiceField(
        queryset=BillType.objects.filter(is_active=True),
        label=_('نوع الفاتورة'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    bill_number = forms.CharField(
        label=_('رقم الفاتورة / الحساب'),
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    customer_name = forms.CharField(
        label=_('اسم العميل'),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    amount = forms.DecimalField(
        label=_('المبلغ'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )


class MoneyTransferForm(forms.Form):
    """نموذج تحويل الأموال"""
    TRANSFER_TYPES = [
        ('wallet', _('محفظة')),
        ('bank', _('بنك')),
        ('mobile', _('رصيد جوال')),
    ]
    
    transfer_type = forms.ChoiceField(
        choices=TRANSFER_TYPES,
        label=_('نوع التحويل'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    sender_name = forms.CharField(
        label=_('اسم المرسل'),
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    sender_phone = forms.CharField(
        label=_('هاتف المرسل'),
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    receiver_name = forms.CharField(
        label=_('اسم المستلم'),
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    receiver_phone = forms.CharField(
        label=_('هاتف المستلم'),
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    receiver_account = forms.CharField(
        label=_('حساب المستلم'),
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    amount = forms.DecimalField(
        label=_('المبلغ'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    notes = forms.CharField(
        label=_('ملاحظات'),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )
