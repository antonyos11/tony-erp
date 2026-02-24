"""
نماذج وحدة الفروع والمعارض الموحدة
تم دمج وحدة المعارض (showrooms) في هذه الوحدة
"""
from decimal import Decimal
from django.db import models, transaction
from django.db.models import Q, Sum, F
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Branch(models.Model):
    """
    نموذج الفرع/المعرض الموحد
    يدعم جميع أنواع الفروع: فرع رئيسي، فرع، مستودع، معرض، مصنع
    """
    STATUS_CHOICES = [
        ('active', _('نشط')),
        ('inactive', _('غير نشط')),
        ('suspended', _('معلق')),
    ]
    
    BRANCH_TYPE_CHOICES = [
        ('main', _('فرع رئيسي')),
        ('branch', _('فرع')),
        ('warehouse', _('مستودع')),
        ('showroom', _('معرض/صالة عرض')),
        ('factory', _('مصنع')),
        ('store', _('متجر')),
    ]
    
    # معلومات أساسية
    code = models.CharField(_('كود الفرع'), max_length=20, unique=True)
    name = models.CharField(_('اسم الفرع'), max_length=200)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=200, blank=True)
    branch_type = models.CharField(_('نوع الفرع'), max_length=20, choices=BRANCH_TYPE_CHOICES, default='branch')
    
    # الربط بالمخزن
    location = models.OneToOneField(
        'inventory.Location', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='branch',
        verbose_name=_('الموقع المخزني')
    )
    
    # العنوان والموقع
    address = models.TextField(_('العنوان'), blank=True)
    city = models.CharField(_('المدينة'), max_length=100, blank=True)
    state = models.CharField(_('المنطقة/المحافظة'), max_length=100, blank=True)
    country = models.CharField(_('الدولة'), max_length=100, default='مصر')
    postal_code = models.CharField(_('الرمز البريدي'), max_length=20, blank=True)
    
    # معلومات الاتصال
    phone = models.CharField(_('الهاتف'), max_length=50, blank=True)
    mobile = models.CharField(_('الجوال'), max_length=50, blank=True)
    email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    fax = models.CharField(_('الفاكس'), max_length=50, blank=True)
    contact_person = models.CharField(_('مسؤول التواصل'), max_length=120, blank=True)
    
    # الموقع الجغرافي
    latitude = models.DecimalField(_('خط العرض'), max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(_('خط الطول'), max_digits=10, decimal_places=7, null=True, blank=True)
    
    # الإدارة
    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='managed_branches', verbose_name=_('المدير')
    )
    parent_branch = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sub_branches', verbose_name=_('الفرع الرئيسي')
    )
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='active')
    is_main = models.BooleanField(_('هل هو الفرع الرئيسي؟'), default=False)
    is_active = models.BooleanField(_('نشط'), default=True)
    
    # إعدادات المخزون
    allow_negative_stock = models.BooleanField(_('السماح بالمخزون السالب'), default=False)
    auto_approve_transfers = models.BooleanField(_('الموافقة التلقائية على التحويلات'), default=False)
    
    # إعدادات المصروفات (من المعارض)
    expense_approval_limit = models.DecimalField(
        _('حد اعتماد المصروفات'), 
        max_digits=12, decimal_places=2, 
        default=Decimal('0'),
        help_text=_('المبلغ الأقصى للمصروفات بدون موافقة')
    )
    require_expense_approval = models.BooleanField(_('يتطلب موافقة للمصروفات'), default=True)
    
    # معلومات ضريبية
    tax_id = models.CharField(_('الرقم الضريبي'), max_length=50, blank=True)
    commercial_register = models.CharField(_('السجل التجاري'), max_length=50, blank=True)
    
    # === حقول إدارة الملكية والعقود ===
    OWNERSHIP_TYPE_CHOICES = [
        ('owned', _('مملوك')),
        ('rented', _('مؤجر')),
        ('temporary', _('مؤقت')),
    ]
    
    ownership_type = models.CharField(
        _('نوع الملكية'), max_length=20, 
        choices=OWNERSHIP_TYPE_CHOICES, default='owned'
    )
    
    # معلومات المالك (في حالة الإيجار)
    owner_name = models.CharField(_('اسم المالك'), max_length=200, blank=True)
    owner_phone = models.CharField(_('هاتف المالك'), max_length=50, blank=True)
    owner_id_number = models.CharField(_('رقم هوية المالك'), max_length=50, blank=True)
    owner_bank_account = models.CharField(_('حساب المالك البنكي'), max_length=100, blank=True)
    owner_bank_name = models.CharField(_('اسم البنك'), max_length=100, blank=True)
    
    # معلومات العقد
    contract_number = models.CharField(_('رقم العقد'), max_length=50, blank=True)
    contract_start_date = models.DateField(_('تاريخ بداية العقد'), null=True, blank=True)
    contract_end_date = models.DateField(_('تاريخ نهاية العقد'), null=True, blank=True)
    contract_duration_months = models.PositiveIntegerField(_('مدة العقد (بالأشهر)'), null=True, blank=True)
    
    # قيم الإيجار
    monthly_rent = models.DecimalField(
        _('الإيجار الشهري'), max_digits=12, decimal_places=2, 
        default=Decimal('0'), blank=True
    )
    annual_rent = models.DecimalField(
        _('الإيجار السنوي'), max_digits=12, decimal_places=2, 
        default=Decimal('0'), blank=True
    )
    deposit_amount = models.DecimalField(
        _('مبلغ التأمين'), max_digits=12, decimal_places=2, 
        default=Decimal('0'), blank=True
    )
    
    # تفاصيل العقار
    property_area = models.DecimalField(
        _('مساحة العقار (م²)'), max_digits=10, decimal_places=2, 
        null=True, blank=True
    )
    property_type = models.CharField(_('نوع العقار'), max_length=50, blank=True,
        help_text=_('مثال: معرض تجاري، مستودع، فيلا، شقة، أرض')
    )
    
    # إشعارات وتنبيهات
    rent_due_day = models.PositiveIntegerField(
        _('يوم استحقاق الإيجار'), default=1,
        help_text=_('اليوم من الشهر الذي يستحق فيه الإيجار')
    )
    contract_reminder_days = models.PositiveIntegerField(
        _('التنبيه قبل انتهاء العقد (أيام)'), default=30
    )
    
    # ملاحظات العقد
    contract_notes = models.TextField(_('ملاحظات العقد'), blank=True)
    contract_file = models.FileField(
        _('ملف العقد'), upload_to='contracts/branches/', 
        null=True, blank=True
    )
    
    # التواريخ
    opening_date = models.DateField(_('تاريخ الافتتاح'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_branches', verbose_name=_('أنشئ بواسطة')
    )
    
    # ملاحظات
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    class Meta:
        verbose_name = _('فرع')
        verbose_name_plural = _('الفروع')
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['branch_type']),
            models.Index(fields=['is_active']),
        ]
        permissions = [
            ('view_branch_stock', 'عرض مخزون الفرع'),
            ('manage_branch_transfers', 'إدارة تحويلات الفرع'),
            ('view_branch_reports', 'عرض تقارير الفرع'),
            ('manage_all_branches', 'إدارة جميع الفروع'),
            ('manage_branch_expenses', 'إدارة مصروفات الفرع'),
            ('approve_branch_expenses', 'اعتماد مصروفات الفرع'),
            ('manage_branch_pos', 'إدارة أجهزة نقاط البيع'),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def is_showroom(self):
        """هل هذا الفرع معرض؟"""
        return self.branch_type in ('showroom', 'store')
    
    @property
    def is_warehouse(self):
        """هل هذا الفرع مستودع؟"""
        return self.branch_type == 'warehouse'
    
    def get_stock_value(self):
        """حساب قيمة المخزون في الفرع"""
        if not self.location:
            return Decimal('0.00')
        from inventory.models import Stock
        result = Stock.objects.filter(location=self.location).aggregate(
            total=Sum(F('quantity') * F('product__cost'))
        )
        return result['total'] or Decimal('0.00')
    
    def get_current_stock(self):
        """الحصول على المخزون الحالي"""
        if not self.location:
            return 0
        from inventory.models import Stock
        result = Stock.objects.filter(location=self.location).aggregate(
            total=Sum('quantity')
        )
        return result['total'] or 0


class BranchStaff(models.Model):
    """
    موظفو الفرع/المعرض
    يدمج ShowroomEmployee مع BranchStaff
    """
    ROLE_CHOICES = [
        ('manager', _('مدير')),
        ('supervisor', _('مشرف')),
        ('cashier', _('أمين صندوق')),
        ('sales', _('مبيعات')),
        ('storekeeper', _('أمين مخزن')),
        ('warehouse_worker', _('عامل مستودع')),
        ('accountant', _('محاسب')),
        ('hr', _('شؤون موظفين')),
        ('call_center', _('كول سنتر')),
        ('customer_service', _('خدمة عملاء')),
        ('porter', _('حامل/عامل تحميل')),
        ('pantry', _('بانتري/ضيافة')),
        ('worker', _('عامل')),
        ('other', _('أخرى')),
    ]
    
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, 
        related_name='staff', verbose_name=_('الفرع')
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, 
        related_name='branch_assignments', verbose_name=_('الموظف')
    )
    role = models.CharField(_('الدور'), max_length=20, choices=ROLE_CHOICES, default='other')
    position = models.CharField(_('المنصب'), max_length=100, blank=True)
    
    # صلاحيات
    can_cross_access = models.BooleanField(_('صلاحية الوصول لجميع الفروع'), default=False)
    extra_perms = models.JSONField(
        _('صلاحيات إضافية'), 
        default=list, blank=True,
        help_text=_('مثال: ["pos.export","inventory.view"]')
    )
    
    is_active = models.BooleanField(_('نشط'), default=True)
    start_date = models.DateField(_('تاريخ البداية'), null=True, blank=True)
    end_date = models.DateField(_('تاريخ النهاية'), null=True, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('موظف فرع')
        verbose_name_plural = _('موظفو الفروع')
        unique_together = ['branch', 'user']
        ordering = ['-is_active', 'role', 'user__username']
        indexes = [
            models.Index(fields=['branch', 'user']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} @ {self.branch.name} ({self.get_role_display()})"
    
    @property
    def is_manager(self):
        return self.role in ('manager', 'supervisor')


class BranchTransfer(models.Model):
    """
    تحويلات بين الفروع
    """
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('pending', _('قيد الانتظار')),
        ('approved', _('معتمد')),
        ('in_transit', _('في الطريق')),
        ('received', _('مستلم')),
        ('rejected', _('مرفوض')),
        ('cancelled', _('ملغى')),
    ]
    
    transfer_number = models.CharField(_('رقم التحويل'), max_length=50, unique=True)
    from_branch = models.ForeignKey(
        Branch, on_delete=models.PROTECT,
        related_name='transfers_out', verbose_name=_('من فرع')
    )
    to_branch = models.ForeignKey(
        Branch, on_delete=models.PROTECT,
        related_name='transfers_in', verbose_name=_('إلى فرع')
    )
    
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='draft')
    transfer_date = models.DateField(_('تاريخ التحويل'), default=timezone.localdate)
    expected_arrival = models.DateField(_('تاريخ الوصول المتوقع'), null=True, blank=True)
    actual_arrival = models.DateField(_('تاريخ الوصول الفعلي'), null=True, blank=True)
    
    # المسؤولين
    requested_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='branch_transfer_requests', verbose_name=_('طلب بواسطة')
    )
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='branch_transfer_approvals', verbose_name=_('اعتمد بواسطة')
    )
    received_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='branch_transfer_receipts', verbose_name=_('استلم بواسطة')
    )
    
    # التواريخ
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)
    received_at = models.DateTimeField(_('تاريخ الاستلام'), null=True, blank=True)
    
    # الملاحظات
    notes = models.TextField(_('ملاحظات'), blank=True)
    rejection_reason = models.TextField(_('سبب الرفض'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('تحويل بين الفروع')
        verbose_name_plural = _('تحويلات بين الفروع')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transfer_number']),
            models.Index(fields=['status']),
            models.Index(fields=['from_branch', 'to_branch']),
        ]
    
    def __str__(self):
        return f"{self.transfer_number}: {self.from_branch.code} → {self.to_branch.code}"
    
    def save(self, *args, **kwargs):
        if not self.transfer_number:
            ym = timezone.now().strftime('%Y%m')
            last = BranchTransfer.objects.filter(
                transfer_number__startswith=f'BT-{ym}-'
            ).order_by('id').last()
            seq = 1
            if last and last.transfer_number:
                try:
                    seq = int(last.transfer_number.split('-')[-1]) + 1
                except:
                    pass
            self.transfer_number = f'BT-{ym}-{seq:04d}'
        super().save(*args, **kwargs)
    
    @property
    def total_items(self):
        return self.items.count()
    
    @property
    def total_quantity(self):
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0
    
    def approve(self, user):
        """اعتماد التحويل"""
        if self.status != 'pending':
            return False
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
        return True
    
    def reject(self, user, reason=''):
        """رفض التحويل"""
        if self.status not in ('pending', 'draft'):
            return False
        self.status = 'rejected'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()
        return True
    
    def receive(self, user):
        """تأكيد استلام التحويل"""
        if self.status not in ('approved', 'in_transit'):
            return False
        self.status = 'received'
        self.received_by = user
        self.received_at = timezone.now()
        self.actual_arrival = timezone.now().date()
        self.save()
        self._process_stock_movement()
        return True
    
    def _process_stock_movement(self):
        """معالجة حركة المخزون عند الاستلام"""
        if not self.from_branch.location or not self.to_branch.location:
            return
        from inventory.models import Stock
        for item in self.items.all():
            # خصم من المخزن المصدر
            from_stock, _ = Stock.objects.get_or_create(
                product=item.product,
                location=self.from_branch.location
            )
            from_stock.quantity -= item.quantity
            from_stock.save()
            
            # إضافة للمخزن الوجهة
            to_stock, _ = Stock.objects.get_or_create(
                product=item.product,
                location=self.to_branch.location
            )
            to_stock.quantity += item.quantity
            to_stock.save()


class BranchTransferItem(models.Model):
    """
    بنود تحويل الفرع
    """
    transfer = models.ForeignKey(
        BranchTransfer, on_delete=models.CASCADE,
        related_name='items', verbose_name=_('التحويل')
    )
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.PROTECT,
        related_name='branch_transfer_items', verbose_name=_('المنتج')
    )
    quantity = models.PositiveIntegerField(_('الكمية'), validators=[MinValueValidator(1)])
    received_quantity = models.PositiveIntegerField(_('الكمية المستلمة'), default=0)
    unit_cost = models.DecimalField(_('تكلفة الوحدة'), max_digits=12, decimal_places=2, default=Decimal('0'))
    notes = models.CharField(_('ملاحظات'), max_length=255, blank=True)
    
    class Meta:
        verbose_name = _('بند تحويل')
        verbose_name_plural = _('بنود التحويل')
        unique_together = ['transfer', 'product']
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    @property
    def total_cost(self):
        return self.quantity * self.unit_cost


