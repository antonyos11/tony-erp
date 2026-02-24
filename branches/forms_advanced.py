"""
نماذج الفروع المتقدمة
"""

from django import forms
from branches.models_advanced import BranchTarget, InterBranchTransfer


class BranchTargetForm(forms.ModelForm):
    class Meta:
        model = BranchTarget
        fields = [
            'branch', 'period',
            'sales_target', 'new_customers_target', 'collection_target',
            'notes',
        ]
        widgets = {
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'period': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2026-01'}),
            'sales_target': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'new_customers_target': forms.NumberInput(attrs={'class': 'form-control'}),
            'collection_target': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class InterBranchTransferForm(forms.ModelForm):
    class Meta:
        model = InterBranchTransfer
        fields = [
            'from_branch', 'to_branch', 'reason', 'notes',
        ]
        widgets = {
            'from_branch': forms.Select(attrs={'class': 'form-select'}),
            'to_branch': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
