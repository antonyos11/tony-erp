"""
URLs تطبيق المشتريات — RITA ERP
"""
from django.urls import path
from apps.purchases import views

app_name = 'purchases'

urlpatterns = [
    # الموردون
    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/create/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('suppliers/<int:pk>/', views.SupplierDetailView.as_view(), name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier_update'),
    path('suppliers/<int:pk>/statement/', views.SupplierStatementView.as_view(), name='supplier_statement'),

    # أوامر الشراء
    path('orders/', views.PurchaseOrderListView.as_view(), name='order_list'),
    path('orders/create/', views.PurchaseOrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/edit/', views.PurchaseOrderUpdateView.as_view(), name='order_update'),
    path('orders/<int:pk>/cancel/', views.PurchaseOrderCancelView.as_view(), name='order_cancel'),
    path('orders/<int:pk>/receive/', views.ReceivePurchaseView.as_view(), name='order_receive'),
    path('orders/<int:pk>/print/', views.PurchaseOrderPrintView.as_view(), name='order_print'),

    # إضافة سريعة (AJAX)
    path('suppliers/quick-add/', views.quick_add_supplier, name='quick_add_supplier'),
]
