"""
URLs لنظام الحضور والانصراف
"""
from django.urls import path
from . import views
from . import api_views

app_name = 'attendance'

urlpatterns = [
    # واجهات الويب
    path('', views.dashboard, name='dashboard'),
    path('check-in/', views.check_in, name='check_in'),
    path('check-out/', views.check_out, name='check_out'),
    path('my-attendance/', views.my_attendance, name='my_attendance'),
    path('list/', views.attendance_list, name='attendance_list'),
    path('requests/', views.request_list, name='request_list'),
    path('requests/create/', views.request_create, name='request_create'),
    path('locations/', views.locations_list, name='locations_list'),
    path('settings/', views.settings_view, name='settings'),
    
    # APIs للموبايل
    path('api/check-in/', api_views.api_check_in, name='api_check_in'),
    path('api/check-out/', api_views.api_check_out, name='api_check_out'),
    path('api/my-records/', api_views.api_my_records, name='api_my_records'),
    path('api/locations/', api_views.api_locations, name='api_locations'),
    path('api/settings/', api_views.api_settings, name='api_settings'),
    path('api/validate-location/', api_views.api_validate_location, name='api_validate_location'),
    path('api/face-recognition/', api_views.api_face_recognition, name='api_face_recognition'),
]

# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('request-approve/<int:pk>/', stub_view, name='request_approve'),
    path('request-reject/<int:pk>/', stub_view, name='request_reject'),
]
