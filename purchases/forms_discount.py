"""
نماذج إشعارات الخصم للموردين - Forms for Supplier Discount Notes
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models_discount import SupplierDiscountNote
from partners.models import Supplier


class SupplierDiscountNoteForm(forms.ModelForm):
    """نموذج إشعار خصم مكتسب من المورد"""
    
    class Meta:
        model = SupplierDiscountNote
        fields = [
            'supplier',
            'supplier_note_number',
            'bill',
            'date',
            'amount',
            'is_percentage',
            'percentage_value',
            'reason',
            'notes',
        ]
        widgets = {
            'supplier': forms.Select(attrs={
                'class': 'form-select select2-supplier',
                'data-placeholder': _('ابحث بالاسم...'),
            }),
            'supplier_note_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('مثال: CN-2024-001'),
            }),
            'bill': forms.Select(attrs={
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
        self.fields['supplier'].queryset = Supplier.objects.all().order_by('name')
        self.fields['bill'].required = False
        self.fields['bill'].queryset = self.fields['bill'].queryset.none()
        
        # إذا كان هناك مورد محدد، نعرض فواتيره
        if self.instance.pk and self.instance.supplier_id:
            from .models import PurchaseBill
            self.fields['bill'].queryset = PurchaseBill.objects.filter(
                supplier=self.instance.supplier,
                is_deleted=False
            ).order_by('-date')
        elif 'supplier' in self.data:
            try:
                supplier_id = int(self.data.get('supplier'))
                from .models import PurchaseBill
                self.fields['bill'].queryset = PurchaseBill.objects.filter(
                    supplier_id=supplier_id,
                    is_deleted=False
                ).order_by('-date')
            except (ValueError, TypeError):
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        is_percentage = cleaned_data.get('is_percentage')
        amount = cleaned_data.get('amount')
        percentage_value = cleaned_data.get('percentage_value')
        bill = cleaned_data.get('bill')
        
        if is_percentage:
            if not bill:
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


class SupplierDiscountNoteSearchForm(forms.Form):
    """نموذج بحث في إشعارات الخصم"""
    
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.all(),
        required=False,
        label=_('المورد'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', _('الكل'))] + list(SupplierDiscountNote.STATUS_CHOICES),
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
