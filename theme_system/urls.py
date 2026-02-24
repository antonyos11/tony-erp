"""
URLs لنظام السمات
"""

from django.urls import path
from . import views

app_name = 'theme_system'

urlpatterns = [
    path('settings/', views.theme_settings, name='settings'),
    path('toggle-dark/', views.toggle_dark_mode, name='toggle_dark'),
    path('toggle-compact/', views.toggle_compact_mode, name='toggle_compact'),
    path('toggle-sidebar/', views.toggle_sidebar, name='toggle_sidebar'),
    path('css/', views.get_theme_css, name='get_css'),
    path('preview/<int:theme_id>/', views.preview_theme, name='preview'),
]
