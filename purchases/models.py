from django.db import models, transaction
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from inventory.models import Product, Location, Stock
from partners.models import Partner
from core.sequence_utils import next_sequence, format_code


class PurchaseBill(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    STATUS_CHOICES = [
        ("draft", _("مسودة")),
        ("posted", _("مرحلة")),
    ]
    number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name='bills')
    date = models.DateField(default=timezone.localdate)
    # ربط فاتورة المشتريات بالمعرض/الفرع
    showroom = models.ForeignKey(
        'showrooms.Showroom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_bills',
        verbose_name=_('المعرض/الفرع')
    )
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name=_('الحالة'))
    posted_at = models.DateTimeField(null=True, blank=True, verbose_name=_('تاريخ الترحيل'))
    # حقول الدفع الجديدة (إن تم دفع جزء فوري عند إنشاء الفاتورة)
    payment_method = models.ForeignKey(
        'payments.PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('طريقة الدفع')
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('مرجع الدفع (شيك/تحويل/Instapay/محفظة)')
    )
    supplier_invoice_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('رقم فاتورة المورد (خارجي)')
    )
    # حذف ناعم بموافقة المدير المالي/المدير
    is_deleted = models.BooleanField(default=False, verbose_name=_('محذوف'))
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_('تاريخ الحذف'))
    deleted_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='deleted_purchase_bills', verbose_name=_('محذوف بواسطة'))
    delete_reason = models.TextField(blank=True, verbose_name=_('سبب الحذف'))

    def __str__(self):
        return self.number

    @property
    def total(self):
        return sum(item.total for item in self.items.all()) - self.discount

    @property
    def remaining(self):
        return (self.total or 0) - (self.paid or 0)

    def post(self, user=None):
        """إنشاء قيد محاسبي للفاتورة إن لم تكن مرحلة."""
        if self.status == 'posted':
            return None
        from accounting.services import post_purchase_bill_journal
        je = post_purchase_bill_journal(self, user=user)
        if je and je.is_posted:
            from django.utils import timezone as _tz
            self.status = 'posted'
            self.posted_at = _tz.now()
            self.save(update_fields=['status', 'posted_at'])
        return je

    def save(self, *args, **kwargs):
        if not self.number:
            from core.sequence_utils import next_sequence
            from django.db import IntegrityError
            from django.utils import timezone
            import time
            
            now = timezone.now()
            prefix = f"PB-{now.strftime('%Y%m')}"
            
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    seq = next_sequence(f'PURCHASE_BILL_{now.strftime("%Y%m")}')
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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['supplier', 'supplier_invoice_number'],
                name='uniq_supplier_ext_invoice',
                condition=~models.Q(supplier_invoice_number=''),
            ),
        ]
        indexes = [
            models.Index(fields=['date'], name='purchasebill_date_idx'),
            models.Index(fields=['supplier', 'date'], name='purchasebill_supplier_date_idx'),
            models.Index(fields=['status'], name='purchasebill_status_idx'),
            models.Index(fields=['is_deleted', 'date'], name='purchasebill_deleted_date_idx'),
        ]


