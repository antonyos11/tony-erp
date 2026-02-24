"""
Admin لمنشئ التقارير
"""

from django.contrib import admin
from .models import (
    DataSource, Report, ReportWidget, ReportTemplate,
    ScheduledReport, ReportExecution
)


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'content_type', 'created_by', 'created_at']
    list_filter = ['source_type', 'created_at']
    search_fields = ['name']
    raw_id_fields = ['created_by']


class ReportWidgetInline(admin.TabularInline):
    model = ReportWidget
    extra = 0


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'status', 'view_count', 'created_by', 'created_at']
    list_filter = ['report_type', 'status', 'created_at']
    search_fields = ['name', 'description']
    raw_id_fields = ['created_by', 'data_source']
    filter_horizontal = ['shared_with']
    inlines = [ReportWidgetInline]
    readonly_fields = ['uuid', 'view_count', 'last_viewed']


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_system', 'is_active', 'created_at']
    list_filter = ['is_system', 'is_active', 'category']
    search_fields = ['name']


@admin.register(ScheduledReport)
class ScheduledReportAdmin(admin.ModelAdmin):
    list_display = ['report', 'frequency', 'export_format', 'is_active', 'next_run']
    list_filter = ['frequency', 'is_active', 'export_format']
    raw_id_fields = ['report', 'created_by']


@admin.register(ReportExecution)
class ReportExecutionAdmin(admin.ModelAdmin):
    list_display = ['report', 'status', 'rows_count', 'execution_time', 'executed_by', 'started_at']
    list_filter = ['status', 'started_at']
    raw_id_fields = ['report', 'executed_by']
    readonly_fields = ['started_at', 'completed_at']
