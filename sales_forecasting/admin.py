from django.contrib import admin
from .models import (
    ForecastPeriod, SalesForecast, DemandPattern,
    InventoryRecommendation, ForecastAccuracyMetrics
)


@admin.register(ForecastPeriod)
class ForecastPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'period_type', 'start_date', 'end_date', 'is_active', 'created_at']
    list_filter = ['period_type', 'is_active', 'created_at']
    search_fields = ['name']
    date_hierarchy = 'start_date'


@admin.register(SalesForecast)
class SalesForecastAdmin(admin.ModelAdmin):
    list_display = ['product', 'period', 'forecasted_quantity', 'actual_quantity', 
                    'accuracy_percentage', 'method', 'status', 'created_at']
    list_filter = ['method', 'status', 'period', 'created_at']
    search_fields = ['product__name', 'notes']
    readonly_fields = ['variance_quantity', 'variance_revenue', 'accuracy_percentage']
    date_hierarchy = 'created_at'


@admin.register(DemandPattern)
class DemandPatternAdmin(admin.ModelAdmin):
    list_display = ['product', 'pattern_type', 'average_daily_demand', 'has_seasonality', 
                    'trend_direction', 'is_active', 'created_at']
    list_filter = ['pattern_type', 'has_seasonality', 'trend_direction', 'is_active']
    search_fields = ['product__name']
    readonly_fields = ['coefficient_of_variation', 'data_points_count']


@admin.register(InventoryRecommendation)
class InventoryRecommendationAdmin(admin.ModelAdmin):
    list_display = ['product', 'recommendation_type', 'priority', 'current_stock',
                    'recommended_order_quantity', 'status', 'created_at']
    list_filter = ['recommendation_type', 'priority', 'status', 'created_at']
    search_fields = ['product__name', 'reason']
    readonly_fields = ['forecast_data', 'demand_pattern']


@admin.register(ForecastAccuracyMetrics)
class ForecastAccuracyMetricsAdmin(admin.ModelAdmin):
    list_display = ['period', 'product', 'total_forecasts', 'overall_accuracy', 
                    'mean_absolute_percentage_error', 'created_at']
    list_filter = ['period', 'created_at']
    search_fields = ['product__name']
    readonly_fields = ['total_forecasts', 'accurate_forecasts']
