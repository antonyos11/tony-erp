from django.contrib import admin
from .models import Competitor, CompetitorProduct, MarketTrend, CompetitiveAnalysis

@admin.register(Competitor)
class CompetitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'market_position', 'estimated_market_share', 'estimated_revenue', 'is_active']
    list_filter = ['market_position', 'is_active']
    search_fields = ['name', 'website']

@admin.register(CompetitorProduct)
class CompetitorProductAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'competitor', 'price', 'our_price', 'price_difference_percentage', 
                    'quality_rating', 'last_price_update']
    list_filter = ['competitor', 'quality_rating']
    search_fields = ['product_name', 'competitor__name']
    readonly_fields = ['price_difference', 'price_difference_percentage']

@admin.register(MarketTrend)
class MarketTrendAdmin(admin.ModelAdmin):
    list_display = ['title', 'trend_type', 'impact_level', 'trend_direction', 'identified_date']
    list_filter = ['trend_type', 'impact_level', 'trend_direction']
    search_fields = ['title', 'description']

@admin.register(CompetitiveAnalysis)
class CompetitiveAnalysisAdmin(admin.ModelAdmin):
    list_display = ['title', 'analysis_date', 'period_start', 'period_end', 'prepared_by', 'reviewed_by']
    list_filter = ['analysis_date']
    search_fields = ['title', 'key_findings']
    filter_horizontal = ['competitors_analyzed']
