"""
Admin للدردشة الداخلية
"""

from django.contrib import admin
from .models import (
    ChatRoom, ChatParticipant, Message, MessageReaction,
    MessageRead, ChatSettings, OnlineStatus
)


class ChatParticipantInline(admin.TabularInline):
    model = ChatParticipant
    extra = 0
    raw_id_fields = ['user']


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'room_type', 'is_archived', 'created_by', 'created_at']
    list_filter = ['room_type', 'is_archived', 'created_at']
    search_fields = ['name']
    raw_id_fields = ['created_by']
    inlines = [ChatParticipantInline]
    readonly_fields = ['uuid']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'room', 'message_type', 'is_deleted', 'created_at']
    list_filter = ['message_type', 'is_deleted', 'created_at']
    search_fields = ['content', 'sender__username']
    raw_id_fields = ['room', 'sender', 'reply_to']
    readonly_fields = ['uuid', 'created_at']


@admin.register(ChatSettings)
class ChatSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'sound_enabled', 'desktop_notifications', 'show_online_status']
    raw_id_fields = ['user']


@admin.register(OnlineStatus)
class OnlineStatusAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_online', 'last_seen']
    list_filter = ['is_online']
    raw_id_fields = ['user']
