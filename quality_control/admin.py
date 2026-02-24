from django.contrib import admin
from .models import QualityStandard, InspectionType, QualityInspection, InspectionResult, QualityIssue

@admin.register(QualityStandard)
class QualityStandardAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'min_value', 'max_value', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['code', 'name']

@admin.register(InspectionType)
class InspectionTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active']
    filter_horizontal = ['standards']

class InspectionResultInline(admin.TabularInline):
    model = InspectionResult
    extra = 1

@admin.register(QualityInspection)
class QualityInspectionAdmin(admin.ModelAdmin):
    list_display = ['code', 'inspection_type', 'product', 'inspection_date', 'status', 'overall_score']
    list_filter = ['status', 'inspection_type', 'inspection_date']
    search_fields = ['code', 'batch_number']
    inlines = [InspectionResultInline]

@admin.register(QualityIssue)
class QualityIssueAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'severity', 'status', 'reported_by', 'assigned_to']
    list_filter = ['severity', 'status']
    search_fields = ['code', 'title']