# ==================== نماذج المعارض المدمجة ====================

class POSDevice(models.Model):
    """
    أجهزة نقاط البيع
    """
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, 
        related_name='pos_devices', verbose_name=_('الفرع')
    )
    name = models.CharField(_('الاسم'), max_length=100)
    identifier = models.CharField(
        _('المعرف'), max_length=120, unique=True, 
        help_text=_('Serial / MAC / UUID')
    )
    api_key = models.CharField(_('مفتاح API'), max_length=64, unique=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    last_seen = models.DateTimeField(_('آخر ظهور'), null=True, blank=True)
    registered_at = models.DateTimeField(_('تاريخ التسجيل'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('جهاز نقطة بيع')
        verbose_name_plural = _('أجهزة نقاط البيع')
        indexes = [
            models.Index(fields=['branch', 'is_active']),
            models.Index(fields=['identifier']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.identifier})"


class DeviceAuthToken(models.Model):
    """
    توكنات مصادقة الأجهزة
    """
    device = models.ForeignKey(
        POSDevice, on_delete=models.CASCADE, 
        related_name='tokens', verbose_name=_('الجهاز')
    )
    token = models.CharField(_('التوكن'), max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(_('ينتهي في'), null=True, blank=True)
    revoked = models.BooleanField(_('ملغي'), default=False)
    
    class Meta:
        verbose_name = _('توكن جهاز')
        verbose_name_plural = _('توكنات الأجهزة')
    
    def is_valid(self):
        if self.revoked:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class BranchAttendance(models.Model):
    """
    سجل حضور موظفي الفرع
    """
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, 
        related_name='attendance_records', verbose_name=_('الفرع')
    )
    employee = models.ForeignKey(
        BranchStaff, on_delete=models.CASCADE, 
        related_name='attendance_records', verbose_name=_('الموظف')
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, 
        related_name='branch_attendance', verbose_name=_('المستخدم')
    )
    date = models.DateField(_('التاريخ'), default=timezone.localdate)
    in_time = models.DateTimeField(_('وقت الدخول'), null=True, blank=True)
    out_time = models.DateTimeField(_('وقت الخروج'), null=True, blank=True)
    device_identifier = models.CharField(_('معرف الجهاز'), max_length=120, blank=True)
    note = models.CharField(_('ملاحظة'), max_length=255, blank=True)
    created_at = models.DateTimeField(_('أُنشئ في'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('سجل حضور')
        verbose_name_plural = _('سجلات الحضور')
        unique_together = ('branch', 'employee', 'date')
        indexes = [
            models.Index(fields=['branch', 'date']),
            models.Index(fields=['employee', 'date']),
        ]
    
    def punch_in(self, device_id=None):
        if self.in_time:
            return False
        self.in_time = timezone.now()
        if device_id:
            self.device_identifier = device_id
        self.save()
        return True
    
    def punch_out(self):
        if self.out_time:
            return False
        self.out_time = timezone.now()
        self.save()
        return True
    
    @property
    def worked_seconds(self):
        if self.in_time and self.out_time:
            return int((self.out_time - self.in_time).total_seconds())
        return 0
    
    @property
    def worked_hours(self):
        return round(self.worked_seconds / 3600, 2)


class BranchExpense(models.Model):
    """
    مصروفات الفرع
    """
    class ExpenseType(models.TextChoices):
        SALARY = 'salary', _('رواتب')
        WAGES = 'wages', _('أجور')
        ELECTRICITY = 'electricity', _('كهرباء')
        WATER = 'water', _('مياه')
        RENT = 'rent', _('إيجار')
        OPERATING = 'operating', _('مشتريات تشغيل')
        ADVANCE = 'advance', _('سُلف')
        MAINTENANCE = 'maintenance', _('صيانة')
        MARKETING = 'marketing', _('تسويق')
        OTHER = 'other', _('أخرى')
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('مسودة')
        SUBMITTED = 'submitted', _('قيد الموافقة')
        APPROVED = 'approved', _('معتمد')
        REJECTED = 'rejected', _('مرفوض')
        PAID = 'paid', _('مدفوع')
    
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, 
        related_name='expenses', verbose_name=_('الفرع')
    )
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    category = models.CharField(
        _('نوع المصروف'), max_length=40, 
        choices=ExpenseType.choices, default=ExpenseType.OTHER
    )
    description = models.TextField(_('الوصف'), blank=True)
    date = models.DateField(_('التاريخ'), default=timezone.localdate)
    status = models.CharField(
        _('الحالة'), max_length=20, 
        choices=Status.choices, default=Status.DRAFT
    )
    requires_approval = models.BooleanField(_('يحتاج موافقة'), default=False)
    attachment = models.FileField(
        _('مرفق/إيصال'), 
        upload_to='branches/expenses/', 
        null=True, blank=True
    )
    
    # المسؤولين
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, 
        related_name='branch_expenses_created', verbose_name=_('أنشئ بواسطة')
    )
    approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, 
        related_name='branch_expenses_approved', verbose_name=_('اعتمد بواسطة')
    )
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)
    rejection_note = models.CharField(_('سبب الرفض'), max_length=255, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('مصروف فرع')
        verbose_name_plural = _('مصروفات الفروع')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['branch', 'status']),
            models.Index(fields=['category']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.branch.code} - {self.get_category_display()} - {self.amount}"
    
    def save(self, *args, **kwargs):
        # تحديد حاجة الموافقة
        limit = self.branch.expense_approval_limit or Decimal('0')
        if self.branch.require_expense_approval and self.amount > limit:
            self.requires_approval = True
            if self.status == self.Status.DRAFT:
                self.status = self.Status.SUBMITTED
        super().save(*args, **kwargs)
    
    def approve(self, user):
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
    
    def reject(self, user, reason=''):
        self.status = self.Status.REJECTED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.rejection_note = reason
        self.save()


class BranchPurchase(models.Model):
    """
    مشتريات مباشرة للفرع
    """
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('confirmed', _('مؤكد')),
        ('cancelled', _('ملغى')),
    ]
    
    number = models.CharField(_('رقم المستند'), max_length=40, unique=True, blank=True)
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, 
        related_name='direct_purchases', verbose_name=_('الفرع')
    )
    supplier = models.ForeignKey(
        'partners.Supplier', on_delete=models.PROTECT, 
        related_name='branch_purchases', verbose_name=_('المورد')
    )
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='draft')
    date = models.DateField(_('التاريخ'), default=timezone.localdate)
    notes = models.TextField(_('ملاحظات'), blank=True)
    invoice_file = models.FileField(
        _('فاتورة/مرفق'), 
        upload_to='branches/purchases/', 
        null=True, blank=True
    )
    total = models.DecimalField(_('الإجمالي'), max_digits=12, decimal_places=2, default=Decimal('0'))
    
    # المسؤولين
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, 
        related_name='branch_purchases_created', verbose_name=_('أنشئ بواسطة')
    )
    confirmed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, 
        related_name='branch_purchases_confirmed', verbose_name=_('أكد بواسطة')
    )
    confirmed_at = models.DateTimeField(_('تاريخ التأكيد'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('شراء مباشر للفرع')
        verbose_name_plural = _('مشتريات مباشرة للفروع')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['branch', 'status']),
            models.Index(fields=['number']),
        ]
    
    def __str__(self):
        return self.number or f"BP-{self.pk or ''}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            ym = timezone.now().strftime('%Y%m')
            last = BranchPurchase.objects.filter(
                number__startswith=f'BP-{ym}-'
            ).order_by('id').last()
            seq = 1
            if last and last.number:
                try:
                    seq = int(last.number.split('-')[-1]) + 1
                except:
                    pass
            self.number = f'BP-{ym}-{seq:04d}'
        super().save(*args, **kwargs)
    
    def recalc_total(self):
        agg = self.items.aggregate(
            total=Sum(F('quantity') * F('cost'))
        )
        self.total = agg['total'] or Decimal('0')
        self.save(update_fields=['total'])
        return self.total
    
    def confirm(self, user=None):
        if self.status != 'draft':
            return False
        if not self.branch.location:
            return False
        
        from inventory.models import Stock
        self.recalc_total()
        
        with transaction.atomic():
            for item in self.items.select_related('product'):
                stock, _ = Stock.objects.get_or_create(
                    product=item.product, 
                    location=self.branch.location
                )
                stock.quantity += item.quantity
                stock.save()
                
                # تسجيل حركة المخزون
                BranchStockMovement.objects.create(
                    branch=self.branch,
                    product=item.product,
                    quantity=item.quantity,
                    movement_type=BranchStockMovement.MovementType.PURCHASE_IN,
                    reference=self.number,
                    created_by=user,
                )
            
            self.status = 'confirmed'
            self.confirmed_by = user
            self.confirmed_at = timezone.now()
            self.save()
        
        return True


