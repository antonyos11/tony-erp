"""
إدارة المراسلات
Correspondence Management Admin
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Correspondence, CorrespondenceThread, CorrespondenceArchive, CorrespondenceTemplate


@admin.register(Correspondence)
class CorrespondenceAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'correspondence_type', 'subject', 'priority', 'status', 'received_date']
    list_filter = ['status', 'correspondence_type', 'priority', 'received_date']
    search_fields = ['reference_number', 'subject', 'sender', 'recipient']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('المراسلة'), {
            'fields': ('reference_number', 'correspondence_type', 'priority')
        }),
        (_('الموضوع'), {
            'fields': ('subject', 'description')
        }),
        (_('الأطراف'), {
            'fields': ('sender', 'recipient', 'assigned_to')
        }),
        (_('التصنيف'), {
            'fields': ('category', 'tags')
        }),
        (_('الحالة والتواريخ'), {
            'fields': ('status', 'received_date', 'reviewed_date', 'response_date')
        }),
        (_('المرفقات'), {
            'fields': ('attachments',)
        }),
        (_('ملاحظات'), {
            'fields': ('notes',)
        }),
    )


@admin.register(CorrespondenceThread)
class CorrespondenceThreadAdmin(admin.ModelAdmin):
    list_display = ['original_correspondence', 'is_resolved', 'resolution_date']
    list_filter = ['is_resolved']
    filter_horizontal = ['replies']


@admin.register(CorrespondenceArchive)
class CorrespondenceArchiveAdmin(admin.ModelAdmin):
    list_display = ['correspondence', 'archive_date', 'access_restricted']
    list_filter = ['access_restricted']
    filter_horizontal = ['allowed_users']
    readonly_fields = ['id', 'archive_date']


@admin.register(CorrespondenceTemplate)
class CorrespondenceTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category']
    list_filter = ['category']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at']
