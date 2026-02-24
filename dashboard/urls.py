"""
URLs للوحة المعلومات
Dashboard URLs
"""

from django.urls import path
from .api_views import (
    DashboardDataAPIView,
    KPIAPIView,
    KPIComparisonAPIView,
    SalesChartAPIView,
    InventoryChartAPIView,
    ClearCacheAPIView
)

app_name = 'dashboard'

urlpatterns = [
    # API Endpoints
    path('api/data/', DashboardDataAPIView.as_view(), name='api-data'),
    path('api/kpis/', KPIAPIView.as_view(), name='api-kpis'),
    path('api/kpis/comparison/', KPIComparisonAPIView.as_view(), name='api-kpis-comparison'),
    path('api/charts/sales/', SalesChartAPIView.as_view(), name='api-sales-chart'),
    path('api/charts/inventory/', InventoryChartAPIView.as_view(), name='api-inventory-chart'),
    path('api/cache/clear/', ClearCacheAPIView.as_view(), name='api-clear-cache'),
]