class PurchaseItem(models.Model):
    """بند فاتورة شراء - يمثل منتج واحد في فاتورة الشراء"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    bill = models.ForeignKey(PurchaseBill, on_delete=models.CASCADE, related_name='items', verbose_name=_('فاتورة الشراء'))
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name=_('المنتج'))
    location = models.ForeignKey(Location, on_delete=models.PROTECT, verbose_name=_('الموقع/المخزن'))
    quantity = models.PositiveIntegerField(verbose_name=_('الكمية'))
    cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('التكلفة'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))

    # حقول إضافية للتتبع
    created_at = models.DateTimeField(auto_now_add=True, null=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, null=True, verbose_name=_('تاريخ التحديث'))

    class Meta:
        verbose_name = _('بند فاتورة شراء')
        verbose_name_plural = _('بنود فواتير الشراء')
        ordering = ['id']
        indexes = [
            models.Index(fields=['bill', 'product']),
            models.Index(fields=['product', 'location']),
        ]

    def __str__(self):
        return f"{self.bill.number} - {self.product.name}"

    @property
    def total(self):
        """إجمالي البند"""
        return self.quantity * self.cost

    def save(self, *args, **kwargs):
        # منع الاستلام الزائد مقابل أمر الشراء المرتبط بالفاتورة
        # (يعمل فقط عند وجود فاتورة مرتبطة بأمر شراء)
        if self.bill_id and not self.pk:  # فحص فقط عند الإنشاء
            try:
                po = getattr(self.bill, 'source_order', None)
                if po:
                    from django.db.models import Sum
                    ordered_total = PurchaseOrderItem.objects.filter(
                        order=po,
                        product=self.product,
                        location=self.location
                    ).aggregate(total=Sum('quantity'))['total'] or 0

                    if ordered_total:
                        existing_received = PurchaseItem.objects.filter(
                            bill__source_order=po,
                            product=self.product,
                            location=self.location
                        ).aggregate(total=Sum('quantity'))['total'] or 0

                        if existing_received + self.quantity > ordered_total:
                            raise ValueError(
                                f"الكمية المستلمة ({existing_received + self.quantity}) "
                                f"تتجاوز المطلوبة ({ordered_total}) للمنتج {self.product}"
                            )
            except ValueError:
                raise
            except Exception as e:
                # تسجيل الخطأ ولكن لا نمنع الحفظ
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"خطأ في التحقق من كمية الاستلام: {e}")

        super().save(*args, **kwargs)


@receiver(post_save, sender=PurchaseItem)
def increase_stock_on_purchase(sender, instance: 'PurchaseItem', created, **kwargs):
    if created:
        stock, _ = Stock.objects.get_or_create(product=instance.product, location=instance.location)
        stock.quantity += instance.quantity
        stock.save()
        # تحديث حالة أمر الشراء المرتبط (إن وُجد) بعد استلام البند فعلياً في الفاتورة
        try:
            if hasattr(instance.bill, 'source_order') and instance.bill.source_order:
                instance.bill.source_order.refresh_fulfillment_status()
        except Exception:
            pass

"""
أوامر الشراء (Purchase Orders)
لا تؤثر على المخزون مباشرة حتى يتم الاستلام/الفوترة.
"""


class PurchaseOrder(models.Model):
    """أمر شراء - يُنشأ قبل الاستلام ولا يؤثر على المخزون حتى يتم تحويله لفاتورة"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    STATUS_CHOICES = [
        ("draft", _("مسودة")),
        ("confirmed", _("مؤكد")),
        ("partial", _("استلام جزئي")),
        ("completed", _("مكتمل")),
        ("cancelled", _("ملغى")),
    ]

    number = models.CharField(_("رقم الأمر"), max_length=50, unique=True)
    supplier = models.ForeignKey(
        Partner,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        verbose_name=_('المورد')
    )
    date = models.DateField(_("التاريخ"), default=timezone.localdate)
    expected_date = models.DateField(_("تاريخ التوريد المتوقع"), null=True, blank=True)
    status = models.CharField(_("الحالة"), max_length=20, choices=STATUS_CHOICES, default="draft")
    discount = models.DecimalField(_("الخصم"), max_digits=12, decimal_places=2, default=Decimal('0'))
    notes = models.TextField(_("ملاحظات"), blank=True)

    # ربط بفاتورة الشراء
    bill = models.OneToOneField(
        'PurchaseBill',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='source_order',
        verbose_name=_('فاتورة الشراء المرتبطة')
    )

    # من أنشأ الطلب (عموماً)
    created_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_purchase_orders',
        verbose_name=_('أنشئ بواسطة')
    )

    # موظف المخزن الذي حوّل طلب خامات إلى أمر شراء (إن وُجد)
    requested_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='requested_purchase_orders',
        verbose_name=_('طُلب بواسطة (المخزن)')
    )

    # حقول التتبع
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name=_('تاريخ التحديث'))

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = _("أمر شراء")
        verbose_name_plural = _("أوامر الشراء")
        indexes = [
            models.Index(fields=['status', 'date']),
            models.Index(fields=['supplier', 'date']),
            models.Index(fields=['expected_date']),
        ]

    def __str__(self) -> str:
        return self.number

    @property
    def total(self):
        return sum(item.total for item in self.items.all()) - self.discount

    @property
    def is_editable(self):
        return self.status == "draft"

    def refresh_fulfillment_status(self, user=None):
        """تحديث حالة أمر الشراء بكفاءة عبر تجميعات SQL بدلاً من تحميل كل البُنود في الذاكرة.

        المنطق:
        - بدون فاتورة: لا تغيير.
        - (sum received == 0) => لا تغيير (تبقى confirmed/ draft)
        - إن كان مجموع المستلم == مجموع المطلوب لكل (product, location) => completed
        - إن كان بعض المستلم >0 وأقل من المطلوب في أي بند => partial
        """
        if not self.bill:
            return
        from django.db.models import Sum, F
        # إجمالي المطلوب لكل مفتاح
        required = (
            PurchaseOrderItem.objects.filter(order=self)
            .values('product_id', 'location_id')
            .annotate(req=Sum('quantity'))
        )
        if not required:
            return
        required_map = {(r['product_id'], r['location_id']): r['req'] for r in required}
        received = (
            PurchaseItem.objects.filter(bill=self.bill, product_id__in=[k[0] for k in required_map.keys()])
            .values('product_id', 'location_id')
            .annotate(rec=Sum('quantity'))
        )
        if not received:
            # لم يُستلم شيء بعد
            return
        all_full = True
        any_received = False
        received_map = {(r['product_id'], r['location_id']): r['rec'] for r in received}
        for key, req_qty in required_map.items():
            rec_qty = received_map.get(key, 0) or 0
            if rec_qty > 0:
                any_received = True
            if rec_qty < req_qty:
                all_full = False
        if all_full:
            new_status = 'completed'
        elif any_received:
            new_status = 'partial'
        else:
            return
        if new_status != self.status:
            old = self.status
            self.status = new_status
            self.save(update_fields=['status'])
            try:
                from core.models import AuditLog
                AuditLog.objects.create(
                    user=user,
                    action=AuditLog.ACTION_UPDATE,
                    model_name='PurchaseOrder',
                    app_label='purchases',
                    object_id=str(self.pk),
                    object_repr=str(self),
                    changes={'status': f'{old} -> {new_status}'}
                )
                if new_status == 'completed':
                    AuditLog.objects.create(
                        user=user,
                        action=AuditLog.ACTION_CREATE,
                        model_name='Notification',
                        app_label='core',
                        object_id=str(self.pk),
                        object_repr=f'PO {self.number}',
                        changes={'message': 'اكتمل أمر الشراء'}
                    )
            except Exception:
                pass

    @property
    def fulfillment_progress(self):
        """Return (received, required, percent)"""
        if not self.bill:
            total_required = sum(oi.quantity for oi in self.items.all()) or 0
            return 0, total_required, 0 if total_required else 0
        order_items = list(self.items.all())
        bill_items = list(self.bill.items.all())
        required = sum(oi.quantity for oi in order_items) or 0
        received = 0
        if required:
            # map
            for bi in bill_items:
                received += bi.quantity
        pct = round((received / required) * 100, 2) if required else 0
        return received, required, pct

    def save(self, *args, **kwargs):
        if not self.number:
            from django.db import IntegrityError
            from django.utils import timezone
            import time
            
            now = timezone.now()
            prefix = f"PO-{now.strftime('%Y%m')}"
            
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    seq = next_sequence(f'PURCHASE_ORDER_{now.strftime("%Y%m")}')
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


