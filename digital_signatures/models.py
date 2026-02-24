"""
نماذج التوقيعات الرقمية
Digital Signatures Models
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import hashlib
import uuid

User = get_user_model()


class SignatureProfile(models.Model):
    """ملف التوقيع للمستخدم"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='signature_profile',
        verbose_name='المستخدم'
    )
    
    # التوقيع المحفوظ
    signature_image = models.ImageField(
        'صورة التوقيع',
        upload_to='signatures/profiles/',
        blank=True
    )
    signature_data = models.TextField('بيانات التوقيع (Base64)', blank=True)
    
    # الختم
    stamp_image = models.ImageField(
        'صورة الختم',
        upload_to='signatures/stamps/',
        blank=True
    )
    
    # الأحرف الأولى
    initials_image = models.ImageField(
        'صورة الأحرف الأولى',
        upload_to='signatures/initials/',
        blank=True
    )
    initials_data = models.TextField('بيانات الأحرف الأولى (Base64)', blank=True)
    
    # إعدادات
    default_font = models.CharField('الخط الافتراضي', max_length=100, default='Tajawal')
    default_color = models.CharField('اللون الافتراضي', max_length=20, default='#000000')
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'ملف توقيع'
        verbose_name_plural = 'ملفات التوقيعات'
    
    def __str__(self):
        return f"توقيع {self.user.username}"


