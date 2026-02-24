"""
تسجيل نماذج الصلاحيات والموافقات في لوحة التحكم
"""

from django.contrib import admin
from django.utils.html import format_html

from accounts.models_permissions import (
    UserBranchPermission,
    DataAccessRule,
    SecurityPolicy,
)
from accounts.models_workflow import (
    ApprovalWorkflow,
    ApprovalStep,
    ApprovalRequest,
    ApprovalAction,
)


@admin.register(UserBranchPermission)
class UserBranchPermissionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'branch', 'is_default_branch',
        'can_view', 'can_create', 'can_edit',
        'can_delete', 'can_approve', 'financial_limit'
    ]
    list_filter = ['branch', 'can_view', 'can_create', 'can_approve', 'is_default_branch']
    search_fields = ['user__username', 'user__first_name', 'branch__name']
    list_editable = [
        'can_view', 'can_create', 'can_edit',
        'can_delete', 'can_approve', 'financial_limit'
    ]
    raw_id_fields = ['user']
    autocomplete_fields = ['branch']


@admin.register(DataAccessRule)
class DataAccessRuleAdmin(admin.ModelAdmin):
    list_display = ['role', 'module', 'access_level', 'is_active']
    list_filter = ['module', 'access_level', 'is_active']
    list_editable = ['access_level', 'is_active']


@admin.register(SecurityPolicy)
class SecurityPolicyAdmin(admin.ModelAdmin):
    list_display = [
        'min_password_length', 'max_login_attempts',
        'session_timeout_minutes', 'require_2fa_for_admins', 'updated_at'
    ]

    def has_add_permission(self, request):
        return not SecurityPolicy.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class ApprovalStepInline(admin.TabularInline):
    model = ApprovalStep
    extra = 1
    ordering = ['step_order']


@admin.register(ApprovalWorkflow)
class ApprovalWorkflowAdmin(admin.ModelAdmin):
    list_display = ['name', 'document_type', 'is_active', 'apply_to_all_branches', 'created_at']
    list_filter = ['document_type', 'is_active', 'apply_to_all_branches']
    search_fields = ['name']
    inlines = [ApprovalStepInline]
    filter_horizontal = ['branches']


class ApprovalActionInline(admin.TabularInline):
    model = ApprovalAction
    extra = 0
    readonly_fields = ['step', 'action', 'acted_by', 'notes', 'created_at']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'document_type', 'document_number', 'amount',
        'status_colored', 'requested_by', 'branch', 'created_at'
    ]
    list_filter = ['status', 'document_type', 'branch']
    search_fields = ['document_number', 'requested_by__username']
    readonly_fields = ['created_at', 'completed_at']
    inlines = [ApprovalActionInline]
    raw_id_fields = ['requested_by']

    @admin.display(description='الحالة')
    def status_colored(self, obj):
        colors = {
            'pending': '#f0ad4e',
            'approved': '#5cb85c',
            'rejected': '#d9534f',
            'escalated': '#5bc0de',
            'cancelled': '#777',
            'auto_approved': '#5cb85c',
        }
        color = colors.get(obj.status, '#777')
        return format_html(
            '<span style="color:{}; font-weight:bold">{}</span>',
            color, obj.get_status_display()
        )