class PurchaseOrderItem(models.Model):
    """بند أمر شراء - يمثل منتج واحد في أمر الشراء"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_('أمر الشراء')
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name=_('المنتج'))
    location = models.ForeignKey(Location, on_delete=models.PROTECT, verbose_name=_('الموقع/المخزن'))
    quantity = models.PositiveIntegerField(verbose_name=_('الكمية'))
    cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('التكلفة'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))

    # حقول إضافية للتتبع
    received_quantity = models.PositiveIntegerField(default=0, verbose_name=_('الكمية المستلمة'))
    created_at = models.DateTimeField(auto_now_add=True, null=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, null=True, verbose_name=_('تاريخ التحديث'))

    class Meta:
        verbose_name = _("بند أمر شراء")
        verbose_name_plural = _("بنود أوامر الشراء")
        ordering = ['id']
        indexes = [
            models.Index(fields=['order', 'product']),
            models.Index(fields=['product', 'location']),
        ]

    def __str__(self):
        return f"{self.order.number} - {self.product.name}"

    @property
    def total(self):
        """إجمالي البند"""
        return self.quantity * self.cost

    @property
    def remaining_quantity(self):
        """الكمية المتبقية للاستلام"""
        return max(0, self.quantity - self.received_quantity)


class PurchaseReturn(models.Model):
    """مرتجع شراء - إرجاع بضائع للمورد"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking

    STATUS_CHOICES = [
        ("draft", _("مسودة")),
        ("confirmed", _("مؤكد")),
        ("posted", _("مرحل")),
        ("cancelled", _("ملغى")),
    ]

    number = models.CharField(max_length=50, unique=True, verbose_name=_('رقم المرتجع'))
    bill = models.ForeignKey(
        PurchaseBill,
        on_delete=models.PROTECT,
        related_name='purchase_returns',
        verbose_name=_('فاتورة الشراء')
    )
    date = models.DateField(default=timezone.localdate, verbose_name=_('التاريخ'))
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name=_('الحالة')
    )
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    reason = models.TextField(blank=True, verbose_name=_('سبب الإرجاع'))

    # حقول التتبع
    created_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_purchase_returns',
        verbose_name=_('أنشئ بواسطة')
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, null=True, verbose_name=_('تاريخ التحديث'))

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = _("مرتجع شراء")
        verbose_name_plural = _("مرتجعات الشراء")
        indexes = [
            models.Index(fields=['status', 'date']),
            models.Index(fields=['bill', 'date']),
        ]

    def __str__(self):
        return self.number

    @property
    def total(self):
        """إجمالي المرتجع"""
        return sum(item.total for item in self.items.all())

    def save(self, *args, **kwargs):
        if not self.number:
            from django.db import IntegrityError
            from django.utils import timezone
            import time
            
            now = timezone.now()
            prefix = f"PR-{now.strftime('%Y%m')}"
            
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    seq = next_sequence(f'PURCHASE_RETURN_{now.strftime("%Y%m")}')
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


