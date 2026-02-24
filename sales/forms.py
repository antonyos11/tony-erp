from django import forms
from .models import FieldVisit


class FieldVisitForm(forms.ModelForm):
    class Meta:
        model = FieldVisit
        fields = [
            'visit_date', 'employee', 'customer', 'subject', 'notes',
            'outcome', 'next_action_date'
        ]
        widgets = {
            'visit_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'next_action_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الموضوع'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'ملاحظات الزيارة'}),
            'outcome': forms.Select(attrs={'class': 'form-select'}),
        }
