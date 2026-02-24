"""
نظام إدارة المراسلات
Correspondence Management System
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class Correspondence(models.Model):
    """المراسلات (رسائل واردة/صادرة)"""
    
    TYPE_CHOICES = [
        ('incoming', _('واردة')),
        ('outgoing', _('صادرة')),
    ]
    
    STATUS_CHOICES = [
        ('received', _('مستلمة')),
        ('opened', _('مفتوحة')),
        ('reviewed', _('تمت مراجعتها')),
        ('replied', _('تمت الإجابة عليها')),
        ('closed', _('مغلقة')),
        ('archived', _('مؤرشفة')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('منخفضة')),
        ('normal', _('عادية')),
        ('high', _('عالية')),
        ('urgent', _('عاجلة')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_number = models.CharField(_('رقم المرجع'), max_length=100, unique=True)
    
    # نوع المراسلة
    correspondence_type = models.CharField(_('النوع'), max_length=20, choices=TYPE_CHOICES)
    priority = models.CharField(_('الأولوية'), max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # المعلومات الأساسية
    subject = models.CharField(_('الموضوع'), max_length=200)
    description = models.TextField(_('الوصف'))
    
    # الأطراف
    sender = models.CharField(_('المرسل'), max_length=200)
    recipient = models.CharField(_('المستقبل'), max_length=200)
    
    # التصنيف
    category = models.CharField(_('الفئة'), max_length=100, blank=True)
    tags = models.CharField(_('الوسوم'), max_length=200, blank=True)
    
    # الملفات
    attachments = models.FileField(_('الملفات المرفقة'), upload_to='correspondence/', blank=True)
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='received')
    
    # التواريخ
    received_date = models.DateField(_('تاريخ الاستقبال'))
    reviewed_date = models.DateField(_('تاريخ المراجعة'), null=True, blank=True)
    response_date = models.DateField(_('تاريخ الرد'), null=True, blank=True)
    
    # المسؤولون
    assigned_to = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_correspondence')
    
    # الملاحظات
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('مراسلة')
        verbose_name_plural = _('المراسلات')
        ordering = ['-received_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['correspondence_type']),
            models.Index(fields=['received_date']),
        ]
    
    def __str__(self):
        return f"{self.reference_number} - {self.subject}"
    
    def mark_as_reviewed(self):
        """وضع علامة على أنها تمت مراجعتها"""
        from django.utils import timezone
        self.status = 'reviewed'
        self.reviewed_date = timezone.now().date()
        self.save()


class CorrespondenceThread(models.Model):
    """سلسلة المراسلات (متسلسلة الرد)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_correspondence = models.OneToOneField(Correspondence, on_delete=models.CASCADE, 
                                                  related_name='thread', primary_key=False)
    
    # الردود
    replies = models.ManyToManyField(Correspondence, blank=True, related_name='reply_to_thread')
    
    # الحالة الكلية
    is_resolved = models.BooleanField(_('تم حلها'), default=False)
    resolution_date = models.DateField(_('تاريخ الحل'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('سلسلة مراسلات')
        verbose_name_plural = _('سلاسل المراسلات')
    
    def __str__(self):
        return f"سلسلة - {self.original_correspondence.subject}"


class CorrespondenceArchive(models.Model):
    """أرشيف المراسلات"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    correspondence = models.OneToOneField(Correspondence, on_delete=models.CASCADE, related_name='archive')
    
    # تفاصيل الأرشيف
    archive_date = models.DateField(_('تاريخ الأرشفة'), auto_now_add=True)
    archive_location = models.CharField(_('موقع الأرشيف'), max_length=200)
    
    # الفهرسة
    indexed_keywords = models.TextField(_('الكلمات المفتاحية'), blank=True)
    
    # الصلاحيات
    access_restricted = models.BooleanField(_('وصول مقيد'), default=False)
    allowed_users = models.ManyToManyField('auth.User', blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('أرشيف مراسلة')
        verbose_name_plural = _('أرشيف المراسلات')
    
    def __str__(self):
        return f"أرشيف - {self.correspondence.reference_number}"


class CorrespondenceTemplate(models.Model):
    """قوالب المراسلات"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('الاسم'), max_length=200)
    category = models.CharField(_('الفئة'), max_length=100)
    
    # المحتوى
    subject_template = models.CharField(_('قالب الموضوع'), max_length=200)
    body_template = models.TextField(_('قالب المحتوى'))
    
    # المتغيرات المتاحة
    available_variables = models.TextField(_('المتغيرات المتاحة'), 
                                          help_text='مثل: {sender_name}, {date}, {subject}')
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('قالب مراسلة')
        verbose_name_plural = _('قوالب المراسلات')
    
    def __str__(self):
        return self.name
