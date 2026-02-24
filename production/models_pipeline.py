"""
نماذج خط أنابيب الإنتاج العالمي
Global Production Pipeline Models

تتبع تدفق أمر الإنتاج عبر جميع مراكز العمل (التقطيع ← الخياطة ← التجميع ← التغليف)
مع دعم البث المباشر والطباعة الحرارية.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import uuid


class PipelineStageStatus(models.TextChoices):
    WAITING = 'waiting', _('في الانتظار')
    READY = 'ready', _('جاهز للبدء')
    IN_PROGRESS = 'in_progress', _('قيد التنفيذ')
    COMPLETED = 'completed', _('مكتمل')
    FAILED = 'failed', _('متوقف - عطل')
    SKIPPED = 'skipped', _('تم تخطيه')


class PipelineBoard(models.Model):
    """
    لوحة خط الأنابيب - تمثل تدفق أمر إنتاج عبر جميع مراكز العمل
    """
    production_order = models.OneToOneField(
        'production.ProductionOrder',
        on_delete=models.CASCADE,
        related_name='pipeline_board',
        verbose_name=_('أمر الإنتاج')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name=_('نشط'))

    # Cached overall progress (0-100)
    overall_progress = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0'),
        verbose_name=_('نسبة الإنجاز الكلية')
    )

    class Meta:
        verbose_name = _('لوحة خط الأنابيب')
        verbose_name_plural = _('لوحات خط الأنابيب')
        ordering = ['-created_at']

    def __str__(self):
        return f"Pipeline: {self.production_order.number}"

    def recalculate_progress(self):
        """إعادة حساب نسبة الإنجاز الكلية"""
        stages = self.stage_entries.all()
        total = stages.count()
        if total == 0:
            self.overall_progress = Decimal('0')
        else:
            completed = stages.filter(status=PipelineStageStatus.COMPLETED).count()
            self.overall_progress = Decimal(str(round((completed / total) * 100, 2)))
        self.save(update_fields=['overall_progress', 'updated_at'])


class PipelineStageEntry(models.Model):
    """
    سجل مرحلة واحدة في خط الأنابيب لأمر إنتاج محدد
    """
    board = models.ForeignKey(
        PipelineBoard,
        on_delete=models.CASCADE,
        related_name='stage_entries',
        verbose_name=_('لوحة الأنابيب')
    )
    work_center = models.ForeignKey(
        'production.ProductionWorkCenter',
        on_delete=models.CASCADE,
        related_name='pipeline_entries',
        verbose_name=_('مركز العمل')
    )
    sequence = models.PositiveIntegerField(
        default=0, verbose_name=_('الترتيب')
    )
    status = models.CharField(
        max_length=20,
        choices=PipelineStageStatus.choices,
        default=PipelineStageStatus.WAITING,
        verbose_name=_('الحالة')
    )

    # Timing
    started_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_('وقت البدء')
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_('وقت الإنجاز')
    )

    # Personnel
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pipeline_started',
        verbose_name=_('بدأ بواسطة')
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pipeline_completed',
        verbose_name=_('أكمل بواسطة')
    )

    # Failure tracking
    failure_reason = models.TextField(
        blank=True, default='', verbose_name=_('سبب التوقف')
    )
    failure_category = models.CharField(
        max_length=50, blank=True, default='',
        choices=[
            ('machine_breakdown', _('عطل ماكينة')),
            ('material_shortage', _('نقص مواد')),
            ('quality_issue', _('مشكلة جودة')),
            ('power_outage', _('انقطاع كهرباء')),
            ('labor_shortage', _('نقص عمالة')),
            ('other', _('أخرى')),
        ],
        verbose_name=_('تصنيف العطل')
    )

    # Barcode printing status (for final stage)
    print_status = models.CharField(
        max_length=20, blank=True, default='',
        choices=[
            ('', _('غير مطلوب')),
            ('pending', _('في انتظار الطباعة')),
            ('printing', _('جاري الطباعة')),
            ('printed', _('تم الطباعة')),
            ('print_error', _('خطأ في الطباعة')),
        ],
        verbose_name=_('حالة الطباعة')
    )

    notes = models.TextField(blank=True, default='', verbose_name=_('ملاحظات'))

    class Meta:
        verbose_name = _('مرحلة في خط الأنابيب')
        verbose_name_plural = _('مراحل خط الأنابيب')
        ordering = ['sequence']
        unique_together = ['board', 'work_center']

    def __str__(self):
        return (
            f"{self.board.production_order.number} → "
            f"{self.work_center.name} [{self.get_status_display()}]"
        )

    @property
    def duration_minutes(self):
        """مدة العمل بالدقائق"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None

    @property
    def is_final_stage(self):
        """هل هذه المرحلة الأخيرة (التغليف)؟"""
        return not self.board.stage_entries.filter(
            sequence__gt=self.sequence
        ).exists()


