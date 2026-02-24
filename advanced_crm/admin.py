"""
إدارة CRM المتقدم
Advanced CRM Admin
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import SalesStage, Opportunity, ActivityLog, ForecastRecord


@admin.register(SalesStage)
class SalesStageAdmin(admin.ModelAdmin):
    list_display = ['name', 'sequence', 'conversion_probability', 'color']
    ordering = ['sequence']
    readonly_fields = ['id', 'created_at']


class ActivityLogInline(admin.TabularInline):
    model = ActivityLog
    extra = 1
    fields = ['activity_type', 'activity_date', 'subject']


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ['opportunity_id', 'title', 'stage', 'status', 'expected_value', 'expected_close_date']
    list_filter = ['status', 'stage', 'expected_close_date', 'is_at_risk']
    search_fields = ['opportunity_id', 'title']
    readonly_fields = ['id', 'weighted_value', 'created_at', 'updated_at']
    # inlines = [ActivityLogInline]  # Temporarily disabled for migration
    filter_horizontal = ['products']
    
    fieldsets = (
        (_('الفرصة'), {
            'fields': ('opportunity_id', 'title', 'description')
        }),
        (_('الطرف الثالث'), {
            'fields': ('customer', 'contact', 'owner')
        }),
        (_('المرحلة'), {
            'fields': ('stage', 'status', 'expected_close_date', 'closed_date')
        }),
        (_('البيانات المالية'), {
            'fields': ('expected_value', 'currency', 'weighted_value')
        }),
        (_('المنتجات'), {
            'fields': ('products',)
        }),
        (_('المخاطر والتنبؤات'), {
            'fields': ('is_at_risk', 'risk_reason', 'success_probability')
        }),
        (_('المرفقات'), {
            'fields': ('attachments',)
        }),
    )


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['opportunity', 'activity_type', 'subject', 'activity_date', 'follow_up_required']
    list_filter = ['activity_type', 'activity_date', 'follow_up_required']
    search_fields = ['opportunity__title', 'subject']
    readonly_fields = ['id', 'created_date']


@admin.register(ForecastRecord)
class ForecastRecordAdmin(admin.ModelAdmin):
    list_display = ['forecast_date', 'period', 'expected_revenue', 'accuracy_percentage']
    list_filter = ['forecast_date']
    readonly_fields = ['id', 'created_at', 'created_by']
