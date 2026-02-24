"""
URLs للمساعد الصوتي
"""

from django.urls import path
from . import views

app_name = 'voice_assistant'

urlpatterns = [
    path('', views.voice_dashboard, name='dashboard'),
    path('settings/', views.voice_settings, name='settings'),
    path('process/', views.process_command, name='process'),
    path('toggle/', views.toggle_voice, name='toggle'),
    path('shortcuts/', views.shortcuts_list, name='shortcuts'),
    path('shortcuts/create/', views.create_shortcut, name='create_shortcut'),
    path('shortcuts/<int:shortcut_id>/delete/', views.delete_shortcut, name='delete_shortcut'),
    path('history/', views.command_history, name='history'),
    path('suggestions/', views.get_suggestions, name='suggestions'),
]
