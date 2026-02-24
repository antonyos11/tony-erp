from django.db import models
from django.db import transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext as _t
from inventory.models import Product, Location, Stock
from partners.models import Customer
from hr.models import Employee
from django.contrib.auth.models import User, Permission, ContentType
from decimal import Decimal
from django.db.models import F, Sum
import threading

_sqlite_seq_lock = threading.Lock()
# Use RLock because save() acquires the global sqlite payment lock twice (once for
# sequence generation and again for the actual DB insert). A normal Lock caused
# a self-deadlock in concurrent creation test. RLock allows re-entrant acquisition
# by the same thread while still providing mutual exclusion across threads.
_sqlite_payment_create_lock = threading.RLock()

try:
    from .utils import bump_customer_statement_version
except Exception:  # pragma: no cover
    from typing import Any, TYPE_CHECKING
    def bump_customer_statement_version(customer_id: Any) -> Any:
        return None

if 'TYPE_CHECKING' in globals():
    from django.db.models import QuerySet

class Invoice(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices')
    date = models.DateField(default=timezone.localdate)
    # ربط الفاتورة بالمعرض/الفرع
    showroom = models.ForeignKey(
        'showrooms.Showroom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices',
        verbose_name=_('المعرض/الفرع')
    )
    due_date = models.DateField(null=True, blank=True)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    is_tax_inclusive = models.BooleanField(default=False, help_text=_('السعر/الإجمالي يشمل ضريبة القيمة المضافة؟ (يتم استخدامه للفصل في العرض والحسابات اللاحقة)'))
    is_withholding_applied = models.BooleanField(default=False, help_text=_('هل تم تطبيق خصم/استقطاع من المنبع على هذه الفاتورة يدوياً؟'))
    paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    cached_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), help_text=_('مجموع الفاتورة مخزن لتسريع التحقق تحت SQLite'))
    payment_method = models.ForeignKey('payments.PaymentMethod', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('طريقة الدفع'))
    payment_reference = models.CharField(max_length=100, blank=True, verbose_name=_('مرجع الدفع (شيك/تحويل/Instapay/محفظة)'))
    # تفاصيل اختيارية للحوالة البنكية على مستوى الفاتورة (تُستخدم كافتراض عند إضافة دفعة)
    bank_name = models.CharField(_('اسم البنك (للحوالة)'), max_length=120, blank=True)
    bank_account = models.CharField(_('رقم / IBAN الحساب (للحوالة)'), max_length=120, blank=True)
    # ===== Optional invoice fields (checkbox-controlled) =====
    is_tax_invoice = models.BooleanField(default=False, verbose_name=_('فاتورة ضريبية'))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), verbose_name=_('نسبة الضريبة %'))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name=_('قيمة الضريبة'))
    enable_shipping = models.BooleanField(default=False, verbose_name=_('تفعيل الشحن'))
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name=_('تكلفة الشحن'))
    enable_extra_discount = models.BooleanField(default=False, verbose_name=_('تفعيل خصم إضافي'))
    extra_discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name=_('الخصم الإضافي'))
    enable_previous_balance = models.BooleanField(default=False, verbose_name=_('تفعيل رصيد سابق'))
    previous_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name=_('الرصيد السابق'))

    # Accounting integration
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_invoices',
        verbose_name=_('القيد المحاسبي')
    )
    is_posted = models.BooleanField(default=False, verbose_name=_('مرحّل محاسبياً'))
    # Deletion tracking
    is_deleted = models.BooleanField(default=False, verbose_name=_('محذوف'))
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_('تاريخ الحذف'))
    deleted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='deleted_invoices', verbose_name=_('محذوف بواسطة'))
    delete_reason = models.TextField(blank=True, verbose_name=_('سبب الحذف'))
    
    # Approval tracking
    is_approved = models.BooleanField(default=False, verbose_name=_('معتمد'))
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_invoices', verbose_name=_('معتمد بواسطة'))
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_('تاريخ الاعتماد'))

    def __str__(self):
        customer_name = getattr(self.customer, 'name', '') if hasattr(self, 'customer') else ''
        return f"{self.number} - {customer_name}".strip(" -")

    @property
    def total(self):
        if self.cached_total is not None:
            return (self.cached_total or Decimal('0')) - self.discount
        return sum(item.total for item in self.items.all()) - self.discount

    @property
    def tax(self):
        from decimal import ROUND_HALF_UP
        subtotal = sum(item.total for item in self.items.all())
        # جلب نسبة الضريبة من إعدادات الشركة بدلاً من القيمة الثابتة
        try:
            from core.models import Company
            company = Company.objects.first()
            if company and company.default_vat_rate:
                vat_rate = company.default_vat_rate / Decimal('100')
            else:
                vat_rate = Decimal('0.14')
        except Exception:
            vat_rate = Decimal('0.14')
        if self.is_tax_inclusive:
            base = subtotal / (Decimal('1.0') + vat_rate) if subtotal else Decimal('0')
            tax = subtotal - base
        else:
            tax = subtotal * vat_rate
        return tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @property
    def remaining(self):
        return (self.total or Decimal('0')) - (self.paid or Decimal('0'))

    class Meta:
        permissions = [("print_customerstatement", "طباعة كشف حساب عميل")]
        indexes = [
            models.Index(fields=['date'], name='invoice_date_idx'),
            models.Index(fields=['customer', 'date'], name='invoice_customer_date_idx'),
            models.Index(fields=['is_deleted', 'date'], name='invoice_deleted_date_idx'),
            models.Index(fields=['due_date'], name='invoice_due_date_idx'),
        ]

    def save(self, *args, **kwargs):
        # Apply discount directly to cached_total to keep totals non-negative
        if self.discount and self.discount > 0:
            gross_total = self.cached_total if self.cached_total is not None else sum(item.total for item in self.items.all())
            if gross_total and gross_total > 0:
                if self.discount >= gross_total:
                    self.cached_total = Decimal('0')
                    self.discount = Decimal('0')
                else:
                    # keep gross in cached_total and apply discount at read time
                    self.cached_total = gross_total
        from django.db.utils import OperationalError
        # Auto-generate a unique invoice number if not provided
        if not self.number:
            from core.sequence_utils import next_sequence, format_code
            from django.db import IntegrityError
            from django.utils import timezone
            import time
            
            # استخدام تنسيق يتضمن السنة والشهر لتسهيل التتبع
            now = timezone.now()
            prefix = f"INV-{now.strftime('%Y%m')}"
            
            # محاولة توليد رقم فريد مع إعادة المحاولة عند التكرار
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    seq = next_sequence(f'INVOICE_{now.strftime("%Y%m")}')
                    self.number = f"{prefix}-{str(seq).zfill(6)}"
                    super().save(*args, **kwargs)
                    return  # نجحت العملية
                except (IntegrityError, OperationalError) as e:
                    msg = str(e).lower()
                    if 'unique' in msg or 'locked' in msg:
                        # انتظار قصير ثم إعادة المحاولة
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    raise  # خطأ آخر غير التكرار
            
            # إذا فشلت كل المحاولات، استخدم timestamp
            self.number = f"{prefix}-{int(now.timestamp())}"
        
        super().save(*args, **kwargs)


    # TYPE_CHECKING block removed

