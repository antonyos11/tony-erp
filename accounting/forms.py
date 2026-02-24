from __future__ import annotations
from django import forms
from decimal import Decimal
from .models import Account, AccountingSettings

class CashTransferForm(forms.Form):
    from_account = forms.ModelChoiceField(queryset=Account.objects.filter(is_active=True, can_post=True), label='من حساب', widget=forms.Select(attrs={'class':'form-select'}))
    to_account = forms.ModelChoiceField(queryset=Account.objects.filter(is_active=True, can_post=True), label='إلى حساب', widget=forms.Select(attrs={'class':'form-select'}))
    amount = forms.DecimalField(label='المبلغ', max_digits=14, decimal_places=2, min_value=Decimal('0.01'), widget=forms.NumberInput(attrs={'class':'form-control','step':'0.01'}))
    date = forms.DateField(label='التاريخ', widget=forms.DateInput(attrs={'type':'date','class':'form-control'}))
    description = forms.CharField(label='البيان', required=False, widget=forms.Textarea(attrs={'class':'form-control','rows':2}))
    post_now = forms.BooleanField(label='ترحيل فوراً', required=False, initial=True)

    def clean(self):
        cleaned = super().clean()
        f = cleaned.get('from_account'); t = cleaned.get('to_account'); amt = cleaned.get('amount')
        if f and t and f == t:
            self.add_error('to_account', 'يجب اختيار حسابين مختلفين')
        if f and not f.can_post:
            self.add_error('from_account','الحساب لا يقبل قيد مباشر')
        if t and not t.can_post:
            self.add_error('to_account','الحساب لا يقبل قيد مباشر')
        if amt and amt <= 0:
            self.add_error('amount','المبلغ يجب أن يكون أكبر من صفر')
        return cleaned


class TaxSettingsForm(forms.ModelForm):
    """نموذج إعدادات الضرائب والقيمة المضافة"""
    
    class Meta:
        model = AccountingSettings
        fields = [
            'enable_vat', 
            'default_vat_rate', 
            'vat_input_account', 
            'vat_output_account'
        ]
        widgets = {
            'enable_vat': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_vat_rate': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01', 
                'min': '0', 
                'max': '100'
            }),
            'vat_input_account': forms.Select(attrs={'class': 'form-select'}),
            'vat_output_account': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'enable_vat': 'تفعيل ضريبة القيمة المضافة',
            'default_vat_rate': 'نسبة الضريبة الافتراضية (%)',
            'vat_input_account': 'حساب ضريبة المدخلات',
            'vat_output_account': 'حساب ضريبة المخرجات',
        }
        help_texts = {
            'enable_vat': 'تفعيل أو إلغاء تفعيل ضريبة القيمة المضافة في النظام',
            'default_vat_rate': 'النسبة المئوية الافتراضية للضريبة (مثال: 15 لـ 15%)',
            'vat_input_account': 'الحساب المحاسبي لضريبة المدخلات (المشتريات)',
            'vat_output_account': 'الحساب المحاسبي لضريبة المخرجات (المبيعات)',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تصفية الحسابات المناسبة للضرائب
        tax_accounts = Account.objects.filter(
            is_active=True, 
            account_type__in=['asset', 'liability']
        ).order_by('code')
        
        # تحديث queryset للحقول (نتجاهل التحذيرات النوعية لأن هذه حقول ModelChoiceField)
        self.fields['vat_input_account'].queryset = tax_accounts  # type: ignore
        self.fields['vat_output_account'].queryset = tax_accounts  # type: ignore
        
        # إضافة خيار فارغ
        self.fields['vat_input_account'].empty_label = "اختر حساب ضريبة المدخلات"  # type: ignore
        self.fields['vat_output_account'].empty_label = "اختر حساب ضريبة المخرجات"  # type: ignore
    
    def clean_default_vat_rate(self):
        rate = self.cleaned_data.get('default_vat_rate')
        if rate is not None:
            if rate < 0:
                raise forms.ValidationError('نسبة الضريبة لا يمكن أن تكون سالبة')
            if rate > 100:
                raise forms.ValidationError('نسبة الضريبة لا يمكن أن تزيد عن 100%')
        return rate
    
    def clean(self):
        cleaned_data = super().clean()
        enable_vat = cleaned_data.get('enable_vat')
        vat_input = cleaned_data.get('vat_input_account')
        vat_output = cleaned_data.get('vat_output_account')
        
        if enable_vat:
            if not vat_input:
                self.add_error('vat_input_account', 'يجب اختيار حساب ضريبة المدخلات عند تفعيل الضريبة')
            if not vat_output:
                self.add_error('vat_output_account', 'يجب اختيار حساب ضريبة المخرجات عند تفعيل الضريبة')
            if vat_input and vat_output and vat_input == vat_output:
                self.add_error('vat_output_account', 'يجب أن يكون حساب ضريبة المخرجات مختلف عن حساب المدخلات')
        
        return cleaned_data
