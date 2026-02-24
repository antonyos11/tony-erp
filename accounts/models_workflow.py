"""
نظام سير الموافقات - Approval Workflow Engine
================================================
نظام موافقات متسلسل قابل للتخصيص حسب نوع المستند والمبلغ.
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class ApprovalWorkflow(models.Model):
    """
    تعريف سير عمل الموافقات
    كل نوع مستند يمكن أن يكون له سير عمل خاص
    """
    DOCUMENT_TYPE_CHOICES = [
        ('purchase_order', 'أمر شراء'),
        ('sales_order', 'أمر بيع'),
        ('invoice', 'فاتورة'),
        ('payment', 'دفعة'),
        ('expense', 'مصروف'),
        ('journal_entry', 'قيد يومية'),
        ('inventory_transfer', 'تحويل مخزون'),
        ('production_order', 'أمر إنتاج'),
        ('price_change', 'تغيير سعر'),
        ('discount', 'خصم'),
        ('refund', 'مرتجع'),
        ('write_off', 'إعدام'),
    ]

    name = models.CharField(max_length=200, verbose_name='اسم سير العمل')
    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES,
        verbose_name='نوع المستند'
    )
    description = models.TextField(blank=True, verbose_name='الوصف')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    apply_to_all_branches = models.BooleanField(
        default=True,
        verbose_name='تطبيق على جميع الفروع'
    )
    branches = models.ManyToManyField(
        'branches.Branch',
        blank=True,
        related_name='approval_workflows',
        verbose_name='الفروع',
        help_text='اتركه فارغاً إذا كان يطبق على جميع الفروع'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_workflows',
        verbose_name='أنشئ بواسطة'
    )

    class Meta:
        verbose_name = 'سير عمل الموافقات'
        verbose_name_plural = 'مسارات عمل الموافقات'
        ordering = ['document_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_document_type_display()})"

    def get_steps_for_amount(self, amount):
        """الحصول على خطوات الموافقة المطلوبة لمبلغ معين"""
        steps = self.steps.filter(is_active=True).order_by('step_order')
        required_steps = []
        for step in steps:
            if step.is_required_for_amount(amount):
                required_steps.append(step)
        return required_steps


class ApprovalStep(models.Model):
    """
    خطوة موافقة ضمن سير العمل
    """
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name='سير العمل'
    )
    step_order = models.PositiveIntegerField(verbose_name='ترتيب الخطوة')
    name = models.CharField(max_length=200, verbose_name='اسم الخطوة')
    approver_role = models.ForeignKey(
        'auth.Group',
        on_delete=models.CASCADE,
        verbose_name='دور المعتمِد',
        help_text='أي مستخدم بهذا الدور يمكنه الاعتماد'
    )
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval_steps',
        verbose_name='معتمِد محدد',
        help_text='اختياري: تحديد مستخدم بعينه للاعتماد'
    )
    min_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='الحد الأدنى للمبلغ',
        help_text='هذه الخطوة مطلوبة فقط إذا كان المبلغ أكبر من أو يساوي هذا الحد'
    )
    max_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='الحد الأقصى للمبلغ',
        help_text='اختياري: فارغ = بدون حد أقصى'
    )
    auto_approve_below = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='موافقة تلقائية تحت',
        help_text='موافقة تلقائية إذا المبلغ أقل من هذا الحد'
    )
    timeout_hours = models.PositiveIntegerField(
        default=24,
        verbose_name='مهلة الموافقة (ساعات)'
    )
    escalate_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='escalated_approval_steps',
        verbose_name='تصعيد إلى',
        help_text='في حالة انتهاء المهلة'
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'خطوة موافقة'
        verbose_name_plural = 'خطوات الموافقة'
        ordering = ['workflow', 'step_order']
        unique_together = ['workflow', 'step_order']

    def __str__(self):
        return f"{self.workflow.name} - خطوة {self.step_order}: {self.name}"

    def is_required_for_amount(self, amount):
        """هل هذه الخطوة مطلوبة للمبلغ المحدد؟"""
        from decimal import Decimal
        amount = Decimal(str(amount))
        if amount < self.min_amount:
            return False
        if self.max_amount is not None and amount > self.max_amount:
            return False
        return True

    def should_auto_approve(self, amount):
        """هل يجب الموافقة التلقائية؟"""
        from decimal import Decimal
        amount = Decimal(str(amount))
        if self.auto_approve_below is not None and amount < self.auto_approve_below:
            return True
        return False


class ApprovalRequest(models.Model):
    """
    طلب موافقة على مستند معين
    """
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
        ('escalated', 'مُصعَّد'),
        ('cancelled', 'ملغي'),
        ('auto_approved', 'موافقة تلقائية'),
    ]

    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name='requests',
        verbose_name='سير العمل'
    )
    document_type = models.CharField(max_length=50, verbose_name='نوع المستند')
    document_id = models.PositiveIntegerField(verbose_name='رقم المستند')
    document_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='رقم المستند المرجعي'
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='المبلغ'
    )
    current_step = models.ForeignKey(
        ApprovalStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_requests',
        verbose_name='الخطوة الحالية'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='الحالة'
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='approval_requests_made',
        verbose_name='مقدم الطلب'
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='الفرع'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الطلب')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الإتمام')

    class Meta:
        verbose_name = 'طلب موافقة'
        verbose_name_plural = 'طلبات الموافقة'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document_type', 'document_id']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"طلب #{self.pk} - {self.get_status_display()} - {self.document_number}"

    @property
    def is_overdue(self):
        """هل تجاوز الطلب المهلة المحددة؟"""
        if self.status != 'pending' or not self.current_step:
            return False
        timeout = timezone.timedelta(hours=self.current_step.timeout_hours)
        return timezone.now() > self.created_at + timeout

    def advance_to_next_step(self):
        """الانتقال للخطوة التالية"""
        if not self.current_step:
            return False

        next_steps = self.workflow.steps.filter(
            step_order__gt=self.current_step.step_order,
            is_active=True
        ).order_by('step_order')

        for step in next_steps:
            if step.is_required_for_amount(self.amount):
                if step.should_auto_approve(self.amount):
                    ApprovalAction.objects.create(
                        request=self,
                        step=step,
                        action='auto_approved',
                        notes='موافقة تلقائية - المبلغ أقل من الحد'
                    )
                    continue
                self.current_step = step
                self.save(update_fields=['current_step'])
                return True

        self.status = 'approved'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
        return False


class ApprovalAction(models.Model):
    """
    إجراء على طلب موافقة (اعتماد / رفض / تصعيد)
    """
    ACTION_CHOICES = [
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
        ('escalated', 'مُصعَّد'),
        ('returned', 'مُرجع للتعديل'),
        ('auto_approved', 'موافقة تلقائية'),
    ]

    request = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.CASCADE,
        related_name='actions',
        verbose_name='طلب الموافقة'
    )
    step = models.ForeignKey(
        ApprovalStep,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='الخطوة'
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name='الإجراء'
    )
    acted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflow_approval_actions',
        verbose_name='بواسطة'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإجراء')

    class Meta:
        verbose_name = 'إجراء موافقة'
        verbose_name_plural = 'إجراءات الموافقة'
        ordering = ['created_at']

    def __str__(self):
        actor = self.acted_by or 'النظام'
        return f"{self.get_action_display()} بواسطة {actor}"
