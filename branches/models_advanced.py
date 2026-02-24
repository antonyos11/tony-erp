"""
نماذج الفروع المتقدمة
========================
أهداف المبيعات، تحويلات المخزون بين الفروع، تقارير الربحية
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class BranchTarget(models.Model):
    """أهداف الفرع الشهرية"""
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='targets',
        verbose_name='الفرع'
    )
    period = models.CharField(
        max_length=7,
        verbose_name='الفترة',
        help_text='بتنسيق YYYY-MM مثل 2026-01'
    )
    sales_target = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='هدف المبيعات'
    )
    actual_sales = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='المبيعات الفعلية'
    )
    new_customers_target = models.PositiveIntegerField(
        default=0,
        verbose_name='هدف العملاء الجدد'
    )
    actual_new_customers = models.PositiveIntegerField(
        default=0,
        verbose_name='العملاء الجدد الفعلي'
    )
    collection_target = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='هدف التحصيل'
    )
    actual_collection = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='التحصيل الفعلي'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')

    class Meta:
        verbose_name = 'هدف فرع'
        verbose_name_plural = 'أهداف الفروع'
        unique_together = ['branch', 'period']
        ordering = ['-period', 'branch']

    def __str__(self):
        return f"{self.branch} - {self.period}"

    @property
    def sales_achievement(self):
        if self.sales_target > 0:
            return round(
                (float(self.actual_sales) / float(self.sales_target)) * 100, 1
            )
        return 0

    @property
    def customer_achievement(self):
        if self.new_customers_target > 0:
            return round(
                (self.actual_new_customers / self.new_customers_target) * 100, 1
            )
        return 0

    @property
    def collection_achievement(self):
        if self.collection_target > 0:
            return round(
                (float(self.actual_collection) / float(self.collection_target)) * 100, 1
            )
        return 0

    @property
    def overall_achievement(self):
        scores = []
        if self.sales_target > 0:
            scores.append(self.sales_achievement)
        if self.new_customers_target > 0:
            scores.append(self.customer_achievement)
        if self.collection_target > 0:
            scores.append(self.collection_achievement)
        if scores:
            return round(sum(scores) / len(scores), 1)
        return 0


class InterBranchTransfer(models.Model):
    """تحويلات المخزون بين الفروع"""
    STATUS_CHOICES = [
        ('requested', 'مطلوب'),
        ('approved', 'معتمد'),
        ('in_transit', 'قيد النقل'),
        ('received', 'مستلم'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغي'),
    ]

    transfer_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='رقم التحويل'
    )
    from_branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='inter_transfers_out',
        verbose_name='من فرع'
    )
    to_branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='inter_transfers_in',
        verbose_name='إلى فرع'
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transfer_requests',
        verbose_name='طُلب بواسطة'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_branch_transfers',
        verbose_name='اعتُمد بواسطة'
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_branch_transfers',
        verbose_name='استُلم بواسطة'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='requested',
        verbose_name='الحالة'
    )
    reason = models.TextField(blank=True, verbose_name='سبب التحويل')
    request_date = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الطلب')
    approval_date = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الاعتماد')
    ship_date = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الشحن')
    receive_date = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الاستلام')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'تحويل بين فروع'
        verbose_name_plural = 'تحويلات بين الفروع'
        ordering = ['-request_date']

    def __str__(self):
        return f"#{self.transfer_number}: {self.from_branch} → {self.to_branch}"

    def save(self, *args, **kwargs):
        if not self.transfer_number:
            from django.utils.timezone import now
            prefix = now().strftime('TRF-%Y%m%d-')
            last = InterBranchTransfer.objects.filter(
                transfer_number__startswith=prefix
            ).count()
            self.transfer_number = f"{prefix}{last + 1:04d}"
        super().save(*args, **kwargs)

    def approve(self, user):
        self.status = 'approved'
        self.approved_by = user
        self.approval_date = timezone.now()
        self.save(update_fields=['status', 'approved_by', 'approval_date'])

    def ship(self):
        self.status = 'in_transit'
        self.ship_date = timezone.now()
        self.save(update_fields=['status', 'ship_date'])

    def receive(self, user):
        self.status = 'received'
        self.received_by = user
        self.receive_date = timezone.now()
        self.save(update_fields=['status', 'received_by', 'receive_date'])

    @property
    def total_items(self):
        return self.items.count()

    @property
    def total_quantity(self):
        from django.db.models import Sum
        result = self.items.aggregate(total=Sum('quantity'))
        return result['total'] or 0

    @property
    def total_value(self):
        from django.db.models import F, Sum
        result = self.items.aggregate(
            total=Sum(F('quantity') * F('unit_cost'))
        )
        return result['total'] or 0


class InterBranchTransferItem(models.Model):
    """بند في تحويل بين الفروع"""
    transfer = models.ForeignKey(
        InterBranchTransfer,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='التحويل'
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        verbose_name='المنتج'
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='الكمية'
    )
    received_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='الكمية المستلمة'
    )
    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='تكلفة الوحدة'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'بند تحويل'
        verbose_name_plural = 'بنود التحويل'

    def __str__(self):
        return f"{self.product} × {self.quantity}"

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost

    @property
    def shortage(self):
        return self.quantity - self.received_quantity


class BranchProfitability(models.Model):
    """تقرير ربحية الفرع الشهري"""
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='profitability_reports',
        verbose_name='الفرع'
    )
    period = models.CharField(
        max_length=7,
        verbose_name='الفترة',
        help_text='بتنسيق YYYY-MM'
    )
    total_revenue = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='إجمالي الإيرادات'
    )
    returns_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='المرتجعات'
    )
    cost_of_goods = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='تكلفة البضاعة المباعة'
    )
    salary_expense = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='مصاريف الرواتب'
    )
    rent_expense = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='مصاريف الإيجار'
    )
    utilities_expense = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='مصاريف المرافق'
    )
    marketing_expense = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='مصاريف التسويق'
    )
    other_expenses = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='مصاريف أخرى'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    calculated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ الحساب')
    calculated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='حُسبت بواسطة'
    )

    class Meta:
        verbose_name = 'ربحية فرع'
        verbose_name_plural = 'تقارير ربحية الفروع'
        unique_together = ['branch', 'period']
        ordering = ['-period', 'branch']

    def __str__(self):
        return f"{self.branch} - {self.period}"

    @property
    def net_revenue(self):
        return self.total_revenue - self.returns_amount

    @property
    def gross_profit(self):
        return self.net_revenue - self.cost_of_goods

    @property
    def gross_profit_margin(self):
        if self.net_revenue > 0:
            return round(
                (float(self.gross_profit) / float(self.net_revenue)) * 100, 1
            )
        return 0

    @property
    def total_operating_expenses(self):
        return (
            self.salary_expense +
            self.rent_expense +
            self.utilities_expense +
            self.marketing_expense +
            self.other_expenses
        )

    @property
    def net_profit(self):
        return self.gross_profit - self.total_operating_expenses

    @property
    def net_profit_margin(self):
        if self.net_revenue > 0:
            return round(
                (float(self.net_profit) / float(self.net_revenue)) * 100, 1
            )
        return 0

    @property
    def is_profitable(self):
        return self.net_profit > 0
