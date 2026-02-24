"""
نماذج النسخ الاحتياطي السحابي
Cloud Backup Models
"""

from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class CloudProvider(models.Model):
    """مزود التخزين السحابي"""
    
    PROVIDERS = [
        ('google_drive', 'Google Drive'),
        ('dropbox', 'Dropbox'),
        ('onedrive', 'OneDrive'),
        ('aws_s3', 'Amazon S3'),
        ('azure_blob', 'Azure Blob'),
        ('ftp', 'FTP Server'),
        ('local', 'Local Storage'),
    ]
    
    name = models.CharField('الاسم', max_length=100)
    provider_type = models.CharField('نوع المزود', max_length=30, choices=PROVIDERS)
    
    # بيانات الاعتماد (مشفرة)
    credentials = models.JSONField('بيانات الاعتماد', default=dict)
    
    # الإعدادات
    config = models.JSONField('الإعدادات', default=dict)
    folder_path = models.CharField('مسار المجلد', max_length=500, default='/backups')
    
    is_active = models.BooleanField('نشط', default=True)
    is_default = models.BooleanField('الافتراضي', default=False)
    
    # الحالة
    last_connection = models.DateTimeField('آخر اتصال', null=True, blank=True)
    connection_status = models.BooleanField('حالة الاتصال', default=False)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'مزود سحابي'
        verbose_name_plural = 'مزودون سحابيون'
    
    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()})"


