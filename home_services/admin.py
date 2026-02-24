"""
إدارة Django Admin للخدمات المنزلية
"""

from django.contrib import admin
from .models import (
    ServiceType, MaintenanceCategory, CleaningPackage,
    ServiceRequest, RequestImage, ServiceArea, ServiceWorker,
    HomeServicesSettings
)


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'base_price', 'is_active', 'sort_order']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'code']
    ordering = ['sort_order', 'name']


@admin.register(MaintenanceCategory)
class MaintenanceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['sort_order', 'name']


@admin.register(CleaningPackage)
class CleaningPackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'price', 'discount_price', 'duration_hours', 'is_active', 'is_featured']
    list_filter = ['is_active', 'is_featured']
    search_fields = ['name', 'code']
    ordering = ['sort_order', 'name']


class RequestImageInline(admin.TabularInline):
    model = RequestImage
    extra = 0


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['request_number', 'request_type', 'customer_name', 'customer_phone', 
                    'status', 'payment_status', 'preferred_date', 'created_at']
    list_filter = ['request_type', 'status', 'payment_status', 'urgency', 'created_at']
    search_fields = ['request_number', 'customer_name', 'customer_phone', 'title']
    ordering = ['-created_at']
    readonly_fields = ['request_number', 'created_at', 'updated_at']
    inlines = [RequestImageInline]
    
    fieldsets = (
        ('معلومات الطلب', {
            'fields': ('request_number', 'request_type', 'status', 'payment_status', 'urgency')
        }),
        ('بيانات العميل', {
            'fields': ('user', 'customer_name', 'customer_phone', 'customer_email', 'customer_whatsapp')
        }),
        ('العنوان', {
            'fields': ('address', 'city', 'district', 'building_type')
        }),
        ('تفاصيل الخدمة', {
            'fields': ('service_type', 'maintenance_category', 'cleaning_package', 'title', 'description')
        }),
        ('الموعد', {
            'fields': ('preferred_date', 'preferred_time_from', 'preferred_time_to')
        }),
        ('التسعير', {
            'fields': ('estimated_price', 'final_price', 'discount')
        }),
        ('التنفيذ', {
            'fields': ('assigned_worker', 'started_at', 'completed_at', 'actual_duration_hours')
        }),
        ('الملاحظات', {
            'fields': ('customer_notes', 'worker_notes', 'admin_notes')
        }),
        ('التقييم', {
            'fields': ('rating', 'review')
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ServiceArea)
class ServiceAreaAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'extra_charge', 'is_active']
    list_filter = ['city', 'is_active']
    search_fields = ['name', 'city']


@admin.register(ServiceWorker)
class ServiceWorkerAdmin(admin.ModelAdmin):
    list_display = ['employee', 'average_rating', 'total_jobs', 'completed_jobs', 'is_available', 'is_active']
    list_filter = ['is_available', 'is_active']
    filter_horizontal = ['specializations', 'maintenance_categories', 'service_areas']


@admin.register(HomeServicesSettings)
class HomeServicesSettingsAdmin(admin.ModelAdmin):
    list_display = ['enable_maintenance', 'enable_cleaning', 'working_hours_start', 'working_hours_end']
    
    def has_add_permission(self, request):
        # السماح بسجل واحد فقط
        return not HomeServicesSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False
