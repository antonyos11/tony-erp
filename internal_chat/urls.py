"""
URLs للدردشة الداخلية
"""

from django.urls import path
from . import views

app_name = 'internal_chat'

urlpatterns = [
    path('', views.chat_home, name='home'),
    path('room/<uuid:room_uuid>/', views.chat_room, name='room'),
    path('start/<int:user_id>/', views.start_private_chat, name='start_private'),
    path('create-group/', views.create_group, name='create_group'),
    path('send/<uuid:room_uuid>/', views.send_message, name='send_message'),
    path('messages/<uuid:room_uuid>/', views.get_messages, name='get_messages'),
    path('reaction/<uuid:message_uuid>/', views.add_reaction, name='add_reaction'),
    path('delete/<uuid:message_uuid>/', views.delete_message, name='delete_message'),
    path('search-users/', views.search_users, name='search_users'),
    path('online-status/', views.update_online_status, name='online_status'),
]
