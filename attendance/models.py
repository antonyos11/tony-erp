"""
نماذج قاعدة البيانات لنظام الحضور والانصراف المتقدم
يدعم: بصمة الوجه، GPS، WiFi، تسجيل يدوي
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class AttendanceMethod(models.TextChoices):
    """طرق تسجيل الحضور"""
    MANUAL = 'manual', 'تسجيل يدوي'
    FACE_RECOGNITION = 'face', 'بصمة الوجه'
    GPS = 'gps', 'موقع GPS'
    WIFI = 'wifi', 'شبكة WiFi'
    QR_CODE = 'qr', 'كود QR'
    MOBILE_APP = 'mobile', 'تطبيق الموبايل'


class AttendanceStatus(models.TextChoices):
    """حالة الحضور"""
    PRESENT = 'present', 'حاضر'
    ABSENT = 'absent', 'غائب'
    LATE = 'late', 'متأخر'
    HALF_DAY = 'half_day', 'نصف يوم'
    LEAVE = 'leave', 'إجازة'
    HOLIDAY = 'holiday', 'عطلة'


class WorkLocation(models.Model):
    """المواقع المسموح بالتسجيل منها"""
    name = models.CharField('اسم الموقع', max_length=200)
    code = models.CharField('كود الموقع', max_length=50, unique=True)
    
    # إحداثيات GPS
    latitude = models.DecimalField('خط العرض', max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField('خط الطول', max_digits=10, decimal_places=7, null=True, blank=True)
    radius_meters = models.IntegerField('نطاق القبول (متر)', default=100, 
                                       help_text='المسافة المسموح بها من الموقع')
    
    # شبكات WiFi المسموح بها
    allowed_wifi_networks = models.JSONField('شبكات WiFi المسموح بها', default=list, blank=True,
                                            help_text='قائمة بأسماء شبكات WiFi (SSID) المسموح بها')
    
    # عناوين IP المسموح بها
    allowed_ip_addresses = models.JSONField('عناوين IP المسموح بها', default=list, blank=True)
    
    # أوقات العمل
    work_start_time = models.TimeField('وقت بداية العمل', default='08:00')
    work_end_time = models.TimeField('وقت نهاية العمل', default='17:00')
    grace_period_minutes = models.IntegerField('فترة السماح (دقائق)', default=15,
                                              help_text='المدة المسموح بها للتأخير بدون عقوبة')
    
    is_active = models.BooleanField('فعال', default=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'موقع العمل'
        verbose_name_plural = 'مواقع العمل'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class EmployeeFaceData(models.Model):
    """بيانات بصمة الوجه للموظف"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='face_data')
    
    # بيانات بصمة الوجه (مشفرة)
    face_encoding = models.BinaryField('بيانات البصمة', null=True, blank=True)
    face_image = models.ImageField('صورة الوجه', upload_to='face_data/', null=True, blank=True)
    
    # معلومات إضافية
    is_verified = models.BooleanField('تم التحقق', default=False)
    last_updated = models.DateTimeField('آخر تحديث', auto_now=True)
    accuracy_score = models.FloatField('دقة التعرف', default=0.0,
                                      help_text='نسبة دقة التعرف على الوجه')
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'بيانات بصمة الوجه'
        verbose_name_plural = 'بيانات بصمات الوجه'
    
    def __str__(self):
        return f"بصمة وجه: {self.user.get_full_name()}"


