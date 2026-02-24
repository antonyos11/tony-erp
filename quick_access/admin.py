"""
Quick Access Admin Configuration
"""
from django.contrib import admin
from .models import UserPreference, QuickAction, FrequentlyUsedReport, ScheduledReport, BulkActionHistory


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'default_view', 'theme', 'sidebar_collapsed', 'notifications_enabled', 'updated_at']
    list_filter = ['default_view', 'theme', 'notifications_enabled']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(QuickAction)
class QuickActionAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'usage_count', 'keyboard_shortcut', 'sort_order']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'name_en', 'description']
    list_editable = ['is_active', 'sort_order']
    ordering = ['category', 'sort_order']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('name', 'name_en', 'description', 'icon', 'color')
        }),
        ('التصنيف والرابط', {
            'fields': ('category', 'url', 'permission_required')
        }),
        ('الإعدادات', {
            'fields': ('is_active', 'sort_order', 'keyboard_shortcut')
        }),
        ('الإحصائيات', {
            'fields': ('usage_count',),
            'classes': ('collapse',)
        }),
    )


@admin.register(FrequentlyUsedReport)
class FrequentlyUsedReportAdmin(admin.ModelAdmin):
    list_display = ['user', 'report_name', 'report_type', 'access_count', 'last_accessed']
    list_filter = ['report_type', 'last_accessed']
    search_fields = ['user__username', 'report_name']
    readonly_fields = ['last_accessed']
    ordering = ['-access_count']


@admin.register(ScheduledReport)
class ScheduledReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'report_type', 'frequency', 'is_active', 'next_run', 'last_run']
    list_filter = ['frequency', 'is_active', 'report_type']
    search_fields = ['name', 'user__username']
    readonly_fields = ['last_run', 'created_at']
    list_editable = ['is_active']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('user', 'name', 'report_type', 'report_url')
        }),
        ('الجدولة', {
            'fields': ('frequency', 'day_of_week', 'day_of_month', 'time_of_day', 'next_run')
        }),
        ('المستلمون', {
            'fields': ('email_recipients',)
        }),
        ('الإعدادات', {
            'fields': ('is_active', 'parameters')
        }),
        ('السجل', {
            'fields': ('last_run', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BulkActionHistory)
class BulkActionHistoryAdmin(admin.ModelAdmin):
    list_display = ['action_type', 'user', 'model_name', 'affected_count', 'success_count', 'error_count', 'duration_seconds', 'timestamp']
    list_filter = ['action_type', 'model_name', 'timestamp']
    search_fields = ['user__username', 'action_type']
    readonly_fields = ['timestamp', 'duration_seconds']
    ordering = ['-timestamp']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
