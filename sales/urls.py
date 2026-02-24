from django.urls import path, include
from . import views
from . import views_crm_analytics
from . import views_discount
from . import views_print
from . import invoice_api_views
from rest_framework.routers import DefaultRouter
from .api_views import InvoiceViewSet, InvoicePaymentViewSet, CustomerStatementViewSet, create_invoice_api

"""ملاحظة: كان تضمين الراوتر على المسار الفارغ '' قبل view الجذر يؤدي إلى ظهور واجهة DRF في /sales/
لذلك نقلنا مسارات الـ API إلى بادئة واضحة 'api/' حتى يظل /sales/ يعرض قائمة الفواتير المعتادة."""

router = DefaultRouter()
router.register('invoices', InvoiceViewSet, basename='api-invoices')
router.register('payments', InvoicePaymentViewSet, basename='api-invoice-payments')
router.register('statements', CustomerStatementViewSet, basename='api-customer-statements')

app_name = 'sales'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.sales_dashboard, name='dashboard'),
    
    # API (تم نقلها إلى sales/api/ بدلاً من الجذر)
    path('api/', include(router.urls)),
    
    # Invoice Creation API (separate endpoint for POST)
    path('api/invoices/create/', create_invoice_api, name='api_create_invoice'),
    
    # ========== Enhanced Invoice Features APIs ==========
    # Auto-save
    path('api/autosave/', invoice_api_views.autosave_invoice, name='api_autosave'),
    path('api/autosave/load/', invoice_api_views.load_autosave, name='api_load_autosave'),
    
    # Templates
    path('api/templates/', invoice_api_views.list_templates, name='api_list_templates'),
    path('api/templates/create/', invoice_api_views.create_template, name='api_create_template'),
    path('api/templates/<int:template_id>/increment/', invoice_api_views.increment_template_usage, name='api_increment_template'),
    
    # Smart Customer Search
    path('api/customers/search/', invoice_api_views.search_customers, name='api_search_customers'),
    path('api/customers/<int:customer_id>/last-transactions/', invoice_api_views.customer_last_transactions, name='api_customer_transactions'),
    path('api/customers/<int:customer_id>/credit-check/', invoice_api_views.check_credit_limit, name='api_credit_check'),
    
    # Invoice Copy & Details
    path('api/invoice/<str:invoice_number>/details/', invoice_api_views.get_invoice_details, name='api_invoice_details'),
    
    # Attachments
    path('api/attachments/upload/', invoice_api_views.upload_attachment, name='api_upload_attachment'),
    
    # History
    path('api/invoice/<int:invoice_id>/history/', invoice_api_views.invoice_history, name='api_invoice_history'),
    
    # Main routes - الآن التصميم الجديد افتراضي بدون حاجة لـ parameter
    path('', views.invoice_list, name='invoice_list'),
    path('new/', views.invoice_create, name='invoice_create'),
    path('new/enhanced/', views.invoice_create, {'template': 'enhanced'}, name='invoice_create_enhanced'),
    path('<int:pk>/', views.invoice_detail, name='invoice_detail'),
    
    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    # New Receipt (standalone payment by invoice number)
    path('receipts/new/', views.receipt_create, name='receipt_create'),
    # Sales Returns start (select invoice)
    path('returns/new/', views.sales_return_start, name='sales_return_start'),
    
    # Old Templates (للرجوع للتصميم القديم إذا لزم الأمر)
    path('old/', views.invoice_list, {'template': 'old'}, name='invoice_list_old'),
    path('old/new/', views.invoice_create, {'template': 'old'}, name='invoice_create_old'),
    path('old/<int:pk>/', views.invoice_detail, {'template': 'old'}, name='invoice_detail_old'),
    
    # Other invoice routes
    path('<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('<int:pk>/print/', views.invoice_print, name='invoice_print'),
    path('<int:pk>/direct-print/', views.invoice_direct_print_a4, name='invoice_direct_print_a4'),
    path('<int:pk>/a4-data/', views_print.sales_invoice_a4_data, name='sales_invoice_a4_data'),
    path('<int:pk>/thermal-print/', views.invoice_thermal_print, name='invoice_thermal_print'),
    path('<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    path('<int:pk>/post-accounting/', views.invoice_post_accounting, name='invoice_post_accounting'),
    # Payments (partial receipts)
    path('<int:pk>/add-payment/', views.invoice_add_payment, name='invoice_add_payment'),
    path('payments/<int:payment_id>/receipt/', views.payment_receipt_print, name='payment_receipt_print'),
    path('payments/<int:payment_id>/allocate/', views.payment_allocate, name='payment_allocate'),
    path('payments/<int:payment_id>/cancel/', views.payment_cancel, name='payment_cancel'),
    # Account statement for customer
    path('customers/<int:customer_id>/statement/', views.customer_statement, name='customer_statement'),

    # Customer statement print / PDF (named routes used by templates)
    path('customers/<int:customer_id>/statement/print/', views.customer_statement_print, name='customer_statement_print'),
    path('customers/<int:customer_id>/statement/pdf/', views.customer_statement_pdf, name='customer_statement_pdf'),

    # Sales Returns
    path('invoices/<int:invoice_id>/return/', views.sales_return_create, name='sales_return_create'),
    path('returns/<int:pk>/', views.sales_return_detail, name='sales_return_detail'),

    # New sales sections
    path('field-sales/', views.field_sales, name='field_sales'),
    path('field-sales/new/', views.field_visit_create, name='field_visit_create'),
    path('field-sales/<int:pk>/edit/', views.field_visit_edit, name='field_visit_edit'),
    
    # تتبع المندوبين والمواقع
    path('location/tracking/', views.location_tracking, name='location_tracking'),
    path('location/tracking/api/', views.tracking_api, name='tracking_api'),
    path('location/update/', views.update_location, name='update_location'),
    path('location/mobile/', views.rep_mobile_tracker, name='rep_mobile_tracker'),
    
    path('indoor-sales/', views.indoor_sales, name='indoor_sales'),
    path('key-accounts/', views.key_accounts, name='key_accounts'),
    path('ecommerce/', views.ecommerce_sales, name='ecommerce_sales'),
    path('pricing-offers/', views.pricing_offers, name='pricing_offers'),
    path('collection/', views.followup_collection, name='followup_collection'),
    path('reports/', views.sales_reporting_analytics, name='reporting_analytics'),
    path('reports/quick/', views.sales_quick_report, name='quick_report'),
    path('reports/daily/', views.sales_daily_report, name='daily_report'),
    path('coordination/', views.sales_coordination, name='coordination'),
    # Utilities / AJAX
    path('lookup/barcode/', views.product_lookup_barcode, name='product_lookup_barcode'),
    path('item/<int:item_id>/delete/', views.invoice_item_delete, name='invoice_item_delete'),
    path('ajax/item/add/<int:invoice_id>/', views.invoice_item_add_ajax, name='invoice_item_add_ajax'),
    
    # =====================
    # نظام التحليلات المتقدم للعملاء - CRM Analytics
    # =====================
    path('crm-analytics/', views_crm_analytics.crm_analytics_dashboard, name='crm_analytics_dashboard'),
    path('crm-analytics/clv/', views_crm_analytics.customer_lifetime_value_report, name='clv_report'),
    path('crm-analytics/clv/<int:customer_id>/', views_crm_analytics.customer_lifetime_value_report, name='customer_clv_detail'),
    path('crm-analytics/segmentation/', views_crm_analytics.customer_segmentation_view, name='customer_segmentation'),
    path('crm-analytics/pipeline/', views_crm_analytics.sales_pipeline_view, name='sales_pipeline'),
    path('crm-analytics/commission/', views_crm_analytics.employee_commission_report, name='commission_report'),
    path('crm-analytics/commission/<int:employee_id>/', views_crm_analytics.employee_commission_report, name='employee_commission_detail'),
    path('crm-analytics/lead-conversion/', views_crm_analytics.lead_conversion_report, name='lead_conversion_report'),
    path('crm-analytics/export-csv/', views_crm_analytics.export_customers_csv, name='export_customers_csv'),
    path('crm-analytics/ajax/customer/<int:customer_id>/', views_crm_analytics.ajax_customer_analytics, name='ajax_customer_analytics'),
    path('crm-analytics/ajax/update-visit/', views_crm_analytics.ajax_update_visit_outcome, name='ajax_update_visit_outcome'),
    
    # =====================
    # خصم مسموح به (إشعار مدين) - Customer Discount Notes
    # =====================
    path('cust-discount/', views_discount.customer_discount_list, name='customer_discount_list'),
    path('cust-discount/new/', views_discount.customer_discount_create, name='customer_discount_create'),
    path('cust-discount/<int:pk>/', views_discount.customer_discount_detail, name='customer_discount_detail'),
    path('cust-discount/<int:pk>/edit/', views_discount.customer_discount_edit, name='customer_discount_edit'),
    path('cust-discount/<int:pk>/post/', views_discount.customer_discount_post, name='customer_discount_post'),
    path('cust-discount/<int:pk>/cancel/', views_discount.customer_discount_cancel, name='customer_discount_cancel'),
    path('cust-discount/ajax/invoices/', views_discount.customer_invoices_ajax, name='customer_invoices_ajax'),
    path('cust-discount/ajax/balance/', views_discount.customer_balance_ajax, name='customer_balance_ajax'),
    
    # =====================
    # APIs البحث السريع عن العملاء وإضافة عميل جديد
    # =====================
    path('api/customers/search/', views.customer_search_api, name='customer_search_api'),
    path('api/customers/quick-create/', views.customer_quick_create_api, name='customer_quick_create_api'),
    path('api/customers/<int:customer_id>/', views.customer_details_api, name='customer_details_api'),
    
    # =====================
    # معاينة أرقام الفواتير التالية
    # =====================
    path('next-numbers/', views.next_invoice_numbers_view, name='next_invoice_numbers'),
    path('api/next-numbers/', views.next_invoice_numbers_api, name='api_next_invoice_numbers'),
]
# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('crm-report-export/', stub_view, name='crm_report_export'),
    path('ecommerce-settings/', stub_view, name='ecommerce_settings'),
    path('lead-create/', stub_view, name='lead_create'),
    path('offer-detail/<int:pk>/', stub_view, name='offer_detail'),
    path('offer-edit/<int:pk>/', stub_view, name='offer_edit'),
    path('payment-detail/<int:pk>/', stub_view, name='payment_detail'),
    path('rep-details/<int:pk>/', stub_view, name='rep_details'),
    path('sales-return-approve/<int:pk>/', stub_view, name='sales_return_approve'),
    path('sales-return-list/', stub_view, name='sales_return_list'),
    path('sales-return-print/<int:pk>/', stub_view, name='sales_return_print'),
    path('sales-return-reject/<int:pk>/', stub_view, name='sales_return_reject'),
    path('segment-create/', stub_view, name='segment_create'),
    path('task-create/', stub_view, name='task_create'),
]