class PurchaseReturnItem(models.Model):
    """بند مرتجع شراء - يمثل منتج واحد في المرتجع"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    purchase_return = models.ForeignKey(
        PurchaseReturn,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('مرتجع الشراء')
    )
    bill_item = models.ForeignKey(
        PurchaseItem,
        on_delete=models.PROTECT,
        verbose_name=_('بند فاتورة الشراء')
    )
    quantity = models.PositiveIntegerField(verbose_name=_('الكمية'))
    reason = models.TextField(blank=True, verbose_name=_('سبب الإرجاع'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))

    # حقول التتبع
    created_at = models.DateTimeField(auto_now_add=True, null=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, null=True, verbose_name=_('تاريخ التحديث'))

    class Meta:
        verbose_name = _('بند مرتجع شراء')
        verbose_name_plural = _('بنود مرتجعات الشراء')
        ordering = ['id']
        indexes = [
            models.Index(fields=['purchase_return', 'bill_item']),
        ]

    def __str__(self):
        return f"{self.purchase_return.number} - {self.bill_item.product.name}"

    @property
    def total(self):
        """إجمالي البند"""
        return self.quantity * self.bill_item.cost

    def apply_stock(self):
        """إخراج الكمية من المخزون في نفس الموقع"""
        stock, _ = Stock.objects.get_or_create(
            product=self.bill_item.product,
            location=self.bill_item.location
        )
        if stock.quantity < self.quantity:
            raise ValueError(_("الكمية في المخزون لا تكفي للمرتجع"))
        stock.quantity -= self.quantity
        stock.save()


class PurchaseBillOrderLink(models.Model):
    """ربط فاتورة شراء بأمر/أوامر شراء متعددة.

    يسمح بربط فاتورة واحدة بأكثر من PO والعكس،
    بدون تغيير حقل "bill" القديم في نموذج PurchaseOrder للحفاظ على التوافق.
    """

    bill = models.ForeignKey(PurchaseBill, on_delete=models.CASCADE, related_name='order_links')
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='bill_links')

    class Meta:
        verbose_name = _('ربط فاتورة بأمر شراء')
        verbose_name_plural = _('روابط فواتير أوامر الشراء')
        unique_together = ('bill', 'order')


class SupplierPayment(models.Model):
    """دفعة مورد مرتبطة بفاتورة اختيارياً (أو دفعة عامة على حساب المورد)."""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    supplier = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name='payments', verbose_name=_('المورد'))
    bill = models.ForeignKey(PurchaseBill, null=True, blank=True, on_delete=models.SET_NULL, related_name='supplier_payments', verbose_name=_('فاتورة شراء'))
    receipt_number = models.CharField(_('رقم إيصال المورد'), max_length=30, unique=True, blank=True)
    date = models.DateTimeField(_('التاريخ'), default=timezone.now)
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    payment_method = models.ForeignKey('payments.PaymentMethod', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('طريقة الدفع'))
    reference = models.CharField(_('مرجع (شيك/تحويل)'), max_length=100, blank=True)
    description = models.TextField(_('بيان'), blank=True)
    journal_entry = models.ForeignKey('accounting.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, related_name='supplier_payments', verbose_name=_('القيد المحاسبي'))
    locked = models.BooleanField(_('مقفول'), default=False, help_text=_('يمنع التعديل بعد الترحيل أو الطباعة'))
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_supplier_payments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('دفعة مورد')
        verbose_name_plural = _('دفعات الموردين')
        ordering = ['-date', '-id']
        indexes = [
            models.Index(fields=['date'], name='supppay_date_idx'),
        ]

    def __str__(self):
        return f"{self.receipt_number} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            ym = timezone.now().strftime('%Y%m')
            base_key = f'SUPPAY_{ym}'
            seq = next_sequence(base_key)
            self.receipt_number = f'SUPPAY-{ym}-{seq:04d}'
        super().save(*args, **kwargs)

    def post(self, user=None):
        if self.locked:
            return self.journal_entry
        from accounting.services import post_supplier_payment_journal
        je = post_supplier_payment_journal(self, user=user)
        if je and je.is_posted:
            self.locked = True
            self.journal_entry = je
            self.save(update_fields=['locked', 'journal_entry'])
            # تحديث حالة الفاتورة والمبلغ المدفوع
            if self.bill:
                with transaction.atomic():
                    self.bill.paid += self.amount
                    self.bill.save(update_fields=['paid'])
        return je


# ============================================================================
# Purchase Requisitions (PR) - طلبات الشراء الداخلية
# ============================================================================

class PurchaseRequisition(models.Model):
    """طلب شراء داخلي من قسم/موظف قبل إنشاء أمر الشراء"""
    
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('submitted', _('مُقدّم')),
        ('under_review', _('قيد المراجعة')),
        ('approved', _('معتمد')),
        ('rejected', _('مرفوض')),
        ('converted', _('مُحوّل لأمر شراء')),
        ('cancelled', _('ملغى')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('منخفضة')),
        ('normal', _('عادية')),
        ('high', _('عالية')),
        ('urgent', _('عاجلة')),
    ]
    
    number = models.CharField(_('رقم الطلب'), max_length=50, unique=True)
    department = models.CharField(_('القسم'), max_length=200, blank=True)
    requested_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='purchase_requisitions',
        verbose_name=_('طلب بواسطة')
    )
    
    date = models.DateField(_('تاريخ الطلب'), default=timezone.localdate)
    required_date = models.DateField(_('تاريخ الحاجة'), null=True, blank=True)
    
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(_('الأولوية'), max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    justification = models.TextField(_('المبرر'), blank=True, help_text=_('سبب الطلب'))
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    # Approval workflow
    reviewed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_purchase_requisitions',
        verbose_name=_('راجعه')
    )
    reviewed_at = models.DateTimeField(_('تاريخ المراجعة'), null=True, blank=True)
    review_notes = models.TextField(_('ملاحظات المراجع'), blank=True)
    
    approved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_purchase_requisitions',
        verbose_name=_('اعتمده')
    )
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)
    approval_notes = models.TextField(_('ملاحظات الاعتماد'), blank=True)
    
    rejected_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_purchase_requisitions',
        verbose_name=_('رفضه')
    )
    rejected_at = models.DateTimeField(_('تاريخ الرفض'), null=True, blank=True)
    rejection_reason = models.TextField(_('سبب الرفض'), blank=True)
    
    # Conversion to PO
    purchase_order = models.ForeignKey(
        'PurchaseOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_requisition',
        verbose_name=_('أمر الشراء')
    )
    converted_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='converted_purchase_requisitions',
        verbose_name=_('حُوّل بواسطة')
    )
    converted_at = models.DateTimeField(_('تاريخ التحويل'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        ordering = ['-date', '-id']
        verbose_name = _('طلب شراء')
        verbose_name_plural = _('طلبات الشراء')
        permissions = [
            ('can_review_pr', _('يمكنه مراجعة طلبات الشراء')),
            ('can_approve_pr', _('يمكنه اعتماد طلبات الشراء')),
            ('can_convert_pr_to_po', _('يمكنه تحويل طلب الشراء لأمر شراء')),
        ]
        indexes = [
            models.Index(fields=['-date']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['requested_by']),
        ]
    
    def __str__(self):
        return f"{self.number} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            seq = next_sequence('PURCHASE_REQUISITION')
            self.number = format_code('PR', seq)
        super().save(*args, **kwargs)
    
    @property
    def total_estimated_amount(self):
        """إجمالي القيمة التقديرية"""
        return sum(item.estimated_total for item in self.items.all())
    
    @property
    def is_editable(self):
        """هل يمكن تعديل الطلب؟"""
        return self.status in ['draft', 'submitted']
    
    @property
    def can_be_approved(self):
        """هل يمكن اعتماد الطلب؟"""
        return self.status in ['submitted', 'under_review']
    
    def submit(self, user=None):
        """تقديم الطلب للمراجعة"""
        if self.status == 'draft':
            self.status = 'submitted'
            self.save()
            return True
        return False
    
    def review(self, user, notes=''):
        """مراجعة الطلب"""
        if self.status in ['submitted', 'under_review']:
            self.status = 'under_review'
            self.reviewed_by = user
            self.reviewed_at = timezone.now()
            self.review_notes = notes
            self.save()
            return True
        return False
    
    def approve(self, user, notes=''):
        """اعتماد الطلب"""
        if self.can_be_approved:
            self.status = 'approved'
            self.approved_by = user
            self.approved_at = timezone.now()
            self.approval_notes = notes
            self.save()
            return True
        return False
    
    def reject(self, user, reason=''):
        """رفض الطلب"""
        if self.can_be_approved:
            self.status = 'rejected'
            self.rejected_by = user
            self.rejected_at = timezone.now()
            self.rejection_reason = reason
            self.save()
            return True
        return False
    
    def convert_to_po(self, user, supplier):
        """تحويل الطلب لأمر شراء"""
        if self.status != 'approved' or self.purchase_order:
            return None
        
        with transaction.atomic():
            # إنشاء أمر شراء
            po = PurchaseOrder.objects.create(
                supplier=supplier,
                date=timezone.now().date(),
                expected_date=self.required_date,
                notes=f"تم التحويل من طلب شراء {self.number}\n{self.justification}",
                created_by=user,
                requested_by=self.requested_by
            )
            
            # نسخ البنود
            for item in self.items.all():
                PurchaseOrderItem.objects.create(
                    order=po,
                    product=item.product,
                    location=item.location,
                    quantity=item.quantity,
                    cost=item.estimated_price or Decimal('0')
                )
            
            # تحديث حالة الطلب
            self.status = 'converted'
            self.purchase_order = po
            self.converted_by = user
            self.converted_at = timezone.now()
            self.save()
            
            return po


class PurchaseRequisitionItem(models.Model):
    """بند طلب شراء"""
    
    requisition = models.ForeignKey(
        PurchaseRequisition,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('طلب الشراء')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name=_('المنتج')
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        verbose_name=_('الموقع'),
        help_text=_('المستودع المطلوب استلام المادة فيه')
    )
    
    quantity = models.PositiveIntegerField(_('الكمية'))
    estimated_price = models.DecimalField(
        _('السعر التقديري'),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    current_stock = models.DecimalField(
        _('الرصيد الحالي'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        help_text=_('الرصيد وقت إنشاء الطلب')
    )
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    class Meta:
        ordering = ['id']
        verbose_name = _('بند طلب شراء')
        verbose_name_plural = _('بنود طلبات الشراء')
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity}"
    
    @property
    def estimated_total(self):
        """إجمالي تقديري"""
        if self.estimated_price:
            return self.quantity * self.estimated_price
        return Decimal('0')