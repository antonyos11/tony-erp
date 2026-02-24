"""
API Views لنظام الحضور والانصراف - للاستخدام من الموبايل
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
import math
from .models import (
    WorkLocation, EmployeeFaceData, AttendanceRecord,
    AttendanceSettings, AttendanceMethod, AttendanceStatus
)
from .serializers import (
    WorkLocationSerializer, AttendanceRecordSerializer,
    CheckInSerializer, CheckOutSerializer, AttendanceSettingsSerializer
)


def calculate_distance(lat1, lon1, lat2, lon2):
    """حساب المسافة بين نقطتين GPS بالمتر"""
    # Haversine formula
    R = 6371000  # نصف قطر الأرض بالمتر
    
    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    delta_lat = math.radians(float(lat2) - float(lat1))
    delta_lon = math.radians(float(lon2) - float(lon1))
    
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def validate_location(location, latitude, longitude, wifi_ssid=None, ip_address=None):
    """التحقق من صحة الموقع"""
    settings = AttendanceSettings.get_settings()
    errors = []
    
    # التحقق من GPS
    if settings.enable_gps_validation and location.latitude and location.longitude:
        if latitude and longitude:
            distance = calculate_distance(
                location.latitude, location.longitude,
                latitude, longitude
            )
            if distance > location.radius_meters:
                errors.append(f'أنت خارج نطاق الموقع المسموح (المسافة: {int(distance)} متر)')
        else:
            errors.append('يجب توفير موقع GPS')
    
    # التحقق من WiFi
    if settings.enable_wifi_validation and location.allowed_wifi_networks:
        if wifi_ssid:
            if wifi_ssid not in location.allowed_wifi_networks:
                errors.append('شبكة WiFi غير مسموح بها')
        else:
            errors.append('يجب الاتصال بشبكة WiFi المسموح بها')
    
    # التحقق من IP
    if settings.enable_ip_validation and location.allowed_ip_addresses:
        if ip_address:
            if ip_address not in location.allowed_ip_addresses:
                errors.append('عنوان IP غير مسموح به')
        else:
            errors.append('عنوان IP غير متوفر')
    
    return len(errors) == 0, errors


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_check_in(request):
    """API لتسجيل الحضور"""
    serializer = CheckInSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    today = timezone.now().date()
    
    # التحقق من وجود سجل لليوم
    existing_record = AttendanceRecord.objects.filter(
        user=request.user,
        date=today
    ).first()
    
    if existing_record and existing_record.check_in_time:
        return Response({
            'success': False,
            'message': 'لقد قمت بتسجيل الحضور بالفعل اليوم',
            'record': AttendanceRecordSerializer(existing_record).data
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # الحصول على الموقع
    location = None
    location_id = data.get('location_id')
    if location_id:
        try:
            location = WorkLocation.objects.get(id=location_id, is_active=True)
        except WorkLocation.DoesNotExist:
            return Response({
                'success': False,
                'message': 'الموقع غير موجود أو غير فعال'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # التحقق من صحة الموقع
    if location:
        is_valid, errors = validate_location(
            location,
            data.get('latitude'),
            data.get('longitude'),
            data.get('wifi_ssid'),
            request.META.get('REMOTE_ADDR')
        )
        
        if not is_valid:
            return Response({
                'success': False,
                'message': 'فشل التحقق من الموقع',
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # إنشاء أو تحديث سجل الحضور
    if existing_record:
        record = existing_record
    else:
        record = AttendanceRecord(user=request.user, date=today)
    
    record.check_in_time = timezone.now()
    record.check_in_method = data.get('method')
    record.location = location
    record.check_in_latitude = data.get('latitude')
    record.check_in_longitude = data.get('longitude')
    record.check_in_wifi_ssid = data.get('wifi_ssid')
    record.check_in_device_info = data.get('device_info', {})
    record.check_in_ip = request.META.get('REMOTE_ADDR')
    record.notes = data.get('notes', '')
    
    # حفظ الصورة إذا تم رفعها
    if 'photo' in request.FILES:
        record.check_in_photo = request.FILES['photo']
    
    record.save()
    record.calculate_late_minutes()
    
    return Response({
        'success': True,
        'message': 'تم تسجيل الحضور بنجاح',
        'record': AttendanceRecordSerializer(record).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_check_out(request):
    """API لتسجيل الانصراف"""
    serializer = CheckOutSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    today = timezone.now().date()
    
    # الحصول على سجل اليوم
    record = AttendanceRecord.objects.filter(
        user=request.user,
        date=today
    ).first()
    
    if not record or not record.check_in_time:
        return Response({
            'success': False,
            'message': 'يجب تسجيل الحضور أولاً'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if record.check_out_time:
        return Response({
            'success': False,
            'message': 'لقد قمت بتسجيل الانصراف بالفعل',
            'record': AttendanceRecordSerializer(record).data
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # تحديث سجل الانصراف
    record.check_out_time = timezone.now()
    record.check_out_method = data.get('method')
    record.check_out_latitude = data.get('latitude')
    record.check_out_longitude = data.get('longitude')
    record.check_out_wifi_ssid = data.get('wifi_ssid')
    record.check_out_device_info = data.get('device_info', {})
    record.check_out_ip = request.META.get('REMOTE_ADDR')
    
    note_text = data.get('notes')
    if note_text:
        record.notes += '\n' + note_text
    
    # حفظ الصورة إذا تم رفعها
    if 'photo' in request.FILES:
        record.check_out_photo = request.FILES['photo']
    
    record.save()
    record.calculate_hours()
    
    return Response({
        'success': True,
        'message': 'تم تسجيل الانصراف بنجاح',
        'record': AttendanceRecordSerializer(record).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_my_records(request):
    """API للحصول على سجلات حضور المستخدم"""
    # الفلترة بالتاريخ
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    limit = int(request.GET.get('limit', 30))
    
    records = AttendanceRecord.objects.filter(
        user=request.user
    ).select_related('location').order_by('-date')
    
    if start_date:
        records = records.filter(date__gte=start_date)
    if end_date:
        records = records.filter(date__lte=end_date)
    
    records = records[:limit]
    
    # الإحصائيات
    all_records = AttendanceRecord.objects.filter(user=request.user)
    if start_date:
        all_records = all_records.filter(date__gte=start_date)
    if end_date:
        all_records = all_records.filter(date__lte=end_date)
    
    stats = {
        'total_days': all_records.count(),
        'present_days': all_records.filter(status=AttendanceStatus.PRESENT).count(),
        'late_days': all_records.filter(status=AttendanceStatus.LATE).count(),
        'absent_days': all_records.filter(status=AttendanceStatus.ABSENT).count(),
        'total_hours': float(all_records.aggregate(total=Sum('total_hours'))['total'] or 0),
        'overtime_hours': float(all_records.aggregate(total=Sum('overtime_hours'))['total'] or 0),
    }
    
    return Response({
        'success': True,
        'records': AttendanceRecordSerializer(records, many=True).data,
        'stats': stats
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_locations(request):
    """API للحصول على قائمة المواقع المسموح بها"""
    locations = WorkLocation.objects.filter(is_active=True)
    
    return Response({
        'success': True,
        'locations': WorkLocationSerializer(locations, many=True).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_settings(request):
    """API للحصول على إعدادات النظام"""
    settings = AttendanceSettings.get_settings()
    
    return Response({
        'success': True,
        'settings': AttendanceSettingsSerializer(settings).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_validate_location(request):
    """API للتحقق من صحة الموقع"""
    location_id = request.data.get('location_id')
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    wifi_ssid = request.data.get('wifi_ssid')
    
    if not location_id:
        return Response({
            'success': False,
            'message': 'يجب توفير معرّف الموقع'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        location = WorkLocation.objects.get(id=location_id, is_active=True)
    except WorkLocation.DoesNotExist:
        return Response({
            'success': False,
            'message': 'الموقع غير موجود أو غير فعال'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # حساب المسافة
    distance = None
    if location.latitude and location.longitude and latitude and longitude:
        distance = calculate_distance(
            location.latitude, location.longitude,
            latitude, longitude
        )
    
    # التحقق من الموقع
    is_valid, errors = validate_location(
        location,
        latitude,
        longitude,
        wifi_ssid,
        request.META.get('REMOTE_ADDR')
    )
    
    return Response({
        'success': is_valid,
        'valid': is_valid,
        'distance': int(distance) if distance else None,
        'max_distance': location.radius_meters,
        'errors': errors if not is_valid else []
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_face_recognition(request):
    """API للتعرف على الوجه"""
    # هذه دالة نموذجية - يمكن تطويرها لاحقاً لاستخدام مكتبات التعرف على الوجه
    
    if 'photo' not in request.FILES:
        return Response({
            'success': False,
            'message': 'يجب إرفاق صورة'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    photo = request.FILES['photo']
    
    # هنا يمكن إضافة كود التعرف على الوجه باستخدام مكتبات مثل:
    # - face_recognition
    # - dlib
    # - OpenCV
    
    # للآن نعيد نجاح مبدئي
    return Response({
        'success': True,
        'recognized': True,
        'confidence': 0.95,
        'message': 'تم التعرف على الوجه بنجاح'
    })
