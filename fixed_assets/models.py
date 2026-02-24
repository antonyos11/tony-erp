from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from core.sequence_utils import next_sequence, format_code


class AssetCategory(models.Model):
    """تصنيفات الأصول الثابتة"""
    
    name = models.CharField(_('الاسم'), max_length=200, unique=True)
    code = models.CharField(_('الكود'), max_length=50, unique=True)
    description = models.TextField(_('الوصف'), blank=True)
    
    # Default depreciation settings
    default_depreciation_method = models.CharField(
        _('طريقة الاستهلاك الافتراضية'),
        max_length=20,
        choices=[
            ('straight_line', _('القسط الثابت')),
            ('declining_balance', _('القسط المتناقص')),
            ('units_of_production', _('وحدات الإنتاج')),
        ],
        default='straight_line'
    )
    default_useful_life_years = models.PositiveIntegerField(
        _('العمر الافتراضي (سنوات)'),
        default=5
    )
    default_salvage_value_percent = models.DecimalField(
        _('قيمة الخردة (%)'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00')
    )
    
    # Accounting
    asset_account = models.ForeignKey(
        'accounting.Account',
        on_delete=models.PROTECT,
        related_name='asset_categories',
        verbose_name=_('حساب الأصل'),
        null=True,
        blank=True
    )
    accumulated_depreciation_account = models.ForeignKey(
        'accounting.Account',
        on_delete=models.PROTECT,
        related_name='depreciation_categories',
        verbose_name=_('حساب مجمع الاستهلاك'),
        null=True,
        blank=True
    )
    depreciation_expense_account = models.ForeignKey(
        'accounting.Account',
        on_delete=models.PROTECT,
        related_name='depreciation_expense_categories',
        verbose_name=_('حساب مصروف الاستهلاك'),
        null=True,
        blank=True
    )
    
    is_active = models.BooleanField(_('نشط'), default=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('تصنيف أصل')
        verbose_name_plural = _('تصنيفات الأصول')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Asset(models.Model):
    """الأصول الثابتة"""
    
    STATUS_CHOICES = [
        ('active', _('نشط/قيد التشغيل')),
        ('under_maintenance', _('تحت الصيانة')),
        ('idle', _('متوقف')),
        ('disposed', _('مُتخلَّص منه')),
        ('sold', _('مُباع')),
    ]
    
    DEPRECIATION_METHOD_CHOICES = [
        ('straight_line', _('القسط الثابت')),
        ('declining_balance', _('القسط المتناقص')),
        ('units_of_production', _('وحدات الإنتاج')),
        ('manual', _('يدوي')),
    ]
    
    # Basic Info
    number = models.CharField(_('رقم الأصل'), max_length=50, unique=True)
    name = models.CharField(_('الاسم'), max_length=200)
    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.PROTECT,
        related_name='assets',
        verbose_name=_('التصنيف')
    )
    
    description = models.TextField(_('الوصف'), blank=True)
    serial_number = models.CharField(_('الرقم التسلسلي'), max_length=200, blank=True)
    manufacturer = models.CharField(_('الشركة المصنعة'), max_length=200, blank=True)
    model = models.CharField(_('الموديل/الطراز'), max_length=200, blank=True)
    
    # Location & Assignment
    location = models.CharField(_('الموقع'), max_length=200, blank=True)
    department = models.CharField(_('القسم'), max_length=200, blank=True)
    assigned_to = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_assets',
        verbose_name=_('مُسند إلى')
    )
    
    # Financial Info
    acquisition_date = models.DateField(_('تاريخ الشراء/الاستحواذ'))
    acquisition_cost = models.DecimalField(
        _('تكلفة الاستحواذ'),
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Depreciation Settings
    depreciation_method = models.CharField(
        _('طريقة الاستهلاك'),
        max_length=20,
        choices=DEPRECIATION_METHOD_CHOICES,
        default='straight_line'
    )
    useful_life_years = models.PositiveIntegerField(_('العمر الافتراضي (سنوات)'), default=5)
    useful_life_units = models.PositiveIntegerField(
        _('العمر الافتراضي (وحدات)'),
        null=True,
        blank=True,
        help_text=_('للاستهلاك بوحدات الإنتاج')
    )
    salvage_value = models.DecimalField(
        _('قيمة الخردة'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    depreciation_start_date = models.DateField(
        _('تاريخ بدء الاستهلاك'),
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Disposal Info
    disposal_date = models.DateField(_('تاريخ الاستبعاد'), null=True, blank=True)
    disposal_value = models.DecimalField(
        _('قيمة الاستبعاد'),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    disposal_notes = models.TextField(_('ملاحظات الاستبعاد'), blank=True)
    
    # Maintenance
    warranty_expiry_date = models.DateField(_('تاريخ انتهاء الضمان'), null=True, blank=True)
    last_maintenance_date = models.DateField(_('آخر صيانة'), null=True, blank=True)
    next_maintenance_date = models.DateField(_('الصيانة القادمة'), null=True, blank=True)
    
    # Accounting
    purchase_invoice = models.ForeignKey(
        'purchases.PurchaseBill',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fixed_assets',
        verbose_name=_('فاتورة الشراء')
    )
    
    # Images & Documents
    image = models.ImageField(_('صورة'), upload_to='assets/', null=True, blank=True)
    documents = models.FileField(_('مستندات'), upload_to='assets/docs/', null=True, blank=True)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_assets',
        verbose_name=_('أنشئ بواسطة')
    )
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('أصل ثابت')
        verbose_name_plural = _('الأصول الثابتة')
        ordering = ['-acquisition_date', 'number']
        indexes = [
            models.Index(fields=['status', 'category']),
            models.Index(fields=['acquisition_date']),
            models.Index(fields=['location', 'status']),
            models.Index(fields=['department']),
        ]
    
    def __str__(self):
        return f"{self.number} - {self.name}"

    def clean(self):
        """تحققات أساسية على بيانات الأصل الثابت."""
        errors = {}

        if self.acquisition_cost is not None and self.acquisition_cost <= Decimal('0'):
            errors['acquisition_cost'] = _('تكلفة الاستحواذ يجب أن تكون أكبر من صفر.')

        if (
            self.salvage_value is not None
            and self.acquisition_cost is not None
            and self.salvage_value >= self.acquisition_cost
        ):
            errors['salvage_value'] = _('قيمة الخردة يجب أن تكون أقل من تكلفة الاستحواذ.')

        if self.useful_life_years is not None and self.useful_life_years <= 0:
            errors['useful_life_years'] = _('العمر الافتراضي (سنوات) يجب أن يكون أكبر من صفر.')

        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        if not self.number:
            seq = next_sequence('FIXED_ASSET')
            self.number = format_code('FA', seq)
        
        # Set depreciation start date if not set
        if not self.depreciation_start_date:
            self.depreciation_start_date = self.acquisition_date
        
        super().save(*args, **kwargs)
    
    @property
    def depreciable_amount(self):
        """المبلغ القابل للاستهلاك"""
        return self.acquisition_cost - self.salvage_value
    
    @property
    def current_book_value(self):
        """القيمة الدفترية الحالية"""
        total_depreciation = self.depreciation_entries.filter(
            status='posted'
        ).aggregate(
            total=models.Sum('depreciation_amount')
        )['total'] or Decimal('0')
        
        return self.acquisition_cost - total_depreciation
    
    @property
    def accumulated_depreciation(self):
        """مجمع الاستهلاك"""
        return self.depreciation_entries.filter(
            status='posted'
        ).aggregate(
            total=models.Sum('depreciation_amount')
        )['total'] or Decimal('0')
    
    @property
    def depreciation_rate_yearly(self):
        """معدل الاستهلاك السنوي"""
        if self.useful_life_years > 0:
            return Decimal('100') / Decimal(self.useful_life_years)
        return Decimal('0')
    
    @property
    def is_fully_depreciated(self):
        """هل تم استهلاك الأصل بالكامل؟"""
        return self.current_book_value <= self.salvage_value
    
    @property
    def depreciation_percent(self):
        """نسبة الإهلاك المئوية"""
        if self.acquisition_cost > 0:
            return (self.accumulated_depreciation / self.acquisition_cost) * Decimal('100')
        return Decimal('0')
    
    def calculate_monthly_depreciation(self, date=None):
        """حساب الاستهلاك الشهري"""
        if self.depreciation_method == 'straight_line':
            return self.depreciable_amount / (self.useful_life_years * 12)
        
        elif self.depreciation_method == 'declining_balance':
            # Double declining balance
            rate = (Decimal('2') / Decimal(self.useful_life_years)) / 12
            return self.current_book_value * rate
        
        elif self.depreciation_method == 'manual':
            return Decimal('0')
        
        else:
            return Decimal('0')


class DepreciationSchedule(models.Model):
    """جدول الاستهلاك"""
    
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='depreciation_entries',
        verbose_name=_('الأصل')
    )
    
    period_start = models.DateField(_('بداية الفترة'))
    period_end = models.DateField(_('نهاية الفترة'))
    
    depreciation_amount = models.DecimalField(
        _('مبلغ الاستهلاك'),
        max_digits=15,
        decimal_places=2
    )
    
    accumulated_depreciation = models.DecimalField(
        _('مجمع الاستهلاك'),
        max_digits=15,
        decimal_places=2
    )
    
    book_value = models.DecimalField(
        _('القيمة الدفترية'),
        max_digits=15,
        decimal_places=2
    )
    
    status = models.CharField(
        _('الحالة'),
        max_length=20,
        choices=[
            ('scheduled', _('مُجدول')),
            ('posted', _('مُرحّل')),
            ('cancelled', _('ملغى')),
        ],
        default='scheduled'
    )
    
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='depreciation_entries',
        verbose_name=_('القيد المحاسبي')
    )
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    posted_at = models.DateTimeField(_('تاريخ الترحيل'), null=True, blank=True)
    posted_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('رُحّل بواسطة')
    )
    
    class Meta:
        verbose_name = _('قسط استهلاك')
        verbose_name_plural = _('جدول الاستهلاك')
        ordering = ['asset', 'period_start']
        unique_together = [['asset', 'period_start']]
        indexes = [
            models.Index(fields=['period_start']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.asset.number} - {self.period_start} to {self.period_end}"
    
    def post_depreciation(self, user=None):
        """ترحيل قيد الاستهلاك"""
        if self.status == 'posted':
            return self.journal_entry
        
        from accounting.models import JournalEntry, JournalEntryItem, Account
        
        # Create journal entry
        je = JournalEntry.objects.create(
            entry_type='depreciation',
            date=self.period_end,
            description=f'استهلاك {self.asset.number} - {self.asset.name} للفترة {self.period_start} إلى {self.period_end}',
            notes=self.notes
        )
        
        # Debit: Depreciation Expense
        if self.asset.category.depreciation_expense_account:
            JournalEntryItem.objects.create(
                journal_entry=je,
                account=self.asset.category.depreciation_expense_account,
                type='debit',
                amount=self.depreciation_amount,
                description=f'مصروف استهلاك {self.asset.number}'
            )
        
        # Credit: Accumulated Depreciation
        if self.asset.category.accumulated_depreciation_account:
            JournalEntryItem.objects.create(
                journal_entry=je,
                account=self.asset.category.accumulated_depreciation_account,
                type='credit',
                amount=self.depreciation_amount,
                description=f'مجمع استهلاك {self.asset.number}'
            )
        
        # Post journal entry
        if je.debit_total == je.credit_total:
            je.is_posted = True
            je.posted_by = user
            je.posted_at = timezone.now()
            je.save()
            
            self.status = 'posted'
            self.journal_entry = je
            self.posted_at = timezone.now()
            self.posted_by = user
            self.save()
        
        return je


class AssetMaintenance(models.Model):
    """سجل صيانة الأصول"""
    
    MAINTENANCE_TYPE_CHOICES = [
        ('preventive', _('وقائية')),
        ('corrective', _('تصحيحية')),
        ('emergency', _('طارئة')),
        ('upgrade', _('ترقية/تحسين')),
    ]
    
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='maintenance_records',
        verbose_name=_('الأصل')
    )
    
    maintenance_type = models.CharField(
        _('نوع الصيانة'),
        max_length=20,
        choices=MAINTENANCE_TYPE_CHOICES
    )
    
    date = models.DateField(_('التاريخ'), default=timezone.localdate)
    description = models.TextField(_('الوصف'))
    
    performed_by = models.CharField(_('نُفذت بواسطة'), max_length=200, blank=True)
    vendor = models.ForeignKey(
        'partners.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asset_maintenance',
        verbose_name=_('المقاول/المورد')
    )
    
    cost = models.DecimalField(
        _('التكلفة'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    downtime_hours = models.DecimalField(
        _('ساعات التوقف'),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('أنشئ بواسطة')
    )
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('صيانة أصل')
        verbose_name_plural = _('صيانة الأصول')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['asset', '-date']),
        ]
    
    def __str__(self):
        return f"{self.asset.number} - {self.get_maintenance_type_display()} - {self.date}"


class AssetTransfer(models.Model):
    """نقل/تحويل أصل"""
    
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='transfers',
        verbose_name=_('الأصل')
    )
    
    transfer_date = models.DateField(_('تاريخ النقل'), default=timezone.localdate)
    
    from_location = models.CharField(_('من موقع'), max_length=200)
    to_location = models.CharField(_('إلى موقع'), max_length=200)
    
    from_department = models.CharField(_('من قسم'), max_length=200, blank=True)
    to_department = models.CharField(_('إلى قسم'), max_length=200, blank=True)
    
    from_user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferred_from_assets',
        verbose_name=_('من مستخدم')
    )
    to_user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferred_to_assets',
        verbose_name=_('إلى مستخدم')
    )
    
    reason = models.TextField(_('السبب'))
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    approved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_asset_transfers',
        verbose_name=_('اعتمد بواسطة')
    )
    
    transferred_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executed_asset_transfers',
        verbose_name=_('نُفذ بواسطة')
    )
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('نقل أصل')
        verbose_name_plural = _('نقل الأصول')
        ordering = ['-transfer_date']
    
    def __str__(self):
        return f"{self.asset.number} - {self.from_location} → {self.to_location}"
