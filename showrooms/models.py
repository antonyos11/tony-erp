from decimal import Decimal
from django.db import models, transaction
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import AuditLog


class Showroom(models.Model):
    """
    نموذج الفرع/المعرض/المصنع - يمثل أي موقع تشغيلي في النظام
    """
    
    class ShowroomType(models.TextChoices):
        SHOWROOM = 'showroom', _('معرض')
        FACTORY = 'factory', _('مصنع')
        WAREHOUSE = 'warehouse', _('مستودع')
        BRANCH = 'branch', _('فرع')
    
    class PropertyType(models.TextChoices):
        OWNED = 'owned', _('تمليك')
        RENTED = 'rented', _('إيجار')
        TEMPORARY = 'temporary', _('مؤقت')
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    code = models.CharField(_('الكود'), max_length=10, unique=True)
    name = models.CharField(_('الاسم (إنجليزي)'), max_length=120)
    name_ar = models.CharField(_('الاسم (عربي)'), max_length=120, blank=True, null=True)
    
    # نوع الفرع
    showroom_type = models.CharField(
        _('نوع الفرع'),
        max_length=20,
        choices=ShowroomType.choices,
        default=ShowroomType.SHOWROOM
    )
    
    # بيانات الملكية والعقد
    property_type = models.CharField(
        _('نوع الملكية'),
        max_length=20,
        choices=PropertyType.choices,
        default=PropertyType.RENTED,
        help_text=_('تمليك أو إيجار أو مؤقت')
    )
    property_value = models.DecimalField(
        _('قيمة المعرض'),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('سعر الشراء للتمليك أو قيمة التقييم')
    )
    monthly_rent = models.DecimalField(
        _('الإيجار الشهري'),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('قيمة الإيجار الشهري للمعارض المستأجرة')
    )
    contract_start_date = models.DateField(
        _('تاريخ بداية العقد'),
        null=True,
        blank=True
    )
    contract_end_date = models.DateField(
        _('تاريخ نهاية العقد'),
        null=True,
        blank=True,
        help_text=_('للإيجار أو المعارض المؤقتة')
    )
    contract_document = models.FileField(
        _('عقد الشراء/الإيجار'),
        upload_to='showrooms/contracts/%Y/%m/',
        null=True,
        blank=True,
        help_text=_('رفع نسخة من عقد الشراء أو الإيجار')
    )
    contract_notes = models.TextField(
        _('ملاحظات العقد'),
        blank=True,
        help_text=_('أي تفاصيل إضافية عن العقد أو الاتفاقية')
    )
    
    # حساب الأصول للمعارض المملوكة
    asset_account = models.ForeignKey(
        'accounting.Account',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='showroom_assets',
        verbose_name=_('حساب الأصول'),
        help_text=_('حساب الأصول الثابتة للمعرض المملوك')
    )
    
    # حساب مصروفات الإيجار
    rent_expense_account = models.ForeignKey(
        'accounting.Account',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='showroom_rent_expenses',
        verbose_name=_('حساب مصروفات الإيجار'),
        help_text=_('حساب مصروفات الإيجار للمعارض المستأجرة')
    )
    
    # related_name intentionally changed to 'showroom_link' to avoid potential naming clash if
    # a real field named 'showroom' is (or was) added on Location in experimental branches.
    # We keep backward compatibility for existing code that accessed location.showroom via
    # a dynamic compatibility @property added on Location model.
    location = models.OneToOneField('inventory.Location', on_delete=models.PROTECT, related_name='showroom_link', verbose_name=_('الموقع المخزني'))
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_showrooms', verbose_name=_('المدير'))
    opening_date = models.DateField(_('تاريخ الافتتاح'), null=True, blank=True)
    
    # بيانات العنوان
    country = models.CharField(_('البلد'), max_length=80, blank=True, default='مصر')
    governorate = models.CharField(_('المحافظة'), max_length=80, blank=True)
    city = models.CharField(_('المدينة'), max_length=80, blank=True)
    address = models.CharField(_('العنوان التفصيلي'), max_length=255, blank=True)
    
    contact_phone = models.CharField(_('هاتف التواصل'), max_length=40, blank=True)
    contact_person = models.CharField(_('اسم مسؤول التواصل'), max_length=120, blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    expense_approval_limit = models.DecimalField(_('حد اعتماد المصروفات قبل الموافقة'), max_digits=12, decimal_places=2, default=Decimal('0'))
    require_expense_approval = models.BooleanField(_('يتطلب موافقة للمبالغ الأعلى من الحد'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('فرع/معرض')
        verbose_name_plural = _('الفروع والمعارض')
        ordering = ['showroom_type', 'code']
        indexes = [models.Index(fields=['code']), models.Index(fields=['is_active']), models.Index(fields=['showroom_type'])]

    def __str__(self):
        type_label = self.get_showroom_type_display() if self.showroom_type != 'showroom' else ''
        name = self.name_ar or self.name
        if type_label:
            return f"{self.code} - {name} ({type_label})"
        return f"{self.code} - {name}"
    
    @property
    def is_factory(self):
        return self.showroom_type == self.ShowroomType.FACTORY
    
    @property
    def is_warehouse(self):
        return self.showroom_type == self.ShowroomType.WAREHOUSE
    
    @property
    def is_temporary(self):
        """التحقق من أن المعرض مؤقت"""
        return self.property_type == self.PropertyType.TEMPORARY
    
    @property
    def is_rented(self):
        """التحقق من أن المعرض مستأجر"""
        return self.property_type == self.PropertyType.RENTED
    
    @property
    def is_owned(self):
        """التحقق من أن المعرض مملوك"""
        return self.property_type == self.PropertyType.OWNED
    
    @property
    def contract_days_remaining(self):
        """عدد الأيام المتبقية على العقد"""
        if not self.contract_end_date:
            return None
        from django.utils import timezone
        today = timezone.now().date()
        if self.contract_end_date < today:
            return 0
        return (self.contract_end_date - today).days
    
    @property
    def is_contract_expiring_soon(self):
        """التحقق من قرب انتهاء العقد (30 يوم)"""
        days = self.contract_days_remaining
        return days is not None and 0 < days <= 30
    
    @property
    def type_icon(self):
        """أيقونة حسب النوع"""
        icons = {
            'showroom': 'bi-shop',
            'factory': 'bi-building-gear',
            'warehouse': 'bi-box-seam',
            'branch': 'bi-building',
        }
        return icons.get(self.showroom_type, 'bi-shop')


class ShowroomEmployee(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    ROLE_CHOICES = [
        ('cashier', _('أمين صندوق')),
        ('sales', _('مبيعات')),
        ('supervisor', _('مشرف')),
        ('manager', _('مدير')),
        ('storekeeper', _('أمين مخزن')),
        ('warehouse_worker', _('عامل مستودع')),
        ('hr', _('شؤون موظفين')),
        ('call_center', _('كول سنتر')),
        ('customer_service', _('خدمة عملاء')),
        ('porter', _('حامل/عامل تحميل')),
        ('pantry', _('بانتر/ضيافة')),
        ('worker', _('عامل متنوع')),
    ]
    showroom = models.ForeignKey(Showroom, on_delete=models.CASCADE, related_name='employees', verbose_name=_('المعرض'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='showroom_assignments', verbose_name=_('المستخدم'))
    role = models.CharField(_('الدور'), max_length=20, choices=ROLE_CHOICES)
    can_cross_access = models.BooleanField(_('صلاحية الوصول لجميع المعارض'), default=False)
    extra_perms = models.JSONField(_('صلاحيات إضافية (module.action)'), default=list, blank=True, help_text=_('مثال: ["pos.export","inventory.view"]'))
    active = models.BooleanField(_('نشط'), default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('موظف معرض')
        verbose_name_plural = _('موظفو المعارض')
        unique_together = ('showroom', 'user')
        indexes = [models.Index(fields=['showroom', 'user']), models.Index(fields=['user', 'active'])]
        constraints = [
            models.UniqueConstraint(fields=['showroom'], condition=Q(role='manager', active=True), name='uq_showroom_single_manager'),
        ]

    def __str__(self):
        return f"{self.user} @ {self.showroom} ({self.role})"

    @property
    def is_manager(self):
        return self.role in ('manager', 'supervisor')


class POSDevice(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    showroom = models.ForeignKey(Showroom, on_delete=models.CASCADE, related_name='devices', verbose_name=_('المعرض'))
    name = models.CharField(_('الاسم'), max_length=100)
    identifier = models.CharField(_('المعرف'), max_length=120, unique=True, help_text=_('Serial / MAC / UUID'))
    api_key = models.CharField(_('مفتاح API'), max_length=64, unique=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    last_seen = models.DateTimeField(_('آخر ظهور'), null=True, blank=True)
    registered_at = models.DateTimeField(_('تاريخ التسجيل'), auto_now_add=True)

    class Meta:
        verbose_name = _('جهاز نقطة بيع')
        verbose_name_plural = _('أجهزة نقاط البيع')
        indexes = [models.Index(fields=['showroom','is_active']), models.Index(fields=['identifier'])]

    def __str__(self):
        return f"{self.name} ({self.identifier})"


class DeviceAuthToken(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    device = models.ForeignKey(POSDevice, on_delete=models.CASCADE, related_name='tokens', verbose_name=_('الجهاز'))
    token = models.CharField(_('التوكن'), max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(_('ينتهي في'), null=True, blank=True)
    revoked = models.BooleanField(_('ملغي'), default=False)

    class Meta:
        verbose_name = _('توكن جهاز')
        verbose_name_plural = _('توكنات الأجهزة')

    def is_valid(self):
        from django.utils import timezone
        if self.revoked:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class AttendanceRecord(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    showroom = models.ForeignKey(Showroom, on_delete=models.CASCADE, related_name='attendance_records', verbose_name=_('المعرض'))
    employee = models.ForeignKey(ShowroomEmployee, on_delete=models.CASCADE, related_name='attendance_records', verbose_name=_('الموظف'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='showroom_attendance', verbose_name=_('المستخدم'))
    date = models.DateField(_('التاريخ'), default=models.functions.Now)
    in_time = models.DateTimeField(_('وقت الدخول'), null=True, blank=True)
    out_time = models.DateTimeField(_('وقت الخروج'), null=True, blank=True)
    device_identifier = models.CharField(_('معرف الجهاز'), max_length=120, blank=True)
    note = models.CharField(_('ملاحظة'), max_length=255, blank=True)
    created_at = models.DateTimeField(_('أُنشئ في'), auto_now_add=True)

    class Meta:
        verbose_name = _('سجل حضور')
        verbose_name_plural = _('سجلات الحضور')
        unique_together = ('showroom','employee','date')
        indexes = [models.Index(fields=['showroom','date']), models.Index(fields=['employee','date'])]

    def punch_in(self, device_id=None):
        from django.utils import timezone
        if self.in_time:
            return False
        self.in_time = timezone.now()
        if device_id and not self.device_identifier:
            self.device_identifier = device_id
        self.save(update_fields=['in_time','device_identifier'])
        return True

    def punch_out(self, device_id=None):
        from django.utils import timezone
        if self.out_time:
            return False
        self.out_time = timezone.now()
        self.save(update_fields=['out_time'])
        return True

    @property
    def worked_seconds(self):
        if self.in_time and self.out_time:
            return int((self.out_time - self.in_time).total_seconds())
        return 0


class ShowroomExpense(models.Model):
    """مصروفات المعرض مع تدفق موافقة مبسط."""

    class ExpenseType(models.TextChoices):
        SALARY = 'salary', _('رواتب')
        WAGES = 'wages', _('أجور')
        ELECTRICITY = 'electricity', _('كهرباء')
        OPERATING = 'operating_purchase', _('مشتريات تشغيل')
        ADVANCE = 'advance', _('سُلف')
        MAINTENANCE = 'maintenance', _('صيانة')
        OTHER = 'other', _('أخرى')

    class Status(models.TextChoices):
        DRAFT = 'draft', _('مسودة')
        SUBMITTED = 'submitted', _('قيد الموافقة')
        APPROVED = 'approved', _('معتمد')
        REJECTED = 'rejected', _('مرفوض')

    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    showroom = models.ForeignKey(Showroom, on_delete=models.CASCADE, related_name='expenses', verbose_name=_('المعرض'))
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    category = models.CharField(_('نوع المصروف'), max_length=40, choices=ExpenseType.choices, default=ExpenseType.OTHER)
    description = models.TextField(_('الوصف'), blank=True)
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.DRAFT)
    requires_approval = models.BooleanField(_('يحتاج موافقة'), default=False)
    attachment = models.FileField(_('مرفق/إيصال'), upload_to='showrooms/expenses/', null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='showroom_expenses_created', verbose_name=_('أنشئ بواسطة'))
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='showroom_expenses_approved', verbose_name=_('اعتمد بواسطة'))
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)
    rejection_note = models.CharField(_('سبب الرفض'), max_length=255, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('مصروف معرض')
        verbose_name_plural = _('مصروفات المعارض')
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['showroom', 'status']), models.Index(fields=['category'])]

    def __str__(self):
        return f"{self.showroom} - {self.category} - {self.amount}"

    def clean(self):
        """تحديد حاجة الموافقة بناءً على حد المعرض."""
        limit = self.showroom.expense_approval_limit or Decimal('0')
        if self.showroom.require_expense_approval and self.amount and self.amount > limit:
            self.requires_approval = True
            if self.status == self.Status.DRAFT:
                self.status = self.Status.SUBMITTED

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def approve(self, user=None):
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save(update_fields=['status', 'approved_by', 'approved_at'])
        self._audit('approve', user)

    def reject(self, user=None, reason: str = ''):
        self.status = self.Status.REJECTED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.rejection_note = reason or ''
        self.save(update_fields=['status', 'approved_by', 'approved_at', 'rejection_note'])
        self._audit('reject', user)

    def _audit(self, action: str, user=None):
        try:
            meta = AuditLog.build_object_meta(self)
            AuditLog.objects.create(
                user=user,
                action=AuditLog.ACTION_UPDATE,
                model_name=meta['model_name'],
                app_label=meta['app_label'],
                object_id=meta['object_id'],
                object_repr=meta['object_repr'],
                changes={'action': action, 'status': self.status},
            )
        except Exception:
            pass


class ShowroomPurchase(models.Model):
    """مشتريات مباشرة للمعرض من مورد خارجي مع حركة مخزون فورية."""

    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('confirmed', _('مؤكد')),
        ('cancelled', _('ملغى')),
    ]

    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    number = models.CharField(_('رقم المستند'), max_length=40, unique=True, blank=True)
    showroom = models.ForeignKey(Showroom, on_delete=models.CASCADE, related_name='direct_purchases', verbose_name=_('المعرض'))
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.PROTECT, related_name='showroom_purchases', verbose_name=_('المورد'))
    location = models.ForeignKey('inventory.Location', on_delete=models.PROTECT, related_name='showroom_purchases', verbose_name=_('الموقع'))
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(_('ملاحظات'), blank=True)
    invoice_file = models.FileField(_('فاتورة/مرفق'), upload_to='showrooms/purchases/', null=True, blank=True)
    total = models.DecimalField(_('الإجمالي'), max_digits=12, decimal_places=2, default=Decimal('0'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='showroom_purchases_created', verbose_name=_('أنشئ بواسطة'))
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='showroom_purchases_confirmed', verbose_name=_('أكد بواسطة'))
    confirmed_at = models.DateTimeField(_('تاريخ التأكيد'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('شراء مباشر للمعرض')
        verbose_name_plural = _('مشتريات مباشرة للمعرض')
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['showroom', 'status']), models.Index(fields=['number'])]

    def __str__(self):
        return self.number or f"SHP-{self.pk or ''}"

    def save(self, *args, **kwargs):
        if not self.number:
            ym = timezone.now().strftime('%Y%m')
            last = ShowroomPurchase.objects.filter(number__startswith=f'SHP-{ym}-').order_by('id').last()
            seq = 1
            if last and last.number:
                try:
                    seq = int(last.number.split('-')[-1]) + 1
                except Exception:
                    pass
            self.number = f'SHP-{ym}-{seq:04d}'
        super().save(*args, **kwargs)

    def recalc_total(self):
        agg = self.items.aggregate(total=models.Sum(models.F('quantity') * models.F('cost')))
        self.total = agg['total'] or Decimal('0')
        self.save(update_fields=['total'])
        return self.total

    def confirm(self, user=None):
        if self.status != 'draft':
            return
        from inventory.models import Stock, StockBatch
        self.recalc_total()
        with transaction.atomic():
            for item in self.items.select_related('product'):
                stock, _ = Stock.objects.get_or_create(product=item.product, location=self.location)
                stock.quantity += item.quantity
                stock.save(update_fields=['quantity'])
                StockBatch.objects.create(product=item.product, location=self.location, lot_number=self.number, unit_cost=item.cost, quantity=item.quantity)
                ShowroomStockMovement.objects.create(
                    showroom=self.showroom,
                    location=self.location,
                    product=item.product,
                    quantity=item.quantity,
                    movement_type=ShowroomStockMovement.MovementType.PURCHASE_IN,
                    reference=self.number,
                    created_by=user,
                )
            self.status = 'confirmed'
            self.confirmed_by = user
            self.confirmed_at = timezone.now()
            self.save(update_fields=['status', 'confirmed_by', 'confirmed_at'])
            self._post_accounting_entry(user=user)
            self._audit('confirm', user)

    def _post_accounting_entry(self, user=None):
        """إنشاء قيد محاسبي بسيط (مدين مخزون/مصروف، دائن نقدية/دائنين)."""
        try:
            from accounting.models import AccountingSettings, JournalEntry, JournalEntryItem
        except Exception:
            return
        settings = AccountingSettings.get()
        from accounting.models import Account
        debit_account = settings.inventory_account or Account.objects.filter(account_type='expense').first() or settings.cash_account
        credit_account = settings.ap_account or settings.cash_account
        amount = self.total or Decimal('0')
        if not amount or not debit_account or not credit_account or debit_account == credit_account:
            return
        desc = f"شراء معرض {self.showroom.code} من {self.supplier}"
        je = JournalEntry.objects.create(
            entry_type='purchase',
            description=desc,
            reference=self.number,
            date=timezone.now().date(),
            created_by=user,
            showroom=self.showroom,
            is_posted=True,
        )
        JournalEntryItem.objects.bulk_create([
            JournalEntryItem(
                journal_entry=je,
                account=debit_account,
                type='debit',
                amount=amount,
                description=desc,
            ),
            JournalEntryItem(
                journal_entry=je,
                account=credit_account,
                type='credit',
                amount=amount,
                description=desc,
            ),
        ])

    def _audit(self, action: str, user=None):
        try:
            meta = AuditLog.build_object_meta(self)
            AuditLog.objects.create(
                user=user,
                action=AuditLog.ACTION_UPDATE,
                model_name=meta['model_name'],
                app_label=meta['app_label'],
                object_id=meta['object_id'],
                object_repr=meta['object_repr'],
                changes={'action': action, 'status': self.status},
            )
        except Exception:
            pass


class ShowroomPurchaseItem(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    purchase = models.ForeignKey(ShowroomPurchase, on_delete=models.CASCADE, related_name='items', verbose_name=_('المستند'))
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, verbose_name=_('المنتج'))
    quantity = models.PositiveIntegerField(_('الكمية'))
    cost = models.DecimalField(_('التكلفة'), max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = _('بند شراء معرض')
        verbose_name_plural = _('بنود شراء المعرض')
        constraints = [models.CheckConstraint(check=models.Q(quantity__gt=0), name='showroom_purchase_qty_positive')]

    @property
    def total(self):
        return (self.quantity or 0) * (self.cost or Decimal('0'))

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.purchase.recalc_total()


class ShowroomStockMovement(models.Model):
    """سجل حركات المخزون على مستوى المعرض (عزل كامل لكل معرض)."""

    class MovementType(models.TextChoices):
        PURCHASE_IN = 'purchase_in', _('شراء مباشر')
        TRANSFER_IN = 'transfer_in', _('تحويل وارد')
        TRANSFER_OUT = 'transfer_out', _('تحويل صادر')
        ADJUSTMENT = 'adjustment', _('تسوية مخزون')
        SALE = 'sale', _('بيع')
        RETURN_IN = 'return_in', _('مرتجع')
        EXPENSE_CONSUME = 'expense_consume', _('صرف مصروف')

    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    showroom = models.ForeignKey(Showroom, on_delete=models.CASCADE, related_name='stock_movements', verbose_name=_('المعرض'))
    location = models.ForeignKey('inventory.Location', on_delete=models.PROTECT, related_name='stock_movements', verbose_name=_('الموقع'))
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, related_name='showroom_stock_movements', verbose_name=_('المنتج'))
    quantity = models.IntegerField(_('الكمية (+/-)'))
    movement_type = models.CharField(_('نوع الحركة'), max_length=30, choices=MovementType.choices)
    reference = models.CharField(_('مرجع'), max_length=100, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='showroom_movements_created', verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    note = models.CharField(_('ملاحظة'), max_length=255, blank=True)

    class Meta:
        verbose_name = _('حركة مخزون معرض')
        verbose_name_plural = _('حركات مخزون المعرض')
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['showroom', 'movement_type']), models.Index(fields=['product', 'location'])]

    def __str__(self):
        return f"{self.showroom} {self.movement_type} {self.product} ({self.quantity})"

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        if created:
            try:
                meta = AuditLog.build_object_meta(self)
                AuditLog.objects.create(
                    user=self.created_by,
                    action=AuditLog.ACTION_CREATE,
                    model_name=meta['model_name'],
                    app_label=meta['app_label'],
                    object_id=meta['object_id'],
                    object_repr=meta['object_repr'],
                    changes={'movement_type': self.movement_type, 'quantity': self.quantity, 'reference': self.reference},
                )
            except Exception:
                pass


class ShowroomPayrollEntry(models.Model):
    """رواتب/بدلات بسيطة مرتبطة بالمعرض."""

    class EntryType(models.TextChoices):
        SALARY = 'salary', _('راتب')
        BONUS = 'bonus', _('مكافأة')
        COMMISSION = 'commission', _('عمولة')
        DEDUCTION = 'deduction', _('خصم')

    class Status(models.TextChoices):
        PENDING = 'pending', _('قيد المراجعة')
        APPROVED = 'approved', _('معتمد')
        PAID = 'paid', _('مدفوع')

    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    showroom = models.ForeignKey(Showroom, on_delete=models.CASCADE, related_name='payroll_entries', verbose_name=_('المعرض'))
    employee = models.ForeignKey(ShowroomEmployee, null=True, blank=True, on_delete=models.SET_NULL, related_name='payroll_entries', verbose_name=_('موظف المعرض'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='showroom_payroll_user_entries', verbose_name=_('المستخدم (اختياري)'))
    period = models.DateField(_('الشهر'), help_text=_('استخدم أول يوم في الشهر لتمثيل الفترة'))
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    entry_type = models.CharField(_('النوع'), max_length=20, choices=EntryType.choices, default=EntryType.SALARY)
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.PENDING)
    note = models.CharField(_('ملاحظة'), max_length=255, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='showroom_payroll_approved', verbose_name=_('اعتمد بواسطة'))
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('قيد رواتب معرض')
        verbose_name_plural = _('قيود رواتب المعرض')
        ordering = ['-period', '-id']
        indexes = [models.Index(fields=['showroom', 'period']), models.Index(fields=['status'])]

    def __str__(self):
        return f"{self.showroom} {self.entry_type} {self.period}"

    def approve(self, user=None):
        if self.status == self.Status.PAID:
            return
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save(update_fields=['status', 'approved_by', 'approved_at'])


class ShowroomShift(models.Model):
    """نموذج شفت مرتبط بالمعرض مع توقيت ثابت."""

    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    showroom = models.ForeignKey(Showroom, on_delete=models.CASCADE, related_name='shifts', verbose_name=_('المعرض'))
    name = models.CharField(_('اسم الشفت'), max_length=80)
    start_time = models.TimeField(_('بداية الشفت'))
    end_time = models.TimeField(_('نهاية الشفت'))
    break_minutes = models.PositiveIntegerField(_('دقائق الراحة'), default=0)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('شفت معرض')
        verbose_name_plural = _('شفتات المعارض')
        ordering = ['showroom', 'start_time']
        indexes = [models.Index(fields=['showroom', 'is_active'])]

    def __str__(self):
        return f"{self.showroom.code} {self.name}"


class ShowroomShiftAssignment(models.Model):
    """تعيين موظف معرض لشفت معين مع يوم في الأسبوع."""

    WEEKDAY_CHOICES = [(i, _(day)) for i, day in enumerate([
        'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد'
    ])]

    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    shift = models.ForeignKey(ShowroomShift, on_delete=models.CASCADE, related_name='assignments', verbose_name=_('الشفت'))
    employee = models.ForeignKey(ShowroomEmployee, on_delete=models.CASCADE, related_name='shift_assignments', verbose_name=_('الموظف'))
    day_of_week = models.PositiveSmallIntegerField(_('اليوم'), choices=WEEKDAY_CHOICES)
    note = models.CharField(_('ملاحظة'), max_length=200, blank=True)
    active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('تعيين شفت لموظف معرض')
        verbose_name_plural = _('تعيينات شفتات موظفي المعرض')
        unique_together = ('shift', 'employee', 'day_of_week')
        indexes = [models.Index(fields=['employee', 'active']), models.Index(fields=['shift', 'day_of_week'])]

    def __str__(self):
        return f"{self.employee} -> {self.shift} ({self.day_of_week})"


class ShowroomPricingRule(models.Model):
    """
    قواعد التسعير المرنة لكل معرض
    Flexible Pricing Rules per Showroom
    """
    
    ADJUSTMENT_TYPE_CHOICES = [
        ('fixed', _('سعر ثابت')),
        ('percentage', _('نسبة من السعر الأساسي')),
        ('markup', _('هامش ربح')),
        ('discount', _('خصم')),
    ]
    
    id = models.AutoField(primary_key=True)
    showroom = models.ForeignKey(Showroom, on_delete=models.CASCADE, related_name='pricing_rules', verbose_name=_('المعرض'))
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='showroom_prices', verbose_name=_('المنتج'))
    adjustment_type = models.CharField(_('نوع التسعير'), max_length=20, choices=ADJUSTMENT_TYPE_CHOICES, default='percentage')
    value = models.DecimalField(_('القيمة'), max_digits=12, decimal_places=2, help_text=_('السعر الثابت أو النسبة المئوية أو قيمة الهامش'))
    effective_from = models.DateField(_('ساري من'), default=timezone.localdate)
    effective_to = models.DateField(_('ساري حتى'), null=True, blank=True, help_text=_('اتركه فارغاً للتطبيق الدائم'))
    is_active = models.BooleanField(_('نشط'), default=True)
    priority = models.IntegerField(_('الأولوية'), default=1, help_text=_('الأولوية الأعلى تطبق أولاً'))
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='pricing_rules_created', verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('قاعدة تسعير معرض')
        verbose_name_plural = _('قواعد تسعير المعارض')
        ordering = ['showroom', '-priority', 'product']
        indexes = [
            models.Index(fields=['showroom', 'product', 'is_active']),
            models.Index(fields=['effective_from', 'effective_to']),
        ]
    
    def __str__(self):
        return f"{self.showroom.name} - {self.product.name} ({self.adjustment_type})"
    
    def calculate_price(self, base_price):
        """حساب السعر النهائي بناءً على القاعدة"""
        if not base_price:
            return Decimal('0')
        
        if self.adjustment_type == 'fixed':
            return self.value
        elif self.adjustment_type == 'percentage':
            return base_price * (self.value / Decimal('100'))
        elif self.adjustment_type == 'markup':
            return base_price + self.value
        elif self.adjustment_type == 'discount':
            return base_price - self.value
        
        return base_price
    
    def is_currently_valid(self):
        """التحقق من صلاحية القاعدة في التاريخ الحالي"""
        from django.utils import timezone
        today = timezone.now().date()
        
        if not self.is_active:
            return False
        
        if self.effective_from > today:
            return False
        
        if self.effective_to and self.effective_to < today:
            return False
        
        return True


class ShowroomMoneyTransfer(models.Model):
    """
    تحويل الأموال بين المعارض
    Money Transfer between Showrooms
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('قيد الانتظار')
        APPROVED = 'approved', _('معتمد')
        COMPLETED = 'completed', _('مكتمل')
        REJECTED = 'rejected', _('مرفوض')
        CANCELLED = 'cancelled', _('ملغي')
    
    class TransferMethod(models.TextChoices):
        CASH = 'cash', _('نقدي')
        BANK = 'bank', _('تحويل بنكي')
        CHEQUE = 'cheque', _('شيك')
        INTERNAL = 'internal', _('تحويل داخلي')
        OTHER = 'other', _('أخرى')
    
    id = models.AutoField(primary_key=True)
    transfer_number = models.CharField(_('رقم التحويل'), max_length=30, unique=True, blank=True)
    
    from_showroom = models.ForeignKey(
        Showroom, 
        on_delete=models.PROTECT, 
        related_name='outgoing_transfers',
        verbose_name=_('من معرض')
    )
    to_showroom = models.ForeignKey(
        Showroom, 
        on_delete=models.PROTECT, 
        related_name='incoming_transfers',
        verbose_name=_('إلى معرض')
    )
    
    amount = models.DecimalField(_('المبلغ'), max_digits=14, decimal_places=2)
    transfer_method = models.CharField(
        _('طريقة التحويل'), 
        max_length=20, 
        choices=TransferMethod.choices, 
        default=TransferMethod.CASH
    )
    
    # تفاصيل إضافية حسب طريقة التحويل
    bank_name = models.CharField(_('اسم البنك'), max_length=100, blank=True)
    bank_account = models.CharField(_('رقم الحساب'), max_length=50, blank=True)
    cheque_number = models.CharField(_('رقم الشيك'), max_length=50, blank=True)
    cheque_date = models.DateField(_('تاريخ الشيك'), null=True, blank=True)
    reference_number = models.CharField(_('رقم المرجع'), max_length=100, blank=True)
    
    status = models.CharField(
        _('الحالة'), 
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    
    reason = models.TextField(_('سبب التحويل'), blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    rejection_reason = models.TextField(_('سبب الرفض'), blank=True)
    
    # سجل المستخدمين
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='showroom_transfers_created',
        verbose_name=_('أنشئ بواسطة')
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='showroom_transfers_approved',
        verbose_name=_('اعتمد بواسطة')
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='showroom_transfers_received',
        verbose_name=_('استلم بواسطة')
    )
    
    # التواريخ
    transfer_date = models.DateField(_('تاريخ التحويل'), default=timezone.localdate)
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)
    completed_at = models.DateTimeField(_('تاريخ الاكتمال'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    # ربط بالقيود المحاسبية
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='showroom_money_transfers',
        verbose_name=_('القيد المحاسبي')
    )
    
    class Meta:
        verbose_name = _('تحويل أموال بين معارض')
        verbose_name_plural = _('تحويلات الأموال بين المعارض')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['from_showroom', 'to_showroom']),
            models.Index(fields=['status']),
            models.Index(fields=['transfer_date']),
            models.Index(fields=['transfer_method']),
        ]
    
    def __str__(self):
        return f"{self.transfer_number}: {self.from_showroom.code} → {self.to_showroom.code} ({self.amount})"
    
    def save(self, *args, **kwargs):
        if not self.transfer_number:
            from core.utils import next_sequence, format_code
            seq = next_sequence('SHOWROOM_TRANSFER')
            self.transfer_number = format_code('SMT', seq)
        super().save(*args, **kwargs)
    
    def approve(self, user):
        """اعتماد التحويل"""
        if self.status != self.Status.PENDING:
            return False
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save(update_fields=['status', 'approved_by', 'approved_at'])
        
        # تسجيل في سجل التدقيق
        AuditLog.objects.create(
            user=user,
            action='approve',
            model_name='ShowroomMoneyTransfer',
            object_id=self.id,
            changes={'status': 'approved', 'amount': str(self.amount)}
        )
        return True
    
    def complete(self, user):
        """إتمام التحويل"""
        if self.status not in [self.Status.PENDING, self.Status.APPROVED]:
            return False
        self.status = self.Status.COMPLETED
        self.received_by = user
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'received_by', 'completed_at'])
        
        # تسجيل في سجل التدقيق
        AuditLog.objects.create(
            user=user,
            action='complete',
            model_name='ShowroomMoneyTransfer',
            object_id=self.id,
            changes={'status': 'completed', 'amount': str(self.amount)}
        )
        return True
    
    def reject(self, user, reason=''):
        """رفض التحويل"""
        if self.status != self.Status.PENDING:
            return False
        self.status = self.Status.REJECTED
        self.rejection_reason = reason
        self.save(update_fields=['status', 'rejection_reason'])
        
        AuditLog.objects.create(
            user=user,
            action='reject',
            model_name='ShowroomMoneyTransfer',
            object_id=self.id,
            changes={'status': 'rejected', 'reason': reason}
        )
        return True
    
    def cancel(self, user):
        """إلغاء التحويل"""
        if self.status in [self.Status.COMPLETED, self.Status.CANCELLED]:
            return False
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status'])
        
        AuditLog.objects.create(
            user=user,
            action='cancel',
            model_name='ShowroomMoneyTransfer',
            object_id=self.id,
            changes={'status': 'cancelled'}
        )
        return True


class ShowroomStockRequest(models.Model):
    """
    طلب نقل مخزون من معرض لآخر
    عندما يكون منتج غير متوفر في معرض معين، يمكن طلبه من معرض آخر
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _('قيد الانتظار')
        APPROVED = 'approved', _('معتمد')
        IN_TRANSIT = 'in_transit', _('قيد النقل')
        DELIVERED = 'delivered', _('تم التسليم')
        REJECTED = 'rejected', _('مرفوض')
        CANCELLED = 'cancelled', _('ملغي')
    
    class Priority(models.TextChoices):
        LOW = 'low', _('منخفضة')
        NORMAL = 'normal', _('عادية')
        HIGH = 'high', _('عالية')
        URGENT = 'urgent', _('عاجلة')
    
    id = models.AutoField(primary_key=True)
    request_number = models.CharField(_('رقم الطلب'), max_length=30, unique=True, editable=False)
    
    # المعرض الطالب والمعرض المصدر
    requesting_showroom = models.ForeignKey(
        Showroom, 
        on_delete=models.PROTECT, 
        related_name='stock_requests_out',
        verbose_name=_('المعرض الطالب')
    )
    source_showroom = models.ForeignKey(
        Showroom, 
        on_delete=models.PROTECT, 
        related_name='stock_requests_in',
        verbose_name=_('المعرض المصدر')
    )
    
    # المنتج والكمية
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='stock_requests',
        verbose_name=_('المنتج')
    )
    quantity_requested = models.PositiveIntegerField(_('الكمية المطلوبة'), default=1)
    quantity_approved = models.PositiveIntegerField(_('الكمية المعتمدة'), null=True, blank=True)
    quantity_delivered = models.PositiveIntegerField(_('الكمية المستلمة'), null=True, blank=True)
    
    # الحالة والأولوية
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.PENDING)
    priority = models.CharField(_('الأولوية'), max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    
    # سبب الطلب
    reason = models.TextField(_('سبب الطلب'), blank=True, help_text=_('مثال: طلب عميل، نفاد المخزون'))
    customer_name = models.CharField(_('اسم العميل (اختياري)'), max_length=150, blank=True)
    customer_phone = models.CharField(_('هاتف العميل (اختياري)'), max_length=30, blank=True)
    
    # التواريخ
    request_date = models.DateTimeField(_('تاريخ الطلب'), default=timezone.now)
    needed_by = models.DateField(_('مطلوب بحلول'), null=True, blank=True)
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)
    shipped_at = models.DateTimeField(_('تاريخ الشحن'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('تاريخ التسليم'), null=True, blank=True)
    
    # المسؤولون
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='stock_requests_created',
        verbose_name=_('طلب بواسطة')
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='stock_requests_approved',
        verbose_name=_('اعتمد بواسطة')
    )
    shipped_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='stock_requests_shipped',
        verbose_name=_('شحن بواسطة')
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='stock_requests_received',
        verbose_name=_('استلم بواسطة')
    )
    
    # ملاحظات
    notes = models.TextField(_('ملاحظات'), blank=True)
    rejection_reason = models.TextField(_('سبب الرفض'), blank=True)
    
    # الطابع الزمني
    created_at = models.DateTimeField(_('أُنشئ في'), auto_now_add=True)
    updated_at = models.DateTimeField(_('آخر تحديث'), auto_now=True)
    
    # ربط بحركة المخزون
    stock_transfer = models.ForeignKey(
        'inventory.StockTransfer',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='showroom_stock_requests',
        verbose_name=_('حركة المخزون')
    )
    
    class Meta:
        verbose_name = _('طلب نقل مخزون')
        verbose_name_plural = _('طلبات نقل المخزون')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['requesting_showroom', 'status']),
            models.Index(fields=['source_showroom', 'status']),
            models.Index(fields=['product']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['request_date']),
        ]
    
    def __str__(self):
        return f"{self.request_number}: {self.product.name} ({self.quantity_requested})"
    
    def save(self, *args, **kwargs):
        if not self.request_number:
            from core.utils import next_sequence, format_code
            seq = next_sequence('SHOWROOM_STOCK_REQUEST')
            self.request_number = format_code('SSR', seq)
        super().save(*args, **kwargs)
    
    def approve(self, user, quantity=None):
        """اعتماد الطلب"""
        if self.status != self.Status.PENDING:
            return False
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.quantity_approved = quantity if quantity else self.quantity_requested
        self.save(update_fields=['status', 'approved_by', 'approved_at', 'quantity_approved'])
        
        AuditLog.objects.create(
            user=user,
            action='approve',
            model_name='ShowroomStockRequest',
            object_id=self.id,
            changes={'status': 'approved', 'quantity_approved': self.quantity_approved}
        )
        return True
    
    def ship(self, user):
        """بدء الشحن"""
        if self.status != self.Status.APPROVED:
            return False
        self.status = self.Status.IN_TRANSIT
        self.shipped_by = user
        self.shipped_at = timezone.now()
        self.save(update_fields=['status', 'shipped_by', 'shipped_at'])
        
        AuditLog.objects.create(
            user=user,
            action='ship',
            model_name='ShowroomStockRequest',
            object_id=self.id,
            changes={'status': 'in_transit'}
        )
        return True
    
    def deliver(self, user, quantity=None):
        """تأكيد التسليم"""
        if self.status != self.Status.IN_TRANSIT:
            return False
        self.status = self.Status.DELIVERED
        self.received_by = user
        self.delivered_at = timezone.now()
        self.quantity_delivered = quantity if quantity else self.quantity_approved
        self.save(update_fields=['status', 'received_by', 'delivered_at', 'quantity_delivered'])
        
        AuditLog.objects.create(
            user=user,
            action='deliver',
            model_name='ShowroomStockRequest',
            object_id=self.id,
            changes={'status': 'delivered', 'quantity_delivered': self.quantity_delivered}
        )
        return True
    
    def reject(self, user, reason=''):
        """رفض الطلب"""
        if self.status not in [self.Status.PENDING, self.Status.APPROVED]:
            return False
        self.status = self.Status.REJECTED
        self.rejection_reason = reason
        self.save(update_fields=['status', 'rejection_reason'])
        
        AuditLog.objects.create(
            user=user,
            action='reject',
            model_name='ShowroomStockRequest',
            object_id=self.id,
            changes={'status': 'rejected', 'reason': reason}
        )
        return True
    
    def cancel(self, user):
        """إلغاء الطلب"""
        if self.status in [self.Status.DELIVERED, self.Status.CANCELLED]:
            return False
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status'])
        
        AuditLog.objects.create(
            user=user,
            action='cancel',
            model_name='ShowroomStockRequest',
            object_id=self.id,
            changes={'status': 'cancelled'}
        )
        return True
    
    @property
    def is_urgent(self):
        """هل الطلب عاجل؟"""
        return self.priority == self.Priority.URGENT
    
    @property
    def is_overdue(self):
        """هل تأخر الطلب عن موعده؟"""
        if self.needed_by and self.status not in [self.Status.DELIVERED, self.Status.CANCELLED, self.Status.REJECTED]:
            from datetime import date
            return date.today() > self.needed_by
        return False