class PipelinePrintJob(models.Model):
    """
    سجل مهام طباعة الباركود من خط الأنابيب
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stage_entry = models.ForeignKey(
        PipelineStageEntry,
        on_delete=models.CASCADE,
        related_name='print_jobs',
        verbose_name=_('مرحلة الأنابيب')
    )
    production_order = models.ForeignKey(
        'production.ProductionOrder',
        on_delete=models.CASCADE,
        related_name='pipeline_print_jobs',
        verbose_name=_('أمر الإنتاج')
    )

    # Print details
    barcode_data = models.TextField(verbose_name=_('بيانات الباركود'))
    zpl_command = models.TextField(
        blank=True, default='', verbose_name=_('أمر ZPL')
    )
    copies = models.PositiveIntegerField(default=1, verbose_name=_('عدد النسخ'))

    status = models.CharField(
        max_length=20,
        choices=[
            ('queued', _('في الطابور')),
            ('sent', _('تم الإرسال')),
            ('printing', _('جاري الطباعة')),
            ('completed', _('مكتمل')),
            ('failed', _('فشل')),
        ],
        default='queued',
        verbose_name=_('الحالة')
    )
    error_message = models.TextField(
        blank=True, default='', verbose_name=_('رسالة الخطأ')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('طلب بواسطة')
    )

    class Meta:
        verbose_name = _('مهمة طباعة باركود')
        verbose_name_plural = _('مهام طباعة الباركود')
        ordering = ['-created_at']

    def __str__(self):
        return f"Print Job {self.id} [{self.status}]"


class ProductionIssue(models.Model):
    """
    مشكلة إنتاج — يتم تسجيلها من واجهة الكشك عند الضغط على زر 'ISSUE'.
    Production Issue — logged from kiosk interface when 'ISSUE' button is pressed.
    """
    SEVERITY_CHOICES = [
        ('low', _('منخفضة')),
        ('medium', _('متوسطة')),
        ('high', _('عالية')),
        ('critical', _('حرجة')),
    ]

    CATEGORY_CHOICES = [
        ('material_defect', _('عيب في المواد الخام')),
        ('machine_failure', _('عطل آلة')),
        ('quality_issue', _('مشكلة جودة')),
        ('missing_material', _('نقص مواد')),
        ('worker_error', _('خطأ عامل')),
        ('design_issue', _('مشكلة تصميم')),
        ('power_outage', _('انقطاع كهرباء')),
        ('other', _('أخرى')),
    ]

    STATUS_CHOICES = [
        ('open', _('مفتوح')),
        ('investigating', _('قيد التحقيق')),
        ('resolved', _('تم الحل')),
        ('escalated', _('تم التصعيد')),
        ('closed', _('مغلق')),
    ]

    production_order = models.ForeignKey(
        'ProductionOrder',
        on_delete=models.CASCADE,
        related_name='issues',
        verbose_name=_('أمر الإنتاج'),
    )
    stage_entry = models.ForeignKey(
        PipelineStageEntry,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='issues',
        verbose_name=_('مرحلة الأنبوب'),
    )
    work_center = models.ForeignKey(
        'ProductionWorkCenter',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='issues',
        verbose_name=_('مركز العمل'),
    )

    category = models.CharField(
        _('التصنيف'), max_length=30, choices=CATEGORY_CHOICES, default='other',
    )
    severity = models.CharField(
        _('الخطورة'), max_length=10, choices=SEVERITY_CHOICES, default='medium',
    )
    status = models.CharField(
        _('الحالة'), max_length=15, choices=STATUS_CHOICES, default='open',
    )

    title = models.CharField(_('العنوان'), max_length=200)
    description = models.TextField(_('الوصف'), blank=True)
    resolution = models.TextField(_('الحل'), blank=True)

    # Impact tracking
    units_affected = models.PositiveIntegerField(_('عدد الوحدات المتأثرة'), default=0)
    downtime_minutes = models.PositiveIntegerField(_('وقت التوقف (دقائق)'), default=0)
    estimated_cost = models.DecimalField(
        _('التكلفة التقديرية'), max_digits=12, decimal_places=2, default=0,
    )

    # People
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='production_reported_issues',
        verbose_name=_('المُبلِّغ'),
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='production_assigned_issues',
        verbose_name=_('المسؤول'),
    )

    # Photo evidence
    photo = models.ImageField(
        _('صورة المشكلة'), upload_to='production_issues/', blank=True, null=True,
    )

    reported_at = models.DateTimeField(_('وقت الإبلاغ'), auto_now_add=True)
    resolved_at = models.DateTimeField(_('وقت الحل'), null=True, blank=True)

    class Meta:
        ordering = ['-reported_at']
        verbose_name = _('مشكلة إنتاج')
        verbose_name_plural = _('مشاكل الإنتاج')

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title} — {self.production_order.number}"

    @property
    def is_open(self):
        return self.status in ('open', 'investigating')

    def resolve(self, resolution_text: str, user=None):
        self.status = 'resolved'
        self.resolution = resolution_text
        self.resolved_at = timezone.now()
        if user:
            self.assigned_to = user
        self.save(update_fields=[
            'status', 'resolution', 'resolved_at', 'assigned_to',
        ])
