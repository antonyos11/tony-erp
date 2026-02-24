from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class Notification(models.Model):
    LEVELS = [
        ('info', _('معلومة')),
        ('success', _('نجاح')),
        ('warning', _('تحذير')),
        ('error', _('خطأ')),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='notifications', null=True, blank=True, verbose_name=_('المستخدم'))
    title = models.CharField(max_length=200, verbose_name=_('العنوان'))
    message = models.TextField(verbose_name=_('النص'))
    level = models.CharField(max_length=20, choices=LEVELS, default='info', verbose_name=_('المستوى'))
    is_read = models.BooleanField(default=False, verbose_name=_('مقروء'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))

    class Meta:
        verbose_name = _('إشعار')
        verbose_name_plural = _('الإشعارات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
            models.Index(fields=['level', 'is_read']),
        ]

    def __str__(self):
        return f"{self.title} ({self.level})"