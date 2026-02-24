"""
Quick Access URLs Configuration
"""
from django.urls import path
from . import views

app_name = 'quick_access'

urlpatterns = [
    # لوحة التحكم الموحدة
    path('', views.quick_dashboard, name='dashboard'),
    
    # البحث الشامل
    path('search/', views.global_search, name='global_search'),
    
    # التفضيلات
    path('preferences/update/', views.update_preferences, name='update_preferences'),
    
    # تتبع الاستخدام
    path('track/action/<int:action_id>/', views.track_action_usage, name='track_action'),
    path('track/report/', views.track_report_access, name='track_report'),
    
    # اختصارات لوحة المفاتيح
    path('shortcuts/', views.keyboard_shortcuts_guide, name='shortcuts_guide'),
    
    # العمليات الجماعية
    path('bulk-actions/', views.bulk_actions_interface, name='bulk_actions'),
    path('bulk-actions/execute/', views.execute_bulk_action, name='execute_bulk_action'),
    path('bulk-actions/locations/', views.get_locations_json, name='get_locations'),

    # التقارير المجدولة
    path('scheduled-reports/', views.scheduled_reports_manager, name='scheduled_reports'),
]
