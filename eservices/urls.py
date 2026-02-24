"""
مسارات URL للخدمات الإلكترونية - Tony ERP
"""

from django.urls import path
from . import views

app_name = 'eservices'

urlpatterns = [
    # لوحة التحكم
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alt'),
    
    # الفئات
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    
    # مزودي الخدمات
    path('providers/', views.provider_list, name='provider_list'),
    path('providers/create/', views.provider_create, name='provider_create'),
    path('providers/<int:pk>/edit/', views.provider_edit, name='provider_edit'),
    
    # الخدمات
    path('services/', views.service_list, name='service_list'),
    path('services/create/', views.service_create, name='service_create'),
    path('services/<int:pk>/edit/', views.service_edit, name='service_edit'),
    
    # شحن الرصيد
    path('recharge/', views.recharge_dashboard, name='recharge_dashboard'),
    path('recharge/create/', views.recharge_create, name='recharge_create'),
    
    # دفع الفواتير
    path('bills/', views.bill_dashboard, name='bill_dashboard'),
    path('bills/pay/', views.bill_payment_create, name='bill_payment_create'),
    
    # تحويل الأموال
    path('transfer/', views.transfer_dashboard, name='transfer_dashboard'),
    path('transfer/create/', views.transfer_create, name='transfer_create'),
    
    # المعاملات
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/<int:pk>/', views.transaction_detail, name='transaction_detail'),
    
    # المشغلين
    path('operators/', views.operator_list, name='operator_list'),
    path('operators/create/', views.operator_create, name='operator_create'),
    path('operators/<int:pk>/edit/', views.operator_edit, name='operator_edit'),
    
    # التقارير
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/transactions/', views.transactions_report, name='transactions_report'),
    path('reports/revenue/', views.revenue_report, name='revenue_report'),
]