class BranchPurchaseItem(models.Model):
    """
    بنود شراء الفرع
    """
    purchase = models.ForeignKey(
        BranchPurchase, on_delete=models.CASCADE, 
        related_name='items', verbose_name=_('المستند')
    )
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.PROTECT, 
        verbose_name=_('المنتج')
    )
    quantity = models.PositiveIntegerField(_('الكمية'))
    cost = models.DecimalField(_('التكلفة'), max_digits=12, decimal_places=2)
    
    class Meta:
        verbose_name = _('بند شراء فرع')
        verbose_name_plural = _('بنود شراء الفرع')
        constraints = [
            models.CheckConstraint(
                check=Q(quantity__gt=0), 
                name='branch_purchase_qty_positive'
            )
        ]
    
    @property
    def total(self):
        return (self.quantity or 0) * (self.cost or Decimal('0'))
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.purchase.recalc_total()


class BranchStockMovement(models.Model):
    """
    حركات مخزون الفرع
    """
    class MovementType(models.TextChoices):
        PURCHASE_IN = 'purchase_in', _('شراء مباشر')
        TRANSFER_IN = 'transfer_in', _('تحويل وارد')
        TRANSFER_OUT = 'transfer_out', _('تحويل صادر')
        ADJUSTMENT = 'adjustment', _('تسوية مخزون')
        SALE = 'sale', _('بيع')
        RETURN_IN = 'return_in', _('مرتجع')
        EXPENSE_CONSUME = 'expense_consume', _('صرف مصروف')
    
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, 
        related_name='stock_movements', verbose_name=_('الفرع')
    )
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.PROTECT, 
        related_name='branch_stock_movements', verbose_name=_('المنتج')
    )
    quantity = models.IntegerField(_('الكمية (+/-)'))
    movement_type = models.CharField(
        _('نوع الحركة'), max_length=30, 
        choices=MovementType.choices
    )
    reference = models.CharField(_('مرجع'), max_length=100, blank=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, 
        related_name='branch_movements_created', verbose_name=_('أنشئ بواسطة')
    )
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    note = models.CharField(_('ملاحظة'), max_length=255, blank=True)
    
    class Meta:
        verbose_name = _('حركة مخزون فرع')
        verbose_name_plural = _('حركات مخزون الفروع')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['branch', 'movement_type']),
            models.Index(fields=['product']),
        ]
    
    def __str__(self):
        return f"{self.branch.code} {self.get_movement_type_display()} {self.product.name} ({self.quantity})"


