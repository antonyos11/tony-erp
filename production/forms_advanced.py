"""
نماذج الإنتاج المتقدمة
"""

from django import forms
from production.models_advanced import ProductionLine, ProductionSchedule


class ProductionLineForm(forms.ModelForm):
    class Meta:
        model = ProductionLine
        fields = ['name', 'code', 'branch', 'capacity_per_hour', 'is_active', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'capacity_per_hour': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ProductionScheduleForm(forms.ModelForm):
    class Meta:
        model = ProductionSchedule
        fields = [
            'production_order', 'production_line', 'planned_start',
            'planned_end', 'priority', 'notes',
        ]
        widgets = {
            'production_order': forms.Select(attrs={'class': 'form-select'}),
            'production_line': forms.Select(attrs={'class': 'form-select'}),
            'planned_start': forms.DateTimeInput(attrs={
                'class': 'form-control', 'type': 'datetime-local'
            }),
            'planned_end': forms.DateTimeInput(attrs={
                'class': 'form-control', 'type': 'datetime-local'
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
