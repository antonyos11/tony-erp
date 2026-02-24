"""
نماذج وحدة الفروع الموحدة
تم دمج وحدة المعارض في هذه الوحدة
"""
from django import forms
from django.contrib.auth import get_user_model
from .models import (
    Branch, BranchStaff, BranchTransfer, BranchTransferItem,
    POSDevice, BranchAttendance, BranchExpense, BranchPurchase,
    BranchPurchaseItem, BranchPayroll, BranchShift, BranchShiftAssignment
)

User = get_user_model()


class BranchForm(forms.ModelForm):
    """نموذج إنشاء/تعديل فرع"""
    
    class Meta:
        model = Branch
        fields = [
            'code', 'name', 'name_en', 'branch_type', 'status',
            'address', 'city', 'state', 'country', 'postal_code',
            'phone', 'mobile', 'email', 'fax', 'contact_person',
            'latitude', 'longitude',
            'manager', 'parent_branch', 'is_main',
            'allow_negative_stock', 'auto_approve_transfers',
            'expense_approval_limit', 'require_expense_approval',
            'tax_id', 'commercial_register',
            'opening_date', 'notes',
            # حقول إدارة الملكية والعقود
            'ownership_type', 'owner_name', 'owner_phone', 
            'owner_id_number', 'owner_bank_account', 'owner_bank_name',
            'contract_number', 'contract_start_date', 'contract_end_date',
            'contract_duration_months', 'monthly_rent', 'annual_rent',
            'deposit_amount', 'property_area', 'property_type',
            'rent_due_day', 'contract_reminder_days', 'contract_notes',
            'contract_file',
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'BR001'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'name_en': forms.TextInput(attrs={'class': 'form-control'}),
            'branch_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'fax': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0000001'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
            'parent_branch': forms.Select(attrs={'class': 'form-select'}),
            'expense_approval_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'commercial_register': forms.TextInput(attrs={'class': 'form-control'}),
            'opening_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            # حقول الملكية والعقود
            'ownership_type': forms.Select(attrs={'class': 'form-select', 'id': 'ownership_type'}),
            'owner_name': forms.TextInput(attrs={'class': 'form-control'}),
            'owner_phone': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'owner_id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'owner_bank_account': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'owner_bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control'}),
            'contract_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contract_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contract_duration_months': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'monthly_rent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'annual_rent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deposit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'property_area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'property_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'معرض تجاري، مستودع...'}),
            'rent_due_day': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '31'}),
            'contract_reminder_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'contract_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contract_file': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # جعل الحقول اختيارية مع قيم افتراضية
        self.fields['country'].required = False
        self.fields['country'].initial = 'المملكة العربية مصر'
        self.fields['expense_approval_limit'].required = False
        self.fields['expense_approval_limit'].initial = 10000
        
    def clean_country(self):
        return self.cleaned_data.get('country') or 'المملكة العربية مصر'
    
    def clean_expense_approval_limit(self):
        return self.cleaned_data.get('expense_approval_limit') or 10000


class BranchStaffForm(forms.ModelForm):
    """نموذج تعيين موظف في فرع"""
    
    class Meta:
        model = BranchStaff
        fields = ['branch', 'user', 'role', 'position', 'can_cross_access', 'is_active', 'start_date', 'end_date', 'extra_perms', 'notes']
        widgets = {
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'user': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class BranchTransferForm(forms.ModelForm):
    """نموذج إنشاء تحويل بين الفروع"""
    
    class Meta:
        model = BranchTransfer
        fields = [
            'from_branch', 'to_branch', 'transfer_date', 'expected_arrival',
            'notes'
        ]
        widgets = {
            'from_branch': forms.Select(attrs={'class': 'form-select'}),
            'to_branch': forms.Select(attrs={'class': 'form-select'}),
            'transfer_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_arrival': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        from_branch = cleaned_data.get('from_branch')
        to_branch = cleaned_data.get('to_branch')
        
        if from_branch and to_branch and from_branch == to_branch:
            raise forms.ValidationError('لا يمكن التحويل من وإلى نفس الفرع')
        
        return cleaned_data


class BranchTransferItemForm(forms.ModelForm):
    """نموذج بند تحويل"""
    
    class Meta:
        model = BranchTransferItem
        fields = ['product', 'quantity', 'unit_cost', 'notes']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select product-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }


BranchTransferItemFormSet = forms.inlineformset_factory(
    BranchTransfer,
    BranchTransferItem,
    form=BranchTransferItemForm,
    extra=3,
    can_delete=True
)


class TransferReceiveForm(forms.Form):
    """نموذج استلام التحويل"""
    received_quantity = forms.IntegerField(
        label='الكمية المستلمة',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
    )
    notes = forms.CharField(
        label='ملاحظات',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


class TransferApprovalForm(forms.Form):
    """نموذج الموافقة/الرفض"""
    action = forms.ChoiceField(
        choices=[('approve', 'موافقة'), ('reject', 'رفض')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    rejection_reason = forms.CharField(
        label='سبب الرفض',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


# ==================== نماذج المعارض المدمجة ====================

class POSDeviceForm(forms.ModelForm):
    """نموذج جهاز نقطة بيع"""
    
    class Meta:
        model = POSDevice
        fields = ['branch', 'name', 'identifier', 'api_key', 'is_active']
        widgets = {
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'identifier': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'api_key': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
        }


class BranchAttendanceForm(forms.ModelForm):
    """نموذج سجل حضور"""
    
    class Meta:
        model = BranchAttendance
        fields = ['branch', 'employee', 'date', 'in_time', 'out_time', 'note']
        widgets = {
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'in_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'out_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'note': forms.TextInput(attrs={'class': 'form-control'}),
        }


class BranchExpenseForm(forms.ModelForm):
    """نموذج مصروف فرع"""
    
    class Meta:
        model = BranchExpense
        fields = ['branch', 'amount', 'category', 'description', 'date', 'attachment']
        widgets = {
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }


class BranchPayrollForm(forms.ModelForm):
    """نموذج قيد راتب"""
    
    class Meta:
        model = BranchPayroll
        fields = ['branch', 'employee', 'period', 'amount', 'entry_type', 'note']
        widgets = {
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'period': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'entry_type': forms.Select(attrs={'class': 'form-select'}),
            'note': forms.TextInput(attrs={'class': 'form-control'}),
        }


class BranchShiftForm(forms.ModelForm):
    """نموذج وردية"""
    
    class Meta:
        model = BranchShift
        fields = ['branch', 'name', 'start_time', 'end_time', 'break_minutes', 'is_active']
        widgets = {
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'break_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }


class BranchShiftAssignmentForm(forms.ModelForm):
    """نموذج تعيين وردية"""
    
    class Meta:
        model = BranchShiftAssignment
        fields = ['shift', 'employee', 'day_of_week', 'note', 'active']
        widgets = {
            'shift': forms.Select(attrs={'class': 'form-select'}),
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'note': forms.TextInput(attrs={'class': 'form-control'}),
        }
