"""
لوحة إدارة تطبيق الطباعة — RITA ERP
"""
from django.contrib import admin
from .models import PrintTemplate


@admin.register(PrintTemplate)
class PrintTemplateAdmin(admin.ModelAdmin):
    list_display  = ['name', 'template_type', 'paper_size', 'is_default', 'created_at']
    list_filter   = ['template_type', 'paper_size', 'is_default']
    search_fields = ['name']
    ordering      = ['template_type', 'name']
