"""
URLs لتكامل الساعات الذكية
"""

from django.urls import path
from . import views

app_name = 'smartwatch'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    # إدارة الأجهزة
    path('register/', views.register_device, name='register'),
    path('unregister/<int:device_id>/', views.unregister_device, name='unregister'),
    
    # API للساعة
    path('sync/<str:device_id>/', views.sync_device, name='sync'),
    path('action/<str:device_id>/', views.execute_action, name='execute_action'),
    
    # الإعدادات
    path('settings/', views.update_settings, name='settings'),
    path('actions/', views.get_quick_actions, name='quick_actions'),
    path('notify/', views.send_notification, name='notify'),
]
