from django import forms
from .models import BankStatement, Reconciliation, ReconciliationItem

class BankStatementUploadForm(forms.ModelForm):
    class Meta:
        model = BankStatement
        fields = ['bank_account', 'statement_date', 'start_date', 'end_date', 'opening_balance', 'closing_balance', 'file', 'notes']
        widgets = {
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'statement_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control'}),
            'closing_balance': forms.NumberInput(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class ReconciliationForm(forms.ModelForm):
    class Meta:
        model = Reconciliation
        fields = ['bank_account', 'reconciliation_date', 'book_balance', 'bank_balance', 'notes']
        widgets = {
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'reconciliation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'book_balance': forms.NumberInput(attrs={'class': 'form-control'}),
            'bank_balance': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
