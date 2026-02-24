# -*- coding: utf-8 -*-
"""
نماذج (Forms) موصول التحضير والاستماد
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory
from decimal import Decimal

from .models import (
    PreparationRequest, PreparationItem,
    ApprovalDocument, ApprovalDocumentItem
)


class PreparationRequestForm(forms.ModelForm):
    """نموذج طلب التحضير"""
    
    class Meta:
        model = PreparationRequest
        fields = [
            'request_type', 'title', 'description',
            'required_date', 'priority',
            'department', 'cost_center', 'project',
            'notes'
        ]
        widgets = {
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('عنوان الطلب')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'required_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'cost_center': forms.Select(attrs={'class': 'form-select'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class PreparationItemForm(forms.ModelForm):
    """نموذج بند التحضير"""
    
    class Meta:
        model = PreparationItem
        fields = [
            'product', 'description',
            'quantity_requested', 'unit',
            'estimated_unit_price', 'notes'
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select product-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('وصف البند')}),
            'quantity_requested': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.001', 'step': '0.001'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('الوحدة')}),
            'estimated_unit_price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }


# Formset لبنود التحضير
PreparationItemFormSet = inlineformset_factory(
    PreparationRequest,
    PreparationItem,
    form=PreparationItemForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class ApprovalDocumentForm(forms.ModelForm):
    """نموذج مستند الاستماد"""
    
    class Meta:
        model = ApprovalDocument
        fields = [
            'document_type', 'title', 'description',
            'due_date', 'department', 'cost_center',
            'supplier', 'employee', 'currency', 'notes'
        ]
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('عنوان المستند')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'cost_center': forms.Select(attrs={'class': 'form-select'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ApprovalDocumentItemForm(forms.ModelForm):
    """نموذج بند الاستماد"""
    
    class Meta:
        model = ApprovalDocumentItem
        fields = [
            'description', 'product', 'account',
            'quantity', 'unit', 'unit_price', 'notes'
        ]
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('وصف البند')}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'account': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.001', 'step': '0.001'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }


# Formset لبنود الاستماد
ApprovalDocumentItemFormSet = inlineformset_factory(
    ApprovalDocument,
    ApprovalDocumentItem,
    form=ApprovalDocumentItemForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class ApprovalActionForm(forms.Form):
    """نموذج إجراء الاعتماد"""
    
    ACTION_CHOICES = [
        ('approve', _('موافقة')),
        ('reject', _('رفض')),
        ('return', _('إرجاع للتعديل')),
    ]
    
    action = forms.ChoiceField(
        label=_('الإجراء'),
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    approved_amount = forms.DecimalField(
        label=_('المبلغ المعتمد'),
        required=False,
        min_value=Decimal('0'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    notes = forms.CharField(
        label=_('ملاحظات'),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        notes = cleaned_data.get('notes')
        
        if action == 'reject' and not notes:
            raise forms.ValidationError(_('يجب تحديد سبب الرفض'))
        
        return cleaned_data


class PreparationFilterForm(forms.Form):
    """نموذج فلترة طلبات التحضير"""
    
    search = forms.CharField(
        label=_('بحث'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('رقم الطلب أو العنوان...')
        })
    )
    status = forms.ChoiceField(
        label=_('الحالة'),
        required=False,
        choices=[('', _('الكل'))] + list(PreparationRequest.Status.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    request_type = forms.ChoiceField(
        label=_('النوع'),
        required=False,
        choices=[('', _('الكل'))] + list(PreparationRequest.RequestType.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    priority = forms.ChoiceField(
        label=_('الأولوية'),
        required=False,
        choices=[('', _('الكل'))] + list(PreparationRequest.Priority.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        label=_('من تاريخ'),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        label=_('إلى تاريخ'),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class ApprovalFilterForm(forms.Form):
    """نموذج فلترة مستندات الاستماد"""
    
    search = forms.CharField(
        label=_('بحث'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('رقم المستند أو العنوان...')
        })
    )
    status = forms.ChoiceField(
        label=_('الحالة'),
        required=False,
        choices=[('', _('الكل'))] + list(ApprovalDocument.Status.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    document_type = forms.ChoiceField(
        label=_('نوع المستند'),
        required=False,
        choices=[('', _('الكل'))] + list(ApprovalDocument.DocumentType.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        label=_('من تاريخ'),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        label=_('إلى تاريخ'),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    min_amount = forms.DecimalField(
        label=_('الحد الأدنى للمبلغ'),
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    max_amount = forms.DecimalField(
        label=_('الحد الأقصى للمبلغ'),
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
