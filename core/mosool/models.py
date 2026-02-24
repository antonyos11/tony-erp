# -*- coding: utf-8 -*-
"""
نماذج موصول التحضير والاستماد
Preparation and Approval Document Models
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal


class PreparationRequest(models.Model):
    """
    طلب التحضير - موصول التحضير
    يستخدم لإعداد طلبات الشراء أو صرف المواد قبل الاعتماد
    """
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('مسودة')
        PENDING = 'pending', _('قيد المراجعة')
        IN_PROGRESS = 'in_progress', _('قيد التنفيذ')
        COMPLETED = 'completed', _('مكتمل')
        CANCELLED = 'cancelled', _('ملغى')
    
    class RequestType(models.TextChoices):
        PURCHASE = 'purchase', _('طلب شراء')
        MATERIAL_ISSUE = 'material_issue', _('صرف مواد')
        PRODUCTION = 'production', _('إنتاج')
        MAINTENANCE = 'maintenance', _('صيانة')
        OTHER = 'other', _('أخرى')
    
    class Priority(models.TextChoices):
        LOW = 'low', _('منخفضة')
        NORMAL = 'normal', _('عادية')
        HIGH = 'high', _('عالية')
        URGENT = 'urgent', _('عاجلة')
    
    number = models.CharField(_('رقم الطلب'), max_length=50, unique=True, editable=False)
    request_type = models.CharField(_('نوع الطلب'), max_length=30, choices=RequestType.choices, default=RequestType.PURCHASE)
    title = models.CharField(_('العنوان'), max_length=200)
    description = models.TextField(_('الوصف'), blank=True)
    
    # التواريخ
    request_date = models.DateField(_('تاريخ الطلب'), default=timezone.localdate)
    required_date = models.DateField(_('تاريخ الاحتياج'), null=True, blank=True)
    
    # المبالغ
    estimated_total = models.DecimalField(_('المبلغ التقديري'), max_digits=15, decimal_places=2, default=Decimal('0'))
    
    # الحالة والأولوية
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.DRAFT)
    priority = models.CharField(_('الأولوية'), max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    
    # الجهة الطالبة
    department = models.ForeignKey(
        'hr.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('القسم الطالب'),
        related_name='preparation_requests'
    )
    cost_center = models.ForeignKey(
        'accounting.CostCenter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('مركز التكلفة')
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('المشروع'),
        related_name='preparation_requests'
    )
    
    # المستخدمين
    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_preparations',
        verbose_name=_('مقدم الطلب')
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_preparations',
        verbose_name=_('المكلف بالتنفيذ')
    )
    
    # الملاحظات والمرفقات
    notes = models.TextField(_('ملاحظات'), blank=True)
    attachments = models.FileField(_('المرفقات'), upload_to='preparations/', null=True, blank=True)
    
    # التتبع
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('آخر تحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('طلب تحضير')
        verbose_name_plural = _('طلبات التحضير')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['request_type']),
            models.Index(fields=['request_date']),
            models.Index(fields=['priority']),
        ]
        permissions = [
            ('can_approve_preparation', _('يمكنه اعتماد طلبات التحضير')),
            ('can_process_preparation', _('يمكنه معالجة طلبات التحضير')),
        ]
    
    def __str__(self):
        return f"{self.number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            from core.sequence_utils import next_sequence, format_code
            seq = next_sequence('PREP_REQ')
            self.number = format_code('PREP', seq)
        
        # حساب المجموع التقديري من البنود
        if self.pk:
            self.estimated_total = sum(
                item.estimated_amount for item in self.items.all()
            )
        
        super().save(*args, **kwargs)
    
    def submit(self):
        """تقديم الطلب للمراجعة"""
        if self.status == self.Status.DRAFT:
            self.status = self.Status.PENDING
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False
    
    def start_processing(self, user):
        """بدء معالجة الطلب"""
        if self.status == self.Status.PENDING:
            self.status = self.Status.IN_PROGRESS
            self.assigned_to = user
            self.save(update_fields=['status', 'assigned_to', 'updated_at'])
            return True
        return False
    
    def complete(self):
        """إكمال الطلب"""
        if self.status == self.Status.IN_PROGRESS:
            self.status = self.Status.COMPLETED
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False
    
    def cancel(self, reason=''):
        """إلغاء الطلب"""
        if self.status in [self.Status.DRAFT, self.Status.PENDING]:
            self.status = self.Status.CANCELLED
            if reason:
                self.notes = f"{self.notes}\n\nسبب الإلغاء: {reason}".strip()
            self.save(update_fields=['status', 'notes', 'updated_at'])
            return True
        return False


class PreparationItem(models.Model):
    """
    بند طلب التحضير
    """
    
    preparation = models.ForeignKey(
        PreparationRequest,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('طلب التحضير')
    )
    
    # المنتج/الخدمة
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_('المنتج')
    )
    description = models.CharField(_('الوصف'), max_length=500)
    
    # الكميات
    quantity_requested = models.DecimalField(_('الكمية المطلوبة'), max_digits=12, decimal_places=3, default=Decimal('1'))
    unit = models.CharField(_('الوحدة'), max_length=50, default='قطعة')
    
    # التكاليف
    estimated_unit_price = models.DecimalField(_('السعر التقديري'), max_digits=12, decimal_places=2, default=Decimal('0'))
    
    # الحالة
    is_approved = models.BooleanField(_('معتمد'), default=False)
    quantity_approved = models.DecimalField(_('الكمية المعتمدة'), max_digits=12, decimal_places=3, default=Decimal('0'))
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('بند تحضير')
        verbose_name_plural = _('بنود التحضير')
        ordering = ['id']
    
    def __str__(self):
        return f"{self.description} ({self.quantity_requested} {self.unit})"
    
    @property
    def estimated_amount(self):
        """المبلغ التقديري"""
        return self.quantity_requested * self.estimated_unit_price
    
    @property
    def approved_amount(self):
        """المبلغ المعتمد"""
        return self.quantity_approved * self.estimated_unit_price


class ApprovalDocument(models.Model):
    """
    مستند الاستماد - موصول الاستماد
    يستخدم لاعتماد المستندات والطلبات المالية والإدارية
    """
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('مسودة')
        PENDING_APPROVAL = 'pending', _('في انتظار الاعتماد')
        PARTIALLY_APPROVED = 'partial', _('معتمد جزئياً')
        APPROVED = 'approved', _('معتمد')
        REJECTED = 'rejected', _('مرفوض')
        CANCELLED = 'cancelled', _('ملغى')
    
    class DocumentType(models.TextChoices):
        PURCHASE_REQUEST = 'pr', _('طلب شراء')
        PURCHASE_ORDER = 'po', _('أمر شراء')
        PAYMENT_REQUEST = 'pay', _('طلب صرف')
        EXPENSE_CLAIM = 'exp', _('طلب مصروفات')
        BUDGET_TRANSFER = 'bt', _('نقل موازنة')
        CONTRACT = 'contract', _('عقد')
        SALARY_ADVANCE = 'sa', _('سلفة راتب')
        CUSTODY = 'custody', _('عهدة')
        OTHER = 'other', _('أخرى')
    
    class ApprovalLevel(models.IntegerChoices):
        LEVEL_1 = 1, _('المستوى الأول')
        LEVEL_2 = 2, _('المستوى الثاني')
        LEVEL_3 = 3, _('المستوى الثالث')
        LEVEL_4 = 4, _('المستوى الرابع')
        LEVEL_5 = 5, _('المستوى الخامس')
    
    number = models.CharField(_('رقم المستند'), max_length=50, unique=True, editable=False)
    document_type = models.CharField(_('نوع المستند'), max_length=30, choices=DocumentType.choices)
    title = models.CharField(_('العنوان'), max_length=200)
    description = models.TextField(_('الوصف'), blank=True)
    
    # الربط بطلب التحضير (اختياري)
    preparation_request = models.ForeignKey(
        PreparationRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval_documents',
        verbose_name=_('طلب التحضير المرتبط')
    )
    
    # التواريخ
    document_date = models.DateField(_('تاريخ المستند'), default=timezone.localdate)
    due_date = models.DateField(_('تاريخ الاستحقاق'), null=True, blank=True)
    
    # المبالغ
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=15, decimal_places=2, default=Decimal('0'))
    approved_amount = models.DecimalField(_('المبلغ المعتمد'), max_digits=15, decimal_places=2, default=Decimal('0'))
    
    # العملة
    currency = models.ForeignKey(
        'core.Currency',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('العملة')
    )
    
    # الحالة ومستوى الاعتماد
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.DRAFT)
    current_approval_level = models.IntegerField(_('مستوى الاعتماد الحالي'), default=0)
    required_approval_level = models.IntegerField(_('مستوى الاعتماد المطلوب'), default=1)
    
    # الجهة
    department = models.ForeignKey(
        'hr.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('القسم')
    )
    cost_center = models.ForeignKey(
        'accounting.CostCenter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('مركز التكلفة')
    )
    budget_item = models.ForeignKey(
        'accounting.CostCenterBudget',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('بند الموازنة')
    )
    
    # المستخدمين
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_approval_docs',
        verbose_name=_('منشئ المستند')
    )
    
    # المورد/العميل (اختياري)
    supplier = models.ForeignKey(
        'partners.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('المورد')
    )
    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('الموظف')
    )
    
    # الملاحظات والمرفقات
    notes = models.TextField(_('ملاحظات'), blank=True)
    attachments = models.FileField(_('المرفقات'), upload_to='approval_docs/', null=True, blank=True)
    
    # الحقول المحاسبية
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('القيد المحاسبي')
    )
    
    # التتبع
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(_('تاريخ التقديم'), null=True, blank=True)
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('مستند استماد')
        verbose_name_plural = _('مستندات الاستماد')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['document_type']),
            models.Index(fields=['document_date']),
            models.Index(fields=['current_approval_level']),
        ]
        permissions = [
            ('can_approve_level_1', _('اعتماد المستوى الأول')),
            ('can_approve_level_2', _('اعتماد المستوى الثاني')),
            ('can_approve_level_3', _('اعتماد المستوى الثالث')),
            ('can_approve_level_4', _('اعتماد المستوى الرابع')),
            ('can_approve_level_5', _('اعتماد المستوى الخامس')),
            ('can_reject_approval', _('رفض المستندات')),
        ]
    
    def __str__(self):
        return f"{self.number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            from core.sequence_utils import next_sequence, format_code
            seq = next_sequence('APPROVAL_DOC')
            self.number = format_code('APD', seq)
        
        # تحديد مستوى الاعتماد المطلوب بناءً على المبلغ
        if not self.pk or 'total_amount' in kwargs.get('update_fields', []):
            self._set_required_approval_level()
        
        super().save(*args, **kwargs)
    
    def _set_required_approval_level(self):
        """تحديد مستوى الاعتماد المطلوب بناءً على المبلغ"""
        amount = self.total_amount
        if amount <= Decimal('1000'):
            self.required_approval_level = 1
        elif amount <= Decimal('5000'):
            self.required_approval_level = 2
        elif amount <= Decimal('25000'):
            self.required_approval_level = 3
        elif amount <= Decimal('100000'):
            self.required_approval_level = 4
        else:
            self.required_approval_level = 5
    
    def submit_for_approval(self):
        """تقديم للاعتماد"""
        if self.status == self.Status.DRAFT:
            self.status = self.Status.PENDING_APPROVAL
            self.current_approval_level = 1
            self.submitted_at = timezone.now()
            self.save(update_fields=['status', 'current_approval_level', 'submitted_at', 'updated_at'])
            return True
        return False
    
    def approve(self, user, level, notes='', approved_amount=None):
        """اعتماد المستند"""
        if self.status not in [self.Status.PENDING_APPROVAL, self.Status.PARTIALLY_APPROVED]:
            return False, "المستند ليس في حالة انتظار الاعتماد"
        
        if level != self.current_approval_level:
            return False, "مستوى الاعتماد غير صحيح"
        
        # إنشاء سجل الاعتماد
        DocumentApproval.objects.create(
            document=self,
            approved_by=user,
            approval_level=level,
            action='approve',
            notes=notes,
            amount_approved=approved_amount or self.total_amount
        )
        
        if approved_amount:
            self.approved_amount = approved_amount
        else:
            self.approved_amount = self.total_amount
        
        # التحقق من اكتمال الاعتماد
        if self.current_approval_level >= self.required_approval_level:
            self.status = self.Status.APPROVED
            self.approved_at = timezone.now()
        else:
            self.status = self.Status.PARTIALLY_APPROVED
            self.current_approval_level += 1
        
        self.save(update_fields=['status', 'current_approval_level', 'approved_amount', 'approved_at', 'updated_at'])
        return True, "تم الاعتماد بنجاح"
    
    def reject(self, user, reason):
        """رفض المستند"""
        if self.status not in [self.Status.PENDING_APPROVAL, self.Status.PARTIALLY_APPROVED]:
            return False, "المستند ليس في حالة انتظار الاعتماد"
        
        DocumentApproval.objects.create(
            document=self,
            approved_by=user,
            approval_level=self.current_approval_level,
            action='reject',
            notes=reason
        )
        
        self.status = self.Status.REJECTED
        self.save(update_fields=['status', 'updated_at'])
        return True, "تم الرفض"
    
    def cancel(self, reason=''):
        """إلغاء المستند"""
        if self.status in [self.Status.DRAFT, self.Status.PENDING_APPROVAL]:
            self.status = self.Status.CANCELLED
            if reason:
                self.notes = f"{self.notes}\n\nسبب الإلغاء: {reason}".strip()
            self.save(update_fields=['status', 'notes', 'updated_at'])
            return True
        return False


class ApprovalDocumentItem(models.Model):
    """
    بند مستند الاستماد
    """
    
    document = models.ForeignKey(
        ApprovalDocument,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('المستند')
    )
    
    description = models.CharField(_('الوصف'), max_length=500)
    
    # المنتج/الخدمة (اختياري)
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('المنتج')
    )
    account = models.ForeignKey(
        'accounting.Account',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('الحساب')
    )
    
    # الكميات والمبالغ
    quantity = models.DecimalField(_('الكمية'), max_digits=12, decimal_places=3, default=Decimal('1'))
    unit = models.CharField(_('الوحدة'), max_length=50, default='قطعة')
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=12, decimal_places=2, default=Decimal('0'))
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('بند استماد')
        verbose_name_plural = _('بنود الاستماد')
        ordering = ['id']
    
    def __str__(self):
        return f"{self.description} ({self.quantity} {self.unit})"
    
    @property
    def total_amount(self):
        """المبلغ الإجمالي"""
        return self.quantity * self.unit_price


class PreparationApproval(models.Model):
    """
    سجل اعتماد طلب التحضير
    """
    
    ACTION_CHOICES = [
        ('approve', _('موافقة')),
        ('reject', _('رفض')),
        ('return', _('إرجاع للتعديل')),
        ('comment', _('تعليق')),
    ]
    
    preparation = models.ForeignKey(
        PreparationRequest,
        on_delete=models.CASCADE,
        related_name='approvals',
        verbose_name=_('طلب التحضير')
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_('المعتمد')
    )
    action = models.CharField(_('الإجراء'), max_length=20, choices=ACTION_CHOICES)
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('اعتماد تحضير')
        verbose_name_plural = _('اعتمادات التحضير')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.preparation.number} - {self.get_action_display()} by {self.approved_by}"


class DocumentApproval(models.Model):
    """
    سجل اعتماد مستند الاستماد
    """
    
    ACTION_CHOICES = [
        ('approve', _('موافقة')),
        ('reject', _('رفض')),
        ('return', _('إرجاع للتعديل')),
        ('comment', _('تعليق')),
    ]
    
    document = models.ForeignKey(
        ApprovalDocument,
        on_delete=models.CASCADE,
        related_name='approvals',
        verbose_name=_('المستند')
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_('المعتمد')
    )
    approval_level = models.IntegerField(_('مستوى الاعتماد'), default=1)
    action = models.CharField(_('الإجراء'), max_length=20, choices=ACTION_CHOICES)
    notes = models.TextField(_('ملاحظات'), blank=True)
    amount_approved = models.DecimalField(_('المبلغ المعتمد'), max_digits=15, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('اعتماد مستند')
        verbose_name_plural = _('اعتمادات المستندات')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.document.number} L{self.approval_level} - {self.get_action_display()} by {self.approved_by}"


class ApprovalWorkflow(models.Model):
    """
    سير عمل الاعتماد
    تحديد من يعتمد في كل مستوى لكل نوع مستند
    """
    
    document_type = models.CharField(_('نوع المستند'), max_length=30, choices=ApprovalDocument.DocumentType.choices)
    approval_level = models.IntegerField(_('مستوى الاعتماد'), default=1)
    
    # من يمكنه الاعتماد
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval_workflows',
        verbose_name=_('المعتمد')
    )
    approver_role = models.ForeignKey(
        'users.UserRole',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('دور المعتمد')
    )
    department = models.ForeignKey(
        'hr.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('القسم')
    )
    
    # الحدود
    min_amount = models.DecimalField(_('الحد الأدنى للمبلغ'), max_digits=15, decimal_places=2, default=Decimal('0'))
    max_amount = models.DecimalField(_('الحد الأقصى للمبلغ'), max_digits=15, decimal_places=2, null=True, blank=True)
    
    is_active = models.BooleanField(_('نشط'), default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('سير عمل اعتماد')
        verbose_name_plural = _('سير عمل الاعتمادات')
        ordering = ['document_type', 'approval_level', 'min_amount']
        unique_together = ['document_type', 'approval_level', 'department']
    
    def __str__(self):
        return f"{self.get_document_type_display()} - المستوى {self.approval_level}"
