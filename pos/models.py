from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from decimal import Decimal
from accounting.models import JournalEntry, JournalEntryItem, Account, AccountingSettings

User = get_user_model()


class POSSession(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='pos_sessions', verbose_name=_('المستخدم'))
    location = models.ForeignKey('inventory.Location', on_delete=models.PROTECT, related_name='pos_sessions', verbose_name=_('الموقع / المعرض'), null=True, blank=True)
    opened_at = models.DateTimeField(_('وقت الفتح'), default=timezone.now)
    closed_at = models.DateTimeField(_('وقت الإغلاق'), null=True, blank=True)
    opening_balance = models.DecimalField(_('رصيد افتتاحي'), max_digits=12, decimal_places=2, default=0)
    closing_balance = models.DecimalField(_('رصيد إغلاق'), max_digits=12, decimal_places=2, default=0)
    is_open = models.BooleanField(_('مفتوحة'), default=True)

    class Meta:
        verbose_name = _('جلسة نقطة بيع')
        verbose_name_plural = _('جلسات نقاط البيع')
        ordering = ['-opened_at', '-id']

    def __str__(self):
        return f"POS Session {self.id} - {self.user} - {'OPEN' if self.is_open else 'CLOSED'}"

    @property
    def total_sales(self):
        agg = self.orders.filter(status='paid').aggregate(total=models.Sum('total'))
        return agg['total'] or Decimal('0')

    def close(self, closing_balance: Decimal):
        if not self.is_open:
            return
        self.closing_balance = closing_balance
        self.closed_at = timezone.now()
        self.is_open = False
        self.save(update_fields=['closing_balance', 'closed_at', 'is_open'])


class POSOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('paid', _('مدفوعة')),
        ('cancelled', _('ملغاة')),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking

    number = models.CharField(_('رقم الطلب'), max_length=30, unique=True, blank=True)
    session = models.ForeignKey(POSSession, on_delete=models.PROTECT, related_name='orders', verbose_name=_('الجلسة'))
    customer = models.ForeignKey('partners.Customer', on_delete=models.PROTECT, null=True, blank=True, related_name='pos_orders', verbose_name=_('العميل'))
    location = models.ForeignKey('inventory.Location', on_delete=models.PROTECT, verbose_name=_('الموقع / المعرض'))
    showroom = models.ForeignKey('showrooms.Showroom', on_delete=models.SET_NULL, null=True, blank=True, related_name='pos_orders', verbose_name=_('المعرض'))
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    paid_amount = models.DecimalField(_('المبلغ المدفوع'), max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(_('الإجمالي'), max_digits=12, decimal_places=2, default=0, help_text=_('مخزن لتسريع الاستعلامات'))
    discount_amount = models.DecimalField(_('قيمة الخصم'), max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_('قيمة الضريبة'), max_digits=12, decimal_places=2, default=0)
    vat_rate = models.DecimalField(_('نسبة VAT %'), max_digits=5, decimal_places=2, default=0)
    cogs_amount = models.DecimalField(_('تكلفة البضاعة المباعة'), max_digits=12, decimal_places=2, default=0)
    is_tax_invoice = models.BooleanField(_('فاتورة ضريبية؟'), default=False, help_text=_('هل يتم إظهار الرقم الضريبي والضريبة في الإيصال'))
    withholding_tax_rate = models.DecimalField(_('نسبة ضريبة المنبع %'), max_digits=5, decimal_places=2, default=0)
    withholding_tax_amount = models.DecimalField(_('قيمة ضريبة المنبع'), max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(_('مصاريف الشحن'), max_digits=12, decimal_places=2, default=0)
    is_return = models.BooleanField(_('إرجاع؟'), default=False)
    original_order = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='return_orders', verbose_name=_('الطلب الأصلي'))

    class Meta:
        verbose_name = _('طلب POS')
        verbose_name_plural = _('طلبات POS')
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['created_at'], name='posorder_created_idx'),
            models.Index(fields=['status'], name='posorder_status_idx'),
        ]
        permissions = [
            ("view", "عرض أوامر نقطة البيع"),
            ("add", "إضافة أوامر نقطة البيع"),
            ("change", "تعديل أوامر نقطة البيع"),
        ]

    def __str__(self):
        return self.number or f"POSOrder {self.id}"

    def save(self, *args, **kwargs):
        if not self.number:
            ym = timezone.now().strftime('%Y%m')
            last = POSOrder.objects.filter(number__startswith=f'POS-{ym}-').order_by('id').last()
            seq = 1
            if last and last.number:
                try:
                    seq = int(last.number.split('-')[-1]) + 1
                except Exception:
                    pass
            self.number = f'POS-{ym}-{seq:04d}'
        if not self.showroom and self.location_id and hasattr(self.location, 'showroom'):
            try:
                self.showroom = self.location.showroom
            except Exception:
                pass
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        """المجموع الفرعي قبل الخصم والضريبة"""
        agg = self.lines.aggregate(total=models.Sum(models.F('quantity') * models.F('price')))
        return agg['total'] or Decimal('0')

    def recalc_total(self):
        agg = self.lines.aggregate(total=models.Sum(models.F('quantity') * models.F('price')))
        subtotal = agg['total'] or Decimal('0')
        total_val = subtotal - (self.discount_amount or Decimal('0'))
        
        # حساب الضريبة فقط إذا كانت فاتورة ضريبية
        if self.is_tax_invoice and self.vat_rate:
            self.tax_amount = (total_val * (self.vat_rate / Decimal('100'))).quantize(Decimal('0.01'))
        else:
            self.tax_amount = Decimal('0')
        
        # حساب ضريبة المنبع
        if self.withholding_tax_rate:
            self.withholding_tax_amount = (total_val * (self.withholding_tax_rate / Decimal('100'))).quantize(Decimal('0.01'))
        else:
            self.withholding_tax_amount = Decimal('0')
        
        # الإجمالي = المجموع + الضريبة - ضريبة المنبع + مصاريف الشحن
        self.total = total_val + (self.tax_amount or Decimal('0')) - (self.withholding_tax_amount or Decimal('0')) + (self.shipping_cost or Decimal('0'))
        self.save(update_fields=['total', 'tax_amount', 'withholding_tax_amount', 'shipping_cost'])
        return self.total

    @property
    def remaining(self):
        return (self.total or Decimal('0')) - (self.paid_amount or Decimal('0'))

    def finalize_payment(self, amount: Decimal, payment_method=None, discount: Decimal=Decimal('0'), vat_rate: Decimal=Decimal('0')):
        """معالجة دفعة (يمكن استدعاؤها عدة مرات حتى اكتمال السداد)."""
        if amount <= 0:
            raise ValueError(_('المبلغ غير صالح'))
        if self.status == 'paid':
            return  # تجاهل دفعات إضافية بعد اكتمال الطلب
        if discount:
            self.discount_amount = discount
        if vat_rate:
            self.vat_rate = vat_rate
        with transaction.atomic():
            self.recalc_total()
            # تحقق المرتجع قبل أي خصومات نهائية
            if self.is_return:
                self._validate_return_constraints()
            # إضافة الدفعة
            self.add_payment(amount, payment_method)
            if self.paid_amount >= self.total:
                self.status = 'paid'
                self.save(update_fields=['status'])
                self._apply_stock_and_generate_invoice()

    def add_payment(self, amount: Decimal, payment_method=None):
        """إضافة دفعة جزئية دون إغلاق الطلب إن لم يكتمل."""
        if amount <= 0:
            raise ValueError(_('المبلغ غير صالح'))
        POSPayment.objects.create(order=self, amount=amount, method=payment_method)
        self.paid_amount = (self.paid_amount or Decimal('0')) + amount
        self.save(update_fields=['paid_amount'])
        return self.paid_amount

    def _validate_return_constraints(self):
        """منع المرتجع غير الصحيح: طلب أصل مفقود أو كميات زائدة."""
        if not self.is_return:
            return True
        if not self.original_order_id:
            raise ValueError(_('يجب تحديد الطلب الأصلي للمرتجع'))
        original = self.original_order
        if not original or original.status != 'paid':
            raise ValueError(_('لا يمكن إرجاع طلب غير مدفوع أو غير موجود'))
        # مقارنة الكميات لكل منتج
        original_map = {}
        for l in original.lines.all():
            original_map[l.product_id] = original_map.get(l.product_id, 0) + l.quantity
        return_map = {}
        for l in self.lines.all():
            return_map[l.product_id] = return_map.get(l.product_id, 0) + l.quantity
        # تحقق عدم تجاوز
        for pid, qty in return_map.items():
            if qty > original_map.get(pid, 0):
                from inventory.models import Product
                prod = Product.objects.filter(id=pid).first()
                raise ValueError(_('كمية مرتجعة أكبر من الأصل للمنتج %(p)s') % {'p': prod or pid})
        return True
    def _apply_stock_and_generate_invoice(self):
        from inventory.models import Stock
        from sales.models import Invoice, InvoiceItem
        # استخدم gettext الفوري بدل gettext_lazy لضمان اسم نصي عادي في قاعدة البيانات
        from django.utils.translation import gettext as _tr
        if not self.customer:
            from partners.models import Customer
            # نستخدم literal عربي مباشر لتفادي أي كائن ترجمة كسول في الحقل
            cash_name = 'عميل نقدي'
            cash_cust, created = Customer.objects.get_or_create(name=cash_name)
            self.customer = cash_cust
            self.save(update_fields=['customer'])
        if not hasattr(self, 'invoice'):
            inv = Invoice.objects.create(number=f"INV-{self.number}", customer=self.customer, discount=0)
            for line in self.lines.all():
                qty = line.quantity
                InvoiceItem.objects.create(invoice=inv, product=line.product, location=self.location, quantity=qty, price=line.price)
            if self.is_return:
                # إشارة InvoiceItem ستخصم المخزون 1، لذا نعوض بإضافة (2 × الكمية) للوصول إلى صافي +1.
                for line in self.lines.select_related('product'):
                    stock, _ = Stock.objects.get_or_create(product=line.product, location=self.location)
                    stock.quantity = models.F('quantity') + (line.quantity * 2)
                    stock.save(update_fields=['quantity'])
                cost_total = Decimal('0')
                self.cogs_amount = cost_total
                self.save(update_fields=['cogs_amount'])
                self._post_accounting_entry()
                self._broadcast_kpi()
                return
        cost_total = self._apply_fifo_and_compute_cogs()
        self.cogs_amount = cost_total
        self.save(update_fields=['cogs_amount'])
        self._post_accounting_entry()
        self._broadcast_kpi()

    def _pick_batches_fifo(self, product, required_qty):
        from inventory.models import Stock, StockBatch
        qs = StockBatch.objects.filter(product=product, location=self.location, quantity__gt=0).order_by('received_at','id')
        picked = []
        remain = int(required_qty)
        for b in qs:
            if remain <= 0:
                break
            take = min(b.quantity, remain)
            picked.append((b, take))
            remain -= take
        # إذا لا توجد دفعات كافية، ننشئ دفعة تلقائية بسعر تكلفة المنتج
        if remain > 0:
            auto_batch = StockBatch.objects.create(
                product=product,
                location=self.location,
                lot_number='AUTO-POS',
                unit_cost=product.cost or Decimal('0'),
                quantity=remain,
            )
            picked.append((auto_batch, remain))
            remain = 0
        return picked

    def _apply_fifo_and_compute_cogs(self):
        from inventory.models import Stock, StockBatch
        total_cost = Decimal('0')
        for line in self.lines.select_related('product'):
            # pick batches
            picked = self._pick_batches_fifo(line.product, line.quantity)
            line_cost = Decimal('0')
            for batch, take in picked:
                line_cost += Decimal(take) * (batch.unit_cost or batch.product.cost)
                batch.quantity -= take
                batch.save(update_fields=['quantity'])
            total_cost += line_cost
        return total_cost.quantize(Decimal('0.01'))

    def _reverse_fifo_and_restore_stock(self):
        # Simplified return: add batch with product.cost
        from inventory.models import Stock, StockBatch
        total_cost = Decimal('0')
        for line in self.lines.select_related('product'):
            stock, _ = Stock.objects.get_or_create(product=line.product, location=self.location)
            stock.quantity += line.quantity
            stock.save(update_fields=['quantity'])
            StockBatch.objects.create(product=line.product, location=self.location, lot_number='RET', unit_cost=line.product.cost, quantity=line.quantity)
            total_cost += Decimal(line.quantity) * line.product.cost
        return total_cost.quantize(Decimal('0.01'))

    def _post_accounting_entry(self):
        """إنشاء قيد محاسبي مبسط لمبيعات POS (نقدية) + احتساب COGS من تكلفة المنتج الحالية."""
        try:
            if self.status != 'paid':
                return
            settings_obj = AccountingSettings.get()
            cash_acc = settings_obj.cash_account
            revenue_acc = Account.objects.filter(account_type='revenue').first()
            inventory_acc = settings_obj.inventory_account
            cogs_acc = Account.objects.filter(name__icontains='COGS').first() or Account.objects.filter(account_type='expense').first()
            total_sales = self.total or Decimal('0')
            net_sales = (self.total - self.tax_amount) if self.tax_amount else self.total
            if self.is_return:
                sign = -1
            else:
                sign = 1
            if not (cash_acc and revenue_acc and inventory_acc and cogs_acc):
                return
            je = JournalEntry.objects.create(
                number='',
                date=timezone.now().date(),
                entry_type='sales',
                description=f'POS {"Return" if self.is_return else "Sale"} {self.number}',
                reference=self.number,
                showroom=self.showroom,
                created_by=self.session.user if hasattr(self.session, 'user') else None,
                is_posted=True,
            )
            items = [
                JournalEntryItem(journal_entry=je, account=cash_acc, type='debit' if sign==1 else 'credit', amount=abs(total_sales), description='POS Cash'),
                JournalEntryItem(journal_entry=je, account=revenue_acc, type='credit' if sign==1 else 'debit', amount=abs(net_sales - (self.discount_amount or 0)), description='POS Revenue'),
            ]
            if self.tax_amount:
                vat_out = settings_obj.vat_output_account
                if vat_out:
                    items.append(JournalEntryItem(journal_entry=je, account=vat_out, type='credit' if sign==1 else 'debit', amount=abs(self.tax_amount), description='VAT'))
            # COGS / Inventory (reverse for returns)
            if self.cogs_amount:
                items.append(JournalEntryItem(journal_entry=je, account=cogs_acc, type='debit' if sign==1 else 'credit', amount=abs(self.cogs_amount), description='COGS'))
                items.append(JournalEntryItem(journal_entry=je, account=inventory_acc, type='credit' if sign==1 else 'debit', amount=abs(self.cogs_amount), description='Inventory'))
            JournalEntryItem.objects.bulk_create(items)
        except Exception:
            pass

    def _broadcast_kpi(self):
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            if not self.showroom_id:
                return
            layer = get_channel_layer()
            if not layer:
                return
            from django.utils import timezone as _tz
            today = _tz.now().date()
            from .models import POSOrder as _PO
            agg = _PO.objects.filter(showroom_id=self.showroom_id, status='paid', created_at__date=today, is_return=False).aggregate(total=models.Sum('total'))
            sales_today = float(agg['total'] or 0)
            async_to_sync(layer.group_send)(f'showroom_{self.showroom_id}', {'type': 'kpi.message', 'data': {'sales_today': sales_today, 'order_id': self.id}})
        except Exception:
            pass


