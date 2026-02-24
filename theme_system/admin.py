"""
Admin لنظام السمات
"""

from django.contrib import admin
from .models import Theme, UserThemePreference


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'theme_type', 'is_default', 'is_active', 'created_at']
    list_filter = ['theme_type', 'is_default', 'is_active']
    search_fields = ['name', 'description']
    list_editable = ['is_default', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'slug', 'theme_type', 'description', 'is_default', 'is_active')
        }),
        ('الألوان الأساسية', {
            'fields': ('primary_color', 'secondary_color', 'accent_color')
        }),
        ('ألوان الخلفية', {
            'fields': ('background_color', 'surface_color', 'card_color')
        }),
        ('ألوان النصوص', {
            'fields': ('text_primary', 'text_secondary', 'text_muted')
        }),
        ('الشريط الجانبي', {
            'fields': ('sidebar_bg', 'sidebar_text', 'sidebar_active')
        }),
        ('الهيدر', {
            'fields': ('header_bg', 'header_text')
        }),
        ('ألوان الحالات', {
            'fields': ('success_color', 'warning_color', 'danger_color', 'info_color')
        }),
        ('إعدادات متقدمة', {
            'fields': ('border_radius', 'box_shadow', 'font_family', 'custom_css'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserThemePreference)
class UserThemePreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'theme', 'mode', 'compact_mode', 'sidebar_collapsed']
    list_filter = ['mode', 'compact_mode', 'sidebar_collapsed']
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ['user']
