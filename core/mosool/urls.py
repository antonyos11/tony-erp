# -*- coding: utf-8 -*-
"""
URLs موصول التحضير والاستماد
"""

from django.urls import path
from . import views

app_name = 'mosool'

urlpatterns = [
    # لوحات التحكم
    path('preparation/', views.preparation_dashboard, name='preparation_dashboard'),
    path('approval/', views.approval_dashboard, name='approval_dashboard'),
    
    # طلبات التحضير
    path('preparation/list/', views.preparation_list, name='preparation_list'),
    path('preparation/create/', views.preparation_create, name='preparation_create'),
    path('preparation/<int:pk>/', views.preparation_detail, name='preparation_detail'),
    path('preparation/<int:pk>/edit/', views.preparation_edit, name='preparation_edit'),
    path('preparation/<int:pk>/submit/', views.preparation_submit, name='preparation_submit'),
    path('preparation/<int:pk>/start/', views.preparation_start, name='preparation_start'),
    path('preparation/<int:pk>/complete/', views.preparation_complete, name='preparation_complete'),
    path('preparation/<int:pk>/cancel/', views.preparation_cancel, name='preparation_cancel'),
    path('preparation/<int:pk>/convert/', views.convert_to_approval, name='convert_to_approval'),
    
    # مستندات الاستماد
    path('approval/list/', views.approval_list, name='approval_list'),
    path('approval/pending/', views.approval_pending, name='approval_pending'),
    path('approval/create/', views.approval_create, name='approval_create'),
    path('approval/<int:pk>/', views.approval_detail, name='approval_detail'),
    path('approval/<int:pk>/edit/', views.approval_edit, name='approval_edit'),
    path('approval/<int:pk>/submit/', views.approval_submit, name='approval_submit'),
    path('approval/<int:pk>/action/', views.approval_action, name='approval_action'),
    path('approval/<int:pk>/cancel/', views.approval_cancel, name='approval_cancel'),
    
    # التصدير
    path('preparation/export/csv/', views.export_preparations_csv, name='export_preparations_csv'),
    path('approval/export/csv/', views.export_approvals_csv, name='export_approvals_csv'),
    
    # API
    path('api/preparation/stats/', views.api_preparation_stats, name='api_preparation_stats'),
    path('api/approval/stats/', views.api_approval_stats, name='api_approval_stats'),
    path('api/dashboard/', views.api_dashboard, name='api_dashboard'),
]
