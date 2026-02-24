"""
نماذج الفترات المحاسبية المتقدمة
"""

from django import forms
from accounting.models_advanced import AccountingPeriod


class AccountingPeriodForm(forms.ModelForm):
    class Meta:
        model = AccountingPeriod
        fields = [
            'fiscal_year', 'name', 'period_type',
            'start_date', 'end_date', 'is_adjustment_period', 'notes',
        ]
        widgets = {
            'fiscal_year': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'period_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_adjustment_period': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
