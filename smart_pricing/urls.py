"""
URLs for Smart Pricing Module
نظام التسعير الذكي المتقدم
"""

from django.urls import path, include
from . import views
from . import views_extended as ve
from . import views_price_list as vpl

app_name = 'smart_pricing'

urlpatterns = [
    # REST API endpoints (DRF ViewSets)
    path('api/v2/', include('smart_pricing.api_urls')),
    
    # لوحة التحكم
    path('', ve.pricing_dashboard, name='dashboard'),
    path('dashboard/', ve.pricing_dashboard, name='pricing_dashboard'),
    
    # قواعد التسعير
    path('rules/', ve.pricing_rules_list, name='rules_list'),
    path('rules/create/', ve.rule_create, name='rule_create'),
    path('rules/<int:rule_id>/', ve.rule_detail, name='rule_detail'),
    path('rules/<int:rule_id>/edit/', ve.rule_edit, name='rule_edit'),
    path('rules/<int:rule_id>/delete/', ve.rule_delete, name='rule_delete'),
    
    # عروض الأسعار الذكية
    path('quotes/', ve.smart_quotes_list, name='quotes_list'),
    path('quotes/create/', ve.create_smart_quote, name='create_quote'),
    path('quotes/<int:quote_id>/', ve.quote_detail, name='quote_detail'),
    path('quote/calculate/competition-based/', ve.competition_based_calculation, name='competition_based_calc'),
    
    # المنافسين
    path('competitors/', ve.competitors_list, name='competitors_list'),
    path('competitors/<int:competitor_id>/', ve.competitor_detail, name='competitor_detail'),
    path('competitors/add-price/', ve.add_competitor_price, name='add_competitor_price'),
    
    # حسابات التسعير المختلفة
    path('quote/calculate/competition-based/', ve.competition_based_calculation, name='competition_based_calc'),
    path('quote/calculate/value-based/', ve.value_based_calculation, name='value_based_calc'),
    path('quote/calculate/cost-plus/', ve.cost_plus_calculation, name='cost_plus_calc'),
    path('quote/calculate/margin-based/', ve.margin_based_calculation, name='margin_based_calc'),
    path('quote/calculate/cost-based/', ve.cost_based_calculation, name='cost_based_calc'),
    path('quote/calculate/ai-recommendation/', ve.ai_recommendation_calculation, name='ai_recommendation_calc'),
    path('production-line-suggestion/', ve.production_line_suggestion, name='production_line_suggestion'),
    # Sub-pages for Production Line Suggestion
    path('production-line-suggestion/capacity/', ve.production_line_capacity, name='production_line_capacity'),
    path('production-line-suggestion/efficiency/', ve.production_line_efficiency, name='production_line_efficiency'),
    path('production-line-suggestion/ai/', ve.production_line_ai, name='production_line_ai'),
    path('production-line-suggestion/cost/', ve.production_line_cost, name='production_line_cost'),
    
    # تاريخ الأسعار
    path('history/', ve.price_history_list, name='price_history'),
    path('history/', ve.price_history_list, name='price_history_list'),
    
    # التنبيهات
    path('alerts/', ve.alerts_list, name='alerts_list'),
    path('alerts/<int:alert_id>/action/', ve.mark_alert_actioned, name='mark_alert_actioned'),
    
    # التسعير الموسمي
    path('seasonal/', ve.seasonal_pricing_list, name='seasonal_list'),
    
    # الاستراتيجيات
    path('strategies/', ve.strategies_list, name='strategies_list'),
    
    # الأهداف
    path('goals/', ve.goals_list, name='goals_list'),
    
    # الحزم
    path('bundles/', ve.bundles_list, name='bundles_list'),
    path('bundles/<int:bundle_id>/', ve.bundle_detail, name='bundle_detail'),
    
    # الأدوات
    path('optimizer/', ve.pricing_optimizer, name='optimizer'),
    path('simulation/', ve.price_simulation, name='simulation'),
    path('auto-pricing/', ve.auto_pricing, name='auto_pricing'),
    
    # التقارير
    path('reports/', ve.reports, name='reports'),
    
    # أوامر الصرف
    path('releases/', ve.material_releases_list, name='releases_list'),
    
    # API Endpoints
    path('api/calculate-price/', ve.api_calculate_price, name='api_calculate_price'),
    path('api/bulk-calculate/', ve.api_bulk_calculate, name='api_bulk_calculate'),
    path('api/alerts/', ve.api_get_alerts, name='api_get_alerts'),
    path('api/dashboard-stats/', ve.api_dashboard_stats, name='api_dashboard_stats'),
    
    # ============ نظام قوائم الأسعار ============
    
    # لوحة تحكم قوائم الأسعار
    path('price-lists/', vpl.price_list_dashboard, name='price_list_dashboard'),
    
    # إدارة المقاسات
    # إدارة المقاسات
    path('price-lists/sizes/', vpl.sizes_list, name='sizes_list'),
    path('price-lists/sizes/create/', vpl.size_create, name='size_create'),
    path('price-lists/sizes/<int:size_id>/edit/', vpl.size_edit, name='size_edit'),
    path('price-lists/sizes/<int:size_id>/delete/', vpl.size_delete, name='size_delete'),
    path('price-lists/sizes/bulk-create/', vpl.bulk_create_sizes, name='bulk_create_sizes'),
    
    # إدارة عائلات المنتجات
    path('price-lists/families/', vpl.families_list, name='families_list'),
    path('price-lists/families/create/', vpl.family_create, name='family_create'),
    path('price-lists/families/generate-code/', vpl.generate_family_code, name='generate_family_code'),
    path('price-lists/families/<int:family_id>/', vpl.family_detail, name='family_detail'),
    path('price-lists/families/<int:family_id>/edit/', vpl.family_edit, name='family_edit'),
    path('price-lists/families/<int:family_id>/delete/', vpl.family_delete, name='family_delete'),
    path('price-lists/families/<int:family_id>/update-prices/', vpl.family_update_prices, name='family_update_prices'),
    path('price-lists/families/<int:family_id>/sync-inventory/', vpl.sync_family_to_inventory, name='sync_family_to_inventory'),
    path('price-lists/families/sync-all/', vpl.sync_all_families_to_inventory, name='sync_all_families_to_inventory'),
    
    # إدارة قوائم الأسعار
    path('price-lists/lists/', vpl.price_lists_list, name='price_lists_list'),
    path('price-lists/lists/create/', vpl.price_list_create, name='price_list_create'),
    path('price-lists/lists/<int:price_list_id>/', vpl.price_list_view, name='price_list_view'),
    path('price-lists/lists/<int:price_list_id>/print/', vpl.price_list_print, name='price_list_print'),
    path('price-lists/lists/<int:price_list_id>/smart/', vpl.price_list_smart, name='price_list_smart'),
    path('price-lists/lists/<int:price_list_id>/a4/', vpl.price_list_a4, name='price_list_a4'),
    path('price-lists/lists/<int:price_list_id>/export/', vpl.export_price_list, name='export_price_list'),
    # مسارات مختصرة للتصدير
    path('price-lists/<int:price_list_id>/export/', vpl.export_price_list, name='export_price_list_short'),
    path('price-lists/export-all/', vpl.export_all_lists, name='export_all_lists'),
    
    # إدارة التكاليف
    path('price-lists/cost-categories/', vpl.cost_categories_list, name='cost_categories_list'),
    path('price-lists/variants/<int:variant_id>/cost/', vpl.variant_cost_detail, name='variant_cost_detail'),
    path('price-lists/variants/<int:variant_id>/update-cost/', vpl.update_variant_cost, name='update_variant_cost'),
    
    # الإعدادات
    path('price-lists/settings/', vpl.settings_view, name='price_list_settings'),
    
    # API Endpoints لقوائم الأسعار
    path('api/price-lists/family/<int:family_id>/prices/', vpl.api_get_family_prices, name='api_family_prices'),
    path('api/price-lists/calculate/', vpl.api_calculate_price, name='api_price_list_calculate'),
    path('api/price-lists/bulk-update/', vpl.api_bulk_update_prices, name='api_bulk_update_prices'),
    path('api/calculate-product-cost/<int:product_id>/', vpl.api_calculate_product_cost, name='api_calculate_product_cost'),
    path('api/create-category/', vpl.api_create_category, name='api_create_category'),
]
