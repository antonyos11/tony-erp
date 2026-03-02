"""
نماذج تطبيق المخزون — RITA ERP
"""
from decimal import Decimal
from django.db import models
from apps.core.models import AuditMixin


class Category(AuditMixin):
    """تصنيف المنتجات"""
    name = models.CharField(max_length=200, verbose_name='الاسم')
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='children', verbose_name='التصنيف الأب',
    )

    class Meta:
        verbose_name = 'تصنيف'
        verbose_name_plural = 'التصنيفات'
        ordering = ['name']

    def __str__(self):
        return self.name


class UnitOfMeasure(models.Model):
    """وحدة القياس"""
    name = models.CharField(max_length=100, verbose_name='الاسم')
    symbol = models.CharField(max_length=20, verbose_name='الرمز')

    class Meta:
        verbose_name = 'وحدة قياس'
        verbose_name_plural = 'وحدات القياس'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.symbol})'


class Product(AuditMixin):
    """المنتجات والمواد"""
    PRODUCT_TYPE_CHOICES = [
        ('raw_material', 'مادة خام'),
        ('semi_finished', 'نصف مصنع'),
        ('finished', 'منتج تام'),
        ('consumable', 'مستهلك'),
    ]
    VALUATION_METHOD_CHOICES = [
        ('fifo', 'FIFO - الوارد أولاً صادر أولاً'),
        ('average', 'متوسط التكلفة'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name='الكود')
    barcode = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name='الباركود')
    name = models.CharField(max_length=300, verbose_name='الاسم')
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, verbose_name='نوع المنتج')
    category = models.ForeignKey(
        'Category', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='products', verbose_name='التصنيف',
    )
    unit = models.ForeignKey(
        'UnitOfMeasure', on_delete=models.PROTECT,
        related_name='products', verbose_name='وحدة القياس',
    )
    valuation_method = models.CharField(
        max_length=10, choices=VALUATION_METHOD_CHOICES,
        default='average', verbose_name='طريقة التقييم',
    )
    cost_price = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='سعر التكلفة')
    retail_price = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='سعر التجزئة')
    wholesale_price = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='سعر الجملة')
    reorder_level = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='مستوى إعادة الطلب')
    is_taxable = models.BooleanField(default=True, verbose_name='خاضع للضريبة')
    warranty_months = models.PositiveIntegerField(default=0, verbose_name='ضمان (أشهر)')
    description = models.TextField(blank=True, verbose_name='الوصف')
    is_custom_size = models.BooleanField(default=False, verbose_name='مقاس مخصص')
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='العرض (سم)')
    length = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='الطول (سم)')
    height = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='الارتفاع (سم)')
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'منتج'
        verbose_name_plural = 'المنتجات'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class BillOfMaterials(AuditMixin):
    """قائمة مواد (BOM) — محسّنة"""
    BOM_TYPES = [
        ('standard', 'قياسية'),
        ('phantom', 'وهمية (نصف مصنع يذوب)'),
        ('configurable', 'قابلة للتخصيص'),
    ]

    product = models.ForeignKey(
        'Product', on_delete=models.CASCADE,
        related_name='boms', verbose_name='المنتج النهائي',
    )
    code = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name='كود BOM')
    name = models.CharField(max_length=255, verbose_name='اسم BOM')
    bom_type = models.CharField(max_length=20, choices=BOM_TYPES, default='standard', verbose_name='النوع')
    version = models.IntegerField(default=1, verbose_name='الإصدار')

    # لو BOM لمقاس معين
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='العرض (سم)')
    length = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='الطول (سم)')
    height = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='الارتفاع (سم)')

    # التكلفة التقديرية
    estimated_material_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='تكلفة خامات تقديرية')
    estimated_labor_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='تكلفة عمالة تقديرية')
    estimated_overhead_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='overhead تقديري')
    estimated_total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='التكلفة الإجمالية التقديرية')

    is_default = models.BooleanField(default=False, verbose_name='افتراضي')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'قائمة مواد (BOM)'
        verbose_name_plural = 'قوائم المواد (BOM)'
        ordering = ['product__name', '-version']

    def __str__(self):
        size = f' {self.width}×{self.length}' if self.width else ''
        return f'{self.name}{size} (v{self.version})'

    def calculate_estimated_cost(self):
        """حساب التكلفة التقديرية من السطور"""
        total = Decimal('0')
        for line in self.lines.all():
            if line.is_sub_assembly:
                sub_bom = line.component.boms.filter(is_active=True).first()
                sub_bom.calculate_estimated_cost()
                line_cost = sub_bom.estimated_total_cost * line.effective_quantity
            else:
                line_cost = (line.component.cost_price or Decimal('0')) * line.effective_quantity
            total += line_cost

        self.estimated_material_cost = total
        self.estimated_total_cost = total + self.estimated_labor_cost + self.estimated_overhead_cost
        self.save(update_fields=['estimated_material_cost', 'estimated_total_cost'])
        return self.estimated_total_cost


