# -*- coding: utf-8 -*-
"""
URLs موديول الاستيراد والتصدير
"""

from django.urls import path
from . import views

app_name = 'import_export'

urlpatterns = [
    # ============= التصدير =============
    # وكلاء الشحن
    path('shipping-agents/', views.shipping_agent_list, name='shipping_agent_list'),
    path('shipping-agents/create/', views.shipping_agent_create, name='shipping_agent_create'),
    path('shipping-agents/<int:pk>/', views.shipping_agent_detail, name='shipping_agent_detail'),
    path('shipping-agents/<int:pk>/edit/', views.shipping_agent_edit, name='shipping_agent_edit'),
    path('shipping-agents/<int:pk>/delete/', views.shipping_agent_delete, name='shipping_agent_delete'),
    
    # طلبات التصدير
    path('orders/', views.export_order_list, name='export_order_list'),
    path('orders/create/', views.export_order_create, name='export_order_create'),
    path('orders/<int:pk>/', views.export_order_detail, name='export_order_detail'),
    path('orders/<int:pk>/edit/', views.export_order_edit, name='export_order_edit'),
    
    # الموافقة المالية
    path('financial-approval/', views.financial_approval_list, name='financial_approval_list'),
    path('financial-approval/create/', views.financial_approval_create, name='financial_approval_create'),
    path('financial-approval/create/<int:export_order_id>/', views.financial_approval_create, name='financial_approval_create_for_order'),
    path('financial-approval/<int:pk>/', views.financial_approval_detail, name='financial_approval_detail'),
    path('financial-approval/<int:pk>/edit/', views.financial_approval_edit, name='financial_approval_edit'),
    path('financial-approval/<int:pk>/print/', views.financial_approval_print, name='financial_approval_print'),
    path('financial-approval/<int:pk>/<str:action>/', views.financial_approval_action, name='financial_approval_action'),
    
    # الفواتير المبدئية
    path('pre-export-invoice/', views.pre_export_invoice_list, name='pre_export_invoice_list'),
    path('pre-export-invoice/create/', views.pre_export_invoice_create, name='pre_export_invoice_create'),
    path('pre-export-invoice/create/<int:export_order_id>/', views.pre_export_invoice_create, name='pre_export_invoice_create_for_order'),
    path('pre-export-invoice/<int:pk>/', views.pre_export_invoice_detail, name='pre_export_invoice_detail'),
    
    # شهادات التصدير
    path('export-certificate/', views.export_certificate_list, name='export_certificate_list'),
    path('export-certificate/create/', views.export_certificate_create, name='export_certificate_create'),
    path('export-certificate/create/<int:export_order_id>/', views.export_certificate_create, name='export_certificate_create_for_order'),
    
    # ============= الاستيراد =============
    # المخلصون الجمركيون
    path('customs-clearance/', views.customs_clearance_list, name='customs_clearance_list'),
    path('customs-clearance/create/', views.customs_clearance_create, name='customs_clearance_create'),
    path('customs-clearance/<int:pk>/', views.customs_clearance_detail, name='customs_clearance_detail'),
    path('customs-clearance/<int:pk>/edit/', views.customs_clearance_edit, name='customs_clearance_edit'),
    path('customs-clearance/<int:pk>/delete/', views.customs_clearance_delete, name='customs_clearance_delete'),
    
    # أوامر الاستيراد
    path('import-orders/', views.import_order_list, name='import_order_list'),
    path('import-orders/create/', views.import_order_create, name='import_order_create'),
    path('import-orders/<int:pk>/', views.import_order_detail, name='import_order_detail'),
    path('import-orders/<int:pk>/edit/', views.import_order_edit, name='import_order_edit'),
    path('import-orders/<int:pk>/delete/', views.import_order_delete, name='import_order_delete'),
    path('import-orders/<int:pk>/print/', views.import_order_print, name='import_order_print'),
    path('import-orders/<int:pk>/status/<str:status>/', views.import_order_status, name='import_order_status'),
    
    # شهادات الاستيراد
    path('certificates/', views.import_certificate_list, name='import_certificate_list'),
    path('certificates/create/', views.import_certificate_create, name='import_certificate_create'),
    path('certificates/create/<int:import_order_id>/', views.import_certificate_create, name='import_certificate_create_for_order'),
    
    # أذون الإفراج
    path('release-orders/', views.release_order_list, name='release_order_list'),
    path('release-orders/create/', views.release_order_create, name='release_order_create'),
    path('release-orders/create/<int:import_order_id>/', views.release_order_create, name='release_order_create_for_order'),
    path('release-orders/<int:pk>/', views.release_order_detail, name='release_order_detail'),
    
    # التنازلات
    path('waiver/', views.import_waiver_list, name='import_waiver_list'),
    path('waiver/create/', views.import_waiver_create, name='import_waiver_create'),
    path('waiver/create/<int:import_order_id>/', views.import_waiver_create, name='import_waiver_create_for_order'),
    path('waiver/<int:pk>/', views.import_waiver_detail, name='import_waiver_detail'),
    
    # التقارير
    path('reports/', views.import_reports, name='import_reports'),
    path('export-reports/', views.export_reports, name='export_reports'),
    
    # تصدير البيانات CSV
    path('csv/<str:model_type>/', views.export_to_csv, name='export_to_csv'),
]
