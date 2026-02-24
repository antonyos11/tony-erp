"""
نماذج نظام التصدير والنسخ الاحتياطية
"""
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _  # Added for i18n


class BackupRecord(models.Model):
    """سجل النسخ الاحتياطية"""
    BACKUP_TYPES = [
        ('manual', _('يدوي')),
        ('scheduled', _('مجدول')),
        ('automatic', _('تلقائي')),
    ]
    
    BACKUP_STATUS = [
        ('in_progress', _('جاري التنفيذ')),
        ('completed', _('مكتمل')),
        ('failed', _('فشل')),
    ]
    
    backup_name = models.CharField(_('اسم النسخة الاحتياطية'), max_length=255)
    backup_type = models.CharField(_('نوع النسخة'), max_length=20, choices=BACKUP_TYPES)
    file_path = models.CharField(_('مسار الملف'), max_length=500)
    file_size = models.BigIntegerField(_('حجم الملف (بايت)'), default=0)
    status = models.CharField(_('الحالة'), max_length=20, choices=BACKUP_STATUS, default='in_progress')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    completed_at = models.DateTimeField(_('تاريخ الاكتمال'), null=True, blank=True)
    error_message = models.TextField(_('رسالة الخطأ'), blank=True)
    includes_media = models.BooleanField(_('يتضمن الملفات'), default=True)
    includes_database = models.BooleanField(_('يتضمن قاعدة البيانات'), default=True)
    
    class Meta:
        verbose_name = _('نسخة احتياطية')
        verbose_name_plural = _('النسخ الاحتياطية')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.backup_name


class DataExport(models.Model):
    """تصدير البيانات"""
    EXPORT_FORMATS = [
        ('csv', _('CSV')),
        ('excel', _('Excel')),
        ('pdf', _('PDF')),
        ('json', _('JSON')),
    ]
    
    EXPORT_STATUS = [
        ('pending', _('معلق')),
        ('processing', _('جاري المعالجة')),
        ('completed', _('مكتمل')),
        ('failed', _('فشل')),
    ]
    
    export_name = models.CharField(_('اسم التصدير'), max_length=255)
    export_type = models.CharField(_('نوع البيانات'), max_length=50)  # sales, inventory, hr, etc
    export_format = models.CharField(_('تنسيق التصدير'), max_length=10, choices=EXPORT_FORMATS)
    parameters = models.JSONField(_('معايير التصدير'), default=dict, blank=True)
    file_path = models.CharField(_('مسار الملف'), max_length=500, blank=True)
    file_size = models.BigIntegerField(_('حجم الملف (بايت)'), default=0)
    status = models.CharField(_('الحالة'), max_length=20, choices=EXPORT_STATUS, default='pending')
    progress = models.IntegerField(_('نسبة التقدم %'), default=0)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('طلب بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الطلب'), auto_now_add=True)
    completed_at = models.DateTimeField(_('تاريخ الاكتمال'), null=True, blank=True)
    download_count = models.IntegerField(_('عدد مرات التحميل'), default=0)
    expires_at = models.DateTimeField(_('ينتهي في'), null=True, blank=True)
    error_message = models.TextField(_('رسالة الخطأ'), blank=True)
    
    class Meta:
        verbose_name = _('تصدير بيانات')
        verbose_name_plural = _('تصدير البيانات')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.export_name} ({self.get_export_format_display()})"

    def mark_progress(self, value: int):
        self.progress = max(0, min(100, value))
        self.save(update_fields=['progress'])

    def mark_failed(self, error: str):
        self.status = 'failed'
        self.error_message = error[:2000]
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at'])

    def mark_completed(self, file_path: str, file_size: int):
        self.status = 'completed'
        self.file_path = file_path
        self.file_size = file_size
        self.progress = 100
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'file_path', 'file_size', 'progress', 'completed_at'])

    def set_default_expiry(self, hours: int):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=hours)
            self.save(update_fields=['expires_at'])