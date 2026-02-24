from django import forms
from .models import FiscalYear, Budget, BudgetLine

class FiscalYearForm(forms.ModelForm):
    class Meta:
        model = FiscalYear
        fields = ['name', 'code', 'start_date', 'end_date', 'status', 'is_current']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['name', 'code', 'fiscal_year', 'budget_type', 'start_date', 'end_date', 'total_amount', 'department', 'cost_center', 'description', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'fiscal_year': forms.Select(attrs={'class': 'form-select'}),
            'budget_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'cost_center': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class BudgetLineForm(forms.ModelForm):
    class Meta:
        model = BudgetLine
        fields = ['account', 'description', 'planned_amount', 'notes']
        widgets = {
            'account': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'planned_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }
