"""
URLs لمكالمات الفيديو
"""

from django.urls import path
from . import views

app_name = 'video_calls'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('create/', views.create_room, name='create'),
    path('join/<uuid:room_uuid>/', views.join_room, name='join'),
    path('leave/<uuid:room_uuid>/', views.leave_room, name='leave'),
    path('toggle/<uuid:room_uuid>/', views.toggle_media, name='toggle_media'),
    path('message/<uuid:room_uuid>/', views.send_message, name='send_message'),
    path('status/<uuid:room_uuid>/', views.get_room_status, name='status'),
]
