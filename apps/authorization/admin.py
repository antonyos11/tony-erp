"""
إدارة الصلاحيات من لوحة التحكم — RITA ERP
"""
from django.contrib import admin
from apps.authorization.models import (
    Role, Permission, UserRole, AuditLog, Delegation,
    # Sprint 22A — نماذج النظام الجديد
    SystemPermission, SystemRole, UserRoleAssignment, SecurityViolationLog,
)


class PermissionInline(admin.TabularInline):
    model = Permission
    extra = 0


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'is_active', 'max_discount_percentage')
    list_filter = ('level', 'is_active')
    search_fields = ('name',)
    inlines = [PermissionInline]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'module', 'action', 'is_allowed')
    list_filter = ('role', 'module', 'action', 'is_allowed')


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_primary', 'is_active')
    list_filter = ('role', 'is_active', 'is_primary')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'module', 'model_name', 'timestamp', 'ip_address')
    list_filter = ('action', 'module', 'timestamp')
    search_fields = ('user__username', 'description', 'model_name')
    readonly_fields = (
        'user', 'action', 'module', 'model_name', 'object_id',
        'description', 'old_value', 'new_value', 'ip_address',
        'branch', 'timestamp',
    )
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Delegation)
class DelegationAdmin(admin.ModelAdmin):
    list_display = ('delegator', 'delegate', 'role', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'role')
    search_fields = (
        'delegator__username', 'delegate__username',
        'delegator__first_name', 'delegate__first_name',
    )


# ══════════════════════════════════════════════════════
# Sprint 22A — نماذج النظام الجديد
# ══════════════════════════════════════════════════════

@admin.register(SystemPermission)
class SystemPermissionAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'module', 'action', 'is_sensitive')
    list_filter = ('module', 'action', 'is_sensitive')
    search_fields = ('code', 'name', 'description')
    ordering = ('module', 'action')
    readonly_fields = ('code',)


class SystemPermissionInline(admin.TabularInline):
    model = SystemRole.permissions.through
    extra = 0
    verbose_name = "صلاحية"
    verbose_name_plural = "الصلاحيات"


@admin.register(SystemRole)
class SystemRoleAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'scope', 'max_discount_percentage',
                    'invoice_approval_limit', 'is_system', 'is_active', 'sort_order')
    list_filter = ('scope', 'is_system', 'is_active')
    search_fields = ('code', 'name', 'description')
    filter_horizontal = ('permissions', 'can_be_granted_by')
    ordering = ('sort_order', 'name')
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('code', 'name', 'description', 'scope', 'is_system', 'is_active', 'sort_order')
        }),
        ('الصلاحيات', {
            'fields': ('permissions',)
        }),
        ('سقوف الاعتماد والتفويض', {
            'fields': ('invoice_approval_limit', 'expense_approval_limit',
                       'return_approval_limit', 'max_discount_percentage', 'can_be_granted_by')
        }),
    )


@admin.register(UserRoleAssignment)
class UserRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'assigned_by', 'assigned_at', 'branch', 'is_active')
    list_filter = ('role', 'is_active', 'branch')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'role__name')
    autocomplete_fields = ('user',)
    readonly_fields = ('assigned_at',)
    date_hierarchy = 'assigned_at'


@admin.register(SecurityViolationLog)
class SecurityViolationLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'attempted_module', 'attempted_action', 'attempted_url',
                    'ip_address', 'timestamp')
    list_filter = ('attempted_module', 'attempted_action', 'timestamp')
    search_fields = ('user__username', 'attempted_url', 'ip_address')
    readonly_fields = (
        'user', 'attempted_url', 'attempted_module', 'attempted_action',
        'ip_address', 'user_agent', 'timestamp',
    )
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
