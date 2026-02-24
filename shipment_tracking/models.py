"""
نماذج نظام تتبع الشحنات
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator


class ShippingCompany(models.Model):
    """شركات الشحن"""
    name = models.CharField('اسم الشركة', max_length=200)
    name_en = models.CharField('الاسم بالإنجليزية', max_length=200, blank=True)
    logo = models.ImageField('الشعار', upload_to='shipping_companies/', blank=True, null=True)
    phone = models.CharField('الهاتف', max_length=20, blank=True)
    email = models.EmailField('البريد الإلكتروني', blank=True)
    website = models.URLField('الموقع الإلكتروني', blank=True)
    tracking_url_template = models.CharField(
        'رابط التتبع',
        max_length=500,
        blank=True,
        help_text='استخدم {tracking_number} كمتغير، مثل: https://example.com/track/{tracking_number}'
    )
    api_key = models.CharField('API Key', max_length=500, blank=True)
    is_active = models.BooleanField('مفعل', default=True)
    notes = models.TextField('ملاحظات', blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'شركة شحن'
        verbose_name_plural = 'شركات الشحن'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_tracking_url(self, tracking_number):
        """إرجاع رابط التتبع مع رقم الشحنة"""
        if self.tracking_url_template:
            return self.tracking_url_template.replace('{tracking_number}', tracking_number)
        return None


class Shipment(models.Model):
    """الشحنات"""
    
    STATUS_CHOICES = [
        ('pending', '⏳ قيد الانتظار'),
        ('picked_up', '📦 تم الاستلام'),
        ('in_transit', '🚚 قيد النقل'),
        ('out_for_delivery', '🏃 خارج للتوصيل'),
        ('delivered', '✅ تم التسليم'),
        ('failed', '❌ فشل التوصيل'),
        ('returned', '↩️ مرتجع'),
        ('cancelled', '🚫 ملغي'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('prepaid', 'مدفوع مسبقاً'),
        ('cod', 'الدفع عند الاستلام'),
    ]
    
    # معلومات أساسية
    tracking_number = models.CharField(
        'رقم التتبع',
        max_length=100,
        unique=True,
        db_index=True
    )
    reference_number = models.CharField(
        'الرقم المرجعي',
        max_length=100,
        blank=True,
        help_text='رقم الطلب أو الفاتورة'
    )
    shipping_company = models.ForeignKey(
        ShippingCompany,
        on_delete=models.PROTECT,
        verbose_name='شركة الشحن',
        related_name='shipments'
    )
    
    # معلومات المرسل
    sender_name = models.CharField('اسم المرسل', max_length=200)
    sender_phone = models.CharField('هاتف المرسل', max_length=20)
    sender_address = models.TextField('عنوان المرسل')
    sender_city = models.CharField('مدينة المرسل', max_length=100)
    
    # معلومات المستلم
    receiver_name = models.CharField('اسم المستلم', max_length=200)
    receiver_phone = models.CharField('هاتف المستلم', max_length=20)
    receiver_alternate_phone = models.CharField('هاتف بديل', max_length=20, blank=True)
    receiver_email = models.EmailField('بريد المستلم', blank=True)
    receiver_address = models.TextField('عنوان المستلم')
    receiver_city = models.CharField('مدينة المستلم', max_length=100)
    receiver_district = models.CharField('الحي', max_length=100, blank=True)
    receiver_postal_code = models.CharField('الرمز البريدي', max_length=20, blank=True)
    
    # معلومات الشحنة
    description = models.TextField('وصف المحتوى', blank=True)
    weight = models.DecimalField('الوزن (كجم)', max_digits=10, decimal_places=2, null=True, blank=True)
    pieces_count = models.PositiveIntegerField('عدد القطع', default=1)
    declared_value = models.DecimalField('القيمة المعلنة', max_digits=12, decimal_places=2, default=0)
    
    # معلومات الدفع
    payment_method = models.CharField('طريقة الدفع', max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod')
    cod_amount = models.DecimalField('مبلغ الدفع عند الاستلام', max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField('تكلفة الشحن', max_digits=10, decimal_places=2, default=0)
    
    # الحالة والتواريخ
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    current_location = models.CharField('الموقع الحالي', max_length=200, blank=True)
    estimated_delivery_date = models.DateField('تاريخ التسليم المتوقع', null=True, blank=True)
    pickup_date = models.DateTimeField('تاريخ الاستلام', null=True, blank=True)
    delivery_date = models.DateTimeField('تاريخ التسليم الفعلي', null=True, blank=True)
    
    # معلومات إضافية
    notes = models.TextField('ملاحظات', blank=True)
    failure_reason = models.TextField('سبب الفشل', blank=True)
    special_instructions = models.TextField('تعليمات خاصة', blank=True)
    
    # GPS Coordinates (optional)
    current_latitude = models.DecimalField('خط العرض', max_digits=10, decimal_places=7, null=True, blank=True)
    current_longitude = models.DecimalField('خط الطول', max_digits=10, decimal_places=7, null=True, blank=True)
    
    # إشعارات
    customer_notified = models.BooleanField('تم إشعار العميل', default=False)
    last_notification_sent = models.DateTimeField('آخر إشعار', null=True, blank=True)
    
    # النظام
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tracking_created_shipments', verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'شحنة'
        verbose_name_plural = 'الشحنات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tracking_number']),
            models.Index(fields=['status']),
            models.Index(fields=['receiver_phone']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.tracking_number} - {self.receiver_name}"
    
    def get_tracking_url(self):
        """الحصول على رابط التتبع"""
        return self.shipping_company.get_tracking_url(self.tracking_number)
    
    def get_status_display_ar(self):
        """عرض الحالة بالعربي مع الأيقونة"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def is_delivered(self):
        """هل تم التسليم؟"""
        return self.status == 'delivered'
    
    def is_in_progress(self):
        """هل الشحنة قيد التنفيذ؟"""
        return self.status in ['picked_up', 'in_transit', 'out_for_delivery']
    
    def can_be_cancelled(self):
        """هل يمكن إلغاء الشحنة؟"""
        return self.status in ['pending', 'picked_up']


