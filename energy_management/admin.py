from django.contrib import admin
from .models import UtilityMeter, UtilityReading, EnergyConsumptionAnalysis, EnergyAlert

@admin.register(UtilityMeter)
class UtilityMeterAdmin(admin.ModelAdmin):
    list_display = ['meter_number', 'utility_type', 'location', 'branch', 'is_active']
    list_filter = ['utility_type', 'is_active']
    search_fields = ['meter_number', 'location']

@admin.register(UtilityReading)
class UtilityReadingAdmin(admin.ModelAdmin):
    list_display = ['meter', 'reading_date', 'consumption', 'total_cost', 'recorded_by']
    list_filter = ['reading_date', 'meter__utility_type']
    search_fields = ['meter__meter_number']
    readonly_fields = ['consumption', 'total_cost']

@admin.register(EnergyConsumptionAnalysis)
class EnergyConsumptionAnalysisAdmin(admin.ModelAdmin):
    list_display = ['meter', 'period_start', 'period_end', 'total_consumption', 'total_cost', 
                    'variance_percentage', 'efficiency_score']
    list_filter = ['period_end', 'efficiency_score']
    search_fields = ['meter__meter_number']

@admin.register(EnergyAlert)
class EnergyAlertAdmin(admin.ModelAdmin):
    list_display = ['meter', 'alert_type', 'severity', 'actual_value', 'is_resolved', 'created_at']
    list_filter = ['alert_type', 'severity', 'is_resolved']
    search_fields = ['meter__meter_number', 'message']