class InvoiceItem(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    location = models.ForeignKey('inventory.Location', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def total(self):
        return self.quantity * self.price


@receiver(post_save, sender=InvoiceItem)
def invoice_item_added(sender, instance: 'InvoiceItem', created, **kwargs):
    """
    Post-save signal — intentionally minimal.

    1. Update invoice cached_total (fast F() UPDATE, no row lock needed).
    2. Delegate stock deduction to sales.services.stock_service which owns
       its own @transaction.atomic + select_for_update block.

    WHY NOT select_for_update HERE:
    Signals fire inside the caller's transaction.  Acquiring a row lock inside
    a signal while the caller also holds locks is a deadlock recipe under
    concurrent load.  The service releases its lock before returning so the
    outer transaction is never blocked.
    """
    if not created:
        return

    import logging
    logger = logging.getLogger(__name__)

    # 1) Update cached_total — single F() UPDATE, no lock required.
    line_total = instance.quantity * instance.price
    Invoice.objects.filter(pk=instance.invoice_id).update(
        cached_total=F('cached_total') + line_total
    )

    # 2) Deduct stock via service (owns its own atomic + select_for_update).
    try:
        from sales.services.stock_service import deduct_stock_for_invoice_item
        deduct_stock_for_invoice_item(instance)
    except Exception as e:
        logger.error(
            "Error deducting stock for InvoiceItem %s: %s",
            instance.pk, e, exc_info=True,
        )


@receiver(pre_delete, sender=InvoiceItem)
def invoice_item_deleted(sender, instance: 'InvoiceItem', **kwargs):
    """
    Pre-delete signal — intentionally minimal.

    1. Reverse invoice cached_total (fast F() UPDATE, no row lock needed).
    2. Delegate stock restoration to sales.services.stock_service which owns
       its own @transaction.atomic + select_for_update block.
    """
    import logging
    logger = logging.getLogger(__name__)

    # 1) Reverse cached_total — single F() UPDATE, no lock required.
    line_total = instance.quantity * instance.price
    Invoice.objects.filter(pk=instance.invoice_id).update(
        cached_total=F('cached_total') - line_total
    )

    # 2) Restore stock via service (owns its own atomic + select_for_update).
    try:
        from sales.services.stock_service import restore_stock_for_invoice_item
        restore_stock_for_invoice_item(instance)
    except Exception as e:
        logger.error(
            "Error restoring stock for deleted InvoiceItem %s: %s",
            instance.pk, e, exc_info=True,
        )


# ============================================================================
# خريطة طلبات البيع (SaleOrder/SaleOrderItem) لأغراض التحليلات والاختبارات
# ============================================================================


class SaleOrderManager(models.Manager):
    """مدير مبسط ينشئ Invoice أساسية ليستخدمها محلل المخزون."""

    def create(self, customer_name=None, date=None, status='confirmed', **kwargs):  # type: ignore[override]
        from partners.models import Customer
        from django.utils import timezone

        customer_name = customer_name or "Test Customer"
        customer, _ = Customer.objects.get_or_create(name=customer_name)
        invoice = Invoice.objects.create(
            customer=customer,
            date=date or timezone.now().date(),
            delete_reason=status or '',  # احتفاظ اختياري بالحالة الأصلية
        )
        return self.model.objects.get(pk=invoice.pk)


class SaleOrder(Invoice):
    """Proxy على Invoice لتوفير واجهة SaleOrder المستخدمة بالاختبارات."""

    objects = SaleOrderManager()

    class Meta:
        proxy = True
        verbose_name = "Sale Order"
        verbose_name_plural = "Sale Orders"

    @property
    def customer_name(self):
        return getattr(self.customer, 'name', '') if self.customer_id else ''

    @property
    def status(self):
        # تُخزن حالة الإنشاء في حقل delete_reason عند الحاجة فقط للأغراض التحليلية
        return self.delete_reason or 'confirmed'


class SaleOrderItemManager(models.Manager):
    """ينشئ InvoiceItem مرتبطاً لالتقاط المبيعات في التحليلات."""

    def create(self, order=None, product=None, quantity=0, unit_price=Decimal('0'), **kwargs):  # type: ignore[override]
        from inventory.models import Location
        if order is None or product is None:
            raise ValueError("order and product are required")
        location = kwargs.get('location')
        if location is None:
            location, _ = Location.objects.get_or_create(code="DEFAULT", defaults={'name': 'Default Location'})
        invoice_item = InvoiceItem.objects.create(
            invoice=order,
            product=product,
            location=location,
            quantity=quantity,
            price=unit_price,
        )
        return self.model.objects.get(pk=invoice_item.pk)


class SaleOrderItem(InvoiceItem):
    """Proxy على InvoiceItem لضمان توافق واجهة الاختبار."""

    objects = SaleOrderItemManager()

    class Meta:
        proxy = True
        verbose_name = "Sale Order Item"
        verbose_name_plural = "Sale Order Items"


class FieldVisit(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    OUTCOME_CHOICES = [
        ("won", _("إغلاق ناجح")),
        ("lost", _("لم يكتمل")),
        ("follow_up", _("متابعة مطلوبة")),
        ("demo", _("عرض توضيحي")),
    ]

    visit_date = models.DateField(default=timezone.localdate, verbose_name=_("تاريخ الزيارة"))
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("المندوب"))
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("العميل"))
    subject = models.CharField(max_length=200, blank=True, verbose_name=_("الموضوع"))
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, default="follow_up", verbose_name=_("النتيجة"))
    next_action_date = models.DateField(null=True, blank=True, verbose_name=_("تاريخ المتابعة"))
    
    # حقول الموقع الجغرافي للتتبع
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name=_("خط العرض"))
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name=_("خط الطول"))
    location_accuracy = models.FloatField(null=True, blank=True, verbose_name=_("دقة الموقع (متر)"))
    check_in_time = models.DateTimeField(null=True, blank=True, verbose_name=_("وقت تسجيل الدخول"))
    check_out_time = models.DateTimeField(null=True, blank=True, verbose_name=_("وقت تسجيل الخروج"))
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("زيارة ميدانية")
        verbose_name_plural = _("زيارات ميدانية")
        ordering = ["-visit_date", "-id"]
        indexes = [
            models.Index(fields=["visit_date"], name="fieldvisit_visit_date_idx"),
            models.Index(fields=["outcome"], name="fieldvisit_outcome_idx"),
        ]

    def __str__(self) -> str:
        who = self.customer.name if self.customer else _("عميل غير محدد")
        return _("زيارة %(who)s - %(date)s") % {"who": who, "date": self.visit_date}


