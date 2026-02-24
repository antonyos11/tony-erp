"""
نماذج الدردشة الداخلية
Internal Chat Models
"""

from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class ChatRoom(models.Model):
    """غرفة الدردشة"""
    
    ROOM_TYPES = [
        ('private', 'خاص'),
        ('group', 'مجموعة'),
        ('channel', 'قناة'),
        ('department', 'قسم'),
        ('project', 'مشروع'),
    ]
    
    uuid = models.UUIDField('المعرف الفريد', default=uuid.uuid4, unique=True)
    name = models.CharField('الاسم', max_length=200, blank=True)
    description = models.TextField('الوصف', blank=True)
    
    room_type = models.CharField('نوع الغرفة', max_length=20, choices=ROOM_TYPES, default='private')
    
    # المشاركون
    participants = models.ManyToManyField(
        User,
        through='ChatParticipant',
        related_name='chat_rooms',
        verbose_name='المشاركون'
    )
    
    # الإعدادات
    avatar = models.ImageField('الصورة', upload_to='chat/rooms/', blank=True)
    is_archived = models.BooleanField('مؤرشفة', default=False)
    is_muted = models.BooleanField('مكتومة', default=False)
    
    # للقنوات
    is_public = models.BooleanField('عامة', default=False)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_rooms',
        verbose_name='أنشئت بواسطة'
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'غرفة دردشة'
        verbose_name_plural = 'غرف الدردشة'
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name or f"محادثة {self.uuid}"
    
    def get_display_name(self, for_user=None):
        """الحصول على اسم العرض"""
        if self.name:
            return self.name
        
        if self.room_type == 'private' and for_user:
            other = self.participants.exclude(id=for_user.id).first()
            if other:
                return other.get_full_name() or other.username
        
        return f"محادثة #{self.id}"


class ChatParticipant(models.Model):
    """مشارك في الدردشة"""
    
    ROLES = [
        ('member', 'عضو'),
        ('admin', 'مدير'),
        ('owner', 'مالك'),
    ]
    
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    role = models.CharField('الدور', max_length=20, choices=ROLES, default='member')
    
    # الإعدادات
    is_muted = models.BooleanField('مكتوم', default=False)
    is_pinned = models.BooleanField('مثبت', default=False)
    notifications_enabled = models.BooleanField('الإشعارات', default=True)
    
    # آخر قراءة
    last_read_at = models.DateTimeField('آخر قراءة', null=True, blank=True)
    
    joined_at = models.DateTimeField('تاريخ الانضمام', auto_now_add=True)
    
    class Meta:
        verbose_name = 'مشارك'
        verbose_name_plural = 'المشاركون'
        unique_together = ['room', 'user']
    
    def __str__(self):
        return f"{self.user.username} - {self.room}"


class Message(models.Model):
    """رسالة"""
    
    MESSAGE_TYPES = [
        ('text', 'نص'),
        ('image', 'صورة'),
        ('file', 'ملف'),
        ('audio', 'صوت'),
        ('video', 'فيديو'),
        ('system', 'نظام'),
        ('reply', 'رد'),
    ]
    
    uuid = models.UUIDField('المعرف الفريد', default=uuid.uuid4, unique=True)
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='الغرفة'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages',
        verbose_name='المرسل'
    )
    
    message_type = models.CharField('نوع الرسالة', max_length=20, choices=MESSAGE_TYPES, default='text')
    content = models.TextField('المحتوى')
    
    # المرفقات
    attachment = models.FileField('المرفق', upload_to='chat/attachments/', blank=True)
    attachment_name = models.CharField('اسم المرفق', max_length=255, blank=True)
    attachment_size = models.IntegerField('حجم المرفق', default=0)
    
    # الرد على رسالة
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='رد على'
    )
    
    # التعديل
    is_edited = models.BooleanField('معدلة', default=False)
    edited_at = models.DateTimeField('تاريخ التعديل', null=True, blank=True)
    
    # الحذف
    is_deleted = models.BooleanField('محذوفة', default=False)
    deleted_at = models.DateTimeField('تاريخ الحذف', null=True, blank=True)
    
    created_at = models.DateTimeField('تاريخ الإرسال', auto_now_add=True)
    
    class Meta:
        verbose_name = 'رسالة'
        verbose_name_plural = 'الرسائل'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender}: {self.content[:50]}"


class MessageReaction(models.Model):
    """تفاعل مع الرسالة"""
    
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='reactions',
        verbose_name='الرسالة'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='المستخدم'
    )
    
    emoji = models.CharField('الإيموجي', max_length=10)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'تفاعل'
        verbose_name_plural = 'التفاعلات'
        unique_together = ['message', 'user', 'emoji']
    
    def __str__(self):
        return f"{self.user.username}: {self.emoji}"


class MessageRead(models.Model):
    """قراءة الرسالة"""
    
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='reads',
        verbose_name='الرسالة'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='المستخدم'
    )
    read_at = models.DateTimeField('تاريخ القراءة', auto_now_add=True)
    
    class Meta:
        verbose_name = 'قراءة'
        verbose_name_plural = 'القراءات'
        unique_together = ['message', 'user']


class ChatSettings(models.Model):
    """إعدادات الدردشة للمستخدم"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='chat_settings',
        verbose_name='المستخدم'
    )
    
    # الإشعارات
    sound_enabled = models.BooleanField('الصوت', default=True)
    desktop_notifications = models.BooleanField('إشعارات سطح المكتب', default=True)
    email_notifications = models.BooleanField('إشعارات البريد', default=False)
    
    # الخصوصية
    show_online_status = models.BooleanField('إظهار الحالة', default=True)
    show_read_receipts = models.BooleanField('إظهار علامة القراءة', default=True)
    
    # المظهر
    chat_theme = models.CharField('السمة', max_length=20, default='default')
    message_size = models.CharField('حجم الخط', max_length=20, default='medium')
    
    # الحالة
    status = models.CharField('الحالة', max_length=50, default='متاح')
    custom_status = models.CharField('حالة مخصصة', max_length=100, blank=True)
    
    class Meta:
        verbose_name = 'إعدادات دردشة'
        verbose_name_plural = 'إعدادات الدردشة'
    
    def __str__(self):
        return f"إعدادات {self.user.username}"


class OnlineStatus(models.Model):
    """حالة الاتصال"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='online_status',
        verbose_name='المستخدم'
    )
    
    is_online = models.BooleanField('متصل', default=False)
    last_seen = models.DateTimeField('آخر ظهور', auto_now=True)
    
    class Meta:
        verbose_name = 'حالة اتصال'
        verbose_name_plural = 'حالات الاتصال'
    
    def __str__(self):
        return f"{self.user.username}: {'متصل' if self.is_online else 'غير متصل'}"
