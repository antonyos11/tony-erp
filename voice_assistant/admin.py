"""
Admin للمساعد الصوتي
"""

from django.contrib import admin
from .models import VoiceCommand, VoiceCommandTemplate, UserVoicePreference, VoiceShortcut


@admin.register(VoiceCommand)
class VoiceCommandAdmin(admin.ModelAdmin):
    list_display = ['user', 'command_text', 'command_type', 'status', 'confidence', 'created_at']
    list_filter = ['command_type', 'status', 'created_at']
    search_fields = ['user__username', 'command_text', 'response_text']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'processed_at']


@admin.register(VoiceCommandTemplate)
class VoiceCommandTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'command_type', 'action_type', 'priority', 'is_active']
    list_filter = ['command_type', 'action_type', 'is_active']
    search_fields = ['name', 'response_template']
    list_editable = ['priority', 'is_active']


@admin.register(UserVoicePreference)
class UserVoicePreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_enabled', 'voice_type', 'language', 'auto_listen']
    list_filter = ['is_enabled', 'voice_type', 'language']
    search_fields = ['user__username']
    raw_id_fields = ['user']


@admin.register(VoiceShortcut)
class VoiceShortcutAdmin(admin.ModelAdmin):
    list_display = ['user', 'trigger_phrase', 'action_url', 'usage_count', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__username', 'trigger_phrase', 'action_url']
    raw_id_fields = ['user']
