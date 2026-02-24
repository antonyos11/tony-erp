from django.urls import path
from . import views

app_name = 'woocommerce_integration'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Configuration
    path('config/', views.config_list, name='config_list'),
    path('config/create/', views.config_create, name='config_create'),
    path('config/<int:pk>/edit/', views.config_edit, name='config_edit'),
    path('config/<int:pk>/test/', views.test_connection, name='test_connection'),
    
    # Manual Sync
    path('sync/products/push/', views.sync_products_push, name='sync_products_push'),
    path('sync/products/pull/', views.sync_products_pull, name='sync_products_pull'),
    path('sync/inventory/', views.sync_inventory, name='sync_inventory'),
    path('sync/orders/', views.sync_orders, name='sync_orders'),
    path('sync/customers/', views.sync_customers, name='sync_customers'),
    
    # Mappings
    path('mappings/products/', views.product_mappings, name='product_mappings'),
    path('mappings/orders/', views.order_mappings, name='order_mappings'),
    path('mappings/customers/', views.customer_mappings, name='customer_mappings'),
    
    # Logs
    path('logs/', views.sync_logs, name='sync_logs'),
]
