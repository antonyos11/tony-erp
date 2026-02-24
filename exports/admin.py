from django.contrib import admin
from .models import BackupRecord, DataExport


@admin.register(BackupRecord)
class BackupRecordAdmin(admin.ModelAdmin):
    list_display = ['backup_name', 'backup_type', 'status', 'file_size', 'created_at']
    list_filter = ['backup_type', 'status', 'created_at']
    search_fields = ['backup_name']
    readonly_fields = ['created_at', 'completed_at', 'file_size']


@admin.register(DataExport)
class DataExportAdmin(admin.ModelAdmin):
    list_display = ['export_name', 'export_type', 'export_format', 'status', 'progress', 'created_at']
    list_filter = ['export_type', 'export_format', 'status', 'created_at']
    search_fields = ['export_name']
    readonly_fields = ['created_at', 'completed_at', 'file_size', 'download_count']