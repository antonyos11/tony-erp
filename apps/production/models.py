"""
نماذج تطبيق الإنتاج — RITA ERP
"""
from django.db import models
from apps.core.models import AuditMixin


class ProductionLine(AuditMixin):
    """خط الإنتاج"""
    name = models.CharField(max_length=200, verbose_name='الاسم')
    description = models.TextField(blank=True, verbose_name='الوصف')
    supervisor = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supervised_lines', verbose_name='المشرف',
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'خط إنتاج'
        verbose_name_plural = 'خطوط الإنتاج'
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductionStageTemplate(AuditMixin):
    """قالب مراحل الإنتاج"""
    name = models.CharField(max_length=200, verbose_name='الاسم')
    product_category = models.ForeignKey(
        'inventory.Category', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='stage_templates', verbose_name='تصنيف المنتج',
    )

    class Meta:
        verbose_name = 'قالب مراحل إنتاج'
        verbose_name_plural = 'قوالب مراحل الإنتاج'

    def __str__(self):
        return self.name


class StageStep(models.Model):
    """خطوة في قالب المراحل"""
    template = models.ForeignKey(
        'ProductionStageTemplate', on_delete=models.CASCADE,
        related_name='steps', verbose_name='القالب',
    )
    order = models.PositiveIntegerField(verbose_name='الترتيب')
    name = models.CharField(max_length=200, verbose_name='الاسم')
    estimated_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='الساعات المقدرة')

    class Meta:
        verbose_name = 'خطوة إنتاج'
        verbose_name_plural = 'خطوات الإنتاج'
        ordering = ['order']

    def __str__(self):
        return f'{self.order}. {self.name}'


class ProductionOrder(AuditMixin):
    """أمر الإنتاج"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('in_progress', 'قيد التنفيذ'),
        ('quality_check', 'مراقبة الجودة'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
    ]

    order_number = models.CharField(max_length=50, unique=True, verbose_name='رقم الأمر')
    date = models.DateField(verbose_name='التاريخ')
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.PROTECT,
        related_name='production_orders', verbose_name='المنتج',
    )
    bom = models.ForeignKey(
        'inventory.BillOfMaterials', on_delete=models.PROTECT,
        related_name='production_orders', verbose_name='قائمة المواد',
    )
    quantity = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='الكمية المطلوبة')
    quantity_produced = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الكمية المنتجة')
    quantity_wasted = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='كمية الهالك')
    production_line = models.ForeignKey(
        'ProductionLine', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='production_orders', verbose_name='خط الإنتاج',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='الحالة')
    expected_date = models.DateField(null=True, blank=True, verbose_name='التاريخ المتوقع')
    actual_completion_date = models.DateField(null=True, blank=True, verbose_name='تاريخ الاكتمال الفعلي')
    warehouse_raw = models.ForeignKey(
        'core.Warehouse', on_delete=models.PROTECT,
        related_name='production_orders_raw', verbose_name='مخزن الخامات',
    )
    warehouse_finished = models.ForeignKey(
        'core.Warehouse', on_delete=models.PROTECT,
        related_name='production_orders_finished', verbose_name='مخزن المنتجات التامة',
    )
    material_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='تكلفة المواد')
    labor_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='تكلفة العمالة')
    overhead_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='التكاليف الإضافية')
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي التكلفة')
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='تكلفة الوحدة')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'أمر إنتاج'
        verbose_name_plural = 'أوامر الإنتاج'
        ordering = ['-date', '-order_number']

    def __str__(self):
        return f'{self.order_number} - {self.product}'


class ProductionStage(AuditMixin):
    """مرحلة الإنتاج الفعلية"""
    STATUS_CHOICES = [
        ('pending', 'في الانتظار'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتملة'),
        ('skipped', 'متجاوزة'),
    ]

    production_order = models.ForeignKey(
        'ProductionOrder', on_delete=models.CASCADE,
        related_name='stages', verbose_name='أمر الإنتاج',
    )
    step = models.ForeignKey(
        'StageStep', on_delete=models.PROTECT,
        related_name='production_stages', verbose_name='خطوة الإنتاج',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='الحالة')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='وقت البداية')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='وقت الاكتمال')
    worker_count = models.PositiveIntegerField(default=0, verbose_name='عدد العمال')
    actual_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='الساعات الفعلية')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'مرحلة إنتاج'
        verbose_name_plural = 'مراحل الإنتاج'

    def __str__(self):
        return f'{self.production_order} - {self.step}'


class MaterialConsumption(AuditMixin):
    """استهلاك المواد في الإنتاج"""
    production_order = models.ForeignKey(
        'ProductionOrder', on_delete=models.CASCADE,
        related_name='material_consumptions', verbose_name='أمر الإنتاج',
    )
    raw_material = models.ForeignKey(
        'inventory.Product', on_delete=models.PROTECT,
        related_name='material_consumptions', verbose_name='المادة الخام',
    )
    planned_quantity = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='الكمية المخططة')
    actual_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الكمية الفعلية')
    waste_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='كمية الهالك')
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='تكلفة الوحدة')
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي التكلفة')
    stock_move = models.ForeignKey(
        'inventory.StockMove', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='material_consumptions', verbose_name='حركة المخزون',
    )

    class Meta:
        verbose_name = 'استهلاك مواد'
        verbose_name_plural = 'استهلاكات المواد'

    def __str__(self):
        return f'{self.raw_material} - أمر: {self.production_order}'

