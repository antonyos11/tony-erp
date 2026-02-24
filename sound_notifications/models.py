"""
نماذج نظام الإشعارات الصوتية
Sound Notifications Models
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator

User = get_user_model()


class SoundTheme(models.Model):
    """سمات الأصوات"""
    
    name = models.CharField('اسم السمة', max_length=100)
    description = models.TextField('الوصف', blank=True)
    is_default = models.BooleanField('افتراضي', default=False)
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'سمة أصوات'
        verbose_name_plural = 'سمات الأصوات'
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.is_default:
            SoundTheme.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class NotificationSound(models.Model):
    """أصوات الإشعارات"""
    
    SOUND_TYPES = [
        ('new_order', 'طلب جديد'),
        ('new_invoice', 'فاتورة جديدة'),
        ('payment_received', 'دفعة مستلمة'),
        ('low_stock', 'مخزون منخفض'),
        ('approval_needed', 'موافقة مطلوبة'),
        ('task_assigned', 'مهمة جديدة'),
        ('message_received', 'رسالة جديدة'),
        ('reminder', 'تذكير'),
        ('error', 'خطأ'),
        ('success', 'نجاح'),
        ('warning', 'تحذير'),
        ('chat', 'دردشة'),
        ('call', 'مكالمة'),
        ('meeting', 'اجتماع'),
        ('birthday', 'عيد ميلاد'),
        ('contract_expiry', 'انتهاء عقد'),
        ('custom', 'مخصص'),
    ]
    
    theme = models.ForeignKey(
        SoundTheme,
        on_delete=models.CASCADE,
        related_name='sounds',
        verbose_name='السمة'
    )
    sound_type = models.CharField('نوع الصوت', max_length=50, choices=SOUND_TYPES)
    name = models.CharField('اسم الصوت', max_length=100)
    sound_file = models.FileField(
        'ملف الصوت',
        upload_to='sounds/notifications/',
        validators=[FileExtensionValidator(['mp3', 'wav', 'ogg', 'webm'])]
    )
    volume = models.IntegerField('مستوى الصوت', default=80)  # 0-100
    duration = models.FloatField('المدة (ثواني)', default=1.0)
    is_active = models.BooleanField('نشط', default=True)
    
    class Meta:
        verbose_name = 'صوت إشعار'
        verbose_name_plural = 'أصوات الإشعارات'
        unique_together = ['theme', 'sound_type']
        ordering = ['theme', 'sound_type']
    
    def __str__(self):
        return f"{self.theme.name} - {self.get_sound_type_display()}"


class UserSoundPreference(models.Model):
    """تفضيلات الصوت للمستخدم"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='sound_preferences',
        verbose_name='المستخدم'
    )
    is_enabled = models.BooleanField('تفعيل الأصوات', default=True)
    theme = models.ForeignKey(
        SoundTheme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='السمة المختارة'
    )
    master_volume = models.IntegerField('مستوى الصوت العام', default=80)
    
    # تخصيص كل نوع
    enable_new_order = models.BooleanField('صوت الطلب الجديد', default=True)
    enable_payment = models.BooleanField('صوت الدفع', default=True)
    enable_low_stock = models.BooleanField('صوت المخزون المنخفض', default=True)
    enable_approval = models.BooleanField('صوت الموافقات', default=True)
    enable_tasks = models.BooleanField('صوت المهام', default=True)
    enable_messages = models.BooleanField('صوت الرسائل', default=True)
    enable_reminders = models.BooleanField('صوت التذكيرات', default=True)
    enable_chat = models.BooleanField('صوت الدردشة', default=True)
    enable_calls = models.BooleanField('صوت المكالمات', default=True)
    
    # أوقات عدم الإزعاج
    do_not_disturb = models.BooleanField('وضع عدم الإزعاج', default=False)
    dnd_start_time = models.TimeField('بداية عدم الإزعاج', null=True, blank=True)
    dnd_end_time = models.TimeField('نهاية عدم الإزعاج', null=True, blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'تفضيلات صوت المستخدم'
        verbose_name_plural = 'تفضيلات أصوات المستخدمين'
    
    def __str__(self):
        return f"تفضيلات {self.user.username}"
    
    def is_sound_enabled(self, sound_type):
        """التحقق من تفعيل صوت معين"""
        if not self.is_enabled or self.do_not_disturb:
            return False
        
        mapping = {
            'new_order': self.enable_new_order,
            'new_invoice': self.enable_new_order,
            'payment_received': self.enable_payment,
            'low_stock': self.enable_low_stock,
            'approval_needed': self.enable_approval,
            'task_assigned': self.enable_tasks,
            'message_received': self.enable_messages,
            'reminder': self.enable_reminders,
            'chat': self.enable_chat,
            'call': self.enable_calls,
        }
        
        return mapping.get(sound_type, True)


class SoundLog(models.Model):
    """سجل تشغيل الأصوات"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sound_logs',
        verbose_name='المستخدم'
    )
    sound_type = models.CharField('نوع الصوت', max_length=50)
    played_at = models.DateTimeField('وقت التشغيل', auto_now_add=True)
    was_muted = models.BooleanField('كان مكتوم', default=False)
    
    class Meta:
        verbose_name = 'سجل صوت'
        verbose_name_plural = 'سجل الأصوات'
        ordering = ['-played_at']
