# quick/urls.py
from django.urls import path
from . import views

app_name = 'quick'

urlpatterns = [
    # الصفحة الرئيسية للعمليات الجماعية
    path('bulk-actions/', views.bulk_actions_dashboard, name='bulk_actions'),
    
    # تحديث الأسعار
    path('bulk-actions/update-prices/', views.bulk_update_prices, name='bulk_update_prices'),
    
    # تحديث المخزون
    path('bulk-actions/update-inventory/', views.bulk_update_inventory, name='bulk_update_inventory'),
    
    # إرسال بريد إلكتروني جماعي
    path('bulk-actions/send-email/', views.bulk_send_email, name='bulk_send_email'),
    
    # حذف جماعي
    path('bulk-actions/bulk-delete/', views.bulk_delete, name='bulk_delete'),
    
    # تصدير البيانات
    path('bulk-actions/export-data/', views.export_data, name='export_data'),
    
    # API endpoints للعمليات
    path('api/bulk-update-prices/', views.api_bulk_update_prices, name='api_bulk_update_prices'),
    path('api/bulk-update-inventory/', views.api_bulk_update_inventory, name='api_bulk_update_inventory'),
    path('api/bulk-send-email/', views.api_bulk_send_email, name='api_bulk_send_email'),
    path('api/bulk-delete/', views.api_bulk_delete, name='api_bulk_delete'),
    path('api/export-data/', views.api_export_data, name='api_export_data'),
]
