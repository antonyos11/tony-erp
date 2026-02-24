"""
نماذج CRM المتقدمة
"""

from django import forms
from crm.models_advanced import FollowUpRule, SupportSLA


class FollowUpRuleForm(forms.ModelForm):
    class Meta:
        model = FollowUpRule
        fields = [
            'name', 'description', 'trigger', 'days_after',
            'action', 'template_message', 'assigned_to', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'trigger': forms.Select(attrs={'class': 'form-select'}),
            'days_after': forms.NumberInput(attrs={'class': 'form-control'}),
            'action': forms.Select(attrs={'class': 'form-select'}),
            'template_message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SupportSLAForm(forms.ModelForm):
    class Meta:
        model = SupportSLA
        fields = [
            'name', 'priority', 'first_response_hours',
            'resolution_hours', 'escalation_after_hours',
            'escalate_to', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'first_response_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'resolution_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'escalation_after_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'escalate_to': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
