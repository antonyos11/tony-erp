"""
URLs للأنظمة الجديدة (Enterprise)
- MRP
- Costing
- Distribution
- Unified Dashboard
- Integration
"""

from django.urls import path
from . import views_enterprise as views

app_name = 'enterprise'

urlpatterns = [
    # ==================== MRP ====================
    path('mrp/requirements/', views.mrp_material_requirements, name='mrp_requirements'),
    path('mrp/schedule/', views.mrp_production_schedule, name='mrp_schedule'),
    path('mrp/purchase-suggestions/', views.mrp_purchase_suggestions, name='mrp_purchase_suggestions'),
    path('mrp/alerts/', views.mrp_alerts, name='mrp_alerts'),
    path('mrp/capacity/', views.mrp_capacity, name='mrp_capacity'),
    
    # ==================== Costing ====================
    path('costing/standard/', views.costing_standard_cost, name='costing_standard'),
    path('costing/actual/', views.costing_actual_cost, name='costing_actual'),
    path('costing/variances/', views.costing_variances, name='costing_variances'),
    path('costing/margin/', views.costing_product_margin, name='costing_margin'),
    path('costing/analysis/', views.costing_analysis_report, name='costing_analysis'),
    
    # ==================== Distribution ====================
    path('distribution/stock-levels/', views.distribution_stock_levels, name='distribution_stock_levels'),
    path('distribution/replenishment/', views.distribution_replenishment_suggestions, name='distribution_replenishment'),
    path('distribution/create-replenishment/', views.distribution_create_replenishment, name='distribution_create_replenishment'),
    path('distribution/dashboard/', views.distribution_dashboard, name='distribution_dashboard'),
    path('distribution/movements/', views.distribution_movements, name='distribution_movements'),
    
    # ==================== Unified Dashboard ====================
    path('dashboard/unified/', views.unified_dashboard, name='unified_dashboard'),
    path('dashboard/company/', views.dashboard_company_overview, name='dashboard_company'),
    path('dashboard/branches/', views.dashboard_branches_performance, name='dashboard_branches'),
    path('dashboard/production/', views.dashboard_production_status, name='dashboard_production'),
    path('dashboard/inventory/', views.dashboard_inventory_overview, name='dashboard_inventory'),
    path('dashboard/alerts/', views.dashboard_alerts, name='dashboard_alerts'),
    path('dashboard/charts/', views.dashboard_charts, name='dashboard_charts'),
    
    # ==================== Integration ====================
    path('integration/demands/', views.integration_demands, name='integration_demands'),
    path('integration/create-production/', views.integration_create_production, name='integration_create_production'),
    path('integration/create-transfer/', views.integration_create_transfer, name='integration_create_transfer'),
    path('integration/links/', views.integration_links, name='integration_links'),
    path('integration/dashboard/', views.integration_dashboard, name='integration_dashboard'),
    path('integration/auto-process/', views.integration_auto_process, name='integration_auto_process'),
]