class CollectionTask(models.Model):
    STATUS_CHOICES = [("open", _("مفتوحة")), ("in_progress", _("قيد المعالجة")), ("done", _("منجزة"))]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, verbose_name=_("العميل"))
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="collection_tasks", verbose_name=_("فاتورة"))
    due_date = models.DateField(verbose_name=_("تاريخ الاستحقاق"))
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("المبلغ المستحق"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open", verbose_name=_("الحالة"))
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("مسؤول المتابعة"))
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("مهمة تحصيل")
        verbose_name_plural = _("مهام التحصيل")
        ordering = ["due_date", "-id"]
        indexes = [
            models.Index(fields=["status"], name="collection_status_idx"),
            models.Index(fields=["due_date"], name="collection_due_date_idx"),
        ]

    def __str__(self) -> str:
        return _("تحصيل %(customer)s - %(amount)s يستحق %(due)s") % {"customer": self.customer, "amount": self.amount_due, "due": self.due_date}


class SalesReturn(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    number = models.CharField(max_length=50, unique=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='sales_returns')
    date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = _("مرتجع بيع")
        verbose_name_plural = _("مرتجعات البيع")
        indexes = [models.Index(fields=["date"], name="salesreturn_date_idx")]

    def __str__(self):
        return self.number

    def save(self, *args, **kwargs):
        if not self.number:
            from core.sequence_utils import next_sequence
            from django.db import IntegrityError
            from django.utils import timezone
            import time
            
            now = timezone.now()
            prefix = f"RET-{now.strftime('%Y%m')}"
            
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    seq = next_sequence(f'SALES_RETURN_{now.strftime("%Y%m")}')
                    self.number = f"{prefix}-{str(seq).zfill(6)}"
                    super().save(*args, **kwargs)
                    return
                except IntegrityError as e:
                    if 'UNIQUE constraint failed' in str(e) or 'unique' in str(e).lower():
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    raise
            
            self.number = f"{prefix}-{int(now.timestamp())}"
        
        super().save(*args, **kwargs)


class SalesReturnItem(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    sales_return = models.ForeignKey(SalesReturn, on_delete=models.CASCADE, related_name='items')
    invoice_item = models.ForeignKey('InvoiceItem', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    def apply_stock(self):
        stock, _ = Stock.objects.get_or_create(product=self.invoice_item.product, location=self.invoice_item.location)
        stock.quantity += self.quantity
        stock.save()


class InvoicePayment(models.Model):
    @staticmethod
    def _recalc_invoice_paid(invoice_id):
        """Recalculate the paid amount from existing payments to avoid stale values."""
        if not invoice_id:
            return
        total_paid = InvoicePayment.objects.filter(invoice_id=invoice_id).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        Invoice.objects.filter(pk=invoice_id).update(paid=total_paid)

    @property
    def unapplied_amount(self):
        from django.db.models import Sum as DJSum
        total_alloc = self.allocations.aggregate(s=DJSum('amount'))['s'] or Decimal('0')
        return (self.amount or Decimal('0')) - total_alloc if (self.invoice is None) else Decimal('0')
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    # Nullable للسماح بإيصالات (دفعات) مقدمة غير مرتبطة بفاتورة بعد
    invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.SET_NULL, related_name='payments', verbose_name=_('الفاتورة'))
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoice_payments', verbose_name=_('العميل'))
    receipt_number = models.CharField(_('رقم الإيصال'), max_length=30, unique=True, blank=True)
    date = models.DateTimeField(_('التاريخ'), default=timezone.now)
    amount = models.DecimalField(_('المبلغ المدفوع'), max_digits=12, decimal_places=2)
    payment_method = models.CharField(_('طريقة الدفع'), max_length=20, default='cash')
    reference = models.CharField(_('مرجع (شيك/تحويل)'), max_length=100, blank=True)
    # إدخال يدوي لبيانات البنك (اسم البنك، رقم/IBAN الحساب) في حالة الحوالة البنكية
    bank_name = models.CharField(_('اسم البنك (مخصص للدفعة)'), max_length=120, blank=True)
    bank_account = models.CharField(_('رقم / IBAN الحساب (مخصص للدفعة)'), max_length=120, blank=True)
    description = models.TextField(_('وصف / بيان'), blank=True, help_text=_('بيان توضيحي يظهر في الإيصال وكشف الحساب'))
    journal_entry = models.ForeignKey('accounting.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_payments', verbose_name=_('القيد المحاسبي'))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_invoice_payments', verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    first_printed_at = models.DateTimeField(_('تاريخ أول طباعة'), null=True, blank=True)
    printed_count = models.PositiveIntegerField(_('عدد مرات الطباعة'), default=0)
    locked = models.BooleanField(_('مقفول بعد الطباعة'), default=False, help_text=_('يمنع التعديل/الحذف بعد القفل'))
    status = models.CharField(_('الحالة'), max_length=12, default='draft', choices=[('draft','مسودة'),('posted','مرحلة'),('cancelled','ملغاة')])
    is_advance = models.BooleanField(_('دفعة مقدمة'), default=False, help_text=_('تكون صحيحة إذا لم ترتبط الدفعة بفاتورة عند الترحيل'))
    posted_at = models.DateTimeField(_('تاريخ الترحيل'), null=True, blank=True)
    posted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='posted_invoice_payments', verbose_name=_('رحّل بواسطة'))
    reverse_journal_entry = models.ForeignKey('accounting.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, related_name='reversed_invoice_payments', verbose_name=_('قيد الإلغاء'))

    class Meta:
        verbose_name = _('دفعة فاتورة')
        verbose_name_plural = _('دفعات الفواتير')
        ordering = ['-date', '-id']
        indexes = [
            models.Index(fields=['date'], name='invpay_date_idx'),
            models.Index(fields=['receipt_number'], name='invpay_receipt_idx'),
        ]
        permissions = [
            ("lock_invoicepayment", _('قفل دفعة فاتورة')),
            ("print_invoicepayment", _('طباعة إيصال دفعة فاتورة')),
            ("cancel_invoicepayment", _('إلغاء دفعة فاتورة')),
        ]

    def __str__(self):
        return f"{self.receipt_number} - {self.amount}"

    @property
    def monthly_sequence(self):
        if not self.receipt_number:
            return None
        try:
            return int(self.receipt_number.rsplit('-', 1)[1])
        except Exception:
            return None

    def save(self, *args, **kwargs):
        # Ensure customer is synced from invoice before any access
        if self.invoice and not getattr(self, 'customer_id', None):
            try:
                self.customer = self.invoice.customer
            except Exception:
                pass
        # منع تعديل جوهري بعد الترحيل (المبلغ / الفاتورة / العميل) مع السماح بتحديث حقول الطباعة
        if self.pk:
            try:
                orig = InvoicePayment.objects.filter(pk=self.pk).only('status','amount','invoice','customer').first()
                if orig and orig.status in ('posted','cancelled'):
                    immutable_fields = []
                    if self.amount != orig.amount:
                        immutable_fields.append('amount')
                    if (self.invoice.id if self.invoice else None) != (orig.invoice.id if orig.invoice else None):
                        immutable_fields.append('invoice')
                    if (self.customer.id if self.customer else None) != (orig.customer.id if orig.customer else None):
                        immutable_fields.append('customer')
                    if immutable_fields:
                        raise ValueError(_t('لا يمكن تعديل الحقول بعد الترحيل: ') + ', '.join(immutable_fields))
            except Exception:
                pass
        from django.db import connection
        # Ensure reasonable busy timeout for SQLite to reduce transient lock errors.
        if connection.vendor == 'sqlite':
            global _sqlite_busy_timeout_set
            try:
                _sqlite_busy_timeout_set  # type: ignore
            except NameError:  # pragma: no cover
                _sqlite_busy_timeout_set = False  # type: ignore
            if not _sqlite_busy_timeout_set:  # type: ignore
                try:  # pragma: no cover
                    with connection.cursor() as c:
                        c.execute('PRAGMA busy_timeout=5000')
                    _sqlite_busy_timeout_set = True  # type: ignore
                except Exception:
                    pass
        # Outer retry for rare 'database table is locked: sales_invoice' escaping internal retries
        outer_attempts = 0
        from django.db import OperationalError
        while True:
            lock_acquired = False
            if connection.vendor == 'sqlite' and not self.pk:
                _sqlite_payment_create_lock.acquire()
                lock_acquired = True
            try:
                # locked modification prevention
                if self.pk:
                    orig = InvoicePayment.objects.filter(pk=self.pk).only('locked','amount','payment_method','reference','description').first()
                    if orig and orig.locked:
                        for f in ['amount','payment_method','reference','description']:
                            if getattr(self, f, None) != getattr(orig, f, None):
                                raise ValueError(_t('لا يمكن تعديل دفعة مقفولة (تمت طباعة الإيصال)'))
                # duplicate reference per نفس الفاتورة فقط (السماح بإعادة الاستخدام لعملاء متعددين أو فواتير مختلفة)
                if self.reference and self.invoice_id:
                    qs = InvoicePayment.objects.filter(invoice_id=self.invoice_id, reference=self.reference)
                    if self.pk:
                        qs = qs.exclude(pk=self.pk)
                    if qs.exists():
                        raise ValueError(_t('مرجع الدفع مكرر لهذه الفاتورة'))
                # sequence generation (only if new)
                if not self.receipt_number:
                    now = timezone.now()
                    ym = now.strftime('%Y%m')
                    attempts = 0
                    while True:
                        try:
                            with transaction.atomic():
                                seq, _ = InvoicePaymentSequence.objects.select_for_update().get_or_create(year_month=ym)
                                seq.last_number += 1
                                seq.save(update_fields=['last_number'])
                                self.receipt_number = f"RCPT-{ym}-{seq.last_number:04d}"
                            break
                        except OperationalError as e:
                            if 'lock' in str(e).lower() and attempts < 8:
                                attempts += 1
                                import time; time.sleep(0.01 * attempts)
                                continue
                            raise
                # sync customer
                if self.invoice:
                    # sync customer from invoice if not explicitly set
                    current_customer = None
                    try:
                        current_customer = self.customer  # may raise RelatedObjectDoesNotExist if unset
                    except Exception:
                        current_customer = None
                    if (not current_customer or (self.invoice and current_customer != self.invoice.customer)) and self.invoice:
                        self.customer = self.invoice.customer
                    # compute remaining using direct DB values (avoid stale instance attributes)
                    inv_attempts = 0
                    while True:
                        try:
                            inv_vals = Invoice.objects.filter(pk=self.invoice.id if self.invoice else None).values('paid', 'cached_total', 'discount').first()
                            break
                        except OperationalError as e:
                            if 'lock' in str(e).lower() and connection.vendor == 'sqlite' and inv_attempts < 6:
                                inv_attempts += 1
                                import time; time.sleep(0.01 * inv_attempts)
                                continue
                            raise
                    if inv_vals:
                        cached_total = inv_vals['cached_total'] or Decimal('0')
                        discount = inv_vals['discount'] or Decimal('0')
                        total = (cached_total - discount)
                        paid_val = inv_vals['paid'] or Decimal('0')
                        remaining = (total or Decimal('0')) - paid_val
                    else:
                        remaining = Decimal('0')
                else:
                    remaining = None  # unapplied receipt (advance)
                old_amount = Decimal('0')
                if self.pk:
                    old_amount = InvoicePayment.objects.filter(pk=self.pk).values_list('amount', flat=True).first() or Decimal('0')
                    if remaining is not None:
                        remaining += old_amount
                if remaining is not None and remaining > Decimal('0') and self.amount > (remaining + Decimal('0.0001')):
                    raise ValueError(_t('المبلغ المدفوع يتجاوز المتبقي على الفاتورة'))
                # core save with retry on sqlite lock
                save_attempts = 0
                while True:
                    try:
                        super().save(*args, **kwargs)
                        break
                    except OperationalError as e:
                        if 'lock' in str(e).lower() and save_attempts < 8 and connection.vendor == 'sqlite':
                            save_attempts += 1
                            import time; time.sleep(0.01 * save_attempts)
                            continue
                        raise
                # update invoice paid delta with retry for sqlite locked errors
                if self.invoice:
                    self._recalc_invoice_paid(self.invoice.id)
                try:
                    bump_customer_statement_version(self.customer.id if self.customer else None)
                except Exception:
                    pass
                # success -> break outer loop
                break
            except OperationalError as e:
                if 'lock' in str(e).lower() and outer_attempts < 5 and connection.vendor == 'sqlite':
                    outer_attempts += 1
                    import time; time.sleep(0.02 * outer_attempts)
                    continue
                else:
                    raise
            finally:
                if lock_acquired:
                    try:
                        _sqlite_payment_create_lock.release()
                    except Exception:
                        pass

    def delete(self, using=None, keep_parents=False):
        if self.locked:
            raise ValueError(_t('لا يمكن حذف دفعة بعد قفلها'))
        amount = self.amount or Decimal('0')
        inv_id = self.invoice.id if self.invoice else None
        cust_id = self.customer.id if self.customer else None
        res = super().delete(using=using, keep_parents=keep_parents)
        try:
            if inv_id:
                self._recalc_invoice_paid(inv_id)
        except Exception:
            pass
        try:
            bump_customer_statement_version(cust_id)
        except Exception:
            pass
        return res


class InvoicePaymentSequence(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    year_month = models.CharField(max_length=6, unique=True, help_text=_('تنسيق YYYYMM'))
    last_number = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('تسلسل إيصالات المدفوعات')
        verbose_name_plural = _('تسلسلات إيصالات المدفوعات')

    def __str__(self):
        return f"{self.year_month}: {self.last_number}"


class InvoicePaymentAllocation(models.Model):
    """تخصيص جزء من دفعة (قد تكون مقدمة) إلى فاتورة معينة.

    القيود:
    - لا يتجاوز المبلغ المتبقي على الفاتورة
    - لا يتجاوز الرصيد غير المخصص في الدفعة
    """
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    payment = models.ForeignKey(InvoicePayment, on_delete=models.CASCADE, related_name='allocations', verbose_name=_('الدفعة'))
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payment_allocations', verbose_name=_('الفاتورة'))
    amount = models.DecimalField(_('المبلغ المخصص'), max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_payment_allocations', verbose_name=_('أنشئ بواسطة'))

    class Meta:
        verbose_name = _('تخصيص دفعة')
        verbose_name_plural = _('تخصيصات الدفعات')
        ordering = ['-id']
        indexes = [
            models.Index(fields=['invoice'], name='alloc_invoice_idx'),
            models.Index(fields=['payment'], name='alloc_payment_idx'),
        ]

    def __str__(self):
        return f"ALLOC {self.payment.id}->{self.invoice.id} {self.amount}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.amount <= 0:
            raise ValidationError(_('المبلغ يجب أن يكون > 0'))
        # تحقق المتبقي على الفاتورة (استناداً إلى paid و total الحالية)
        inv = self.invoice
        remaining_invoice = inv.remaining  # property deducts paid
        if self.pk is None and self.amount > remaining_invoice + Decimal('0.0001'):
            raise ValidationError(_('المبلغ يتجاوز المتبقي على الفاتورة'))
        # تحقق الرصيد غير المخصص في الدفعة
        available = self.payment.unapplied_amount if hasattr(self.payment, 'unapplied_amount') else Decimal('0')
        # عند تعديل تخصيص قائم يمكن السماح بنفس القيمة
        if self.pk:
            original = InvoicePaymentAllocation.objects.filter(pk=self.pk).values_list('amount', flat=True).first() or Decimal('0')
            available += original
        if self.amount > available + Decimal('0.0001'):
            raise ValidationError(_('المبلغ يتجاوز الرصيد المتبقي غير المخصص في الدفعة'))

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.full_clean()
        super().save(*args, **kwargs)
        # تحديث paid للفاتورة بعد حفظ تخصيص جديد فقط (الدفعة الأصلية غير مرتبطة بالفاتورة)
        if is_new:
            Invoice.objects.filter(pk=self.invoice.id if self.invoice else None).update(paid=F('paid') + self.amount)
            try:
                bump_customer_statement_version(self.payment.customer.id if self.payment and self.payment.customer else None)
            except Exception:
                pass

    def delete(self, using=None, keep_parents=False):
        amount = self.amount
        inv_id = self.invoice.id if self.invoice else None
        cust_id = self.payment.customer.id if self.payment and self.payment.customer else None
        res = super().delete(using=using, keep_parents=keep_parents)
        try:
            if amount and inv_id:
                Invoice.objects.filter(pk=inv_id).update(paid=F('paid') - amount)
        except Exception:
            pass
        try:
            bump_customer_statement_version(cust_id)
        except Exception:
            pass
        return res

    @property
    def customer(self):  # convenience
        return self.payment.customer

# Helper property added dynamically (monkey patch style would be avoided; implement in model)
def _unapplied_amount(self: 'InvoicePayment'):
    from django.db.models import Sum as DJSum
    total_alloc = self.allocations.aggregate(s=DJSum('amount'))['s'] or Decimal('0')
    return (self.amount or Decimal('0')) - total_alloc if (self.invoice is None) else Decimal('0')

setattr(InvoicePayment, 'unapplied_amount', property(_unapplied_amount))

# تمت إزالة إشارات إعادة احتساب paid لصالح تحديثات F expressions داخل save/delete


# ============================================================================
# Sales Orders - أوامر البيع
# ============================================================================

class SalesOrder(models.Model):
    """أمر بيع - يُنشأ قبل الفاتورة لتأكيد الطلب وحجز المخزون"""
    
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('confirmed', _('مؤكد')),
        ('in_production', _('قيد التصنيع')),
        ('ready', _('جاهز للتسليم')),
        ('partially_delivered', _('تسليم جزئي')),
        ('delivered', _('تم التسليم')),
        ('invoiced', _('تم إصدار الفاتورة')),
        ('cancelled', _('ملغى')),
    ]
    
    number = models.CharField(_('رقم الأمر'), max_length=50, unique=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='sales_orders',
        verbose_name=_('العميل')
    )
    
    date = models.DateField(_('تاريخ الأمر'), default=timezone.localdate)
    delivery_date = models.DateField(_('تاريخ التسليم المتوقع'), null=True, blank=True)
    
    status = models.CharField(_('الحالة'), max_length=25, choices=STATUS_CHOICES, default='draft')
    
    # Pricing
    discount = models.DecimalField(_('الخصم'), max_digits=12, decimal_places=2, default=Decimal('0'))
    tax_rate = models.DecimalField(_('نسبة الضريبة %'), max_digits=5, decimal_places=2, default=Decimal('14.00'))
    
    # Delivery info
    delivery_address = models.TextField(_('عنوان التسليم'), blank=True)
    delivery_notes = models.TextField(_('ملاحظات التسليم'), blank=True)
    
    # Payment
    payment_terms = models.CharField(_('شروط الدفع'), max_length=200, blank=True)
    advance_payment = models.DecimalField(
        _('الدفعة المقدمة'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    
    # Links
    invoice = models.ForeignKey(
        'Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_order',
        verbose_name=_('الفاتورة')
    )
    
    production_order = models.ForeignKey(
        'production.ProductionOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_orders',
        verbose_name=_('أمر الإنتاج')
    )
    
    # Notes
    notes = models.TextField(_('ملاحظات'), blank=True)
    internal_notes = models.TextField(_('ملاحظات داخلية'), blank=True)
    
    # Users
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_sales_orders',
        verbose_name=_('أنشئ بواسطة')
    )
    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_sales_orders',
        verbose_name=_('أكده')
    )
    confirmed_at = models.DateTimeField(_('تاريخ التأكيد'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('أمر بيع')
        verbose_name_plural = _('أوامر البيع')
        ordering = ['-date', '-id']
        indexes = [
            models.Index(fields=['-date']),
            models.Index(fields=['status']),
            models.Index(fields=['customer']),
        ]
        permissions = [
            ('can_confirm_sales_order', _('يمكنه تأكيد أمر البيع')),
            ('can_convert_to_invoice', _('يمكنه تحويل أمر البيع لفاتورة')),
        ]
    
    def __str__(self):
        return f"{self.number} - {self.customer.name}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            from core.sequence_utils import next_sequence
            from django.db import IntegrityError
            from django.utils import timezone
            import time
            
            now = timezone.now()
            prefix = f"SO-{now.strftime('%Y%m')}"
            
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    seq = next_sequence(f'SALES_ORDER_{now.strftime("%Y%m")}')
                    self.number = f"{prefix}-{str(seq).zfill(6)}"
                    super().save(*args, **kwargs)
                    return
                except IntegrityError as e:
                    if 'UNIQUE constraint failed' in str(e) or 'unique' in str(e).lower():
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    raise
            
            self.number = f"{prefix}-{int(now.timestamp())}"
        
        super().save(*args, **kwargs)
    
    @property
    def subtotal(self):
        """المجموع الفرعي قبل الخصم والضريبة"""
        return sum(item.total for item in self.items.all())
    
    @property
    def total_after_discount(self):
        """المجموع بعد الخصم"""
        return self.subtotal - self.discount
    
    @property
    def tax_amount(self):
        """قيمة الضريبة"""
        return (self.total_after_discount * self.tax_rate) / Decimal('100')
    
    @property
    def total(self):
        """الإجمالي النهائي"""
        return self.total_after_discount + self.tax_amount
    
    @property
    def remaining_amount(self):
        """المبلغ المتبقي"""
        return self.total - self.advance_payment
    
    @property
    def is_editable(self):
        """هل يمكن تعديل الأمر؟"""
        return self.status in ['draft', 'confirmed']
    
    def confirm(self, user=None):
        """تأكيد الأمر"""
        if self.status == 'draft':
            self.status = 'confirmed'
            self.confirmed_by = user
            self.confirmed_at = timezone.now()
            self.save()
            
            # Reserve stock
            for item in self.items.all():
                item.reserve_stock()
            
            return True
        return False
    
    def convert_to_invoice(self, user=None):
        """تحويل الأمر لفاتورة"""
        if self.status not in ['confirmed', 'ready', 'delivered'] or self.invoice:
            return None
        
        with transaction.atomic():
            # Create invoice
            invoice = Invoice.objects.create(
                customer=self.customer,
                date=timezone.now().date(),
            )
            
            # Add line items
            for item in self.items.all():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=item.product,
                    location=item.location,
                    quantity=item.quantity,
                    price=item.price
                )
            
            # Link and update status
            self.invoice = invoice
            self.status = 'invoiced'
            self.save()
            
            return invoice


class SalesOrderLine(models.Model):
    """بند أمر بيع"""
    
    order = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('أمر البيع')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name=_('المنتج')
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        verbose_name=_('الموقع/المستودع')
    )
    
    quantity = models.PositiveIntegerField(_('الكمية'))
    price = models.DecimalField(_('السعر'), max_digits=12, decimal_places=2)
    
    reserved_quantity = models.PositiveIntegerField(_('الكمية المحجوزة'), default=0)
    delivered_quantity = models.PositiveIntegerField(_('الكمية المُسلمة'), default=0)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    class Meta:
        verbose_name = _('بند أمر بيع')
        verbose_name_plural = _('بنود أوامر البيع')
        ordering = ['id']
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity}"
    
    @property
    def total(self):
        """إجمالي البند"""
        return self.quantity * self.price
    
    @property
    def remaining_to_deliver(self):
        """الكمية المتبقية للتسليم"""
        return self.quantity - self.delivered_quantity
    
    def reserve_stock(self):
        """حجز المخزون"""
        # This is a placeholder - implement actual stock reservation logic
        self.reserved_quantity = self.quantity
        self.save()
    
    def release_stock(self):
        """إلغاء حجز المخزون"""
        self.reserved_quantity = 0
        self.save()
