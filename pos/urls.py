from django.urls import path
from . import views
from . import views_enhanced
from . import views_remote_print
from .api_views import POSOrderCreateAPIView, POSOrderListAPIView

app_name = 'pos'

urlpatterns = [
    # REST API endpoints
    path('api/orders/create/', POSOrderCreateAPIView.as_view(), name='api_order_create'),
    path('api/orders/', POSOrderListAPIView.as_view(), name='api_order_list'),
    
    path('', views.dashboard, name='dashboard'),
    path('test-enhancements/', views.test_enhancements, name='test_enhancements'),
    path('session/open/', views.open_session, name='open_session'),
    path('session/<int:session_id>/close/', views.close_session, name='close_session'),
    path('order/new/', views.new_order, name='new_order'),
    path('order/<int:order_id>/add-line/', views.add_line, name='add_line'),
    path('order/<int:order_id>/line/<int:line_id>/delete/', views.delete_line, name='delete_line'),
    path('order/<int:order_id>/line/<int:line_id>/update-qty/', views.update_line_qty, name='update_line_qty'),
    path('order/<int:order_id>/pay/', views.pay_order, name='pay_order'),
    path('order/<int:order_id>/receipt/', views.receipt, name='receipt'),
    path('printer-test/', views.printer_test, name='printer_test'),
    path('api/product-lookup/', views.product_lookup_api, name='product_lookup_api'),
    
    # الصفحات الإضافية
    path('tables/', views.tables, name='tables'),
    path('tables/action/<int:table_id>/', views.table_action, name='table_action'),
    path('tables/save/', views.table_save, name='table_save'),
    path('tables/delete/<int:table_id>/', views.table_delete, name='table_delete'),
    path('shifts/', views.shifts, name='shifts'),
    path('sales-details/', views.sales_details, name='sales_details'),
    path('cashier-report/', views.cashier_report, name='cashier_report'),
    path('deleted-items/', views.deleted_items, name='deleted_items'),
    path('printer-settings/', views.printer_settings, name='printer_settings'),
    path('add-expense/', views.add_expense, name='add_expense'),
    
    # التقسيط
    path('order/<int:order_id>/installment/create/', views.create_installment, name='create_installment'),
    path('api/installment/calculate/', views.calculate_installment_api, name='calculate_installment_api'),
    path('api/installment/plans/', views.installment_plans_api, name='installment_plans_api'),
    path('installments/', views.installments_list, name='installments_list'),
    path('installment/<int:plan_id>/', views.installment_detail, name='installment_detail'),
    path('installment/<int:plan_id>/pay/<int:installment_id>/', views.pay_installment, name='pay_installment'),
    path('installment/<int:plan_id>/print/', views.print_installment_contract, name='print_installment_contract'),
    
    # تسديد أقساط العملاء من POS
    path('api/customer-installments/', views.customer_installments_api, name='customer_installments_api'),
    path('api/pay-installment/', views.pay_customer_installment, name='pay_customer_installment'),
    path('installment-receipt/<int:installment_id>/', views.installment_payment_receipt, name='installment_payment_receipt'),
    
    # تحديث الحالة والخصم
    path('order/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('order/<int:order_id>/apply-discount/', views.apply_discount, name='apply_discount'),
    path('order/<int:order_id>/remove-discount/', views.remove_discount, name='remove_discount'),
    path('order/<int:order_id>/quote-print/', views.quote_print, name='quote_print'),
    path('order/<int:order_id>/update-taxes/', views.update_order_taxes, name='update_order_taxes'),
    
    # الطباعة الحرارية المباشرة XPrinter
    path('order/<int:order_id>/direct-print/', views.direct_print, name='direct_print'),
    path('printer/test/', views.printer_test, name='printer_test'),
    path('printer/setup/', views.qz_setup, name='qz_setup'),
    
    # طباعة فاتورة A4 - طابعات HP وغيرها
    path('order/<int:order_id>/invoice-a4/', views.invoice_a4, name='invoice_a4'),
    path('printers/a4/', views.a4_printers_list, name='a4_printers_list'),
    
    # =========== الميزات المحسنة ===========
    # الطلبات المعلقة
    path('api/hold-order/', views_enhanced.hold_order, name='hold_order'),
    path('api/held-orders/', views_enhanced.list_held_orders, name='list_held_orders'),
    path('api/held-order/<int:hold_id>/', views_enhanced.get_held_order, name='get_held_order'),
    path('api/held-order/<int:hold_id>/restore/', views_enhanced.restore_held_order, name='restore_held_order'),
    path('api/held-order/<int:hold_id>/delete/', views_enhanced.delete_held_order, name='delete_held_order'),
    
    # المنتجات المفضلة
    path('api/toggle-favorite/', views_enhanced.toggle_favorite, name='toggle_favorite'),
    path('api/favorites/', views_enhanced.list_favorites, name='list_favorites'),
    
    # الأكثر مبيعاً
    path('api/top-selling/', views_enhanced.top_selling, name='top_selling'),
    path('api/recent-products/', views_enhanced.recent_products, name='recent_products'),
    
    # تعديلات السلة السريعة
    path('order/<int:order_id>/line/<int:line_id>/price/', views_enhanced.quick_price_change, name='quick_price_change'),
    path('order/<int:order_id>/line/<int:line_id>/discount/', views_enhanced.quick_line_discount, name='quick_line_discount'),
    path('order/<int:order_id>/line/<int:line_id>/quantity/', views_enhanced.update_line_quantity, name='update_line_quantity'),
    
    # أزرار الدفع السريع واختصارات لوحة المفاتيح
    path('api/quick-amounts/', views_enhanced.quick_amounts, name='quick_amounts'),
    path('api/keyboard-shortcuts/', views_enhanced.keyboard_shortcuts, name='keyboard_shortcuts'),
    
    # إتمام الطلب والدفع
    path('api/complete-order/', views_enhanced.complete_order, name='complete_order'),
    path('api/create-installment/', views_enhanced.create_installment_order, name='create_installment_order'),
    
    # الطباعة الحرارية المباشرة
    path('api/print-thermal/<int:order_id>/', views_enhanced.print_thermal_receipt, name='print_thermal_receipt'),
    
    # الطباعة عن بُعد على الطابعة المحلية (XPrinter)
    path('api/receipt-data/<int:order_id>/', views_remote_print.generate_receipt_data, name='generate_receipt_data'),
    
    # =========== إدارة الطابعات ===========
    path('api/printers/', views.list_printers_api, name='list_printers_api'),
    path('api/printer/test/', views.test_printer_api, name='test_printer_api'),
    path('api/printer/print-barcode/', views.print_barcode_api, name='print_barcode_api'),
    path('api/printer/status/', views.printer_status_api, name='printer_status_api'),
]

# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('reservations/', stub_view, name='reservations'),
    path('reserve-table/', stub_view, name='reserve_table'),
    path('table-create/', stub_view, name='table_create'),
    path('view-order/<int:pk>/', stub_view, name='view_order'),
]
