# -*- coding: utf-8 -*-
from django.contrib import admin
from .models import ImportSession, ImportError, SystemInitialization


@admin.register(ImportSession)
class ImportSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'module', 'user', 'status', 'success_count', 'error_count', 'created_at']
    list_filter = ['module', 'status', 'created_at']
    search_fields = ['original_filename', 'user__username']
    readonly_fields = ['created_at', 'completed_at']
    ordering = ['-created_at']


@admin.register(ImportError)
class ImportErrorAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'row_number', 'error_type', 'created_at']
    list_filter = ['error_type', 'session__module']
    search_fields = ['error_message']
    readonly_fields = ['created_at']


@admin.register(SystemInitialization)
class SystemInitializationAdmin(admin.ModelAdmin):
    list_display = ['id', 'is_initialized', 'initialized_at', 'initialized_by']
    readonly_fields = ['created_at', 'updated_at']
