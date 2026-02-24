"""
نماذج المخزون المتقدمة
"""

from django import forms
from inventory.models_advanced import StockAlert, LotTracking, CycleCount


class StockAlertForm(forms.ModelForm):
    class Meta:
        model = StockAlert
        fields = [
            'product', 'location', 'alert_type', 'severity',
            'threshold', 'no_movement_days', 'is_active',
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.Select(attrs={'class': 'form-select'}),
            'alert_type': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'no_movement_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LotTrackingForm(forms.ModelForm):
    class Meta:
        model = LotTracking
        fields = [
            'product', 'lot_number', 'batch_number',
            'manufacturing_date', 'expiry_date',
            'location', 'supplier', 'initial_quantity',
            'current_quantity', 'cost_per_unit', 'notes',
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'lot_number': forms.TextInput(attrs={'class': 'form-control'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'manufacturing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'location': forms.Select(attrs={'class': 'form-select'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'initial_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'current_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cost_per_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class CycleCountForm(forms.ModelForm):
    class Meta:
        model = CycleCount
        fields = [
            'name', 'location', 'count_type', 'scheduled_date',
            'assigned_to', 'supervised_by', 'notes',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.Select(attrs={'class': 'form-select'}),
            'count_type': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'supervised_by': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
