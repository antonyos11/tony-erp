"""
إدارة الإشعارات المتقدمة
Advanced Notifications Admin
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    MessageTemplate, NotificationSchedule, SentNotification,
    NotificationPreference, SMSProvider, WhatsAppProvider
)


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel', 'trigger_event', 'is_active', 'priority']
    list_filter = ['channel', 'trigger_event', 'is_active', 'priority']
    search_fields = ['name', 'body', 'subject']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(NotificationSchedule)
class NotificationScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'template', 'schedule_type', 'is_active']
    list_filter = ['schedule_type', 'is_active']
    readonly_fields = ['id', 'created_at']


@admin.register(SentNotification)
class SentNotificationAdmin(admin.ModelAdmin):
    list_display = ['template', 'recipient_email', 'status', 'sent_at', 'delivery_status']
    list_filter = ['status', 'sent_at', 'delivery_status']
    search_fields = ['recipient_email', 'recipient__email', 'subject']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        (_('المستقبل'), {
            'fields': ('recipient', 'recipient_email', 'recipient_phone')
        }),
        (_('المحتوى'), {
            'fields': ('template', 'subject', 'body')
        }),
        (_('الحالة'), {
            'fields': ('status', 'delivery_status', 'error_message')
        }),
        (_('التتبع'), {
            'fields': ('opened_at', 'clicked_at')
        }),
        (_('المحاولات'), {
            'fields': ('retry_count', 'sent_at')
        }),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_enabled', 'sms_enabled', 'push_enabled']
    list_filter = ['email_enabled', 'sms_enabled', 'push_enabled']


@admin.register(SMSProvider)
class SMSProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'priority']
    list_filter = ['is_active']
    readonly_fields = ['id', 'created_at']


@admin.register(WhatsAppProvider)
class WhatsAppProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'business_account_id', 'is_active']
    list_filter = ['is_active']
    readonly_fields = ['id', 'created_at']
