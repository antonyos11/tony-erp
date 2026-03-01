"""
نماذج تطبيق المشتريات — RITA ERP
"""
from django.db import models
from apps.core.models import AuditMixin


class PurchaseOrder(AuditMixin):
    ORDER_STATUSES = [
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('received', 'تم الاستلام'),
        ('partial', 'استلام جزئي'),
        ('cancelled', 'ملغي'),
    ]
    order_number = models.CharField(max_length=50, unique=True, verbose_name="رقم أمر الشراء")
    date = models.DateTimeField(verbose_name="التاريخ")
    supplier = models.ForeignKey(
        'partners.Supplier', on_delete=models.PROTECT,
        related_name='purchase_orders', verbose_name="المورد",
    )
    branch = models.ForeignKey(
        'core.Branch', on_delete=models.PROTECT,
        related_name='purchase_orders', verbose_name="الفرع",
    )
    warehouse = models.ForeignKey(
        'core.Warehouse', on_delete=models.PROTECT,
        related_name='purchase_orders', verbose_name="المخزن",
    )
    status = models.CharField(
        max_length=20, choices=ORDER_STATUSES, default='draft',
        verbose_name="الحالة",
    )
    subtotal = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name="الإجمالي قبل الضريبة",
    )
    tax_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name="الضريبة",
    )
    total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name="الإجمالي",
    )
    is_taxable = models.BooleanField(default=True, verbose_name="شراء ضريبي")
    paid_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name="المدفوع",
    )
    remaining_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name="المتبقي",
    )
    journal_entry = models.ForeignKey(
        'accounts.JournalEntry', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="القيد",
        related_name='purchase_orders',
    )
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name = "أمر شراء"
        verbose_name_plural = "أوامر الشراء"
        ordering = ['-date', '-order_number']

    def __str__(self):
        return f'{self.order_number} - {self.supplier}'


class PurchaseOrderLine(models.Model):
    order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE,
        related_name='lines', verbose_name="الأمر",
    )
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.PROTECT,
        verbose_name="المنتج",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="الكمية")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="تكلفة الوحدة")
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="الإجمالي")
    received_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="الكمية المستلمة",
    )
    notes = models.CharField(max_length=500, blank=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name = "سطر أمر شراء"
        verbose_name_plural = "سطور أمر الشراء"

    def __str__(self):
        return f'{self.product} x{self.quantity} @ {self.unit_cost}'
