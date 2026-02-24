"""
نماذج نظام المهام والتذكيرات
Tasks & Reminders Models
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class TaskCategory(models.Model):
    """فئات المهام"""
    
    name = models.CharField('اسم الفئة', max_length=100)
    color = models.CharField('اللون', max_length=20, default='primary')
    icon = models.CharField('الأيقونة', max_length=50, default='fas fa-tasks')
    description = models.TextField('الوصف', blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_categories',
        verbose_name='أنشئ بواسطة'
    )
    is_system = models.BooleanField('فئة نظام', default=False)
    is_active = models.BooleanField('نشط', default=True)
    
    class Meta:
        verbose_name = 'فئة مهام'
        verbose_name_plural = 'فئات المهام'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class TaskList(models.Model):
    """قوائم المهام"""
    
    name = models.CharField('اسم القائمة', max_length=100)
    description = models.TextField('الوصف', blank=True)
    color = models.CharField('اللون', max_length=20, default='primary')
    icon = models.CharField('الأيقونة', max_length=50, default='fas fa-list')
    
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_task_lists',
        verbose_name='المالك'
    )
    shared_with = models.ManyToManyField(
        User,
        related_name='shared_task_lists',
        blank=True,
        verbose_name='مشترك مع'
    )
    
    is_default = models.BooleanField('افتراضية', default=False)
    is_active = models.BooleanField('نشطة', default=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'قائمة مهام'
        verbose_name_plural = 'قوائم المهام'
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return self.name


class Task(models.Model):
    """المهام"""
    
    PRIORITY_CHOICES = [
        ('low', 'منخفضة'),
        ('medium', 'متوسطة'),
        ('high', 'عالية'),
        ('urgent', 'عاجلة'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتملة'),
        ('cancelled', 'ملغاة'),
        ('on_hold', 'معلقة'),
    ]
    
    REPEAT_CHOICES = [
        ('none', 'بدون تكرار'),
        ('daily', 'يومياً'),
        ('weekly', 'أسبوعياً'),
        ('monthly', 'شهرياً'),
        ('yearly', 'سنوياً'),
        ('custom', 'مخصص'),
    ]
    
    title = models.CharField('العنوان', max_length=200)
    description = models.TextField('الوصف', blank=True)
    
    task_list = models.ForeignKey(
        TaskList,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='القائمة',
        null=True,
        blank=True
    )
    category = models.ForeignKey(
        TaskCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name='الفئة'
    )
    
    # الأشخاص
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tasks',
        verbose_name='أنشئ بواسطة'
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name='مُسند إلى'
    )
    
    # الحالة والأولوية
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField('الأولوية', max_length=10, choices=PRIORITY_CHOICES, default='medium')
    progress = models.IntegerField('نسبة الإنجاز', default=0)
    
    # التواريخ
    due_date = models.DateTimeField('تاريخ الاستحقاق', null=True, blank=True)
    start_date = models.DateTimeField('تاريخ البداية', null=True, blank=True)
    completed_at = models.DateTimeField('تاريخ الإكمال', null=True, blank=True)
    
    # التكرار
    repeat_type = models.CharField('نوع التكرار', max_length=10, choices=REPEAT_CHOICES, default='none')
    repeat_interval = models.IntegerField('فترة التكرار', default=1)
    repeat_until = models.DateField('تكرار حتى', null=True, blank=True)
    
    # الربط بكيانات أخرى
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # إضافات
    tags = models.JSONField('الوسوم', default=list)
    estimated_hours = models.FloatField('الساعات المقدرة', null=True, blank=True)
    actual_hours = models.FloatField('الساعات الفعلية', null=True, blank=True)
    
    is_pinned = models.BooleanField('مثبتة', default=False)
    is_archived = models.BooleanField('مؤرشفة', default=False)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'مهمة'
        verbose_name_plural = 'المهام'
        ordering = ['-is_pinned', 'due_date', '-priority', '-created_at']
    
    def __str__(self):
        return self.title
    
    def is_overdue(self):
        """هل المهمة متأخرة؟"""
        if self.due_date and self.status not in ['completed', 'cancelled']:
            from django.utils import timezone
            return self.due_date < timezone.now()
        return False


class SubTask(models.Model):
    """المهام الفرعية"""
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='subtasks',
        verbose_name='المهمة الرئيسية'
    )
    title = models.CharField('العنوان', max_length=200)
    is_completed = models.BooleanField('مكتملة', default=False)
    completed_at = models.DateTimeField('تاريخ الإكمال', null=True, blank=True)
    order = models.IntegerField('الترتيب', default=0)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'مهمة فرعية'
        verbose_name_plural = 'المهام الفرعية'
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return self.title


class TaskComment(models.Model):
    """تعليقات المهام"""
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='المهمة'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='task_comments',
        verbose_name='المستخدم'
    )
    content = models.TextField('المحتوى')
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'تعليق'
        verbose_name_plural = 'التعليقات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"تعليق على {self.task.title}"


class TaskAttachment(models.Model):
    """مرفقات المهام"""
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='المهمة'
    )
    file = models.FileField('الملف', upload_to='tasks/attachments/')
    name = models.CharField('الاسم', max_length=200)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='رُفع بواسطة'
    )
    
    created_at = models.DateTimeField('تاريخ الرفع', auto_now_add=True)
    
    class Meta:
        verbose_name = 'مرفق'
        verbose_name_plural = 'المرفقات'
    
    def __str__(self):
        return self.name


class Reminder(models.Model):
    """التذكيرات"""
    
    REMINDER_TYPES = [
        ('task', 'مهمة'),
        ('event', 'حدث'),
        ('meeting', 'اجتماع'),
        ('deadline', 'موعد نهائي'),
        ('follow_up', 'متابعة'),
        ('custom', 'مخصص'),
    ]
    
    NOTIFICATION_CHANNELS = [
        ('app', 'التطبيق'),
        ('email', 'البريد الإلكتروني'),
        ('sms', 'رسالة نصية'),
        ('push', 'إشعار دفع'),
        ('all', 'الجميع'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reminders',
        verbose_name='المستخدم'
    )
    title = models.CharField('العنوان', max_length=200)
    description = models.TextField('الوصف', blank=True)
    
    reminder_type = models.CharField('نوع التذكير', max_length=20, choices=REMINDER_TYPES, default='custom')
    notification_channel = models.CharField('قناة الإشعار', max_length=10, choices=NOTIFICATION_CHANNELS, default='app')
    
    # الربط بمهمة
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reminders',
        verbose_name='المهمة'
    )
    
    # التوقيت
    remind_at = models.DateTimeField('وقت التذكير')
    snoozed_until = models.DateTimeField('مؤجل حتى', null=True, blank=True)
    
    # التكرار
    is_recurring = models.BooleanField('متكرر', default=False)
    recurrence_rule = models.CharField('قاعدة التكرار', max_length=100, blank=True)
    
    # الحالة
    is_sent = models.BooleanField('تم الإرسال', default=False)
    sent_at = models.DateTimeField('وقت الإرسال', null=True, blank=True)
    is_dismissed = models.BooleanField('تم التجاهل', default=False)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'تذكير'
        verbose_name_plural = 'التذكيرات'
        ordering = ['remind_at']
    
    def __str__(self):
        return self.title


class TaskHistory(models.Model):
    """سجل تغييرات المهام"""
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name='المهمة'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='المستخدم'
    )
    action = models.CharField('الإجراء', max_length=50)
    old_value = models.TextField('القيمة القديمة', blank=True)
    new_value = models.TextField('القيمة الجديدة', blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'سجل مهمة'
        verbose_name_plural = 'سجل المهام'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action} - {self.task.title}"
