from django.contrib import admin
from .models import Notification, NotificationSetting


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'category', 'is_read', 'created_at']
    list_filter = ['notification_type', 'category', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['created_at', 'read_at']


@admin.register(NotificationSetting)
class NotificationSettingAdmin(admin.ModelAdmin):
    list_display = ['user', 'stock_alerts', 'invoice_alerts', 'production_alerts', 'hr_alerts', 'financial_alerts']
