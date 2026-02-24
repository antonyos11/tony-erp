from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class AuditLog(models.Model):
    """سجل التدقيق"""
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_CHOICES = [
        (ACTION_CREATE, 'إنشاء'),
        (ACTION_UPDATE, 'تحديث'),
        (ACTION_DELETE, 'حذف'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('المستخدم'))
    action = models.CharField(_('الإجراء'), max_length=20, choices=ACTION_CHOICES, default=ACTION_UPDATE)
    action_type = models.CharField(_('نوع الإجراء'), max_length=50, blank=True)
    model_name = models.CharField(_('اسم النموذج'), max_length=100, blank=True)
    app_label = models.CharField(_('التطبيق'), max_length=100, blank=True)
    object_id = models.CharField(_('معرف الكائن'), max_length=100, blank=True)
    object_repr = models.CharField(_('وصف الكائن'), max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(_('عنوان IP'), null=True, blank=True)
    description = models.TextField(_('الوصف'), blank=True)
    timestamp = models.DateTimeField(_('التوقيت'), auto_now_add=True)
    content_type = models.CharField(_('نوع المحتوى'), max_length=100, blank=True)

    class Meta:
        verbose_name = _('سجل تدقيق')
        verbose_name_plural = _('سجلات التدقيق')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name} ({self.timestamp})"
