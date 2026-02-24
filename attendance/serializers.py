"""
Serializers لنظام الحضور والانصراف - API للموبايل
"""
from rest_framework import serializers
from .models import (
    WorkLocation, EmployeeFaceData, AttendanceRecord, 
    AttendanceRequest, AttendanceSettings, AttendanceReport,
    AttendanceMethod, AttendanceStatus
)
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSimpleSerializer(serializers.ModelSerializer):
    """معلومات بسيطة عن المستخدم"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email']


class WorkLocationSerializer(serializers.ModelSerializer):
    """سيج.مايزر لمواقع العمل"""
    
    class Meta:
        model = WorkLocation
        fields = [
            'id', 'name', 'code', 'latitude', 'longitude', 
            'radius_meters', 'allowed_wifi_networks', 'allowed_ip_addresses',
            'work_start_time', 'work_end_time', 'grace_period_minutes', 
            'is_active'
        ]


class EmployeeFaceDataSerializer(serializers.ModelSerializer):
    """سيج.مايزر لبيانات بصمة الوجه"""
    user = UserSimpleSerializer(read_only=True)
    
    class Meta:
        model = EmployeeFaceData
        fields = [
            'id', 'user', 'face_image', 'is_verified', 
            'accuracy_score', 'last_updated'
        ]
        read_only_fields = ['face_encoding']


class AttendanceRecordSerializer(serializers.ModelSerializer):
    """سيج.مايزر لسجلات الحضور"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    check_in_method_display = serializers.CharField(source='get_check_in_method_display', read_only=True)
    check_out_method_display = serializers.CharField(source='get_check_out_method_display', read_only=True)
    
    class Meta:
        model = AttendanceRecord
        fields = '__all__'
        read_only_fields = ['total_hours', 'overtime_hours', 'late_minutes', 'created_at', 'updated_at']


class CheckInSerializer(serializers.Serializer):
    """سيج.مايزر لتسجيل الحضور"""
    method = serializers.ChoiceField(choices=AttendanceMethod.choices)
    location_id = serializers.IntegerField(required=False, allow_null=True)
    
    # بيانات GPS
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    
    # بيانات WiFi
    wifi_ssid = serializers.CharField(max_length=100, required=False, allow_null=True)
    
    # بيانات الجهاز
    device_info = serializers.JSONField(required=False, default=dict)
    
    # صورة الحضور
    photo = serializers.ImageField(required=False, allow_null=True)
    
    # ملاحظات
    notes = serializers.CharField(required=False, allow_blank=True)


class CheckOutSerializer(serializers.Serializer):
    """سيج.مايزر لتسجيل الانصراف"""
    method = serializers.ChoiceField(choices=AttendanceMethod.choices)
    
    # بيانات GPS
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    
    # بيانات WiFi
    wifi_ssid = serializers.CharField(max_length=100, required=False, allow_null=True)
    
    # بيانات الجهاز
    device_info = serializers.JSONField(required=False, default=dict)
    
    # صورة الانصراف
    photo = serializers.ImageField(required=False, allow_null=True)
    
    # ملاحظات
    notes = serializers.CharField(required=False, allow_blank=True)


class AttendanceRequestSerializer(serializers.ModelSerializer):
    """سيج.مايزر لطلبات تعديل الحضور"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    
    class Meta:
        model = AttendanceRequest
        fields = '__all__'
        read_only_fields = ['user', 'status', 'reviewed_by', 'review_notes', 'reviewed_at']


class AttendanceSettingsSerializer(serializers.ModelSerializer):
    """سيج.مايزر لإعدادات الحضور"""
    
    class Meta:
        model = AttendanceSettings
        fields = '__all__'


class AttendanceReportSerializer(serializers.ModelSerializer):
    """سيج.مايزر لتقارير الحضور"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    users_list = UserSimpleSerializer(source='users', many=True, read_only=True)
    locations_list = WorkLocationSerializer(source='locations', many=True, read_only=True)
    
    class Meta:
        model = AttendanceReport
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']
