"""
إدارة الذكاء الاصطناعي والبيانات الضخمة
Business Intelligence Admin
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Dashboard, Widget, Forecast, PredictiveAnalysis, Report


class WidgetInline(admin.TabularInline):
    model = Widget
    extra = 1
    fields = ['title', 'widget_type', 'position_x', 'position_y', 'width', 'height']


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'is_public', 'is_default', 'updated_at']
    list_filter = ['is_public', 'is_default', 'theme']
    search_fields = ['name', 'description']
    filter_horizontal = ['allowed_users']
    # inlines = [WidgetInline]  # Temporarily disabled for migration
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Widget)
class WidgetAdmin(admin.ModelAdmin):
    list_display = ['dashboard', 'title', 'widget_type', 'position_x', 'position_y']
    list_filter = ['widget_type']
    search_fields = ['title']
    readonly_fields = ['id', 'created_at']


@admin.register(Forecast)
class ForecastAdmin(admin.ModelAdmin):
    list_display = ['forecast_type', 'period_end', 'predicted_value', 'confidence_level', 'accuracy']
    list_filter = ['forecast_type', 'period_end']
    readonly_fields = ['id', 'created_at', 'accuracy']


@admin.register(PredictiveAnalysis)
class PredictiveAnalysisAdmin(admin.ModelAdmin):
    list_display = ['analysis_type', 'entity_type', 'score', 'segment', 'analysis_date']
    list_filter = ['analysis_type']
    search_fields = ['entity_id']
    readonly_fields = ['id', 'analysis_date']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'frequency', 'is_active', 'last_generated']
    list_filter = ['report_type', 'frequency', 'is_active']
    search_fields = ['name']
    filter_horizontal = ['recipients']
    readonly_fields = ['id', 'created_at', 'updated_at']
