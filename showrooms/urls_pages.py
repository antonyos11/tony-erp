from django.urls import path
from . import views_pages

app_name = 'showrooms'

urlpatterns = [
    # Main pages
    path('', views_pages.showroom_list_view, name='list'),
    path('dashboard/', views_pages.showroom_dashboard_view, name='dashboard'),
    path('create/', views_pages.showroom_create_view, name='create'),
    path('<int:pk>/', views_pages.showroom_detail_view, name='detail'),
    path('edit/<int:pk>/', views_pages.showroom_edit_view, name='edit'),
    path('delete/<int:pk>/', views_pages.showroom_delete_view, name='delete'),
    path('<int:pk>/delete/', views_pages.showroom_delete_view, name='delete_alt'),
    
    # Employees
    path('employees/', views_pages.showroom_employees_v2_view, name='employees'),
    path('employees/v2/', views_pages.showroom_employees_v2_view, name='employees_v2'),
    path('employees/add/', views_pages.employee_add_view, name='employee_add'),
    path('employees/<int:pk>/toggle/', views_pages.employee_toggle_view, name='employee_toggle'),
    path('employees/<int:pk>/delete/', views_pages.employee_delete_view, name='employee_delete'),
    
    # Devices
    path('<int:pk>/devices/', views_pages.showroom_devices_view, name='devices'),
    path('<int:showroom_id>/devices/add/', views_pages.device_add_view, name='device_add'),
    path('device/<int:pk>/toggle/', views_pages.device_toggle_view, name='device_toggle'),
    path('device/<int:pk>/delete/', views_pages.device_delete_view, name='device_delete'),
    path('device/<int:pk>/regenerate-key/', views_pages.device_regenerate_key_view, name='device_regenerate_key'),
    
    # Transfer
    path('<int:pk>/transfer/', views_pages.showroom_transfer_view, name='transfer'),
    
    # Expenses
    path('<int:pk>/expense/add/', views_pages.showroom_expense_add_view, name='expense_add'),
    
    # Reports
    path('kpis/', views_pages.showroom_kpis_view, name='kpis'),
    path('pnl/', views_pages.showroom_pnl_view, name='pnl'),
    
    # Alias URLs for menu compatibility
    path('showroom-list/', views_pages.showroom_list_view, name='showroom_list'),
    path('showroom-create/', views_pages.showroom_create_view, name='showroom_create'),
    path('active/', views_pages.showroom_list_view, name='active_showroom'),
    path('employee-list/', views_pages.showroom_employees_v2_view, name='employee_list'),
    path('employee-create/', views_pages.showroom_employees_v2_view, name='employee_create'),
    path('employee-permissions/', views_pages.showroom_employees_v2_view, name='employee_permissions'),
    
    # ==========================================
    # البحث عن المنتجات في المعارض الأخرى
    # ==========================================
    path('product-search/', views_pages.product_availability_search, name='product_search'),
    path('product-availability/', views_pages.product_availability_search, name='product_availability'),
    path('api/product-availability/', views_pages.product_availability_api, name='product_availability_api'),
    
    # ==========================================
    # تحويل الأموال بين المعارض
    # ==========================================
    path('money-transfers/', views_pages.money_transfer_list, name='money_transfer_list'),
    path('money-transfers/create/', views_pages.money_transfer_create, name='money_transfer_create'),
    path('money-transfers/<int:pk>/', views_pages.money_transfer_detail, name='money_transfer_detail'),
    path('money-transfers/<int:pk>/<str:action>/', views_pages.money_transfer_action, name='money_transfer_action'),
    path('money-transfers/<int:pk>/print/', views_pages.money_transfer_print, name='money_transfer_print'),
    
    # ==========================================
    # طلبات نقل المخزون بين المعارض
    # ==========================================
    path('stock-requests/', views_pages.stock_request_list, name='stock_request_list'),
    path('stock-requests/create/', views_pages.stock_request_create, name='stock_request_create'),
    path('stock-requests/from-search/', views_pages.stock_request_from_search, name='stock_request_from_search'),
    path('stock-requests/<int:pk>/', views_pages.stock_request_detail, name='stock_request_detail'),
    path('stock-requests/<int:pk>/<str:action>/', views_pages.stock_request_action, name='stock_request_action'),
    
    # ==========================================
    # إدارة ملكية المعارض
    # ==========================================
    path('property-management/', views_pages.property_management_view, name='property_management'),
    
    # العمالة المؤقتة
    path('temporary-workers/', views_pages.temporary_workers_list, name='temporary_workers'),
    path('temporary-workers/create/', views_pages.temporary_worker_create, name='temporary_worker_create'),
    path('temporary-workers/<int:pk>/', views_pages.temporary_worker_detail, name='temporary_worker_detail'),
    path('temporary-workers/<int:pk>/pay/', views_pages.temporary_worker_pay, name='temporary_worker_pay'),
    
    # دفعات الإيجار
    path('rent-payments/', views_pages.rent_payments_list, name='rent_payments'),
    path('rent-payments/create/', views_pages.rent_payment_create, name='rent_payment_create'),
    path('rent-payments/<int:pk>/pay/', views_pages.rent_payment_pay, name='rent_payment_pay'),
    path('rent-payments/auto-generate/<int:showroom_id>/', views_pages.auto_generate_rent_payments, name='auto_generate_rent_payments'),
]

# --- Stub URL patterns (auto-generated) ---
from core.views_stub import stub_view  # noqa: E402
urlpatterns += [
    path('devices/add-quick/', stub_view, name='add_device'),
    path('employees/add-quick/', stub_view, name='add_employee'),
    path('attendance/', stub_view, name='attendance'),
]