class SignatureRequest(models.Model):
    """طلب توقيع"""
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('pending', 'قيد الانتظار'),
        ('signed', 'تم التوقيع'),
        ('rejected', 'مرفوض'),
        ('expired', 'منتهي الصلاحية'),
        ('cancelled', 'ملغي'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'منخفضة'),
        ('normal', 'عادية'),
        ('high', 'عالية'),
        ('urgent', 'عاجلة'),
    ]
    
    # المعرف الفريد
    uuid = models.UUIDField('المعرف الفريد', default=uuid.uuid4, unique=True)
    
    # المرسل
    requester = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_signature_requests',
        verbose_name='الطالب'
    )
    
    # المستند
    title = models.CharField('العنوان', max_length=200)
    description = models.TextField('الوصف', blank=True)
    document = models.FileField('المستند', upload_to='signatures/documents/')
    
    # الربط بكيان
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # الحالة
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField('الأولوية', max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # التواريخ
    expires_at = models.DateTimeField('ينتهي في', null=True, blank=True)
    completed_at = models.DateTimeField('اكتمل في', null=True, blank=True)
    
    # الأمان
    document_hash = models.CharField('تجزئة المستند', max_length=64, blank=True)
    
    # الرسالة
    message = models.TextField('رسالة للموقعين', blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'طلب توقيع'
        verbose_name_plural = 'طلبات التوقيع'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.document and not self.document_hash:
            self.document_hash = self._calculate_hash()
        super().save(*args, **kwargs)
    
    def _calculate_hash(self):
        """حساب تجزئة المستند"""
        sha256 = hashlib.sha256()
        for chunk in self.document.chunks():
            sha256.update(chunk)
        return sha256.hexdigest()


class Signer(models.Model):
    """الموقع"""
    
    ROLE_CHOICES = [
        ('signer', 'موقّع'),
        ('approver', 'موافق'),
        ('viewer', 'مشاهد'),
        ('cc', 'نسخة'),
    ]
    
    request = models.ForeignKey(
        SignatureRequest,
        on_delete=models.CASCADE,
        related_name='signers',
        verbose_name='طلب التوقيع'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='signature_assignments',
        verbose_name='المستخدم',
        null=True,
        blank=True
    )
    email = models.EmailField('البريد الإلكتروني', blank=True)
    name = models.CharField('الاسم', max_length=100, blank=True)
    
    role = models.CharField('الدور', max_length=20, choices=ROLE_CHOICES, default='signer')
    order = models.IntegerField('الترتيب', default=0)
    
    # الحالة
    is_signed = models.BooleanField('تم التوقيع', default=False)
    signed_at = models.DateTimeField('وقت التوقيع', null=True, blank=True)
    
    is_rejected = models.BooleanField('تم الرفض', default=False)
    rejection_reason = models.TextField('سبب الرفض', blank=True)
    
    # الإشعارات
    notification_sent = models.BooleanField('تم إرسال الإشعار', default=False)
    reminder_count = models.IntegerField('عدد التذكيرات', default=0)
    
    # رمز التحقق للموقعين الخارجيين
    access_token = models.CharField('رمز الوصول', max_length=100, blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'موقّع'
        verbose_name_plural = 'الموقّعون'
        ordering = ['order']
    
    def __str__(self):
        return self.user.username if self.user else self.email


class SignatureField(models.Model):
    """حقل التوقيع في المستند"""
    
    FIELD_TYPES = [
        ('signature', 'توقيع'),
        ('initials', 'أحرف أولى'),
        ('date', 'تاريخ'),
        ('text', 'نص'),
        ('checkbox', 'خانة اختيار'),
        ('stamp', 'ختم'),
    ]
    
    request = models.ForeignKey(
        SignatureRequest,
        on_delete=models.CASCADE,
        related_name='fields',
        verbose_name='طلب التوقيع'
    )
    signer = models.ForeignKey(
        Signer,
        on_delete=models.CASCADE,
        related_name='fields',
        verbose_name='الموقّع'
    )
    
    field_type = models.CharField('نوع الحقل', max_length=20, choices=FIELD_TYPES)
    name = models.CharField('اسم الحقل', max_length=100, blank=True)
    
    # الموقع
    page = models.IntegerField('رقم الصفحة', default=1)
    x = models.FloatField('الموقع X', default=0)
    y = models.FloatField('الموقع Y', default=0)
    width = models.FloatField('العرض', default=200)
    height = models.FloatField('الارتفاع', default=50)
    
    # القيمة
    value = models.TextField('القيمة', blank=True)
    
    is_required = models.BooleanField('مطلوب', default=True)
    is_filled = models.BooleanField('تم الملء', default=False)
    filled_at = models.DateTimeField('وقت الملء', null=True, blank=True)
    
    class Meta:
        verbose_name = 'حقل توقيع'
        verbose_name_plural = 'حقول التوقيع'
    
    def __str__(self):
        return f"{self.get_field_type_display()} - {self.signer}"


class Signature(models.Model):
    """التوقيع الفعلي"""
    
    field = models.OneToOneField(
        SignatureField,
        on_delete=models.CASCADE,
        related_name='signature',
        verbose_name='الحقل'
    )
    signer = models.ForeignKey(
        Signer,
        on_delete=models.CASCADE,
        related_name='signatures',
        verbose_name='الموقّع'
    )
    
    # بيانات التوقيع
    signature_data = models.TextField('بيانات التوقيع (Base64)')
    signature_image = models.ImageField(
        'صورة التوقيع',
        upload_to='signatures/signed/',
        blank=True
    )
    
    # معلومات التحقق
    ip_address = models.GenericIPAddressField('عنوان IP', null=True, blank=True)
    user_agent = models.TextField('المتصفح', blank=True)
    geolocation = models.JSONField('الموقع الجغرافي', default=dict)
    
    # التجزئة
    signature_hash = models.CharField('تجزئة التوقيع', max_length=64)
    
    created_at = models.DateTimeField('تاريخ التوقيع', auto_now_add=True)
    
    class Meta:
        verbose_name = 'توقيع'
        verbose_name_plural = 'التوقيعات'
    
    def __str__(self):
        return f"توقيع {self.signer}"
    
    def save(self, *args, **kwargs):
        if not self.signature_hash:
            self.signature_hash = hashlib.sha256(
                self.signature_data.encode()
            ).hexdigest()
        super().save(*args, **kwargs)


class SignatureAuditLog(models.Model):
    """سجل مراجعة التوقيعات"""
    
    ACTION_CHOICES = [
        ('created', 'تم الإنشاء'),
        ('sent', 'تم الإرسال'),
        ('viewed', 'تم العرض'),
        ('signed', 'تم التوقيع'),
        ('rejected', 'تم الرفض'),
        ('reminder_sent', 'تم إرسال تذكير'),
        ('completed', 'اكتمل'),
        ('cancelled', 'تم الإلغاء'),
        ('downloaded', 'تم التحميل'),
    ]
    
    request = models.ForeignKey(
        SignatureRequest,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        verbose_name='طلب التوقيع'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='المستخدم'
    )
    
    action = models.CharField('الإجراء', max_length=20, choices=ACTION_CHOICES)
    details = models.TextField('التفاصيل', blank=True)
    
    ip_address = models.GenericIPAddressField('عنوان IP', null=True, blank=True)
    user_agent = models.TextField('المتصفح', blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'سجل مراجعة'
        verbose_name_plural = 'سجلات المراجعة'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.request.title}"


class SignatureTemplate(models.Model):
    """قوالب التوقيع"""
    
    name = models.CharField('اسم القالب', max_length=200)
    description = models.TextField('الوصف', blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='signature_templates',
        verbose_name='أنشئ بواسطة'
    )
    
    # المستند
    document = models.FileField('المستند', upload_to='signatures/templates/')
    
    # حقول التوقيع المحددة مسبقاً
    fields_config = models.JSONField('تكوين الحقول', default=list)
    
    # إعدادات
    default_message = models.TextField('الرسالة الافتراضية', blank=True)
    default_expiry_days = models.IntegerField('أيام الانتهاء الافتراضية', default=7)
    
    is_active = models.BooleanField('نشط', default=True)
    usage_count = models.IntegerField('عدد الاستخدامات', default=0)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'قالب توقيع'
        verbose_name_plural = 'قوالب التوقيع'
        ordering = ['-usage_count', 'name']
    
    def __str__(self):
        return self.name
