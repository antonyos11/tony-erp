"""
Smart Pricing API URLs
مسارات API للتسعير الذكي
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

# إنشاء الراوتر
router = DefaultRouter()
router.register(r'rules', api_views.PricingRuleViewSet, basename='pricing-rules')
router.register(r'quotes', api_views.SmartQuoteViewSet, basename='smart-quotes')
router.register(r'competitors', api_views.CompetitorViewSet, basename='competitors')
router.register(r'competitor-prices', api_views.CompetitorPriceViewSet, basename='competitor-prices')
router.register(r'strategies', api_views.PricingStrategyViewSet, basename='strategies')
router.register(r'seasonal', api_views.SeasonalPricingViewSet, basename='seasonal')
router.register(r'history', api_views.PriceHistoryViewSet, basename='price-history')
router.register(r'goals', api_views.PricingGoalViewSet, basename='pricing-goals')
router.register(r'alerts', api_views.PriceAlertViewSet, basename='price-alerts')
router.register(r'profiles', api_views.ProductPricingProfileViewSet, basename='pricing-profiles')
router.register(r'bundles', api_views.BundlePricingViewSet, basename='bundles')

app_name = 'smart_pricing_api'

urlpatterns = [
    # ViewSets
    path('', include(router.urls)),
    
    # Custom API Endpoints
    path('calculate/', api_views.calculate_optimal_price, name='calculate-price'),
    path('bulk-calculate/', api_views.bulk_calculate_prices, name='bulk-calculate'),
    path('auto-pricing/', api_views.run_auto_pricing, name='auto-pricing'),
    path('simulate/', api_views.run_price_simulation, name='simulate'),
    path('dashboard/', api_views.get_dashboard_stats, name='dashboard-stats'),
    path('compare/<int:product_id>/', api_views.get_price_comparison, name='compare'),
    path('reports/', api_views.get_pricing_reports, name='reports'),
]
