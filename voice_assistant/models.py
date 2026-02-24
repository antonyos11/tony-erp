"""
نماذج المساعد الصوتي الذكي
Voice Assistant Models
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class VoiceCommand(models.Model):
    """أوامر صوتية مسجلة"""
    
    COMMAND_TYPES = [
        ('navigation', 'تنقل'),
        ('create', 'إنشاء'),
        ('search', 'بحث'),
        ('report', 'تقرير'),
        ('action', 'إجراء'),
        ('query', 'استعلام'),
        ('custom', 'مخصص'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'قيد المعالجة'),
        ('success', 'تم بنجاح'),
        ('failed', 'فشل'),
        ('partial', 'جزئي'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='voice_commands',
        verbose_name='المستخدم'
    )
    command_text = models.TextField('نص الأمر')
    command_type = models.CharField('نوع الأمر', max_length=20, choices=COMMAND_TYPES)
    
    # معلومات المعالجة
    detected_intent = models.CharField('النية المكتشفة', max_length=100, blank=True)
    extracted_entities = models.JSONField('الكيانات المستخرجة', default=dict)
    confidence = models.FloatField('مستوى الثقة', default=0.0)
    
    # النتيجة
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    response_text = models.TextField('نص الرد', blank=True)
    action_taken = models.CharField('الإجراء المتخذ', max_length=200, blank=True)
    redirect_url = models.CharField('رابط التوجيه', max_length=500, blank=True)
    
    # البيانات الصوتية
    audio_duration = models.FloatField('مدة الصوت (ثواني)', null=True, blank=True)
    language = models.CharField('اللغة', max_length=10, default='ar')
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    processed_at = models.DateTimeField('تاريخ المعالجة', null=True, blank=True)
    
    class Meta:
        verbose_name = 'أمر صوتي'
        verbose_name_plural = 'الأوامر الصوتية'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.command_text[:50]}"


class VoiceCommandTemplate(models.Model):
    """قوالب الأوامر الصوتية"""
    
    name = models.CharField('اسم القالب', max_length=100)
    trigger_phrases = models.JSONField('عبارات التفعيل', default=list)
    command_type = models.CharField('نوع الأمر', max_length=20)
    
    # الإجراء
    action_type = models.CharField('نوع الإجراء', max_length=50)
    action_url = models.CharField('رابط الإجراء', max_length=500, blank=True)
    action_params = models.JSONField('معاملات الإجراء', default=dict)
    
    # الرد
    response_template = models.TextField('قالب الرد')
    
    is_active = models.BooleanField('نشط', default=True)
    priority = models.IntegerField('الأولوية', default=0)
    
    class Meta:
        verbose_name = 'قالب أمر صوتي'
        verbose_name_plural = 'قوالب الأوامر الصوتية'
        ordering = ['-priority', 'name']
    
    def __str__(self):
        return self.name


class UserVoicePreference(models.Model):
    """تفضيلات المستخدم للمساعد الصوتي"""
    
    VOICE_CHOICES = [
        ('male_ar', 'ذكر - عربي'),
        ('female_ar', 'أنثى - عربية'),
        ('male_en', 'ذكر - إنجليزي'),
        ('female_en', 'أنثى - إنجليزية'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='voice_preference',
        verbose_name='المستخدم'
    )
    
    is_enabled = models.BooleanField('تفعيل المساعد', default=True)
    voice_type = models.CharField('نوع الصوت', max_length=20, choices=VOICE_CHOICES, default='female_ar')
    speech_rate = models.FloatField('سرعة الكلام', default=1.0)
    pitch = models.FloatField('نبرة الصوت', default=1.0)
    
    # تفضيلات الإدخال
    auto_listen = models.BooleanField('استماع تلقائي', default=False)
    wake_word = models.CharField('كلمة التنبيه', max_length=50, default='يا نظام')
    language = models.CharField('لغة التعرف', max_length=10, default='ar-SA')
    
    # تفضيلات الإخراج
    read_responses = models.BooleanField('قراءة الردود', default=True)
    confirm_actions = models.BooleanField('تأكيد الإجراءات', default=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'تفضيلات المساعد الصوتي'
        verbose_name_plural = 'تفضيلات المساعد الصوتي'
    
    def __str__(self):
        return f"تفضيلات {self.user.username}"


class VoiceShortcut(models.Model):
    """اختصارات صوتية مخصصة للمستخدم"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='voice_shortcuts',
        verbose_name='المستخدم'
    )
    trigger_phrase = models.CharField('عبارة التفعيل', max_length=200)
    action_url = models.CharField('رابط الإجراء', max_length=500)
    description = models.CharField('الوصف', max_length=200, blank=True)
    is_active = models.BooleanField('نشط', default=True)
    usage_count = models.IntegerField('عدد الاستخدامات', default=0)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'اختصار صوتي'
        verbose_name_plural = 'الاختصارات الصوتية'
        unique_together = ['user', 'trigger_phrase']
    
    def __str__(self):
        return f"{self.trigger_phrase} -> {self.action_url}"
