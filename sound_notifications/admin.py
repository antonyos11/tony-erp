"""
Admin للإشعارات الصوتية
"""

from django.contrib import admin
from .models import SoundTheme, NotificationSound, UserSoundPreference, SoundLog


@admin.register(SoundTheme)
class SoundThemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_default', 'is_active', 'created_at']
    list_filter = ['is_default', 'is_active']
    search_fields = ['name', 'description']
    list_editable = ['is_default', 'is_active']


@admin.register(NotificationSound)
class NotificationSoundAdmin(admin.ModelAdmin):
    list_display = ['name', 'theme', 'sound_type', 'volume', 'is_active']
    list_filter = ['theme', 'sound_type', 'is_active']
    search_fields = ['name']
    list_editable = ['volume', 'is_active']


@admin.register(UserSoundPreference)
class UserSoundPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_enabled', 'theme', 'master_volume', 'do_not_disturb']
    list_filter = ['is_enabled', 'do_not_disturb', 'theme']
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ['user']


@admin.register(SoundLog)
class SoundLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'sound_type', 'played_at', 'was_muted']
    list_filter = ['sound_type', 'was_muted', 'played_at']
    search_fields = ['user__username']
    date_hierarchy = 'played_at'
    readonly_fields = ['user', 'sound_type', 'played_at', 'was_muted']