class ShipmentStatusHistory(models.Model):
    """تاريخ حالات الشحنة"""
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name='الشحنة'
    )
    status = models.CharField('الحالة', max_length=20, choices=Shipment.STATUS_CHOICES)
    location = models.CharField('الموقع', max_length=200, blank=True)
    description = models.TextField('الوصف', blank=True)
    notes = models.TextField('ملاحظات', blank=True)
    
    # GPS
    latitude = models.DecimalField('خط العرض', max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField('خط الطول', max_digits=10, decimal_places=7, null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='سجل بواسطة')
    created_at = models.DateTimeField('التاريخ والوقت', auto_now_add=True, db_index=True)
    
    class Meta:
        verbose_name = 'سجل الحالة'
        verbose_name_plural = 'سجل الحالات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.shipment.tracking_number} - {self.get_status_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class ShipmentDocument(models.Model):
    """مستندات الشحنة"""
    
    DOCUMENT_TYPE_CHOICES = [
        ('label', 'بوليصة الشحن'),
        ('invoice', 'الفاتورة'),
        ('pod', 'إثبات التسليم'),
        ('photo', 'صورة'),
        ('signature', 'التوقيع'),
        ('other', 'أخرى'),
    ]
    
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='الشحنة'
    )
    document_type = models.CharField('نوع المستند', max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    title = models.CharField('العنوان', max_length=200)
    file = models.FileField('الملف', upload_to='shipment_documents/%Y/%m/')
    description = models.TextField('الوصف', blank=True)
    
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='رفع بواسطة')
    uploaded_at = models.DateTimeField('تاريخ الرفع', auto_now_add=True)
    
    class Meta:
        verbose_name = 'مستند شحنة'
        verbose_name_plural = 'مستندات الشحنات'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.shipment.tracking_number} - {self.title}"


class ShipmentNotification(models.Model):
    """إشعارات الشحنات"""
    
    NOTIFICATION_TYPE_CHOICES = [
        ('sms', 'رسالة نصية'),
        ('email', 'بريد إلكتروني'),
        ('push', 'إشعار تطبيق'),
        ('whatsapp', 'واتساب'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('sent', 'تم الإرسال'),
        ('failed', 'فشل'),
    ]
    
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='الشحنة'
    )
    notification_type = models.CharField('نوع الإشعار', max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    recipient = models.CharField('المستلم', max_length=200)
    subject = models.CharField('الموضوع', max_length=200, blank=True)
    message = models.TextField('الرسالة')
    status = models.CharField('حالة الإرسال', max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField('رسالة الخطأ', blank=True)
    
    sent_at = models.DateTimeField('تاريخ الإرسال', null=True, blank=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'إشعار شحنة'
        verbose_name_plural = 'إشعارات الشحنات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.shipment.tracking_number} - {self.get_notification_type_display()}"
