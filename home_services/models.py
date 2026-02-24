"""
نماذج الخدمات المنزلية - طلبات الصيانة والنظافة
Tony ERP Home Services
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
from datetime import time
import uuid

User = get_user_model()


class ServiceType(models.Model):
    """أنواع الخدمات المنزلية"""
    SERVICE_CATEGORIES = [
        ('maintenance', _('صيانة')),
        ('cleaning', _('نظافة')),
        ('other', _('أخرى')),
    ]
    
    name = models.CharField(_('اسم الخدمة'), max_length=200)
    code = models.CharField(_('كود الخدمة'), max_length=50, unique=True)
    category = models.CharField(_('التصنيف'), max_length=20, choices=SERVICE_CATEGORIES)
    description = models.TextField(_('الوصف'), blank=True)
    icon = models.CharField(_('الأيقونة'), max_length=50, default='bi-tools')
    image = models.ImageField(_('الصورة'), upload_to='home_services/types/', blank=True, null=True)
    
    # التسعير
    base_price = models.DecimalField(_('السعر الأساسي'), max_digits=10, decimal_places=2, default=Decimal('0'))
    price_per_hour = models.DecimalField(_('السعر بالساعة'), max_digits=10, decimal_places=2, default=Decimal('0'))
    min_price = models.DecimalField(_('الحد الأدنى للسعر'), max_digits=10, decimal_places=2, default=Decimal('0'))
    
    # الإعدادات
    estimated_duration_hours = models.DecimalField(_('المدة التقديرية (ساعات)'), max_digits=5, decimal_places=2, default=Decimal('1'))
    requires_inspection = models.BooleanField(_('يتطلب معاينة'), default=False)
    is_active = models.BooleanField(_('نشط'), default=True)
    sort_order = models.PositiveIntegerField(_('ترتيب العرض'), default=0)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('نوع خدمة')
        verbose_name_plural = _('أنواع الخدمات')
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


class MaintenanceCategory(models.Model):
    """فئات الصيانة"""
    name = models.CharField(_('اسم الفئة'), max_length=200)
    code = models.CharField(_('كود الفئة'), max_length=50, unique=True)
    description = models.TextField(_('الوصف'), blank=True)
    icon = models.CharField(_('الأيقونة'), max_length=50, default='bi-wrench')
    is_active = models.BooleanField(_('نشط'), default=True)
    sort_order = models.PositiveIntegerField(_('ترتيب العرض'), default=0)
    
    class Meta:
        verbose_name = _('فئة صيانة')
        verbose_name_plural = _('فئات الصيانة')
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


class CleaningPackage(models.Model):
    """باقات النظافة"""
    name = models.CharField(_('اسم الباقة'), max_length=200)
    code = models.CharField(_('كود الباقة'), max_length=50, unique=True)
    description = models.TextField(_('الوصف'), blank=True)
    
    # التفاصيل
    includes = models.TextField(_('تشمل'), blank=True, help_text=_('ما تشمله الباقة'))
    excludes = models.TextField(_('لا تشمل'), blank=True, help_text=_('ما لا تشمله الباقة'))
    
    # التسعير
    price = models.DecimalField(_('السعر'), max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(_('سعر الخصم'), max_digits=10, decimal_places=2, null=True, blank=True)
    
    # المدة
    duration_hours = models.DecimalField(_('المدة (ساعات)'), max_digits=5, decimal_places=2, default=Decimal('2'))
    workers_count = models.PositiveIntegerField(_('عدد العمال'), default=1)
    
    # الإعدادات
    is_active = models.BooleanField(_('نشط'), default=True)
    is_featured = models.BooleanField(_('مميز'), default=False)
    sort_order = models.PositiveIntegerField(_('ترتيب العرض'), default=0)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('باقة نظافة')
        verbose_name_plural = _('باقات النظافة')
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    @property
    def effective_price(self):
        """السعر الفعلي"""
        return self.discount_price if self.discount_price else self.price


class ServiceRequest(models.Model):
    """طلب خدمة منزلية (صيانة أو نظافة)"""
    
    REQUEST_TYPES = [
        ('maintenance', _('طلب صيانة')),
        ('cleaning', _('طلب نظافة')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('قيد الانتظار')),
        ('confirmed', _('مؤكد')),
        ('assigned', _('تم التعيين')),
        ('in_progress', _('قيد التنفيذ')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
        ('rejected', _('مرفوض')),
    ]
    
    PAYMENT_STATUS = [
        ('pending', _('في انتظار الدفع')),
        ('paid', _('مدفوع')),
        ('refunded', _('مسترجع')),
    ]
    
    URGENCY_LEVELS = [
        ('normal', _('عادي')),
        ('urgent', _('عاجل')),
        ('emergency', _('طوارئ')),
    ]
    
    # الرقم والنوع
    request_number = models.CharField(_('رقم الطلب'), max_length=50, unique=True)
    request_type = models.CharField(_('نوع الطلب'), max_length=20, choices=REQUEST_TYPES)
    
    # المستخدم
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                            related_name='service_requests', verbose_name=_('المستخدم'))
    
    # بيانات العميل
    customer_name = models.CharField(_('اسم العميل'), max_length=200)
    customer_phone = models.CharField(_('رقم الهاتف'), max_length=20)
    customer_email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    customer_whatsapp = models.CharField(_('رقم الواتساب'), max_length=20, blank=True)
    
    # العنوان
    address = models.TextField(_('العنوان'))
    city = models.CharField(_('المدينة'), max_length=100)
    district = models.CharField(_('الحي'), max_length=100, blank=True)
    building_type = models.CharField(_('نوع المبنى'), max_length=100, blank=True,
                                     help_text=_('شقة، فيلا، مكتب، إلخ'))
    
    # تفاصيل الخدمة
    service_type = models.ForeignKey(ServiceType, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='requests', verbose_name=_('نوع الخدمة'))
    maintenance_category = models.ForeignKey(MaintenanceCategory, on_delete=models.SET_NULL, 
                                              null=True, blank=True, verbose_name=_('فئة الصيانة'))
    cleaning_package = models.ForeignKey(CleaningPackage, on_delete=models.SET_NULL,
                                          null=True, blank=True, verbose_name=_('باقة النظافة'))
    
    # وصف المشكلة/الطلب
    title = models.CharField(_('عنوان الطلب'), max_length=300)
    description = models.TextField(_('وصف تفصيلي'))
    
    # الموعد المطلوب
    preferred_date = models.DateField(_('التاريخ المفضل'))
    preferred_time_from = models.TimeField(_('من الساعة'), null=True, blank=True)
    preferred_time_to = models.TimeField(_('إلى الساعة'), null=True, blank=True)
    urgency = models.CharField(_('درجة الاستعجال'), max_length=20, choices=URGENCY_LEVELS, default='normal')
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(_('حالة الدفع'), max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # التسعير
    estimated_price = models.DecimalField(_('السعر التقديري'), max_digits=10, decimal_places=2, 
                                           null=True, blank=True)
    final_price = models.DecimalField(_('السعر النهائي'), max_digits=10, decimal_places=2,
                                       null=True, blank=True)
    discount = models.DecimalField(_('الخصم'), max_digits=10, decimal_places=2, default=Decimal('0'))
    
    # الفني/العامل المعين
    assigned_worker = models.ForeignKey('hr.Employee', on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='assigned_service_requests', verbose_name=_('الفني المعين'))
    
    # التنفيذ
    started_at = models.DateTimeField(_('وقت البدء'), null=True, blank=True)
    completed_at = models.DateTimeField(_('وقت الإنتهاء'), null=True, blank=True)
    actual_duration_hours = models.DecimalField(_('المدة الفعلية (ساعات)'), max_digits=5, decimal_places=2,
                                                 null=True, blank=True)
    
    # الملاحظات
    customer_notes = models.TextField(_('ملاحظات العميل'), blank=True)
    worker_notes = models.TextField(_('ملاحظات الفني'), blank=True)
    admin_notes = models.TextField(_('ملاحظات الإدارة'), blank=True)
    
    # التقييم
    rating = models.PositiveIntegerField(_('التقييم'), null=True, blank=True,
                                         choices=[(i, str(i)) for i in range(1, 6)])
    review = models.TextField(_('ملاحظات التقييم'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('طلب خدمة')
        verbose_name_plural = _('طلبات الخدمات')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.request_number} - {self.get_request_type_display()}"
    
    def save(self, *args, **kwargs):
        if not self.request_number:
            prefix = 'MNT' if self.request_type == 'maintenance' else 'CLN'
            self.request_number = f"{prefix}-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
        super().save(*args, **kwargs)


class RequestImage(models.Model):
    """صور مرفقة بطلب الخدمة"""
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, 
                                related_name='images', verbose_name=_('الطلب'))
    image = models.ImageField(_('الصورة'), upload_to='home_services/requests/')
    description = models.CharField(_('وصف الصورة'), max_length=200, blank=True)
    uploaded_at = models.DateTimeField(_('تاريخ الرفع'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('صورة الطلب')
        verbose_name_plural = _('صور الطلب')


class ServiceArea(models.Model):
    """مناطق الخدمة المتاحة"""
    name = models.CharField(_('اسم المنطقة'), max_length=200)
    city = models.CharField(_('المدينة'), max_length=100)
    is_active = models.BooleanField(_('نشط'), default=True)
    extra_charge = models.DecimalField(_('رسوم إضافية'), max_digits=10, decimal_places=2, default=Decimal('0'))
    
    class Meta:
        verbose_name = _('منطقة خدمة')
        verbose_name_plural = _('مناطق الخدمة')
    
    def __str__(self):
        return f"{self.name} - {self.city}"


class ServiceWorker(models.Model):
    """عمال وفنيي الخدمات"""
    employee = models.OneToOneField('hr.Employee', on_delete=models.CASCADE,
                                     related_name='service_worker_profile', verbose_name=_('الموظف'))
    
    # التخصصات
    specializations = models.ManyToManyField(ServiceType, blank=True,
                                              related_name='workers', verbose_name=_('التخصصات'))
    maintenance_categories = models.ManyToManyField(MaintenanceCategory, blank=True,
                                                     related_name='workers', verbose_name=_('فئات الصيانة'))
    
    # الموقع
    service_areas = models.ManyToManyField(ServiceArea, blank=True,
                                            related_name='workers', verbose_name=_('مناطق الخدمة'))
    
    # التقييم
    average_rating = models.DecimalField(_('متوسط التقييم'), max_digits=3, decimal_places=2, default=Decimal('0'))
    total_jobs = models.PositiveIntegerField(_('إجمالي الأعمال'), default=0)
    completed_jobs = models.PositiveIntegerField(_('الأعمال المكتملة'), default=0)
    
    is_available = models.BooleanField(_('متاح'), default=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    
    class Meta:
        verbose_name = _('فني خدمة')
        verbose_name_plural = _('فنيو الخدمة')
    
    def __str__(self):
        return str(self.employee)


class HomeServicesSettings(models.Model):
    """إعدادات خدمات الصيانة والنظافة"""
    
    # إعدادات عامة
    enable_maintenance = models.BooleanField(_('تفعيل خدمة الصيانة'), default=True)
    enable_cleaning = models.BooleanField(_('تفعيل خدمة النظافة'), default=True)
    
    # أوقات العمل
    working_hours_start = models.TimeField(_('بداية العمل'), default=time(8, 0))
    working_hours_end = models.TimeField(_('نهاية العمل'), default=time(22, 0))
    
    # التسعير
    emergency_surcharge_percent = models.DecimalField(_('نسبة رسوم الطوارئ %'), max_digits=5, decimal_places=2, default=Decimal('50'))
    urgent_surcharge_percent = models.DecimalField(_('نسبة رسوم العاجل %'), max_digits=5, decimal_places=2, default=Decimal('25'))
    
    # الحجز
    min_booking_hours_advance = models.PositiveIntegerField(_('الحد الأدنى للحجز (ساعات مسبقة)'), default=2)
    max_booking_days_advance = models.PositiveIntegerField(_('الحد الأقصى للحجز (أيام مسبقة)'), default=30)
    
    # التواصل
    contact_phone = models.CharField(_('رقم التواصل'), max_length=20, blank=True)
    contact_whatsapp = models.CharField(_('رقم الواتساب'), max_length=20, blank=True)
    contact_email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    
    # رسائل
    confirmation_message = models.TextField(_('رسالة التأكيد'), blank=True,
                                             default='شكراً لك! تم استلام طلبك وسيتم التواصل معك قريباً.')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('إعدادات الخدمات المنزلية')
        verbose_name_plural = _('إعدادات الخدمات المنزلية')
    
    @classmethod
    def get_settings(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
