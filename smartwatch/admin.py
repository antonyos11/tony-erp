"""
Admin لتكامل الساعات الذكية
"""

from django.contrib import admin
from .models import (
    WatchDevice, WatchNotification, QuickAction,
    WatchActionLog, WatchDashboardWidget, WatchUserSettings
)


@admin.register(WatchDevice)
class WatchDeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'device_type', 'is_active', 'is_connected', 'last_sync']
    list_filter = ['device_type', 'is_active', 'is_connected']
    search_fields = ['name', 'user__username']
    raw_id_fields = ['user']


@admin.register(WatchNotification)
class WatchNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'device', 'notification_type', 'priority', 'is_sent', 'is_read', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_sent', 'is_read']
    search_fields = ['title', 'body']
    raw_id_fields = ['device']


@admin.register(QuickAction)
class QuickActionAdmin(admin.ModelAdmin):
    list_display = ['name', 'action_type', 'is_global', 'is_active', 'order']
    list_filter = ['action_type', 'is_global', 'is_active']
    search_fields = ['name']
    filter_horizontal = ['available_for']


@admin.register(WatchActionLog)
class WatchActionLogAdmin(admin.ModelAdmin):
    list_display = ['action_name', 'device', 'action_type', 'is_success', 'created_at']
    list_filter = ['action_type', 'is_success', 'created_at']
    search_fields = ['action_name']
    raw_id_fields = ['device', 'action']


@admin.register(WatchDashboardWidget)
class WatchDashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'widget_type', 'is_active', 'order']
    list_filter = ['widget_type', 'is_active']


@admin.register(WatchUserSettings)
class WatchUserSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'notify_on_task', 'notify_on_message', 'vibration_enabled']
    raw_id_fields = ['user']
    filter_horizontal = ['favorite_actions', 'enabled_widgets']
