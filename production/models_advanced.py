"""
نماذج الإنتاج المتقدمة
========================
جدولة الإنتاج، تحليل تباين التكاليف، كفاءة المعدات
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class ProductionLine(models.Model):
    """خط الإنتاج"""
    name = models.CharField(max_length=200, verbose_name='اسم خط الإنتاج')
    code = models.CharField(max_length=50, unique=True, verbose_name='الكود')
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='production_lines',
        verbose_name='الفرع'
    )
    capacity_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='الطاقة الإنتاجية لكل ساعة'
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'خط إنتاج'
        verbose_name_plural = 'خطوط الإنتاج'

    def __str__(self):
        return f"{self.name} ({self.code})"


class ProductionSchedule(models.Model):
    """جدولة الإنتاج"""
    STATUS_CHOICES = [
        ('planned', 'مخطط'),
        ('confirmed', 'مؤكد'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('delayed', 'متأخر'),
        ('cancelled', 'ملغي'),
    ]

    PRIORITY_CHOICES = [
        (1, 'عاجل جداً'),
        (2, 'عاجل'),
        (3, 'عالي'),
        (5, 'عادي'),
        (7, 'منخفض'),
        (10, 'غير مستعجل'),
    ]

    production_order = models.ForeignKey(
        'production.ProductionOrder',
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='أمر الإنتاج'
    )
    production_line = models.ForeignKey(
        ProductionLine,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='خط الإنتاج'
    )
    planned_start = models.DateTimeField(verbose_name='بداية مخططة')
    planned_end = models.DateTimeField(verbose_name='نهاية مخططة')
    actual_start = models.DateTimeField(null=True, blank=True, verbose_name='بداية فعلية')
    actual_end = models.DateTimeField(null=True, blank=True, verbose_name='نهاية فعلية')
    planned_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='الكمية المخططة'
    )
    actual_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='الكمية الفعلية'
    )
    defective_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='الكمية المعيبة'
    )
    priority = models.IntegerField(
        choices=PRIORITY_CHOICES,
        default=5,
        verbose_name='الأولوية'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planned',
        verbose_name='الحالة'
    )
    assigned_workers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='production_schedules',
        verbose_name='العمال المكلفون'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'جدولة إنتاج'
        verbose_name_plural = 'جدولة الإنتاج'
        ordering = ['priority', 'planned_start']

    def __str__(self):
        return f"{self.production_order} - {self.production_line} - {self.planned_start.date()}"

    @property
    def delay_hours(self):
        """ساعات التأخير"""
        if self.actual_end and self.planned_end:
            diff = self.actual_end - self.planned_end
            hours = diff.total_seconds() / 3600
            return round(max(0, hours), 1)
        return 0

    @property
    def planned_duration_hours(self):
        """مدة العمل المخططة بالساعات"""
        diff = self.planned_end - self.planned_start
        return round(diff.total_seconds() / 3600, 1)

    @property
    def actual_duration_hours(self):
        """مدة العمل الفعلية بالساعات"""
        if self.actual_start and self.actual_end:
            diff = self.actual_end - self.actual_start
            return round(diff.total_seconds() / 3600, 1)
        return 0

    @property
    def efficiency_percentage(self):
        """نسبة الكفاءة"""
        if self.planned_quantity and self.planned_quantity > 0:
            good_quantity = self.actual_quantity - self.defective_quantity
            return round((float(good_quantity) / float(self.planned_quantity)) * 100, 1)
        return 0

    @property
    def oee(self):
        """
        Overall Equipment Effectiveness (OEE)
        OEE = Availability × Performance × Quality
        """
        if not self.actual_start or not self.actual_end:
            return 0

        planned_hours = self.planned_duration_hours
        actual_hours = self.actual_duration_hours
        availability = (actual_hours / planned_hours * 100) if planned_hours > 0 else 0

        performance = (
            (float(self.actual_quantity) / float(self.planned_quantity) * 100)
            if self.planned_quantity > 0 else 0
        )

        good_qty = float(self.actual_quantity) - float(self.defective_quantity)
        quality = (
            (good_qty / float(self.actual_quantity) * 100)
            if self.actual_quantity > 0 else 0
        )

        oee_value = (availability * performance * quality) / 10000
        return round(oee_value, 1)


class CostVariance(models.Model):
    """تحليل تباين التكاليف"""
    production_order = models.OneToOneField(
        'production.ProductionOrder',
        on_delete=models.CASCADE,
        related_name='cost_variance',
        verbose_name='أمر الإنتاج'
    )
    standard_material_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='تكلفة مواد معيارية'
    )
    actual_material_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='تكلفة مواد فعلية'
    )
    standard_labor_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='تكلفة عمالة معيارية'
    )
    actual_labor_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='تكلفة عمالة فعلية'
    )
    standard_overhead = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='تكاليف غير مباشرة معيارية'
    )
    actual_overhead = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='تكاليف غير مباشرة فعلية'
    )
    analysis_date = models.DateField(auto_now_add=True, verbose_name='تاريخ التحليل')
    analyzed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='أُعد بواسطة'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'تحليل تباين تكاليف'
        verbose_name_plural = 'تحليلات تباين التكاليف'

    def __str__(self):
        return f"تباين تكاليف - {self.production_order}"

    @property
    def material_variance(self):
        return self.actual_material_cost - self.standard_material_cost

    @property
    def labor_variance(self):
        return self.actual_labor_cost - self.standard_labor_cost

    @property
    def overhead_variance(self):
        return self.actual_overhead - self.standard_overhead

    @property
    def total_standard_cost(self):
        return (
            self.standard_material_cost +
            self.standard_labor_cost +
            self.standard_overhead
        )

    @property
    def total_actual_cost(self):
        return (
            self.actual_material_cost +
            self.actual_labor_cost +
            self.actual_overhead
        )

    @property
    def total_variance(self):
        return self.total_actual_cost - self.total_standard_cost

    @property
    def total_variance_percentage(self):
        if self.total_standard_cost != 0:
            return round(
                (float(self.total_variance) / float(self.total_standard_cost)) * 100, 1
            )
        return 0

    @property
    def is_favorable(self):
        """هل التباين إيجابي (التكلفة الفعلية أقل)؟"""
        return self.total_variance < 0
