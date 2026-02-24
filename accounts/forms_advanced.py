"""
نماذج الصلاحيات والموافقات المتقدمة
"""

from django import forms
from django.contrib.auth.models import User

from accounts.models_permissions import UserBranchPermission, DataAccessRule, SecurityPolicy
from accounts.models_workflow import ApprovalWorkflow, ApprovalStep, ApprovalRequest


class UserBranchPermissionForm(forms.ModelForm):
    class Meta:
        model = UserBranchPermission
        fields = [
            'user', 'branch', 'is_default_branch', 'financial_limit',
            'can_view', 'can_create', 'can_edit', 'can_delete',
            'can_approve', 'can_export',
        ]
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'financial_limit': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01'
            }),
            'is_default_branch': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_view': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_create': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_edit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_delete': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_approve': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_export': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DataAccessRuleForm(forms.ModelForm):
    class Meta:
        model = DataAccessRule
        fields = ['role', 'module', 'access_level', 'is_active']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'module': forms.Select(attrs={'class': 'form-select'}),
            'access_level': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SecurityPolicyForm(forms.ModelForm):
    class Meta:
        model = SecurityPolicy
        fields = [
            'min_password_length', 'require_uppercase', 'require_lowercase',
            'require_numbers', 'require_special_chars', 'password_expiry_days',
            'password_history_count', 'max_login_attempts',
            'lockout_duration_minutes', 'session_timeout_minutes',
            'require_2fa_for_admins', 'allowed_ips',
        ]
        widgets = {
            'min_password_length': forms.NumberInput(attrs={'class': 'form-control'}),
            'require_uppercase': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'require_lowercase': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'require_numbers': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'require_special_chars': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'password_expiry_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'password_history_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_login_attempts': forms.NumberInput(attrs={'class': 'form-control'}),
            'lockout_duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'session_timeout_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'require_2fa_for_admins': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allowed_ips': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'عنوان IP واحد في كل سطر'
            }),
        }


class ApprovalWorkflowForm(forms.ModelForm):
    class Meta:
        model = ApprovalWorkflow
        fields = [
            'name', 'document_type', 'apply_to_all_branches',
            'branches', 'is_active', 'description',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'apply_to_all_branches': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'branches': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ApprovalStepForm(forms.ModelForm):
    class Meta:
        model = ApprovalStep
        fields = [
            'step_order', 'name', 'approver_role', 'approver_user',
            'min_amount', 'max_amount', 'auto_approve_below',
            'timeout_hours', 'escalate_to',
        ]
        widgets = {
            'step_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'approver_role': forms.TextInput(attrs={'class': 'form-control'}),
            'approver_user': forms.Select(attrs={'class': 'form-select'}),
            'min_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'auto_approve_below': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'timeout_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'escalate_to': forms.Select(attrs={'class': 'form-select'}),
        }


ApprovalStepFormSet = forms.inlineformset_factory(
    ApprovalWorkflow,
    ApprovalStep,
    form=ApprovalStepForm,
    extra=1,
    can_delete=True,
)


class ApprovalActionForm(forms.Form):
    """نموذج اتخاذ إجراء على طلب موافقة"""
    action = forms.ChoiceField(
        choices=[('approve', 'موافقة'), ('reject', 'رفض'), ('return', 'إعادة')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='الإجراء'
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='ملاحظات'
    )
