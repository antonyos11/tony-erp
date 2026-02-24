"""
Admin لنظام إدارة المحتوى
"""

from django.contrib import admin
from .models import (
    Page, PageCategory, ContentBlock, Menu, MenuItem,
    MediaFile, PageComment
)


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 0


@admin.register(PageCategory)
class PageCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'status', 'author', 'view_count', 'created_at']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ['author', 'category']
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'category', 'excerpt', 'content')
        }),
        ('الوسائط', {
            'fields': ('featured_image',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('النشر', {
            'fields': ('status', 'published_at', 'scheduled_at', 'author')
        }),
        ('الإعدادات', {
            'fields': ('template', 'is_homepage', 'show_in_menu', 'allow_comments'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ['name', 'block_type', 'is_global', 'created_at']
    list_filter = ['block_type', 'is_global']
    search_fields = ['name']


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'location', 'is_active']
    list_filter = ['is_active']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [MenuItemInline]


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ['title', 'file_type', 'file_size', 'uploaded_by', 'created_at']
    list_filter = ['file_type', 'created_at']
    search_fields = ['title']


@admin.register(PageComment)
class PageCommentAdmin(admin.ModelAdmin):
    list_display = ['page', 'user', 'name', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['content', 'name']
    raw_id_fields = ['page', 'user', 'parent']
