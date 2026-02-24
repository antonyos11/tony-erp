"""
مسارات URL لنظام الشحن - Tony ERP
"""

from django.urls import path
from . import views

app_name = 'shipping'

urlpatterns = [
    # لوحة التحكم
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alt'),
    
    # شركات الشحن
    path('companies/', views.company_list, name='company_list'),
    path('companies/create/', views.company_create, name='company_create'),
    path('companies/<int:pk>/', views.company_detail, name='company_detail'),
    path('companies/<int:pk>/edit/', views.company_edit, name='company_edit'),
    
    # مناطق الشحن
    path('zones/', views.zone_list, name='zone_list'),
    path('zones/create/', views.zone_create, name='zone_create'),
    path('zones/<int:pk>/edit/', views.zone_edit, name='zone_edit'),
    
    # تعريفات الأسعار
    path('rates/', views.rate_list, name='rate_list'),
    path('rates/create/', views.rate_create, name='rate_create'),
    path('rates/<int:pk>/edit/', views.rate_edit, name='rate_edit'),
    
    # الشحنات
    path('shipments/', views.shipment_list, name='shipment_list'),
    path('shipments/create/', views.shipment_create, name='shipment_create'),
    path('shipments/<int:pk>/', views.shipment_detail, name='shipment_detail'),
    path('shipments/<int:pk>/edit/', views.shipment_edit, name='shipment_edit'),
    path('shipments/<int:pk>/update-status/', views.shipment_update_status, name='shipment_update_status'),
    
    # طلبات الاستلام
    path('pickups/', views.pickup_list, name='pickup_list'),
    path('pickups/create/', views.pickup_create, name='pickup_create'),
    
    # الفواتير
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    
    # التتبع العام (بدون تسجيل دخول)
    path('track/', views.track_shipment, name='track_shipment'),
    
    # التقارير
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/shipments/', views.shipments_report, name='shipments_report'),
    path('reports/cod/', views.cod_report, name='cod_report'),
]