class TemporaryWorker(models.Model):
    """
    نموذج العمالة المؤقتة للمعارض المؤقتة أو الموسمية
    """
    
    class WorkerType(models.TextChoices):
        DAILY = 'daily', _('يومي')
        HOURLY = 'hourly', _('بالساعة')
        CONTRACT = 'contract', _('عقد مؤقت')
    
    id = models.AutoField(primary_key=True)
    showroom = models.ForeignKey(
        Showroom,
        on_delete=models.CASCADE,
        related_name='temporary_workers',
        verbose_name=_('المعرض')
    )
    worker_name = models.CharField(_('اسم العامل'), max_length=120)
    worker_phone = models.CharField(_('رقم الهاتف'), max_length=40, blank=True)
    national_id = models.CharField(
        _('رقم الهوية'),
        max_length=40,
        blank=True,
        help_text=_('رقم البطاقة أو الهوية')
    )
    
    worker_type = models.CharField(
        _('نوع العمل'),
        max_length=20,
        choices=WorkerType.choices,
        default=WorkerType.DAILY
    )
    
    job_title = models.CharField(
        _('المسمى الوظيفي'),
        max_length=120,
        help_text=_('مثال: حامل، عامل تنظيف، موزع دعاية')
    )
    
    start_date = models.DateField(_('تاريخ البداية'))
    end_date = models.DateField(
        _('تاريخ النهاية'),
        null=True,
        blank=True,
        help_text=_('للعمالة المؤقتة أو الموسمية')
    )
    
    daily_wage = models.DecimalField(
        _('الأجر اليومي'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    hourly_wage = models.DecimalField(
        _('الأجر بالساعة'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    total_amount = models.DecimalField(
        _('الإجمالي المستحق'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    
    days_worked = models.IntegerField(_('أيام العمل'), default=0)
    hours_worked = models.DecimalField(
        _('ساعات العمل'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0')
    )
    
    is_paid = models.BooleanField(_('تم السداد'), default=False)
    payment_date = models.DateField(_('تاريخ السداد'), null=True, blank=True)
    payment_reference = models.CharField(
        _('مرجع السداد'),
        max_length=100,
        blank=True,
        help_text=_('رقم الإيصال أو القيد المحاسبي')
    )
    
    # ربط بالحسابات
    expense_account = models.ForeignKey(
        'accounting.Account',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='temporary_worker_expenses',
        verbose_name=_('حساب المصروفات'),
        help_text=_('حساب مصروفات العمالة المؤقتة')
    )
    
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='temporary_worker_entries',
        verbose_name=_('القيد المحاسبي')
    )
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='temporary_workers_created',
        verbose_name=_('أنشئ بواسطة')
    )
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('عامل مؤقت')
        verbose_name_plural = _('العمالة المؤقتة')
        ordering = ['-start_date', '-created_at']
        indexes = [
            models.Index(fields=['showroom', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['is_paid']),
        ]
    
    def __str__(self):
        return f"{self.worker_name} - {self.showroom.name} ({self.start_date})"
    
    def calculate_total(self):
        """حساب المبلغ الإجمالي بناءً على نوع العمل"""
        if self.worker_type == self.WorkerType.DAILY and self.daily_wage:
            self.total_amount = self.daily_wage * Decimal(str(self.days_worked))
        elif self.worker_type == self.WorkerType.HOURLY and self.hourly_wage:
            self.total_amount = self.hourly_wage * self.hours_worked
        return self.total_amount
    
    def save(self, *args, **kwargs):
        # حساب الإجمالي تلقائياً قبل الحفظ
        self.calculate_total()
        super().save(*args, **kwargs)
    
    @property
    def duration_days(self):
        """عدد الأيام من البداية للنهاية"""
        if self.end_date:
            return (self.end_date - self.start_date).days + 1
        return None
    
    @property
    def is_finished(self):
        """هل انتهت فترة العمل؟"""
        if self.end_date:
            from django.utils import timezone
            return timezone.now().date() > self.end_date
        return False


class ShowroomRentPayment(models.Model):
    """
    سجل دفعات الإيجار للمعارض المستأجرة
    """
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', _('معلق')
        PAID = 'paid', _('مدفوع')
        OVERDUE = 'overdue', _('متأخر')
        CANCELLED = 'cancelled', _('ملغي')
    
    id = models.AutoField(primary_key=True)
    showroom = models.ForeignKey(
        Showroom,
        on_delete=models.CASCADE,
        related_name='rent_payments',
        verbose_name=_('المعرض')
    )
    
    payment_date = models.DateField(_('تاريخ الدفعة المقرر'))
    amount = models.DecimalField(
        _('المبلغ'),
        max_digits=12,
        decimal_places=2
    )
    
    status = models.CharField(
        _('الحالة'),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    
    actual_payment_date = models.DateField(
        _('تاريخ الدفع الفعلي'),
        null=True,
        blank=True
    )
    
    payment_reference = models.CharField(
        _('مرجع الدفع'),
        max_length=100,
        blank=True
    )
    
    # ربط بالحسابات
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rent_payment_entries',
        verbose_name=_('القيد المحاسبي')
    )
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rent_payments_created',
        verbose_name=_('أنشئ بواسطة')
    )
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('دفعة إيجار')
        verbose_name_plural = _('دفعات الإيجار')
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['showroom', 'status']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.showroom.name} - {self.payment_date} - {self.amount}"
    
    def mark_as_paid(self, user=None, payment_ref=''):
        """تحديد الدفعة كمدفوعة"""
        from django.utils import timezone
        self.status = self.PaymentStatus.PAID
        self.actual_payment_date = timezone.now().date()
        if payment_ref:
            self.payment_reference = payment_ref
        self.save()
    
    def check_overdue(self):
        """التحقق من التأخير في السداد"""
        from django.utils import timezone
        if self.status == self.PaymentStatus.PENDING:
            if timezone.now().date() > self.payment_date:
                self.status = self.PaymentStatus.OVERDUE
                self.save()
    
    @property
    def days_overdue(self):
        """عدد أيام التأخير"""
        if self.status == self.PaymentStatus.OVERDUE:
            from django.utils import timezone
            return (timezone.now().date() - self.payment_date).days
        return 0

