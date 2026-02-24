from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    UserRole, UserProfile, ModulePermission, ResourcePermission, UserSession,
    UserActivity, SecurityAlert
)


class ModulePermissionInline(admin.TabularInline):
    model = ModulePermission
    extra = 0
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('role')


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'approval_level', 'max_approval_amount', 'can_approve', 'is_active']
    list_filter = ['can_approve', 'is_active', 'approval_level']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['approval_level', 'name']
    inlines = [ModulePermissionInline]
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'display_name', 'description', 'is_active')
        }),
        ('صلاحيات الموافقة', {
            'fields': ('can_approve', 'approval_level', 'max_approval_amount'),
            'classes': ['collapse']
        }),
    )


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'ملف التعريف'
    fk_name = 'user'  # تحديد الـ ForeignKey الرئيسي
    
    fieldsets = (
        ('معلومات شخصية', {
            'fields': ('arabic_name', 'employee_id', 'phone', 'position')
        }),
        ('الأدوار والصلاحيات', {
            'fields': ('role', 'secondary_roles')
        }),
        ('إعدادات الوصول', {
            'fields': ('allowed_ips', 'max_concurrent_sessions'),
            'classes': ['collapse']
        }),
        ('إعدادات الموافقة', {
            'fields': ('is_approved', 'approved_by', 'approval_date'),
            'classes': ['collapse']
        }),
        ('إعدادات كلمة المرور', {
            'fields': ('must_change_password', 'account_expires'),
            'classes': ['collapse']
        }),
    )
    
    filter_horizontal = ['secondary_roles']


class CustomUserAdmin(BaseUserAdmin):
    """إدارة المستخدمين مع الملف التعريفي"""
    inlines = [UserProfileInline]
    
    list_display = ['username', 'get_arabic_name', 'get_employee_id', 'get_role', 'is_active', 'is_approved']
    list_filter = ['is_active', 'is_staff', 'profile__is_approved', 'profile__role']
    search_fields = ['username', 'email', 'profile__arabic_name', 'profile__employee_id']
    
    def get_arabic_name(self, obj):
        try:
            return obj.profile.arabic_name
        except:
            return '-'
    get_arabic_name.short_description = 'الاسم بالعربية'
    
    def get_employee_id(self, obj):
        try:
            return obj.profile.employee_id
        except:
            return '-'
    get_employee_id.short_description = 'رقم الموظف'
    
    def get_role(self, obj):
        try:
            return obj.profile.role.display_name
        except:
            return '-'
    get_role.short_description = 'الدور'
    
    def is_approved(self, obj):
        try:
            return obj.profile.is_approved
        except:
            return False
    is_approved.boolean = True
    is_approved.short_description = 'موافق عليه'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile', 'profile__role')


@admin.register(ModulePermission)
class ModulePermissionAdmin(admin.ModelAdmin):
    list_display = ['role', 'module_display', 'action_display', 'is_allowed']
    list_filter = ['module', 'action', 'is_allowed', 'role']
    search_fields = ['role__display_name', 'module', 'action']
    ordering = ['role', 'module', 'action']
    
    def module_display(self, obj):
        return obj.get_module_display()
    module_display.short_description = 'الوحدة'
    
    def action_display(self, obj):
        return obj.get_action_display()
    action_display.short_description = 'العملية'


@admin.register(ResourcePermission)
class ResourcePermissionAdmin(admin.ModelAdmin):
    list_display = ['role', 'module', 'resource', 'action', 'is_allowed', 'description']
    list_filter = ['module', 'action', 'is_allowed', 'role']
    search_fields = ['role__display_name', 'module', 'resource', 'action', 'description']
    ordering = ['role', 'module', 'resource', 'action']
    list_editable = ['is_allowed']
    fieldsets = (
        ('تفاصيل', {'fields': ('role', 'module', 'resource', 'action', 'is_allowed')}),
        ('وصف', {'fields': ('description',), 'classes': ['collapse']}),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'login_time', 'last_activity', 'is_active']
    list_filter = ['is_active', 'login_time']
    search_fields = ['user__username', 'ip_address']
    ordering = ['-last_activity']
    readonly_fields = ['session_key', 'user_agent', 'login_time']
    
    def has_add_permission(self, request):
        return False


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'module', 'description_short', 'timestamp', 'success', 'ip_address']
    list_filter = ['success', 'module', 'action', 'timestamp']
    search_fields = ['user__username', 'description', 'ip_address']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'الوصف'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SecurityAlert)
class SecurityAlertAdmin(admin.ModelAdmin):
    list_display = ['alert_type_display', 'user', 'description_short', 'timestamp', 'is_resolved', 'ip_address']
    list_filter = ['alert_type', 'is_resolved', 'timestamp']
    search_fields = ['user__username', 'description', 'ip_address']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']
    
    fieldsets = (
        ('معلومات التنبيه', {
            'fields': ('alert_type', 'user', 'description', 'ip_address', 'timestamp')
        }),
        ('الحل', {
            'fields': ('is_resolved', 'resolved_by'),
            'classes': ['collapse']
        }),
    )
    
    def alert_type_display(self, obj):
        return obj.get_alert_type_display()
    alert_type_display.short_description = 'نوع التنبيه'
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'الوصف'


# إعادة تسجيل نموذج User مع التحسينات
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# تخصيص عنوان لوحة الإدارة
admin.site.site_header = 'نظام إدارة المستخدمين والصلاحيات - الشامل'
admin.site.site_title = 'إدارة المستخدمين'
admin.site.index_title = 'لوحة تحكم إدارة المستخدمين'