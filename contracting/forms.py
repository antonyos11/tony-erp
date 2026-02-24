"""
Forms for Contracting App - نماذج نظام المقاولات
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import (
    ContractingProject, ContractingWorker, ContractingAttendance,
    ContractingMaterial, ContractingEquipment, ContractingExpense,
    ContractingReceipt, ContractingContract
)


class ProjectForm(forms.ModelForm):
    """نموذج المشروع"""
    
    class Meta:
        model = ContractingProject
        fields = [
            'name', 'code', 'description', 'client_name', 'client_phone',
            'client_email', 'client_address', 'location', 'start_date',
            'expected_end_date', 'contract_value', 'budget', 'status',
            'progress_percentage', 'manager', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'client_name': forms.TextInput(attrs={'class': 'form-control'}),
            'client_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'client_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'client_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contract_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'budget': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'progress_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class WorkerForm(forms.ModelForm):
    """نموذج العامل"""
    
    class Meta:
        model = ContractingWorker
        fields = [
            'name', 'national_id', 'phone', 'address', 'job_title',
            'worker_type', 'daily_wage', 'hire_date', 'is_active',
            'current_project', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'national_id': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'worker_type': forms.Select(attrs={'class': 'form-select'}),
            'daily_wage': forms.NumberInput(attrs={'class': 'form-control'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'current_project': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class AttendanceForm(forms.ModelForm):
    """نموذج الحضور"""
    
    class Meta:
        model = ContractingAttendance
        fields = [
            'worker', 'project', 'date', 'status', 'check_in', 'check_out',
            'hours_worked', 'overtime_hours', 'notes'
        ]
        widgets = {
            'worker': forms.Select(attrs={'class': 'form-select'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'check_in': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hours_worked': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'overtime_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class MaterialForm(forms.ModelForm):
    """نموذج المادة"""
    
    class Meta:
        model = ContractingMaterial
        fields = [
            'name', 'code', 'description', 'unit', 'unit_price',
            'current_stock', 'min_stock', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'current_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'min_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EquipmentForm(forms.ModelForm):
    """نموذج المعدة"""
    
    class Meta:
        model = ContractingEquipment
        fields = [
            'name', 'code', 'description', 'brand', 'model', 'serial_number',
            'purchase_date', 'purchase_price', 'daily_rental_rate', 'status',
            'current_project', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'daily_rental_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'current_project': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ExpenseForm(forms.ModelForm):
    """نموذج المصروف"""
    
    class Meta:
        model = ContractingExpense
        fields = [
            'project', 'expense_type', 'description', 'amount', 'date',
            'reference_number', 'material', 'notes'
        ]
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'expense_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'material': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ReceiptForm(forms.ModelForm):
    """نموذج المقبوض"""
    
    class Meta:
        model = ContractingReceipt
        fields = [
            'project', 'receipt_type', 'payment_method', 'description',
            'amount', 'date', 'reference_number', 'check_number', 'bank_name', 'notes'
        ]
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'receipt_type': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'check_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ContractForm(forms.ModelForm):
    """نموذج العقد"""
    
    class Meta:
        model = ContractingContract
        fields = [
            'project', 'contract_number', 'title', 'description',
            'contractor_name', 'contractor_phone', 'contract_value',
            'advance_payment', 'retention_percentage', 'start_date',
            'end_date', 'status', 'terms', 'signed_date'
        ]
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contractor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contractor_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contract_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'advance_payment': forms.NumberInput(attrs={'class': 'form-control'}),
            'retention_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'signed_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
