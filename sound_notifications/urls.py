"""
URLs للإشعارات الصوتية
"""

from django.urls import path
from . import views

app_name = 'sound_notifications'

urlpatterns = [
    path('settings/', views.sound_settings, name='settings'),
    path('toggle/', views.toggle_sounds, name='toggle'),
    path('toggle-dnd/', views.toggle_dnd, name='toggle_dnd'),
    path('get-sound/<str:sound_type>/', views.get_sound_url, name='get_sound'),
    path('test/<str:sound_type>/', views.test_sound, name='test_sound'),
]
