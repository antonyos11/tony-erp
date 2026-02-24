from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    TaxSettings, TaxCategory, TaxInvoice, TaxInvoiceLine,
    TaxPeriod, TaxPayment, TaxExemption
)


class TaxSettingsForm(forms.ModelForm):
    """نموذج إعدادات الضرائب"""
    
    class Meta:
        model = TaxSettings
        fields = [
            'tax_registration_number', 'tax_file_number', 'commercial_registration',
            'default_vat_rate', 'exemption_threshold', 'is_exempt',
            'einvoice_enabled', 'einvoice_api_key', 'einvoice_client_id',
            'einvoice_client_secret', 'einvoice_environment'
        ]
        widgets = {
            'tax_registration_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم التسجيل الضريبي'}),
            'tax_file_number': forms.TextInput(attrs={'class': 'form-control'}),
            'commercial_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'default_vat_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'exemption_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_exempt': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'einvoice_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'einvoice_api_key': forms.TextInput(attrs={'class': 'form-control'}),
            'einvoice_client_id': forms.TextInput(attrs={'class': 'form-control'}),
            'einvoice_client_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'einvoice_environment': forms.Select(attrs={'class': 'form-control'}),
        }


class TaxCategoryForm(forms.ModelForm):
    """نموذج فئة ضريبية"""
    
    class Meta:
        model = TaxCategory
        fields = ['name', 'code', 'rate', 'description', 'is_exempt', 'is_active', 'eta_code']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_exempt': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'eta_code': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
        }


class TaxInvoiceForm(forms.ModelForm):
    """نموذج فاتورة ضريبية"""
    
    class Meta:
        model = TaxInvoice
        fields = [
            'invoice_type', 'tax_type', 'invoice_date', 'due_date',
            'partner_name', 'partner_tax_id', 'partner_address',
            'subtotal', 'discount', 'tax_rate', 'tax_amount', 'total',
            'notes'
        ]
        widgets = {
            'invoice_type': forms.Select(attrs={'class': 'form-control'}),
            'tax_type': forms.Select(attrs={'class': 'form-control'}),
            'invoice_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'partner_name': forms.TextInput(attrs={'class': 'form-control'}),
            'partner_tax_id': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'partner_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'subtotal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': True}),
            'total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': True}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class TaxInvoiceLineForm(forms.ModelForm):
    """نموذج بند فاتورة"""
    
    class Meta:
        model = TaxInvoiceLine
        fields = [
            'item_code', 'item_name', 'item_description', 'tax_category',
            'quantity', 'unit_price', 'discount', 'tax_rate'
        ]
        widgets = {
            'item_code': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'item_name': forms.TextInput(attrs={'class': 'form-control'}),
            'item_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
            'tax_category': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class TaxPeriodForm(forms.ModelForm):
    """نموذج فترة ضريبية"""
    
    class Meta:
        model = TaxPeriod
        fields = ['name', 'period_type', 'start_date', 'end_date', 'due_date', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'period_type': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class TaxPaymentForm(forms.ModelForm):
    """نموذج سداد ضريبة"""
    
    class Meta:
        model = TaxPayment
        fields = ['period', 'payment_type', 'payment_date', 'amount', 'reference_number', 'bank_name', 'notes']
        widgets = {
            'period': forms.Select(attrs={'class': 'form-control'}),
            'payment_type': forms.Select(attrs={'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class TaxExemptionForm(forms.ModelForm):
    """نموذج إعفاء ضريبي"""
    
    class Meta:
        model = TaxExemption
        fields = ['name', 'description', 'exemption_type', 'legal_reference', 'start_date', 'end_date', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'exemption_type': forms.Select(attrs={'class': 'form-control'}),
            'legal_reference': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TaxReportFilterForm(forms.Form):
    """فلتر تقارير الضرائب"""
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label=_('من تاريخ')
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label=_('إلى تاريخ')
    )
    invoice_type = forms.ChoiceField(
        required=False,
        choices=[('', 'الكل')] + list(TaxInvoice.INVOICE_TYPE_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('نوع الفاتورة')
    )
    tax_type = forms.ChoiceField(
        required=False,
        choices=[('', 'الكل')] + list(TaxInvoice.TAX_TYPE_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('نوع الضريبة')
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'الكل')] + list(TaxInvoice.STATUS_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('الحالة')
    )
