"""
Admin للنسخ الاحتياطي السحابي
"""

from django.contrib import admin
from .models import CloudProvider, BackupSchedule, Backup, RestorePoint, BackupSettings


@admin.register(CloudProvider)
class CloudProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider_type', 'is_active', 'is_default', 'connection_status', 'last_connection']
    list_filter = ['provider_type', 'is_active', 'is_default']
    search_fields = ['name']
    raw_id_fields = ['created_by']


@admin.register(BackupSchedule)
class BackupScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'frequency', 'backup_type', 'is_active', 'last_run', 'next_run']
    list_filter = ['frequency', 'backup_type', 'is_active']
    search_fields = ['name']
    raw_id_fields = ['provider', 'created_by']


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'status', 'file_size_display', 'duration_seconds', 'created_at']
    list_filter = ['status', 'backup_type', 'created_at']
    search_fields = ['name']
    raw_id_fields = ['schedule', 'provider', 'created_by']
    readonly_fields = ['uuid', 'file_size', 'files_count', 'started_at', 'completed_at']


@admin.register(RestorePoint)
class RestorePointAdmin(admin.ModelAdmin):
    list_display = ['backup', 'status', 'initiated_by', 'started_at', 'completed_at']
    list_filter = ['status', 'created_at']
    raw_id_fields = ['backup', 'initiated_by']
    readonly_fields = ['started_at', 'completed_at']


@admin.register(BackupSettings)
class BackupSettingsAdmin(admin.ModelAdmin):
    list_display = ['encryption_enabled', 'compression_enabled', 'default_retention_days']
