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

    # أوامر الشراء
    path('orders/', views.PurchaseOrderListView.as_view(), name='order_list'),
    path('orders/create/', views.PurchaseOrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/receive/', views.ReceivePurchaseView.as_view(), name='order_receive'),
]
