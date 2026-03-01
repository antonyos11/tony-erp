"""
نماذج تطبيق الأقساط — RITA ERP
"""
from django.db import models
from apps.core.models import AuditMixin


class InstallmentPlan(AuditMixin):
    """خطة أقساط مرتبطة بفاتورة بيع"""
    STATUS_CHOICES = [
        ('active',    'نشط'),
        ('completed', 'مكتمل'),
        ('defaulted', 'متعثر'),
    ]

    invoice = models.ForeignKey(
        'sales.SalesInvoice', on_delete=models.PROTECT,
        related_name='installment_plans', verbose_name="الفاتورة",
    )
    customer = models.ForeignKey(
        'sales.Customer', on_delete=models.PROTECT,
        related_name='installment_plans', verbose_name="العميل",
    )
    total_amount = models.DecimalField(
        max_digits=15, decimal_places=2, verbose_name="المبلغ الإجمالي",
    )
    down_payment = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="المقدم",
    )
    number_of_installments = models.IntegerField(verbose_name="عدد الأقساط")
    installment_amount = models.DecimalField(
        max_digits=15, decimal_places=2, verbose_name="قيمة القسط",
    )
    interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name="نسبة الفائدة %",
    )
    start_date = models.DateField(verbose_name="تاريخ أول قسط")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="الحالة",
    )

    class Meta:
        verbose_name = "خطة أقساط"
        verbose_name_plural = "خطط الأقساط"
        ordering = ['-created_at']

    def __str__(self):
        return f"خطة أقساط — {self.customer} ({self.number_of_installments} قسط)"

    @property
    def remaining_amount(self):
        paid = self.installments.filter(status='paid').aggregate(
            total=models.Sum('paid_amount')
        )['total'] or 0
        return self.total_amount - self.down_payment - paid

    @property
    def paid_installments_count(self):
        return self.installments.filter(status='paid').count()


class Installment(AuditMixin):
    """قسط فردي ضمن خطة أقساط"""
    STATUS_CHOICES = [
        ('pending', 'في الانتظار'),
        ('paid',    'مدفوع'),
        ('partial', 'جزئي'),
        ('overdue', 'متأخر'),
    ]

    plan = models.ForeignKey(
        InstallmentPlan, on_delete=models.CASCADE,
        related_name='installments', verbose_name="الخطة",
    )
    installment_number = models.IntegerField(verbose_name="رقم القسط")
    due_date = models.DateField(verbose_name="تاريخ الاستحقاق")
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, verbose_name="المبلغ",
    )
    paid_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="المدفوع",
    )
    paid_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الدفع")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="الحالة",
    )

    class Meta:
        verbose_name = "قسط"
        verbose_name_plural = "الأقساط"
        ordering = ['installment_number']

    def __str__(self):
        return f"قسط #{self.installment_number} — {self.plan} ({self.amount})"

    @property
    def remaining(self):
        return self.amount - self.paid_amount
