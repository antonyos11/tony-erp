"""
نماذج مكالمات الفيديو
Video Calls Models
"""

from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class VideoRoom(models.Model):
    """غرفة الفيديو"""
    
    ROOM_TYPES = [
        ('instant', 'فوري'),
        ('scheduled', 'مجدول'),
        ('recurring', 'متكرر'),
    ]
    
    uuid = models.UUIDField('المعرف الفريد', default=uuid.uuid4, unique=True)
    name = models.CharField('اسم الغرفة', max_length=200)
    description = models.TextField('الوصف', blank=True)
    
    room_type = models.CharField('نوع الغرفة', max_length=20, choices=ROOM_TYPES, default='instant')
    
    # المضيف
    host = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='hosted_video_rooms',
        verbose_name='المضيف'
    )
    
    # المشاركون
    participants = models.ManyToManyField(
        User,
        through='VideoParticipant',
        related_name='video_rooms',
        verbose_name='المشاركون'
    )
    
    # الإعدادات
    max_participants = models.IntegerField('أقصى عدد مشاركين', default=10)
    is_recording_enabled = models.BooleanField('تسجيل مفعل', default=False)
    is_chat_enabled = models.BooleanField('الدردشة مفعلة', default=True)
    is_screen_share_enabled = models.BooleanField('مشاركة الشاشة', default=True)
    
    # الجدولة
    scheduled_at = models.DateTimeField('موعد الاجتماع', null=True, blank=True)
    duration_minutes = models.IntegerField('المدة (دقيقة)', default=60)
    
    # كلمة المرور
    password = models.CharField('كلمة المرور', max_length=50, blank=True)
    
    # الحالة
    is_active = models.BooleanField('نشط', default=True)
    started_at = models.DateTimeField('بدأ في', null=True, blank=True)
    ended_at = models.DateTimeField('انتهى في', null=True, blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'غرفة فيديو'
        verbose_name_plural = 'غرف الفيديو'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def join_url(self):
        return f"/video/join/{self.uuid}/"


class VideoParticipant(models.Model):
    """مشارك في مكالمة الفيديو"""
    
    ROLES = [
        ('host', 'مضيف'),
        ('co_host', 'مضيف مشارك'),
        ('participant', 'مشارك'),
        ('viewer', 'مشاهد'),
    ]
    
    room = models.ForeignKey(VideoRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    role = models.CharField('الدور', max_length=20, choices=ROLES, default='participant')
    
    # الحالة
    is_connected = models.BooleanField('متصل', default=False)
    is_muted = models.BooleanField('صامت', default=False)
    is_video_on = models.BooleanField('الفيديو مفعل', default=True)
    is_screen_sharing = models.BooleanField('يشارك الشاشة', default=False)
    
    joined_at = models.DateTimeField('انضم في', null=True, blank=True)
    left_at = models.DateTimeField('غادر في', null=True, blank=True)
    
    class Meta:
        verbose_name = 'مشارك فيديو'
        verbose_name_plural = 'مشاركو الفيديو'
        unique_together = ['room', 'user']
    
    def __str__(self):
        return f"{self.user.username} - {self.room.name}"


class VideoRecording(models.Model):
    """تسجيل الفيديو"""
    
    room = models.ForeignKey(
        VideoRoom,
        on_delete=models.CASCADE,
        related_name='recordings',
        verbose_name='الغرفة'
    )
    
    file = models.FileField('ملف التسجيل', upload_to='video_calls/recordings/')
    duration_seconds = models.IntegerField('المدة (ثانية)', default=0)
    file_size = models.BigIntegerField('حجم الملف', default=0)
    
    recorded_at = models.DateTimeField('تاريخ التسجيل', auto_now_add=True)
    
    class Meta:
        verbose_name = 'تسجيل'
        verbose_name_plural = 'التسجيلات'
    
    def __str__(self):
        return f"تسجيل {self.room.name}"


class VideoMessage(models.Model):
    """رسالة في مكالمة الفيديو"""
    
    room = models.ForeignKey(
        VideoRoom,
        on_delete=models.CASCADE,
        related_name='video_messages',
        verbose_name='الغرفة'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='المرسل'
    )
    
    content = models.TextField('المحتوى')
    created_at = models.DateTimeField('تاريخ الإرسال', auto_now_add=True)
    
    class Meta:
        verbose_name = 'رسالة فيديو'
        verbose_name_plural = 'رسائل الفيديو'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
