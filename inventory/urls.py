from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views_analytics
from . import views_reports
from . import views_conversions
from . import api_views

# DRF REST API Router
api_router = DefaultRouter()
api_router.register(r'products', api_views.ProductViewSet, basename='api-products')
api_router.register(r'categories', api_views.CategoryViewSet, basename='api-categories')
api_router.register(r'locations', api_views.LocationViewSet, basename='api-locations')
api_router.register(r'stock', api_views.StockViewSet, basename='api-stock')

app_name = 'inventory'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('dashboard/', views.inventory_dashboard, name='dashboard'),
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/create/', views.product_add, name='product_create'),  # Alias for product_create
    path('create/', views.product_add, name='inventory_create'),  # Additional alias for /inventory/create/
    path('products/raw-materials/', views.raw_material_list, name='raw_material_list'),  # قائمة المواد الخام
    path('products/raw-material/create/', views.raw_material_create, name='raw_material_create'),  # إضافة مادة خام
    path('products/raw-material/<int:pk>/edit/', views.raw_material_edit, name='raw_material_edit'),  # تعديل مادة خام
    path('products/raw-material/<int:pk>/quick-price/', views.raw_material_quick_price, name='raw_material_quick_price'),  # تعديل سريع للسعر
    path('products/raw-materials/bulk-price-update/', views.raw_material_bulk_price_update, name='raw_material_bulk_price_update'),  # تحديث جماعي للأسعار
    path('products/<int:product_id>/supplier-prices/', views.supplier_prices_view, name='supplier_prices'),  # أسعار الموردين
    path('products/<int:product_id>/supplier-prices/add/', views.supplier_price_add, name='supplier_price_add'),  # إضافة سعر مورد
    path('supplier-price/<int:price_id>/set-preferred/', views.supplier_price_set_preferred, name='supplier_price_set_preferred'),  # تعيين مورد مفضل
    path('api/supplier/<int:supplier_id>/products/', views.api_supplier_products, name='api_supplier_products'),  # API: منتجات المورد
    path('api/supplier/<int:supplier_id>/materials/', views.api_supplier_materials, name='api_supplier_materials'),  # API: مواد المورد الخام
    path('api/supplier/<int:supplier_id>/price-info/', views.api_supplier_price_info, name='api_supplier_price_info'),  # API: بيانات سعر المورد
    path('products/<int:product_id>/print-barcode/', views.print_product_barcode, name='print_product_barcode'),  # طباعة الباركود
    path('products/<int:product_id>/print-zebra/', views.print_barcode_zebra_api, name='print_barcode_zebra_api'),  # API: طباعة Zebra
    path('api/printer-config/', views.printer_config_api, name='printer_config_api'),  # API: إعدادات الطابعات
    path('products/import/', views.product_list, name='product_import'),  # TODO: implement import
    path('products/<int:pk>/', views.product_edit, name='product_detail'),  # Alias for detail
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('products/<int:pk>/duplicate/', views.product_duplicate, name='product_duplicate'),  # نسخ منتج
    path('products/<int:pk>/save-as-template/', views.save_product_as_template, name='save_product_as_template'),  # حفظ كقالب
    
    # استيراد من Excel/CSV
    path('products/bulk-import/', views.bulk_import_products, name='bulk_import_products'),
    path('products/download-template/', views.download_import_template, name='download_import_template'),
    
    # قوالب المنتجات
    path('templates/', views.product_template_list, name='product_template_list'),
    path('templates/create/', views.product_template_create, name='product_template_create'),
    path('templates/<int:pk>/edit/', views.product_template_edit, name='product_template_edit'),
    path('templates/<int:pk>/delete/', views.product_template_delete, name='product_template_delete'),
    path('templates/<int:template_id>/use/', views.product_add_from_template, name='product_add_from_template'),
    
    path('stock/', views.stock_management, name='stock_management'),
    path('stock/add/', views.stock_add, name='stock_add'),  # إضافة كمية للمخزون
    path('stock/summary/', views.warehouse_summary, name='warehouse_summary'),
    path('stock/adjust/', views.stock_adjust, name='stock_adjust'),
    path('locations/', views.location_list, name='location_list'),
    path('locations/types/', views.warehouse_types_view, name='warehouse_types'),
    path('locations/add/', views.location_add, name='location_add'),
    path('locations/<int:pk>/edit/', views.location_edit, name='location_edit'),
    path('locations/<int:pk>/delete/', views.location_delete, name='location_delete'),
    path('locations/add-inline/', views.location_add_inline, name='location_add_inline'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/json/', views.category_list_json, name='category_list_json'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('categories/add-inline/', views.category_add_inline, name='category_add_inline'),
    path('api/categories/create/', views.api_category_create, name='api_category_create'),  # API: إضافة فئة (JSON)
    
    # التحويلات المخزنية
    path('transfers/', views.transfer_list, name='transfer_list'),
    path('transfers/new/', views.transfer_create, name='transfer_create'),
    path('transfers/<int:pk>/', views.transfer_detail, name='transfer_detail'),
    path('transfers/<int:pk>/edit/', views.transfer_detail, name='transfer_edit'),  # Alias
    path('transfers/<int:pk>/submit/', views.transfer_submit, name='transfer_submit'),
    path('transfers/<int:pk>/confirm/', views.transfer_confirm, name='transfer_confirm'),

    # الاستلام
    path('receiving/', views.receiving_list, name='receiving_list'),
    path('receiving/new/', views.receiving_create, name='receiving_create'),
    path('receiving/<int:pk>/', views.receiving_detail, name='receiving_detail'),
    path('receiving/<int:pk>/edit/', views.receiving_detail, name='receiving_edit'),  # Alias
    path('receiving/<int:pk>/confirm/', views.receiving_confirm, name='receiving_confirm'),

    # الصرف
    path('issue/', views.issue_list, name='issue_list'),
    path('issue/new/', views.issue_create, name='issue_create'),
    path('issue/<int:pk>/', views.issue_detail, name='issue_detail'),
    path('issue/<int:pk>/edit/', views.issue_detail, name='issue_edit'),  # Alias
    path('issue/<int:pk>/items/<int:item_id>/delete/', views.issue_item_delete, name='issue_item_delete'),
    path('issue/<int:pk>/confirm/', views.issue_confirm, name='issue_confirm'),
    path('issue/<int:pk>/print/', views.issue_print, name='issue_print'),

    # طلبات خامات (Requisitions)
    path('requisition/', views.requisition_list, name='requisition_list'),
    path('requisition/create/', views.requisition_create, name='requisition_create'),
    path('requisition/<int:pk>/', views.requisition_detail, name='requisition_detail'),
    path('requisition/<int:pk>/edit/', views.requisition_detail, name='requisition_edit'),  # Alias
    path('requisition/<int:pk>/delete/', views.requisition_delete, name='requisition_delete'),
    path('requisition/<int:pk>/submit/', views.requisition_submit, name='requisition_submit'),
    path('requisition/<int:pk>/approve/', views.requisition_approve, name='requisition_approve'),
    path('requisition/<int:pk>/convert-to-issue/', views.requisition_convert_to_issue, name='requisition_convert_to_issue'),
    path('requisition/<int:pk>/convert-to-po/', views.requisition_convert_to_po, name='requisition_convert_to_po'),
    path('requisition/<int:pk>/print/', views.requisition_print, name='requisition_print'),

    # الجرد
    path('count/', views.count_list, name='count_list'),
    path('count/new/', views.count_create, name='count_create'),
    path('count/<int:pk>/', views.count_detail, name='count_detail'),
    path('count/<int:pk>/edit/', views.count_detail, name='count_edit'),  # Alias
    path('count/<int:pk>/apply/', views.count_apply, name='count_apply'),
    path('count/<int:pk>/scan-barcode/', views.count_scan_barcode, name='count_scan_barcode'),
    
    # نظام الباركود
    path('barcode/', views.barcode_management, name='barcode_management'),
    path('barcode/scanner/', views.barcode_scanner, name='barcode_scanner'),
    path('barcode/search/', views.search_by_barcode, name='search_by_barcode'),
    path('barcode/generate-missing/', views.generate_missing_barcodes, name='generate_missing_barcodes'),
    path('barcode/<int:product_id>/image/', views.generate_barcode_image, name='generate_barcode_image'),
    path('barcode/<int:product_id>/regenerate/', views.regenerate_barcode, name='regenerate_barcode'),
    
    # ملصقات المنتجات
    path('product/<int:product_id>/label/', views.product_label, name='product_label'),
    path('product/<int:product_id>/qr-code/', views.generate_qr_code, name='generate_qr_code'),
    path('labels/batch/', views.batch_labels, name='batch_labels'),
    path('labels/select/', views.batch_labels, name='select_products_for_labels'),  # Alias
    
    # API للباركود
    path('api/barcode/lookup/', views.barcode_lookup_api, name='barcode_lookup_api'),

    # تقارير المخزون
    path('reports/valuation/', views.valuation_report, name='valuation_report'),
    path('reports/aging/', views.aging_report, name='aging_report'),
    path('reports/by-supplier/', views.stock_by_supplier_report, name='stock_by_supplier_report'),
    
    # المراقبة المتقدمة والإشعارات
    path('low-stock/', views.low_stock_dashboard, name='low_stock_dashboard'),
    path('analytics/', views.advanced_stock_analytics, name='advanced_analytics'),
    path('locations/analytics/', views.location_analytics, name='location_analytics'),
    
    # الدورة المستندية الكاملة
    path('document-cycle/', views.document_cycle_view, name='document_cycle'),
    
    # APIs للتحديث المباشر
    path('api/notifications/', views.inventory_notifications_api, name='notifications_api'),
    path('api/stock/<int:product_id>/', views.real_time_stock_update, name='real_time_stock_update'),
    
    # تحليلات المخزون المتقدم (Advanced Inventory Analytics)
    path('analytics/dashboard/', views_analytics.inventory_analytics_dashboard, name='inventory_analytics_dashboard'),
    path('analytics/stock-aging/', views_analytics.stock_aging_report, name='stock_aging_report'),
    path('analytics/abc-analysis/', views_analytics.abc_analysis_report, name='abc_analysis_report'),
    path('analytics/reorder-point/', views_analytics.reorder_point_analysis, name='reorder_point_analysis'),
    path('analytics/turnover/', views_analytics.inventory_turnover_report, name='inventory_turnover_report'),
    path('analytics/dead-stock/', views_analytics.dead_stock_report, name='dead_stock_report'),
    path('analytics/product/<int:product_id>/', views_analytics.product_analytics_detail, name='product_analytics_detail'),
    path('analytics/stock-valuation/', views_analytics.stock_valuation_report, name='stock_valuation_report'),
    
    # تصدير CSV
    path('analytics/export/abc-csv/', views_analytics.export_abc_analysis_csv, name='export_abc_analysis_csv'),
    path('analytics/export/dead-stock-csv/', views_analytics.export_dead_stock_csv, name='export_dead_stock_csv'),
    
    # AJAX APIs
    path('analytics/api/reorder-point/<int:product_id>/', views_analytics.reorder_point_ajax, name='reorder_point_ajax'),
    
    # كتالوج المنتجات - Product Catalog
    path('catalog/', views.catalog_list, name='catalog_list'),
    path('catalog/print/', views.catalog_print, name='catalog_print'),
    path('catalog/settings/', views.catalog_settings, name='catalog_settings'),
    path('catalog/product/<int:pk>/', views.catalog_product_detail, name='catalog_product_detail'),
    path('catalog/category/<int:category_id>/', views.catalog_by_category, name='catalog_by_category'),
    
    # =============================
    # قوائم المواد (BOM)
    # =============================
    path('bom/', views.bom_list, name='bom_list'),
    path('bom/create/', views.bom_create, name='bom_create'),
    path('bom/<int:pk>/', views.bom_detail, name='bom_detail'),
    path('bom/<int:pk>/edit/', views.bom_edit, name='bom_edit'),
    path('bom/<int:pk>/add-item/', views.bom_add_item, name='bom_add_item'),
    path('bom/<int:pk>/delete-item/<int:item_pk>/', views.bom_delete_item, name='bom_delete_item'),
    
    # =============================
    # تقارير الأسعار والتكاليف
    # =============================
    path('reports/price-history/', views_reports.price_history_list, name='price_history_list'),
    path('reports/price-impact/', views_reports.price_impact_analysis, name='price_impact_analysis'),
    path('reports/cost-breakdown/<int:product_id>/', views_reports.product_cost_breakdown, name='product_cost_breakdown'),
    path('reports/cost-comparison/', views_reports.cost_comparison_report, name='cost_comparison_report'),
    path('reports/supplier-trends/', views_reports.supplier_price_trends, name='supplier_price_trends'),
    path('reports/supplier-trends/<int:supplier_id>/', views_reports.supplier_price_trends, name='supplier_price_trends_detail'),
    
    # إشعارات الأسعار
    path('notifications/', views_reports.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/read/', views_reports.mark_notification_read, name='mark_notification_read'),
    
    # APIs للأسعار والتكاليف
    path('api/price-change-preview/', views_reports.price_change_preview, name='price_change_preview'),
    path('api/recalculate-costs/', views_reports.api_recalculate_all_costs, name='api_recalculate_costs'),
    path('api/material/<int:material_id>/price-history/', views_reports.api_get_material_price_history, name='api_material_price_history'),
    path('api/notifications/unread-count/', views_reports.api_get_unread_notifications_count, name='api_unread_notifications'),
    
    # =============================
    # معاملات التحويل
    # =============================
    path('conversion-factors/', views_conversions.conversion_factors_list, name='conversion_factors_list'),
    path('conversion-factors/create/', views_conversions.conversion_factor_create, name='conversion_factor_create'),
    path('conversion-factors/<int:pk>/edit/', views_conversions.conversion_factor_edit, name='conversion_factor_edit'),
    path('conversion-factors/<int:pk>/delete/', views_conversions.conversion_factor_delete, name='conversion_factor_delete'),
    path('conversion-factors/load-defaults/', views_conversions.load_default_conversions, name='load_default_conversions'),
    
    # APIs لمعاملات التحويل
    path('api/conversion/get-factor/', views_conversions.api_get_conversion_factor, name='api_get_conversion_factor'),
    path('api/conversion/convert/', views_conversions.api_convert_value, name='api_convert_value'),
    path('api/conversion/available/', views_conversions.api_get_available_conversions, name='api_get_available_conversions'),
]

# --- Advanced Inventory URLs ---
from inventory import views_advanced as inv_adv  # noqa: E402

urlpatterns += [
    # تنبيهات المخزون
    path('alerts/', inv_adv.stock_alert_list, name='stock_alert_list'),
    path('alerts/create/', inv_adv.stock_alert_create, name='stock_alert_create'),
    path('alerts/<int:pk>/edit/', inv_adv.stock_alert_edit, name='stock_alert_edit'),
    path('alerts/<int:pk>/delete/', inv_adv.stock_alert_delete, name='stock_alert_delete'),

    # تتبع اللوتات
    path('lots/', inv_adv.lot_list, name='lot_list'),
    path('lots/create/', inv_adv.lot_create, name='lot_create'),
    path('lots/<int:pk>/', inv_adv.lot_detail, name='lot_detail'),
    path('lots/<int:pk>/edit/', inv_adv.lot_edit, name='lot_edit'),

    # الجرد الدوري
    path('cycle-counts/', inv_adv.cycle_count_list, name='cycle_count_list'),
    path('cycle-counts/create/', inv_adv.cycle_count_create, name='cycle_count_create'),
    path('cycle-counts/<int:pk>/', inv_adv.cycle_count_detail, name='cycle_count_detail'),
    path('cycle-counts/<int:pk>/complete/', inv_adv.cycle_count_complete, name='cycle_count_complete'),
]

# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('stock-transfer-create/', stub_view, name='stock_transfer_create'),
]

# REST API v1 endpoints
urlpatterns += [
    path('api/v1/', include(api_router.urls)),
]
