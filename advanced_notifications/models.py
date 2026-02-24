"""
نظام الإشعارات والرسائل المتقدمة
Advanced Notifications and Messaging System
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import URLValidator
import uuid


class MessageTemplate(models.Model):
    """قوالب الرسائل"""
    
    CHANNEL_CHOICES = [
        ('email', _('البريد الإلكتروني')),
        ('sms', _('الرسائل النصية')),
        ('whatsapp', _('واتس آب')),
        ('push', _('إشعار فوري')),
        ('in_app', _('داخل التطبيق')),
    ]
    
    TRIGGER_CHOICES = [
        ('invoice_created', _('إنشاء فاتورة')),
        ('payment_received', _('استقبال دفعة')),
        ('order_shipped', _('شحن طلب')),
        ('low_stock', _('مخزون منخفض')),
        ('task_assigned', _('تعيين مهمة')),
        ('payment_due', _('موعد الدفع')),
        ('contract_expiring', _('انتهاء العقد قريباً')),
        ('policy_expiring', _('انتهاء البوليصة قريباً')),
        ('custom', _('مخصص')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('الاسم'), max_length=200)
    channel = models.CharField(_('القناة'), max_length=20, choices=CHANNEL_CHOICES)
    trigger_event = models.CharField(_('حدث الفعل'), max_length=50, choices=TRIGGER_CHOICES)
    
    # محتوى الرسالة
    subject = models.CharField(_('الموضوع'), max_length=200, blank=True)
    body = models.TextField(_('المحتوى'))
    footer = models.TextField(_('التذييل'), blank=True)
    
    # الخصائص
    is_active = models.BooleanField(_('نشطة'), default=True)
    priority = models.CharField(_('الأولوية'), max_length=20,
                               choices=[('low', _('منخفضة')), ('normal', _('عادية')), 
                                      ('high', _('عالية')), ('urgent', _('عاجلة'))])
    
    # المتغيرات المتاحة
    available_variables = models.TextField(_('المتغيرات المتاحة'), help_text='مثل: {customer_name}, {amount}, {date}')
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('قالب رسالة')
        verbose_name_plural = _('قوالب الرسائل')
        unique_together = ['name', 'channel']
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_display()})"


class NotificationSchedule(models.Model):
    """جدولة الإشعارات"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(MessageTemplate, on_delete=models.CASCADE, related_name='schedules')
    
    name = models.CharField(_('اسم الجدولة'), max_length=200)
    is_active = models.BooleanField(_('نشطة'), default=True)
    
    # نوع الجدولة
    schedule_type = models.CharField(_('نوع الجدولة'), max_length=50,
                                    choices=[('immediate', _('فوري')), 
                                            ('delayed', _('مؤجل')),
                                            ('recurring', _('متكرر')),
                                            ('scheduled', _('مجدول'))])
    
    # الفترات الزمنية (للجداول المؤجلة والمتكررة)
    delay_hours = models.IntegerField(_('تأخير (ساعات)'), null=True, blank=True)
    recurrence_pattern = models.CharField(_('نمط التكرار'), max_length=100, blank=True,
                                         help_text='مثل: daily, weekly, monthly')
    max_retries = models.IntegerField(_('محاولات إعادة الإرسال'), default=3)
    
    # الأوقات المسموحة
    quiet_hours_start = models.TimeField(_('بداية أوقات الهدوء'), null=True, blank=True)
    quiet_hours_end = models.TimeField(_('نهاية أوقات الهدوء'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('جدولة إشعار')
        verbose_name_plural = _('جدولة الإشعارات')
    
    def __str__(self):
        return self.name


class SentNotification(models.Model):
    """الإشعارات المرسلة"""
    
    STATUS_CHOICES = [
        ('pending', _('قيد الانتظار')),
        ('sending', _('قيد الإرسال')),
        ('sent', _('مرسلة')),
        ('failed', _('فشلت')),
        ('bounced', _('مرتدة')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(MessageTemplate, on_delete=models.SET_NULL, null=True)
    
    recipient_email = models.EmailField(_('بريد المستقبل'), blank=True)
    recipient_phone = models.CharField(_('هاتف المستقبل'), max_length=20, blank=True)
    recipient = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    subject = models.CharField(_('الموضوع'), max_length=200, blank=True)
    body = models.TextField(_('المحتوى'))
    
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    sent_at = models.DateTimeField(_('تاريخ الإرسال'), null=True, blank=True)
    error_message = models.TextField(_('رسالة الخطأ'), blank=True)
    retry_count = models.IntegerField(_('عدد المحاولات'), default=0)
    
    # التتبع
    delivery_status = models.CharField(_('حالة التوصيل'), max_length=50, blank=True)
    opened_at = models.DateTimeField(_('تاريخ الفتح'), null=True, blank=True)
    clicked_at = models.DateTimeField(_('تاريخ النقر'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('إشعار مرسل')
        verbose_name_plural = _('الإشعارات المرسلة')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['recipient']),
        ]
    
    def __str__(self):
        return f"{self.template.name if self.template else 'Custom'} - {self.status}"


class NotificationPreference(models.Model):
    """تفضيلات الإشعارات"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='notification_preferences')
    
    # تفضيلات القنوات
    email_enabled = models.BooleanField(_('تفعيل البريد الإلكتروني'), default=True)
    sms_enabled = models.BooleanField(_('تفعيل الرسائل النصية'), default=True)
    whatsapp_enabled = models.BooleanField(_('تفعيل واتس آب'), default=False)
    push_enabled = models.BooleanField(_('تفعيل الإشعارات الفورية'), default=True)
    in_app_enabled = models.BooleanField(_('تفعيل الإشعارات داخل التطبيق'), default=True)
    
    # أنواع الإشعارات
    invoice_notifications = models.BooleanField(_('إشعارات الفواتير'), default=True)
    payment_notifications = models.BooleanField(_('إشعارات الدفعات'), default=True)
    inventory_notifications = models.BooleanField(_('إشعارات المخزون'), default=True)
    task_notifications = models.BooleanField(_('إشعارات المهام'), default=True)
    system_notifications = models.BooleanField(_('الإشعارات النظامية'), default=True)
    
    # أوقات الهدوء
    quiet_hours_enabled = models.BooleanField(_('تفعيل أوقات الهدوء'), default=False)
    quiet_hours_start = models.TimeField(_('بداية أوقات الهدوء'), null=True, blank=True)
    quiet_hours_end = models.TimeField(_('نهاية أوقات الهدوء'), null=True, blank=True)
    
    updated_at = models.DateTimeField(_('آخر تحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('تفضيل الإشعارات')
        verbose_name_plural = _('تفضيلات الإشعارات')
    
    def __str__(self):
        return f"تفضيلات {self.user}"


class SMSProvider(models.Model):
    """موفري خدمة SMS"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('الاسم'), max_length=200)
    api_key = models.CharField(_('مفتاح API'), max_length=255)
    api_secret = models.CharField(_('سر API'), max_length=255, blank=True)
    endpoint_url = models.URLField(_('رابط API'))
    
    is_active = models.BooleanField(_('نشط'), default=True)
    priority = models.IntegerField(_('الأولوية'), default=0)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('موفر SMS')
        verbose_name_plural = _('موفري SMS')
        ordering = ['-priority']
    
    def __str__(self):
        return self.name


class WhatsAppProvider(models.Model):
    """موفري خدمة WhatsApp"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('الاسم'), max_length=200)
    api_key = models.CharField(_('مفتاح API'), max_length=255)
    phone_number_id = models.CharField(_('رقم الهاتف'), max_length=50)
    business_account_id = models.CharField(_('رقم الحساب التجاري'), max_length=100)
    
    is_active = models.BooleanField(_('نشط'), default=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('موفر WhatsApp')
        verbose_name_plural = _('موفري WhatsApp')
    
    def __str__(self):
        return self.name
