"""
Admin configuration لنظام الحضور والانصراف
"""
from django.contrib import admin
from .models import (
    WorkLocation, EmployeeFaceData, AttendanceRecord,
    AttendanceRequest, AttendanceSettings, AttendanceReport
)


@admin.register(WorkLocation)
class WorkLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'work_start_time', 'work_end_time']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['name']


@admin.register(EmployeeFaceData)
class EmployeeFaceDataAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_verified', 'accuracy_score', 'last_updated']
    list_filter = ['is_verified']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['face_encoding', 'last_updated']


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'check_in_time', 'check_out_time', 'status', 
                   'total_hours', 'late_minutes', 'is_verified']
    list_filter = ['status', 'date', 'is_verified', 'check_in_method']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    date_hierarchy = 'date'
    readonly_fields = ['total_hours', 'overtime_hours', 'late_minutes', 'created_at', 'updated_at']
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('user', 'date', 'location', 'status')
        }),
        ('أوقات التسجيل', {
            'fields': ('check_in_time', 'check_out_time', 'check_in_method', 'check_out_method')
        }),
        ('بيانات الموقع', {
            'fields': ('check_in_latitude', 'check_in_longitude', 'check_out_latitude', 
                      'check_out_longitude', 'check_in_wifi_ssid', 'check_out_wifi_ssid')
        }),
        ('الصور', {
            'fields': ('check_in_photo', 'check_out_photo')
        }),
        ('الإحصائيات', {
            'fields': ('total_hours', 'overtime_hours', 'late_minutes')
        }),
        ('التحقق', {
            'fields': ('is_verified', 'verified_by', 'notes')
        }),
    )


@admin.register(AttendanceRequest)
class AttendanceRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'request_type', 'date', 'status', 'created_at']
    list_filter = ['request_type', 'status', 'date']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'reason']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('معلومات الطلب', {
            'fields': ('user', 'request_type', 'date', 'reason')
        }),
        ('الأوقات المطلوبة', {
            'fields': ('requested_check_in', 'requested_check_out')
        }),
        ('المرفقات', {
            'fields': ('attachment',)
        }),
        ('المراجعة', {
            'fields': ('status', 'reviewed_by', 'review_notes', 'reviewed_at')
        }),
    )


@admin.register(AttendanceSettings)
class AttendanceSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('التحقق من الموقع', {
            'fields': ('enable_gps_validation', 'enable_wifi_validation', 'enable_ip_validation')
        }),
        ('التعرف على الوجه', {
            'fields': ('enable_face_recognition', 'face_recognition_threshold')
        }),
        ('التسجيل اليدوي', {
            'fields': ('allow_manual_checkin', 'manual_checkin_requires_approval')
        }),
        ('الصور', {
            'fields': ('require_photo_on_checkin', 'require_photo_on_checkout')
        }),
        ('الإشعارات', {
            'fields': ('send_late_notifications', 'send_absent_notifications')
        }),
        ('إعدادات عامة', {
            'fields': ('default_work_hours',)
        }),
    )


@admin.register(AttendanceReport)
class AttendanceReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'report_type', 'start_date', 'end_date', 'created_by', 'created_at']
    list_filter = ['report_type', 'start_date', 'end_date']
    search_fields = ['title']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
