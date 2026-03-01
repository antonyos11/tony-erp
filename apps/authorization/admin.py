"""
إدارة الصلاحيات من لوحة التحكم — RITA ERP
"""
from django.contrib import admin
from apps.authorization.models import Role, Permission, UserRole, AuditLog, Delegation


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
