# branches/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Branch, BranchType, BranchTransfer


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'branch_type_badge', 'city', 'is_active', 'is_main']
    list_filter = ['branch_type', 'is_active', 'is_main', 'city', 'region']
    search_fields = ['name', 'code', 'city', 'address']
    list_editable = ['is_active']
    ordering = ['branch_type', 'name']
    
    fieldsets = (
        (_('البيانات الأساسية'), {
            'fields': ('name', 'code', 'branch_type', 'parent_branch')
        }),
        (_('الموقع'), {
            'fields': ('address', 'city', 'region', ('latitude', 'longitude'))
        }),
        (_('التواصل'), {
            'fields': ('phone', 'mobile', 'email')
        }),
        (_('الإدارة'), {
            'fields': ('manager',)
        }),
        (_('الإعدادات'), {
            'fields': ('is_active', 'is_main', 'can_sell', 'can_purchase', 'has_inventory')
        }),
        (_('أوقات العمل'), {
            'fields': (('working_hours_start', 'working_hours_end'), 'working_days'),
            'classes': ('collapse',)
        }),
        (_('ملاحظات'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def branch_type_badge(self, obj):
        colors = {
            'branch': '#4e73df',
            'showroom': '#1cc88a',
            'warehouse': '#f6c23e',
            'outlet': '#36b9cc',
        }
        color = colors.get(obj.branch_type, '#858796')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_branch_type_display()
        )
    branch_type_badge.short_description = _("النوع")


@admin.register(BranchTransfer)
class BranchTransferAdmin(admin.ModelAdmin):
    list_display = ['transfer_number', 'from_branch', 'to_branch', 'status', 'transfer_date']
    list_filter = ['status', 'transfer_date', 'from_branch', 'to_branch']
    search_fields = ['transfer_number']
    date_hierarchy = 'transfer_date'
    
    fieldsets = (
        (None, {
            'fields': ('transfer_number', 'status')
        }),
        (_('الفروع'), {
            'fields': ('from_branch', 'to_branch')
        }),
        (_('التواريخ'), {
            'fields': ('transfer_date', 'received_date')
        }),
        (_('ملاحظات'), {
            'fields': ('notes',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# تخصيص واجهة الإدارة
admin.site.site_header = "Tony ERP - لوحة الإدارة"
admin.site.site_title = "Tony ERP"
admin.site.index_title = "مرحباً بك في نظام Tony ERP"
