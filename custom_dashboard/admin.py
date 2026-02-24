"""
Admin للوحة التحكم المخصصة
"""

from django.contrib import admin
from .models import DashboardLayout, Widget, DashboardWidget, WidgetData, QuickActionWidget


@admin.register(DashboardLayout)
class DashboardLayoutAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_default', 'is_active', 'columns', 'created_at']
    list_filter = ['is_default', 'is_active', 'columns']
    search_fields = ['name', 'user__username']
    raw_id_fields = ['user']


@admin.register(Widget)
class WidgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'widget_type', 'icon', 'default_size', 'is_active', 'is_system']
    list_filter = ['widget_type', 'is_active', 'is_system']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['widget', 'layout', 'position_x', 'position_y', 'width', 'height', 'is_visible']
    list_filter = ['is_visible', 'is_collapsed']
    raw_id_fields = ['layout', 'widget']


@admin.register(WidgetData)
class WidgetDataAdmin(admin.ModelAdmin):
    list_display = ['widget', 'user', 'cached_at', 'expires_at']
    list_filter = ['cached_at']
    raw_id_fields = ['widget', 'user']


@admin.register(QuickActionWidget)
class QuickActionWidgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'icon', 'color', 'order', 'is_active', 'usage_count']
    list_filter = ['is_active', 'color']
    search_fields = ['name', 'user__username']
    raw_id_fields = ['user']