class BOMLine(models.Model):
    """سطر BOM — محسّن"""
    bom = models.ForeignKey(
        'BillOfMaterials', on_delete=models.CASCADE,
        related_name='lines', verbose_name='قائمة المواد',
    )
    # raw_material kept for backward compatibility; component is the preferred accessor
    raw_material = models.ForeignKey(
        'Product', on_delete=models.PROTECT,
        related_name='bom_lines', verbose_name='المكوّن',
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=4, verbose_name='الكمية')
    unit = models.ForeignKey(
        'UnitOfMeasure', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='الوحدة',
    )

    # هل هو مكوّن بديل أو أساسي
    is_alternative = models.BooleanField(default=False, verbose_name='مكوّن بديل')
    alternative_group = models.CharField(max_length=20, blank=True, verbose_name='مجموعة البدائل')

    # نسبة الهالك المتوقعة
    waste_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نسبة هالك %')

    notes = models.CharField(max_length=500, blank=True, verbose_name='ملاحظات')
    sort_order = models.IntegerField(default=0, verbose_name='الترتيب')

    class Meta:
        verbose_name = 'مكوّن BOM'
        verbose_name_plural = 'مكوّنات BOM'
        ordering = ['sort_order']

    def __str__(self):
        return f'{self.raw_material} x{self.quantity}'

    @property
    def component(self):
        """المكوّن — alias لـ raw_material"""
        return self.raw_material

    @property
    def effective_quantity(self):
        """الكمية الفعلية مع الهالك"""
        return self.quantity * (1 + self.waste_percentage / 100)

    @property
    def line_cost(self):
        """تكلفة السطر"""
        return self.effective_quantity * (self.raw_material.cost_price or Decimal('0'))

    @property
    def is_sub_assembly(self):
        """هل المكوّن نصف مصنع (له BOM خاص به)"""
        return (
            self.raw_material.product_type == 'semi_finished'
            and self.raw_material.boms.filter(is_active=True).exists()
        )


class StockMove(AuditMixin):
    """حركة المخزون"""
    MOVE_TYPE_CHOICES = [
        ('in', 'وارد'),
        ('out', 'صادر'),
        ('transfer', 'تحويل'),
        ('production_in', 'إنتاج وارد'),
        ('production_out', 'إنتاج صادر'),
        ('adjustment', 'تسوية'),
        ('return_in', 'مرتجع وارد'),
        ('return_out', 'مرتجع صادر'),
        ('waste', 'هالك'),
    ]

    move_number = models.CharField(max_length=50, unique=True, verbose_name='رقم الحركة')
    date = models.DateTimeField(verbose_name='التاريخ')
    move_type = models.CharField(max_length=20, choices=MOVE_TYPE_CHOICES, verbose_name='نوع الحركة')
    product = models.ForeignKey(
        'Product', on_delete=models.PROTECT,
        related_name='stock_moves', verbose_name='المنتج',
    )
    quantity = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='الكمية')
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='تكلفة الوحدة')
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي التكلفة')
    warehouse_from = models.ForeignKey(
        'core.Warehouse', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='moves_out', verbose_name='من مخزن',
    )
    warehouse_to = models.ForeignKey(
        'core.Warehouse', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='moves_in', verbose_name='إلى مخزن',
    )
    source_type = models.CharField(max_length=100, blank=True, verbose_name='نوع المصدر')
    source_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='معرف المصدر')
    journal_entry = models.ForeignKey(
        'accounts.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='stock_moves', verbose_name='القيد',
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'حركة مخزون'
        verbose_name_plural = 'حركات المخزون'
        ordering = ['-date']

    def __str__(self):
        return f'{self.move_number} - {self.product}'


class StockLevel(models.Model):
    """مستوى المخزون الحالي"""
    product = models.ForeignKey(
        'Product', on_delete=models.CASCADE,
        related_name='stock_levels', verbose_name='المنتج',
    )
    warehouse = models.ForeignKey(
        'core.Warehouse', on_delete=models.CASCADE,
        related_name='stock_levels', verbose_name='المخزن',
    )
    quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الكمية')
    average_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='متوسط التكلفة')
    last_updated = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')

    class Meta:
        verbose_name = 'مستوى مخزون'
        verbose_name_plural = 'مستويات المخزون'
        unique_together = [['product', 'warehouse']]

    def __str__(self):
        return f'{self.product} @ {self.warehouse}: {self.quantity}'


# ══════════════════════════════════════════════════════
# الجرد المخزني (Sprint 20)
# ══════════════════════════════════════════════════════

class StockCount(AuditMixin):
    """جرد مخزني"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('counting', 'جاري العد'),
        ('review', 'مراجعة'),
        ('applied', 'مطبّق'),
        ('cancelled', 'ملغي'),
    ]

    count_number = models.CharField(max_length=50, unique=True, verbose_name='رقم الجرد')
    date = models.DateField(verbose_name='التاريخ')
    warehouse = models.ForeignKey(
        'core.Warehouse', on_delete=models.PROTECT,
        related_name='stock_counts', verbose_name='المخزن',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='الحالة'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'جرد مخزني'
        verbose_name_plural = 'الجرد المخزني'
        ordering = ['-date']

    def __str__(self):
        return f'{self.count_number} - {self.warehouse}'

    def save(self, *args, **kwargs):
        if not self.count_number:
            from django.utils import timezone as tz
            last = StockCount.objects.order_by('-id').first()
            next_num = (last.id + 1) if last else 1
            self.count_number = f'SC-{tz.now().strftime("%Y%m")}-{next_num:04d}'
        super().save(*args, **kwargs)


class StockCountLine(models.Model):
    """سطر جرد"""
    stock_count = models.ForeignKey(
        StockCount, on_delete=models.CASCADE,
        related_name='lines', verbose_name='الجرد',
    )
    product = models.ForeignKey(
        'Product', on_delete=models.PROTECT,
        related_name='count_lines', verbose_name='المنتج',
    )
    system_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name='الكمية في النظام'
    )
    actual_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='الكمية الفعلية'
    )
    difference = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name='الفرق'
    )
    notes = models.CharField(max_length=500, blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'سطر جرد'
        verbose_name_plural = 'أسطر الجرد'

    def __str__(self):
        return f'{self.stock_count} — {self.product}'

    def save(self, *args, **kwargs):
        if self.actual_quantity is not None:
            self.difference = self.actual_quantity - self.system_quantity
        super().save(*args, **kwargs)