class BackupSchedule(models.Model):
    """جدول النسخ الاحتياطي"""
    
    FREQUENCY_CHOICES = [
        ('hourly', 'كل ساعة'),
        ('daily', 'يومي'),
        ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'),
    ]
    
    BACKUP_TYPES = [
        ('full', 'كامل'),
        ('incremental', 'تزايدي'),
        ('differential', 'تفاضلي'),
    ]
    
    name = models.CharField('الاسم', max_length=200)
    description = models.TextField('الوصف', blank=True)
    
    provider = models.ForeignKey(
        CloudProvider,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='مزود التخزين'
    )
    
    backup_type = models.CharField('نوع النسخ', max_length=20, choices=BACKUP_TYPES, default='full')
    frequency = models.CharField('التكرار', max_length=20, choices=FREQUENCY_CHOICES, default='daily')
    
    # التوقيت
    time_of_day = models.TimeField('وقت التنفيذ', default='02:00')
    day_of_week = models.IntegerField('يوم الأسبوع', null=True, blank=True)  # 0-6
    day_of_month = models.IntegerField('يوم الشهر', null=True, blank=True)  # 1-31
    
    # ما يتم نسخه
    include_database = models.BooleanField('قاعدة البيانات', default=True)
    include_media = models.BooleanField('ملفات الوسائط', default=True)
    include_static = models.BooleanField('الملفات الثابتة', default=False)
    include_logs = models.BooleanField('سجلات النظام', default=False)
    custom_paths = models.JSONField('مسارات مخصصة', default=list)
    
    # الاحتفاظ
    retention_days = models.IntegerField('أيام الاحتفاظ', default=30)
    max_backups = models.IntegerField('أقصى عدد نسخ', default=10)
    
    # الإشعارات
    notify_on_success = models.BooleanField('إشعار عند النجاح', default=False)
    notify_on_failure = models.BooleanField('إشعار عند الفشل', default=True)
    notification_emails = models.JSONField('البريد الإلكتروني للإشعارات', default=list)
    
    # الحالة
    is_active = models.BooleanField('نشط', default=True)
    last_run = models.DateTimeField('آخر تشغيل', null=True, blank=True)
    next_run = models.DateTimeField('التشغيل القادم', null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'جدول نسخ احتياطي'
        verbose_name_plural = 'جداول النسخ الاحتياطي'
    
    def __str__(self):
        return self.name


class Backup(models.Model):
    """النسخة الاحتياطية"""
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('running', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('failed', 'فشل'),
        ('cancelled', 'ملغي'),
    ]
    
    uuid = models.UUIDField('المعرف الفريد', default=uuid.uuid4, unique=True)
    
    schedule = models.ForeignKey(
        BackupSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='backups',
        verbose_name='الجدول'
    )
    provider = models.ForeignKey(
        CloudProvider,
        on_delete=models.CASCADE,
        related_name='backups',
        verbose_name='مزود التخزين'
    )
    
    # المعلومات
    name = models.CharField('الاسم', max_length=200)
    backup_type = models.CharField('نوع النسخ', max_length=20, default='full')
    
    # الحالة
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField('التقدم %', default=0)
    
    # الملفات
    file_path = models.CharField('مسار الملف', max_length=500, blank=True)
    file_size = models.BigIntegerField('حجم الملف (بايت)', default=0)
    files_count = models.IntegerField('عدد الملفات', default=0)
    
    # التفاصيل
    includes_database = models.BooleanField('يتضمن قاعدة البيانات', default=True)
    includes_media = models.BooleanField('يتضمن الوسائط', default=True)
    
    # التشفير
    is_encrypted = models.BooleanField('مشفر', default=True)
    encryption_key_hash = models.CharField('تجزئة مفتاح التشفير', max_length=64, blank=True)
    
    # سجلات
    log = models.TextField('السجل', blank=True)
    error_message = models.TextField('رسالة الخطأ', blank=True)
    
    # التوقيت
    started_at = models.DateTimeField('بدأ في', null=True, blank=True)
    completed_at = models.DateTimeField('اكتمل في', null=True, blank=True)
    duration_seconds = models.IntegerField('المدة (ثانية)', default=0)
    
    # الاستعادة
    restore_count = models.IntegerField('عدد مرات الاستعادة', default=0)
    last_restored = models.DateTimeField('آخر استعادة', null=True, blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='أنشئ بواسطة'
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'نسخة احتياطية'
        verbose_name_plural = 'النسخ الاحتياطية'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def file_size_display(self):
        """عرض الحجم بشكل مقروء"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"


class RestorePoint(models.Model):
    """نقطة استعادة"""
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('running', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('failed', 'فشل'),
    ]
    
    backup = models.ForeignKey(
        Backup,
        on_delete=models.CASCADE,
        related_name='restore_points',
        verbose_name='النسخة الاحتياطية'
    )
    
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # ماذا يتم استعادته
    restore_database = models.BooleanField('استعادة قاعدة البيانات', default=True)
    restore_media = models.BooleanField('استعادة الوسائط', default=True)
    restore_to_path = models.CharField('استعادة إلى', max_length=500, blank=True)
    
    # السجلات
    log = models.TextField('السجل', blank=True)
    error_message = models.TextField('رسالة الخطأ', blank=True)
    
    started_at = models.DateTimeField('بدأ في', null=True, blank=True)
    completed_at = models.DateTimeField('اكتمل في', null=True, blank=True)
    
    initiated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='بدأ بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'نقطة استعادة'
        verbose_name_plural = 'نقاط الاستعادة'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"استعادة {self.backup.name}"


class BackupSettings(models.Model):
    """إعدادات النسخ الاحتياطي"""
    
    # التشفير
    encryption_enabled = models.BooleanField('التشفير مفعل', default=True)
    encryption_algorithm = models.CharField('خوارزمية التشفير', max_length=20, default='AES-256')
    
    # الضغط
    compression_enabled = models.BooleanField('الضغط مفعل', default=True)
    compression_level = models.IntegerField('مستوى الضغط', default=6)  # 1-9
    
    # المسارات المستثناة
    excluded_paths = models.JSONField('المسارات المستثناة', default=list)
    excluded_extensions = models.JSONField('الامتدادات المستثناة', default=list)
    
    # الإشعارات الافتراضية
    default_notify_emails = models.JSONField('البريد الافتراضي للإشعارات', default=list)
    
    # الاحتفاظ الافتراضي
    default_retention_days = models.IntegerField('أيام الاحتفاظ الافتراضية', default=30)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'إعدادات النسخ الاحتياطي'
        verbose_name_plural = 'إعدادات النسخ الاحتياطي'
    
    def __str__(self):
        return "إعدادات النسخ الاحتياطي"
