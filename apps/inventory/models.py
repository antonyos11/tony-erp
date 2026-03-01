"""
نماذج تطبيق المخزون — RITA ERP
"""
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
    """قائمة المواد (BOM)"""
    product = models.ForeignKey(
        'Product', on_delete=models.CASCADE,
        related_name='boms', verbose_name='المنتج',
    )
    name = models.CharField(max_length=200, verbose_name='الاسم')
    is_default = models.BooleanField(default=False, verbose_name='افتراضي')
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'قائمة مواد'
        verbose_name_plural = 'قوائم المواد'

    def __str__(self):
        return f'{self.product} - {self.name}'


class BOMLine(models.Model):
    """سطر قائمة المواد"""
    bom = models.ForeignKey(
        'BillOfMaterials', on_delete=models.CASCADE,
        related_name='lines', verbose_name='قائمة المواد',
    )
    raw_material = models.ForeignKey(
        'Product', on_delete=models.PROTECT,
        related_name='bom_lines', verbose_name='المادة الخام',
    )
    quantity = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='الكمية')
    waste_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نسبة الهالك %')
    notes = models.CharField(max_length=500, blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'سطر قائمة مواد'
        verbose_name_plural = 'أسطر قوائم المواد'

    def __str__(self):
        return f'{self.raw_material} x{self.quantity}'


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