class POSOrderLine(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    order = models.ForeignKey(POSOrder, on_delete=models.CASCADE, related_name='lines', verbose_name=_('الطلب'))
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, verbose_name=_('المنتج'))
    quantity = models.PositiveIntegerField(_('الكمية'), default=1)
    price = models.DecimalField(_('السعر'), max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = _('بند طلب POS')
        verbose_name_plural = _('بنود طلب POS')
        constraints = [
            models.CheckConstraint(check=models.Q(quantity__gt=0), name='posline_qty_positive'),
        ]
        permissions = [
            ("view", "عرض بنود أوامر نقطة البيع"),
            ("add", "إضافة بنود أوامر نقطة البيع"),
            ("change", "تعديل بنود أوامر نقطة البيع"),
        ]

    def __str__(self):
        return f"{self.product} x {self.quantity}"

    @property
    def total(self):
        return self.quantity * self.price

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.order.recalc_total()


class POSPayment(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    order = models.ForeignKey(POSOrder, on_delete=models.CASCADE, related_name='payments', verbose_name=_('الطلب'))
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    method = models.ForeignKey('payments.PaymentMethod', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('طريقة الدفع'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('دفعة POS')
        verbose_name_plural = _('دفعات POS')
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f"{self.amount} - {self.order}"


class POSTable(models.Model):
    """نموذج الطاولات للمطاعم والكافيهات"""
    STATUS_CHOICES = [
        ('available', _('متاحة')),
        ('occupied', _('مشغولة')),
        ('reserved', _('محجوزة')),
        ('cleaning', _('قيد التنظيف')),
    ]
    
    SHAPE_CHOICES = [
        ('square', _('مربعة')),
        ('round', _('دائرية')),
        ('rectangle', _('مستطيلة')),
    ]
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(_('اسم/رقم الطاولة'), max_length=50)
    location = models.ForeignKey('inventory.Location', on_delete=models.CASCADE, related_name='tables', verbose_name=_('الموقع/المعرض'))
    capacity = models.PositiveIntegerField(_('عدد المقاعد'), default=4)
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='available')
    shape = models.CharField(_('الشكل'), max_length=20, choices=SHAPE_CHOICES, default='square')
    floor = models.CharField(_('الطابق/المنطقة'), max_length=50, blank=True, default='')
    position_x = models.PositiveIntegerField(_('الموضع الأفقي'), default=0, help_text=_('للعرض على الخريطة'))
    position_y = models.PositiveIntegerField(_('الموضع العمودي'), default=0, help_text=_('للعرض على الخريطة'))
    is_active = models.BooleanField(_('نشطة'), default=True)
    current_order = models.ForeignKey(POSOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='table_set', verbose_name=_('الطلب الحالي'))
    notes = models.TextField(_('ملاحظات'), blank=True, default='')
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('آخر تحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('طاولة')
        verbose_name_plural = _('الطاولات')
        ordering = ['floor', 'name']
        unique_together = ['location', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"
    
    def occupy(self, order):
        """شغل الطاولة بطلب"""
        self.status = 'occupied'
        self.current_order = order
        self.save(update_fields=['status', 'current_order', 'updated_at'])
    
    def release(self):
        """تحرير الطاولة"""
        self.status = 'available'
        self.current_order = None
        self.save(update_fields=['status', 'current_order', 'updated_at'])
    
    def set_cleaning(self):
        """تعيين الطاولة للتنظيف"""
        self.status = 'cleaning'
        self.current_order = None
        self.save(update_fields=['status', 'current_order', 'updated_at'])
    
    def reserve(self):
        """حجز الطاولة"""
        self.status = 'reserved'
        self.save(update_fields=['status', 'updated_at'])
    
    @property
    def order_total(self):
        """إجمالي الطلب الحالي"""
        if self.current_order:
            return self.current_order.total
        return 0
    
    @property
    def order_duration(self):
        """مدة الطلب الحالي"""
        if self.current_order:
            duration = timezone.now() - self.current_order.created_at
            minutes = int(duration.total_seconds() / 60)
            hours = minutes // 60
            mins = minutes % 60
            if hours > 0:
                return f"{hours}س {mins}د"
            return f"{mins}د"
        return None


# Import installment models
from .models_installment import InstallmentPlan, Installment