class AttendanceRecord(models.Model):
    """سجل الحضور والانصراف"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records',
                            verbose_name='الموظف')
    location = models.ForeignKey(WorkLocation, on_delete=models.SET_NULL, null=True, blank=True,
                                verbose_name='الموقع')
    
    # أوقات التسجيل
    date = models.DateField('التاريخ', default=timezone.localdate)
    check_in_time = models.DateTimeField('وقت الحضور', null=True, blank=True)
    check_out_time = models.DateTimeField('وقت الانصراف', null=True, blank=True)
    
    # طريقة التسجيل
    check_in_method = models.CharField('طريقة تسجيل الحضور', max_length=20, 
                                      choices=AttendanceMethod.choices, null=True, blank=True)
    check_out_method = models.CharField('طريقة تسجيل الانصراف', max_length=20, 
                                       choices=AttendanceMethod.choices, null=True, blank=True)
    
    # الحالة
    status = models.CharField('الحالة', max_length=20, choices=AttendanceStatus.choices, 
                             default=AttendanceStatus.PRESENT)
    
    # بيانات الموقع الجغرافي
    check_in_latitude = models.DecimalField('خط عرض الحضور', max_digits=10, decimal_places=7, 
                                           null=True, blank=True)
    check_in_longitude = models.DecimalField('خط طول الحضور', max_digits=10, decimal_places=7, 
                                            null=True, blank=True)
    check_out_latitude = models.DecimalField('خط عرض الانصراف', max_digits=10, decimal_places=7, 
                                            null=True, blank=True)
    check_out_longitude = models.DecimalField('خط طول الانصراف', max_digits=10, decimal_places=7, 
                                             null=True, blank=True)
    
    # بيانات WiFi
    check_in_wifi_ssid = models.CharField('شبكة WiFi عند الحضور', max_length=100, 
                                         null=True, blank=True)
    check_out_wifi_ssid = models.CharField('شبكة WiFi عند الانصراف', max_length=100, 
                                          null=True, blank=True)
    
    # بيانات الجهاز
    check_in_device_info = models.JSONField('معلومات جهاز الحضور', default=dict, blank=True)
    check_out_device_info = models.JSONField('معلومات جهاز الانصراف', default=dict, blank=True)
    
    # صور التحقق
    check_in_photo = models.ImageField('صورة الحضور', upload_to='attendance/checkin/', 
                                      null=True, blank=True)
    check_out_photo = models.ImageField('صورة الانصراف', upload_to='attendance/checkout/', 
                                       null=True, blank=True)
    
    # عنوان IP
    check_in_ip = models.GenericIPAddressField('IP الحضور', null=True, blank=True)
    check_out_ip = models.GenericIPAddressField('IP الانصراف', null=True, blank=True)
    
    # حساب ساعات العمل
    total_hours = models.DecimalField('إجمالي الساعات', max_digits=5, decimal_places=2, 
                                     default=Decimal('0.00'))
    overtime_hours = models.DecimalField('ساعات إضافية', max_digits=5, decimal_places=2, 
                                        default=Decimal('0.00'))
    late_minutes = models.IntegerField('دقائق التأخير', default=0)
    
    # ملاحظات
    notes = models.TextField('ملاحظات', blank=True)
    is_verified = models.BooleanField('تم التحقق', default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='verified_attendance', verbose_name='تم التحقق بواسطة')
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التعديل', auto_now=True)
    
    class Meta:
        verbose_name = 'سجل حضور'
        verbose_name_plural = 'سجلات الحضور'
        ordering = ['-date', '-check_in_time']
        unique_together = ['user', 'date']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['date', 'status']),
            models.Index(fields=['location', 'date']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.date}"
    
    def calculate_hours(self):
        """حساب ساعات العمل"""
        if self.check_in_time and self.check_out_time:
            delta = self.check_out_time - self.check_in_time
            hours = Decimal(str(delta.total_seconds() / 3600))
            self.total_hours = hours.quantize(Decimal('0.01'))
            
            # حساب الساعات الإضافية
            if self.location:
                work_hours = 8  # ساعات العمل الافتراضية
                if hours > work_hours:
                    self.overtime_hours = (hours - work_hours).quantize(Decimal('0.01'))
            
            self.save()
    
    def calculate_late_minutes(self):
        """حساب دقائق التأخير"""
        if self.check_in_time and self.location:
            scheduled_time = timezone.datetime.combine(
                self.date, 
                self.location.work_start_time
            )
            scheduled_time = timezone.make_aware(scheduled_time)
            
            if self.check_in_time > scheduled_time:
                delta = self.check_in_time - scheduled_time
                self.late_minutes = int(delta.total_seconds() / 60)
                
                # تحديد الحالة بناءً على التأخير
                if self.late_minutes > self.location.grace_period_minutes:
                    self.status = AttendanceStatus.LATE
            
            self.save()


class AttendanceRequest(models.Model):
    """طلبات تعديل الحضور"""
    REQUEST_TYPES = [
        ('missing', 'تسجيل حضور فائت'),
        ('correction', 'تصحيح وقت'),
        ('excuse', 'عذر'),
        ('leave', 'طلب إجازة'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'قيد المراجعة'),
        ('approved', 'موافق عليه'),
        ('rejected', 'مرفوض'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_requests',
                            verbose_name='الموظف')
    request_type = models.CharField('نوع الطلب', max_length=20, choices=REQUEST_TYPES)
    date = models.DateField('التاريخ')
    
    # التفاصيل
    reason = models.TextField('السبب')
    requested_check_in = models.DateTimeField('وقت الحضور المطلوب', null=True, blank=True)
    requested_check_out = models.DateTimeField('وقت الانصراف المطلوب', null=True, blank=True)
    
    # المرفقات
    attachment = models.FileField('مرفق', upload_to='attendance/requests/', null=True, blank=True)
    
    # الحالة
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='reviewed_requests', verbose_name='تمت المراجعة بواسطة')
    review_notes = models.TextField('ملاحظات المراجع', blank=True)
    reviewed_at = models.DateTimeField('تاريخ المراجعة', null=True, blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التعديل', auto_now=True)
    
    class Meta:
        verbose_name = 'طلب تعديل حضور'
        verbose_name_plural = 'طلبات تعديل الحضور'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_request_type_display()} - {self.user.get_full_name()} - {self.date}"


class AttendanceSettings(models.Model):
    """إعدادات نظام الحضور"""
    
    # التحقق من بصمة الوجه
    enable_face_recognition = models.BooleanField('تفعيل التعرف على الوجه', default=True)
    face_recognition_threshold = models.FloatField('حد دقة التعرف', default=0.6,
                                                  help_text='الحد الأدنى للتطابق (0-1)')
    
    # التحقق من الموقع
    enable_gps_validation = models.BooleanField('تفعيل التحقق من GPS', default=True)
    enable_wifi_validation = models.BooleanField('تفعيل التحقق من WiFi', default=True)
    enable_ip_validation = models.BooleanField('تفعيل التحقق من IP', default=False)
    
    # السماح بالتسجيل اليدوي
    allow_manual_checkin = models.BooleanField('السماح بالتسجيل اليدوي', default=True)
    manual_checkin_requires_approval = models.BooleanField('التسجيل اليدوي يحتاج موافقة', default=True)
    
    # الصور
    require_photo_on_checkin = models.BooleanField('صورة إلزامية عند الحضور', default=True)
    require_photo_on_checkout = models.BooleanField('صورة إلزامية عند الانصراف', default=False)
    
    # الإشعارات
    send_late_notifications = models.BooleanField('إرسال إشعارات التأخير', default=True)
    send_absent_notifications = models.BooleanField('إرسال إشعارات الغياب', default=True)
    
    # ساعات العمل الافتراضية
    default_work_hours = models.DecimalField('ساعات العمل الافتراضية', max_digits=4, 
                                            decimal_places=2, default=Decimal('8.00'))
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التعديل', auto_now=True)
    
    class Meta:
        verbose_name = 'إعدادات الحضور'
        verbose_name_plural = 'إعدادات الحضور'
    
    def __str__(self):
        return 'إعدادات نظام الحضور'
    
    @classmethod
    def get_settings(cls):
        """الحصول على الإعدادات (أو إنشاء إعدادات افتراضية)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class AttendanceReport(models.Model):
    """تقارير الحضور"""
    title = models.CharField('العنوان', max_length=200)
    report_type = models.CharField('نوع التقرير', max_length=50, choices=[
        ('daily', 'تقرير يومي'),
        ('weekly', 'تقرير أسبوعي'),
        ('monthly', 'تقرير شهري'),
        ('custom', 'تقرير مخصص'),
    ])
    
    start_date = models.DateField('تاريخ البداية')
    end_date = models.DateField('تاريخ النهاية')
    
    # الفلاتر
    users = models.ManyToManyField(User, blank=True, verbose_name='الموظفون',
                                  related_name='attendance_reports')
    locations = models.ManyToManyField(WorkLocation, blank=True, verbose_name='المواقع',
                                      related_name='attendance_reports')
    
    # البيانات المحسوبة
    data = models.JSONField('بيانات التقرير', default=dict, blank=True)
    
    # الملف المُصدّر
    exported_file = models.FileField('ملف التقرير', upload_to='attendance/reports/', 
                                    null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_reports',
                                  verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'تقرير حضور'
        verbose_name_plural = 'تقارير الحضور'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
