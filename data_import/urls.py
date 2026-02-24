# -*- coding: utf-8 -*-
"""
URLs لنظام استيراد البيانات
"""
from django.urls import path
from . import views

app_name = 'data_import'

urlpatterns = [
    # لوحة التحكم
    path('', views.import_dashboard, name='dashboard'),
    
    # الإعداد الأولي
    path('setup/', views.initial_setup, name='initial_setup'),
    path('setup/complete/', views.mark_initialized, name='mark_initialized'),
    
    # استيراد موديول
    path('import/<str:module>/', views.import_module, name='import_module'),
    path('import/<str:module>/process/', views.process_import, name='process_import'),
    
    # القوالب
    path('templates/<str:module>/', views.download_template, name='download_template'),
    path('templates/', views.download_all_templates, name='download_all_templates'),
    
    # الجلسات
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    
    # API
    path('api/status/', views.check_system_status, name='check_status'),
]
