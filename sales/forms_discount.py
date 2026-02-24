"""
نماذج إشعارات الخصم للعملاء - Forms for Customer Discount Notes
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models_discount import CustomerDiscountNote
from partners.models import Customer


class CustomerDiscountNoteForm(forms.ModelForm):
    """نموذج إشعار خصم مسموح به للعميل"""
    
    class Meta:
        model = CustomerDiscountNote
        fields = [
            'customer',
            'invoice',
            'date',
            'amount',
            'is_percentage',
            'percentage_value',
            'reason',
            'notes',
        ]
        widgets = {
            'customer': forms.Select(attrs={
                'class': 'form-select select2-customer',
                'data-placeholder': _('ابحث بالاسم...'),
            }),
            'invoice': forms.Select(attrs={
                'class': 'form-select',
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'is_percentage': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'percentage_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'reason': forms.Select(attrs={
                'class': 'form-select',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('تفاصيل إضافية...'),
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.all().order_by('name')
        self.fields['invoice'].required = False
        self.fields['invoice'].queryset = self.fields['invoice'].queryset.none()
        
        # إذا كان هناك عميل محدد، نعرض فواتيره
        if self.instance.pk and self.instance.customer_id:
            from .models import Invoice
            self.fields['invoice'].queryset = Invoice.objects.filter(
                customer=self.instance.customer,
                is_deleted=False
            ).order_by('-date')
        elif 'customer' in self.data:
            try:
                customer_id = int(self.data.get('customer'))
                from .models import Invoice
                self.fields['invoice'].queryset = Invoice.objects.filter(
                    customer_id=customer_id,
                    is_deleted=False
                ).order_by('-date')
            except (ValueError, TypeError):
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        is_percentage = cleaned_data.get('is_percentage')
        amount = cleaned_data.get('amount')
        percentage_value = cleaned_data.get('percentage_value')
        invoice = cleaned_data.get('invoice')
        
        if is_percentage:
            if not invoice:
                raise forms.ValidationError(
                    _('يجب تحديد فاتورة عند استخدام النسبة المئوية')
                )
            if not percentage_value or percentage_value <= 0:
                raise forms.ValidationError(
                    _('يجب إدخال نسبة مئوية صحيحة')
                )
        else:
            if not amount or amount <= 0:
                raise forms.ValidationError(
                    _('يجب إدخال قيمة خصم صحيحة')
                )
        
        return cleaned_data


class CustomerDiscountNoteSearchForm(forms.Form):
    """نموذج بحث في إشعارات الخصم"""
    
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        required=False,
        label=_('العميل'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', _('الكل'))] + list(CustomerDiscountNote.STATUS_CHOICES),
        required=False,
        label=_('الحالة'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        label=_('من تاريخ'),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        label=_('إلى تاريخ'),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
