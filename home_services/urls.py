"""
مسارات URL للخدمات المنزلية - Home Services URLs
"""

from django.urls import path
from . import views

app_name = 'home_services'

urlpatterns = [
    # ==================== الصفحات العامة (للعملاء) ====================
    
    # الصفحة الرئيسية للخدمات
    path('', views.services_home, name='services_home'),
    
    # طلب صيانة
    path('maintenance/request/', views.maintenance_request_create, name='maintenance_request'),
    
    # طلب نظافة
    path('cleaning/request/', views.cleaning_request_create, name='cleaning_request'),
    path('cleaning/packages/', views.cleaning_packages_list, name='cleaning_packages'),
    
    # صفحة نجاح الطلب
    path('request/<int:pk>/success/', views.request_success, name='request_success'),
    
    # تتبع الطلب
    path('track/', views.track_request, name='track_request'),
    
    # ==================== لوحة التحكم الإدارية ====================
    
    # لوحة التحكم
    path('admin/dashboard/', views.dashboard, name='dashboard'),
    
    # إدارة الطلبات
    path('admin/requests/', views.request_list, name='request_list'),
    path('admin/requests/<int:pk>/', views.request_detail, name='request_detail'),
    path('admin/requests/<int:pk>/status/', views.request_update_status, name='request_update_status'),
    
    # إدارة فئات الصيانة
    path('admin/categories/', views.maintenance_category_list, name='maintenance_category_list'),
    path('admin/categories/create/', views.maintenance_category_create, name='maintenance_category_create'),
    path('admin/categories/<int:pk>/edit/', views.maintenance_category_edit, name='maintenance_category_edit'),
    
    # إدارة باقات النظافة
    path('admin/packages/', views.cleaning_package_list, name='cleaning_package_list'),
    path('admin/packages/create/', views.cleaning_package_create, name='cleaning_package_create'),
    path('admin/packages/<int:pk>/edit/', views.cleaning_package_edit, name='cleaning_package_edit'),
    
    # الإعدادات
    path('admin/settings/', views.settings_view, name='settings'),
    
    # التقارير
    path('admin/reports/', views.reports_dashboard, name='reports'),
]
