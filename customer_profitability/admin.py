from django.contrib import admin
from .models import CustomerProfitabilityAnalysis, CustomerValueScore

@admin.register(CustomerProfitabilityAnalysis)
class CustomerProfitabilityAnalysisAdmin(admin.ModelAdmin):
    list_display = ['customer', 'total_revenue', 'net_profit', 'profit_margin', 'tier', 'created_at']
    list_filter = ['tier', 'analysis_period_start']
    search_fields = ['customer__name']
    readonly_fields = ['gross_profit', 'net_profit', 'profit_margin', 'tier']

@admin.register(CustomerValueScore)
class CustomerValueScoreAdmin(admin.ModelAdmin):
    list_display = ['customer', 'recency_score', 'frequency_score', 'monetary_score', 'total_score', 'segment']
    list_filter = ['segment']
    search_fields = ['customer__name']