class BranchPayroll(models.Model):
    """
    رواتب موظفي الفرع
    """
    class EntryType(models.TextChoices):
        SALARY = 'salary', _('راتب')
        BONUS = 'bonus', _('مكافأة')
        COMMISSION = 'commission', _('عمولة')
        DEDUCTION = 'deduction', _('خصم')
        ADVANCE = 'advance', _('سلفة')
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('قيد المراجعة')
        APPROVED = 'approved', _('معتمد')
        PAID = 'paid', _('مدفوع')
    
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, 
        related_name='payroll_entries', verbose_name=_('الفرع')
    )
    employee = models.ForeignKey(
        BranchStaff, null=True, blank=True, on_delete=models.SET_NULL, 
        related_name='payroll_entries', verbose_name=_('موظف الفرع')
    )
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, 
        related_name='branch_payroll_entries', verbose_name=_('المستخدم')
    )
    period = models.DateField(_('الشهر'), help_text=_('أول يوم في الشهر'))
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    entry_type = models.CharField(
        _('النوع'), max_length=20, 
        choices=EntryType.choices, default=EntryType.SALARY
    )
    status = models.CharField(
        _('الحالة'), max_length=20, 
        choices=Status.choices, default=Status.PENDING
    )
    note = models.CharField(_('ملاحظة'), max_length=255, blank=True)
    
    approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, 
        related_name='branch_payroll_approved', verbose_name=_('اعتمد بواسطة')
    )
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('قيد رواتب فرع')
        verbose_name_plural = _('قيود رواتب الفروع')
        ordering = ['-period']
        indexes = [
            models.Index(fields=['branch', 'period']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.branch.code} {self.get_entry_type_display()} {self.period}"
    
    def approve(self, user):
        if self.status == self.Status.PAID:
            return False
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
        return True


class BranchShift(models.Model):
    """
    ورديات/شفتات الفرع
    """
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, 
        related_name='shifts', verbose_name=_('الفرع')
    )
    name = models.CharField(_('اسم الوردية'), max_length=80)
    start_time = models.TimeField(_('بداية الوردية'))
    end_time = models.TimeField(_('نهاية الوردية'))
    break_minutes = models.PositiveIntegerField(_('دقائق الراحة'), default=0)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('وردية فرع')
        verbose_name_plural = _('ورديات الفروع')
        ordering = ['branch', 'start_time']
        indexes = [
            models.Index(fields=['branch', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.branch.code} - {self.name}"


class BranchShiftAssignment(models.Model):
    """
    تعيين موظف لوردية
    """
    WEEKDAY_CHOICES = [
        (0, _('الاثنين')),
        (1, _('الثلاثاء')),
        (2, _('الأربعاء')),
        (3, _('الخميس')),
        (4, _('الجمعة')),
        (5, _('السبت')),
        (6, _('الأحد')),
    ]
    
    shift = models.ForeignKey(
        BranchShift, on_delete=models.CASCADE, 
        related_name='assignments', verbose_name=_('الوردية')
    )
    employee = models.ForeignKey(
        BranchStaff, on_delete=models.CASCADE, 
        related_name='shift_assignments', verbose_name=_('الموظف')
    )
    day_of_week = models.PositiveSmallIntegerField(_('اليوم'), choices=WEEKDAY_CHOICES)
    note = models.CharField(_('ملاحظة'), max_length=200, blank=True)
    active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('تعيين وردية')
        verbose_name_plural = _('تعيينات الورديات')
        unique_together = ('shift', 'employee', 'day_of_week')
        indexes = [
            models.Index(fields=['employee', 'active']),
            models.Index(fields=['shift', 'day_of_week']),
        ]
    
    def __str__(self):
        return f"{self.employee.user.username} -> {self.shift.name} ({self.get_day_of_week_display()})"


# ==================== استيراد موديلات التوزيع ====================
# هذه الموديلات موجودة في ملف distribution.py للتنظيم
# يتم استيرادها هنا لضمان تسجيلها في Django

try:
    from .distribution import (
        ShowroomReplenishmentRequest, 
        ReplenishmentRequestItem, 
        BranchStockSettings, 
        AutoReplenishmentRule
    )
except ImportError:
    # الملف لم يُنشأ بعد أو هناك مشكلة في الاستيراد
    pass
