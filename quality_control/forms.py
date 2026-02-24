from django import forms
from .models import QualityStandard, InspectionType, QualityInspection, QualityIssue

class QualityStandardForm(forms.ModelForm):
    class Meta:
        model = QualityStandard
        fields = ['name', 'code', 'description', 'category', 'min_value', 'max_value', 'unit', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'min_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
        }

class QualityInspectionForm(forms.ModelForm):
    class Meta:
        model = QualityInspection
        fields = ['inspection_type', 'product', 'batch_number', 'inspection_date', 'status', 'overall_score', 'notes']
        widgets = {
            'inspection_type': forms.Select(attrs={'class': 'form-select'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'inspection_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'overall_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class QualityIssueForm(forms.ModelForm):
    class Meta:
        model = QualityIssue
        fields = ['title', 'description', 'product', 'severity', 'assigned_to', 'root_cause', 'corrective_action']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'root_cause': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'corrective_action': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
