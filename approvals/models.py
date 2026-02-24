from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class ApprovalRequest(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    class Status(models.TextChoices):
        PENDING = 'pending', _('قيد الانتظار')
        APPROVED = 'approved', _('مقبول')
        REJECTED = 'rejected', _('مرفوض')
        CANCELLED = 'cancelled', _('ملغى')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('آخر تحديث'))
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approval_requests', verbose_name=_('طالب الموافقة'))

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name=_('المبلغ (اختياري)'))
    reason = models.TextField(blank=True, verbose_name=_('السبب'))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_('الحالة'))

    current_level = models.IntegerField(default=1, verbose_name=_('المستوى الحالي'))
    required_levels = models.IntegerField(default=1, verbose_name=_('عدد المستويات المطلوبة'))

    class Meta:
        verbose_name = _('طلب موافقة')
        verbose_name_plural = _('طلبات الموافقة')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Approval#{self.id} {self.get_status_display()}"

    def clean(self):
        """تحقق أساسي من منطق المستويات والقيم."""
        errors = {}

        if self.required_levels is not None and self.required_levels <= 0:
            errors['required_levels'] = _('عدد مستويات الموافقة يجب أن يكون أكبر من صفر.')

        if (
            self.current_level is not None
            and self.required_levels is not None
            and self.current_level > self.required_levels
        ):
            errors['current_level'] = _('المستوى الحالي لا يمكن أن يتجاوز عدد المستويات المطلوبة.')

        if errors:
            raise ValidationError(errors)

    def approve(self, user: User, note: str = ''):
        if self.status != self.Status.PENDING:
            return False
        ApprovalAction.objects.create(
            approval=self,
            user=user,
            action='approve',
            note=note
        )
        profile = getattr(user, 'profile', None)
        level = profile.role.approval_level if profile else 1
        if level >= self.required_levels:
            self.status = self.Status.APPROVED
        else:
            self.current_level = max(self.current_level, level)
        self.save()
        return True

    def reject(self, user: User, note: str = ''):
        if self.status != self.Status.PENDING:
            return False
        ApprovalAction.objects.create(
            approval=self,
            user=user,
            action='reject',
            note=note
        )
        self.status = self.Status.REJECTED
        self.save()
        return True


class ApprovalAction(models.Model):
    ACTIONS = [
        ('approve', _('موافقة')),
        ('reject', _('رفض')),
        ('comment', _('تعليق')),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    approval = models.ForeignKey(ApprovalRequest, on_delete=models.CASCADE, related_name='actions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTIONS)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('إجراء موافقة')
        verbose_name_plural = _('إجراءات الموافقة')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} {self.action} approval {self.approval_id}"