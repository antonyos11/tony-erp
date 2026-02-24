from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views_advanced
from . import views_discount
from . import api_views

# DRF REST API Router
purchases_api_router = DefaultRouter()
purchases_api_router.register(r'suppliers', api_views.SupplierViewSet, basename='api-suppliers')
purchases_api_router.register(r'orders', api_views.PurchaseOrderViewSet, basename='api-orders')
purchases_api_router.register(r'bills', api_views.PurchaseBillViewSet, basename='api-bills')

app_name = 'purchases'

urlpatterns = [
    path('', views.purchase_list, name='purchase_list'),
    path('new/', views.purchase_create, name='purchase_create'),
    # Aliases using 'invoices' terminology for consistency (optional)
    path('invoices/', views.purchase_list, name='purchase_list_invoices_alias'),
    path('invoices/', views.purchase_list, name='invoice_list'),  # Alias
    path('invoices/new/', views.purchase_create, name='purchase_create_invoices_alias'),
    # Purchase Returns start (select bill)
    path('returns/new/', views.purchase_return_start, name='purchase_return_start'),
    path('<int:pk>/', views.purchase_detail, name='purchase_detail'),
    path('<int:pk>/print/', views.purchase_print, name='purchase_print'),
    path('<int:pk>/delete/', views.purchase_delete, name='purchase_delete'),
    path('<int:pk>/edit/', views.purchase_edit, name='purchase_edit'),
    path('<int:pk>/post/', views.purchase_post, name='purchase_post'),
    # Supplier payment
    path('supplier/<int:supplier_id>/payment/new/', views.supplier_payment_create, name='supplier_payment_create'),
    path('bills/<int:bill_id>/payment/new/', views.supplier_payment_create, name='bill_supplier_payment_create'),
    # Generic supplier payment entry point used by navigation (select supplier then redirect)
    path('payments/new/', views.supplier_payment_new_entry, name='supplier_payment_new'),
    # Purchase returns
    path('bills/<int:bill_id>/return/', views.purchase_return_create, name='purchase_return_create'),
    path('returns/<int:pk>/', views.purchase_return_detail, name='purchase_return_detail'),
    path('returns/<int:pk>/print/', views.purchase_return_print, name='purchase_return_print'),
    # Purchase Orders
    path('orders/', views.po_list, name='po_list'),
    path('orders/from-inventory/', views.po_from_inventory, name='po_from_inventory'),
    path('orders/new/', views.po_create, name='po_create'),
    path('orders/<int:pk>/', views.po_detail, name='po_detail'),
    path('orders/<int:pk>/edit/', views.po_detail, name='po_edit'),  # Alias
    path('orders/<int:pk>/print/', views.po_receive, name='po_print'),  # Alias
    path('orders/<int:pk>/receive/', views.po_receive, name='po_receive'),
    path('orders/<int:pk>/confirm/', views.po_confirm, name='po_confirm'),
    path('orders/<int:pk>/approve/', views.po_confirm, name='po_approve'),  # Alias
    path('orders/<int:pk>/to-bill/', views.po_to_bill, name='po_to_bill'),
    path('orders/attention/list/', views.po_attention, name='po_attention'),
    # Vendors (Suppliers) statement
    path('vendors/statement/', views.vendors_statement, name='vendors_statement'),
    path('vendors/balances/', views.vendors_balances, name='vendors_balances'),
    path('vendors/statement', views.vendors_statement),  # دعم بدون سلاش
    path('vendors/balances', views.vendors_balances),  # دعم بدون سلاش
    
    # =============================
    # طلبات الشراء (PR)
    # =============================
    path('requests/', views_advanced.purchase_request_list, name='pr_list'),
    path('requests/new/', views_advanced.purchase_request_create, name='pr_create'),
    path('requests/<int:pk>/', views_advanced.purchase_request_detail, name='pr_detail'),
    path('requests/<int:pk>/approve/', views_advanced.purchase_request_approve, name='pr_approve'),
    path('requests/<int:pk>/to-po/', views_advanced.purchase_request_to_po, name='pr_to_po'),
    path('requests/warehouse/', views_advanced.warehouse_purchase_requests, name='warehouse_purchase_requests'),
    
    # =============================
    # طلب عروض أسعار (RFQ)
    # =============================
    path('rfq/', views_advanced.rfq_list, name='rfq_list'),
    path('rfq/new/', views_advanced.rfq_create, name='rfq_create'),
    path('rfq/<int:pk>/', views_advanced.rfq_detail, name='rfq_detail'),
    path('rfq/<int:pk>/edit/', views_advanced.rfq_edit, name='rfq_edit'),
    path('rfq/<int:pk>/send/', views_advanced.rfq_send, name='rfq_send'),

    # =============================
    # عروض الموردين
    # =============================
    path('quotations/', views_advanced.quotation_list, name='quotation_list'),
    path('rfq/<int:rfq_id>/quotation/new/', views_advanced.quotation_create, name='quotation_create'),
    path('quotations/<int:pk>/', views_advanced.quotation_detail, name='quotation_detail'),
    path('rfq/<int:rfq_id>/quotations/compare/', views_advanced.quotation_compare, name='quotation_compare'),
    
    # =============================
    # السجل التاريخي للأسعار
    # =============================
    path('products/<int:product_id>/price-history/', views_advanced.product_price_history, name='product_price_history'),
    path('price-comparison/', views_advanced.price_comparison_report, name='price_comparison'),

    # =============================
    # أسعار المواد الخام لكل مورد
    # =============================
    path('material-prices/', views.supplier_material_prices, name='supplier_material_prices'),
    path('material-prices/add/', views.supplier_price_create, name='supplier_price_create'),
    path('material-prices/<int:pk>/edit/', views.supplier_price_edit, name='supplier_price_edit'),
    path('material-prices/<int:pk>/delete/', views.supplier_price_delete, name='supplier_price_delete'),
    path('material-prices/api/supplier-materials/', views.api_supplier_materials, name='api_supplier_materials'),
    
    # =============================
    # جدول التسليم والشحنات
    # =============================
    path('shipments/', views_advanced.shipment_list, name='shipment_list'),
    path('orders/<int:po_id>/shipment/new/', views_advanced.shipment_create, name='shipment_create'),
    path('shipments/<int:pk>/', views_advanced.shipment_detail, name='shipment_detail'),
    path('shipments/<int:pk>/track/', views_advanced.shipment_track, name='shipment_track'),
    
    # =============================
    # استلام الواردات
    # =============================
    path('receipts/', views_advanced.goods_receipt_list, name='receipt_list'),
    path('orders/<int:po_id>/receipt/new/', views_advanced.goods_receipt_create, name='receipt_create'),
    path('receipts/<int:pk>/', views_advanced.goods_receipt_detail, name='receipt_detail'),
    path('receipts/<int:pk>/inspect/', views_advanced.goods_receipt_inspect, name='receipt_inspect'),
    
    # =============================
    # تقارير متقدمة
    # =============================
    path('reports/supplier-performance/', views_advanced.supplier_performance_report, name='supplier_performance'),
    path('reports/attention/', views_advanced.purchasing_attention, name='purchasing_attention'),
    path('reports/analytics/', views_advanced.purchasing_analytics, name='purchasing_analytics'),
    
    # =============================
    # URLs إضافية لطلبات الشراء
    # =============================
    path('requests/<int:pk>/edit/', views_advanced.purchase_request_edit, name='pr_edit'),
    path('requests/<int:pk>/reject/', views_advanced.purchase_request_reject, name='pr_reject'),
    path('price-history/', views_advanced.price_history_list, name='price_history_list'),
    
    # =============================
    # خصم مكتسب (إشعار دائن) - Supplier Discount Notes
    # =============================
    path('sup-discount/', views_discount.supplier_discount_list, name='supplier_discount_list'),
    path('sup-discount/new/', views_discount.supplier_discount_create, name='supplier_discount_create'),
    path('sup-discount/<int:pk>/', views_discount.supplier_discount_detail, name='supplier_discount_detail'),
    path('sup-discount/<int:pk>/edit/', views_discount.supplier_discount_edit, name='supplier_discount_edit'),
    path('sup-discount/<int:pk>/post/', views_discount.supplier_discount_post, name='supplier_discount_post'),
    path('sup-discount/<int:pk>/cancel/', views_discount.supplier_discount_cancel, name='supplier_discount_cancel'),
    path('sup-discount/ajax/bills/', views_discount.supplier_bills_ajax, name='supplier_bills_ajax'),
    path('sup-discount/ajax/balance/', views_discount.supplier_balance_ajax, name='supplier_balance_ajax'),
]
# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('create-po-from-quotation/', stub_view, name='create_po_from_quotation'),
    path('po-send-reminder/', stub_view, name='po_send_reminder'),
    path('pr-add-review-note/', stub_view, name='pr_add_review_note'),
    path('pr-to-rfq/', stub_view, name='pr_to_rfq'),
    path('quotation-edit/<int:pk>/', stub_view, name='quotation_edit'),
    path('receipt-edit/<int:pk>/', stub_view, name='receipt_edit'),
    path('receipt-print/<int:pk>/', stub_view, name='receipt_print'),
    path('shipment-edit/<int:pk>/', stub_view, name='shipment_edit'),
]

# REST API v1 endpoints
urlpatterns += [
    path('api/v1/', include(purchases_api_router.urls)),
]
