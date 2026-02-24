from django.db import models
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import transaction


class AccountType(models.TextChoices):
    """أنواع الحسابات المحاسبية"""
    ASSET = 'asset', _('الأصول')
    LIABILITY = 'liability', _('الالتزامات (الخصوم)')
    EQUITY = 'equity', _('حقوق الملكية')
    REVENUE = 'revenue', _('الإيرادات')
    EXPENSE = 'expense', _('المصروفات')


class CostCenterQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def with_expenses(self):
        """ضم حقل expenses_total بحساب واحد بدل حلقة لكل مركز."""
        from django.db.models import Sum, Q
        return self.annotate(
            expenses_total=Sum(
                'journalentryitem__amount',  # العلاقة العكسية الافتراضية
                filter=Q(
                    journalentryitem__journal_entry__is_posted=True,
                    journalentryitem__type='debit',
                    journalentryitem__account__account_type='expense'
                )
            )
        )


class CostCenterManager(models.Manager):
    def get_queryset(self):  # type: ignore[override]
        return CostCenterQuerySet(self.model, using=self._db).select_related('manager', 'parent')

    def active(self):
        return self.get_queryset().active()

    def with_expenses(self):
        return self.get_queryset().with_expenses()


class CostCenter(models.Model):
    """مراكز التكلفة (محسّنة للأداء)."""

    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    code = models.CharField(_('كود المركز'), max_length=20, unique=True)
    name = models.CharField(_('اسم مركز التكلفة'), max_length=200)
    description = models.TextField(_('الوصف'), blank=True)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL,
                                null=True, blank=True,
                                verbose_name=_('مدير المركز'))
    parent = models.ForeignKey('self', on_delete=models.CASCADE,
                               null=True, blank=True,
                               verbose_name=_('المركز الرئيسي'),
                               related_name='children')
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CostCenterManager()

    class Meta:
        verbose_name = _('مركز تكلفة')
        verbose_name_plural = _('مراكز التكلفة')
        ordering = ['code']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['parent']),
            models.Index(fields=['manager']),
        ]

    def __str__(self):  # pragma: no cover
        return f"{self.code} - {self.name}"

    @property
    def total_expenses(self):
        """إجمالي مصروفات المركز مع كاش قصير الأجل لتقليل الاستعلامات.

        يُفرَّغ الكاش عند حفظ/حذف بند قيد له cost_center (سنضيف في signal لاحقاً).
        """
        cache_key = f"cc:totexp:{self.pk}"
        val = cache.get(cache_key)
        if val is not None:
            return val
        from django.db.models import Sum
        total = (
            JournalEntryItem.objects.filter(
                cost_center=self,
                journal_entry__is_posted=True,
                type='debit',
                account__account_type='expense'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        )
        cache.set(cache_key, total, 60)  # دقيقة واحدة كافٍ للتقارير اللحظية
        return total


class Account(models.Model):
    """شجرة الحسابات"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    code = models.CharField(max_length=20, unique=True, verbose_name=_("رمز الحساب"))
    name = models.CharField(max_length=255, verbose_name=_("اسم الحساب"))
    account_type = models.CharField(max_length=20, choices=AccountType.choices, verbose_name=_("نوع الحساب"))
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                             related_name='children', verbose_name=_("الحساب الرئيسي"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    can_post = models.BooleanField(_('يقبل القيد'), default=True, 
                                  help_text=_('إذا كان false، لا يمكن إنشاء قيود على هذا الحساب مباشرة'))
    requires_cost_center = models.BooleanField(_('يتطلب مركز تكلفة'), default=False)
    default_cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL,
                                          null=True, blank=True,
                                          verbose_name=_('مركز التكلفة الافتراضي'))
    credit_limit = models.DecimalField(_('الحد الائتماني'), max_digits=15, decimal_places=2,
                                     default=Decimal('0'), 
                                     validators=[MinValueValidator(Decimal('0'))])
    # الحقول التنظيمية الجديدة
    level = models.PositiveIntegerField(_('المستوى'), default=0, editable=False)
    path = models.CharField(_('المسار'), max_length=255, blank=True, editable=False, db_index=True)
    is_group = models.BooleanField(_('حساب تجميعي'), default=False,
                                   help_text=_('إذا كان True لا يقبل قيد مباشر (سيتم ضبط can_post تلقائياً)'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("حساب")
        verbose_name_plural = _("الحسابات")
        ordering = ['code']
        indexes = [
            models.Index(fields=['account_type']),
            models.Index(fields=['parent']),
            models.Index(fields=['is_active']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['parent', 'name'], name='uniq_account_parent_name')
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def balance(self):
        """حساب رصيد الحساب باستعلام واحد (تحسين أداء)."""
        from django.db.models import Sum, Q
        agg = self.journal_entries.aggregate(  # type: ignore[attr-defined]
            debits=Sum('amount', filter=Q(type='debit')),
            credits=Sum('amount', filter=Q(type='credit')),
        )
        debits = agg['debits'] or Decimal('0')
        credits = agg['credits'] or Decimal('0')
        return debits - credits if self.account_type in ['asset', 'expense'] else credits - debits
    
    @property
    def full_name(self):
        """الاسم الكامل بما في ذلك الحساب الرئيسي"""
        if self.parent:
            return f"{self.parent.name} - {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        # حساب المستوى والمسار
        if self.parent:
            self.level = (self.parent.level or 0) + 1
            parent_path = self.parent.path or self.parent.code
            self.path = f"{parent_path}/{self.code}"
        else:
            self.level = 0
            self.path = self.code
        # ضبط can_post إذا كان حساباً تجميعياً
        if self.is_group and self.can_post:
            self.can_post = False
        # منع جعل حساب له أبناء قابلاً للقيد
        # children علاقة عكسية للحسابات الفرعية
        if self.pk and self.can_post and self.children.exists():  # type: ignore[attr-defined]
            self.can_post = False
        super().save(*args, **kwargs)

    def aggregate_balance(self):
        """رصيد الحساب شاملاً جميع الحسابات الفرعية."""
        from django.db.models import Sum, Q
        from .services import get_account_balance_cached  # للاستفادة من الكاش الفردي
        # إذا كان الحساب ورقة (ليس مجموعة) نستفيد من الكاش المباشر
        if not self.is_group and self.can_post:
            return get_account_balance_cached(self.id)  # type: ignore[attr-defined]
        subtree_ids = Account.objects.filter(path__startswith=self.path).values_list('id', flat=True)
        items = JournalEntryItem.objects.filter(account_id__in=subtree_ids, journal_entry__is_posted=True)
        agg = items.aggregate(
            debits=Sum('amount', filter=Q(type='debit')),
            credits=Sum('amount', filter=Q(type='credit'))
        )
        debits = agg['debits'] or Decimal('0')
        credits = agg['credits'] or Decimal('0')
        return debits - credits if self.account_type in ['asset', 'expense'] else credits - debits

class AccountQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)
    def with_parent(self):
        return self.select_related('parent')
    def of_type(self, t):
        return self.filter(account_type=t)
    def groups(self):
        return self.filter(is_group=True)
    def leafs(self):
        return self.filter(is_group=False, can_post=True)

class AccountManager(models.Manager):
    def get_queryset(self):
        return AccountQuerySet(self.model, using=self._db).select_related('parent')
    def active(self):
        return self.get_queryset().active()
    def build_tree(self):
        """إرجاع شجرة الحسابات (قائمة من العقد)"""
        nodes = {}
        result = []
        for acc in self.get_queryset().order_by('path'):
            node = {
                'id': acc.id,
                'code': acc.code,
                'name': acc.name,
                'level': acc.level,
                'is_group': acc.is_group,
                'can_post': acc.can_post,
                'account_type': acc.account_type,
                'children': []
            }
            nodes[acc.id] = node
            if acc.parent_id and acc.parent_id in nodes:
                nodes[acc.parent_id]['children'].append(node)
            else:
                result.append(node)
        return result

# ربط المدير المخصص
Account.add_to_class('objects', AccountManager())


class JournalEntry(models.Model):
    """القيود المحاسبية"""
    ENTRY_TYPE = [
        ('manual', _('قيد يدوي')),
        ('sales', _('من المبيعات')),
        ('purchase', _('من المشتريات')),
        ('payment', _('دفعة')),
        ('receipt', _('إيصال')),
        ('adjustment', _('قيد تسوية')),
        ('salary', _('من الرواتب')),
        ('inventory', _('من المخزون')),
        ('pos', _('من نقاط البيع')),
        ('depreciation', _('قيد إهلاك')),
        ('closing', _('قيد إقفال')),
        ('revenue', _('قيد إيراد')),
        ('expense', _('قيد مصروف')),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking

    number = models.CharField(max_length=50, unique=True, verbose_name=_("رقم القيد"))
    date = models.DateField(default=timezone.localdate, verbose_name=_("التاريخ"))
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE, default='manual', verbose_name=_("نوع القيد"))
    description = models.TextField(verbose_name=_("البيان"))
    reference = models.CharField(max_length=100, blank=True, verbose_name=_("المرجع"))
    
    # ربط مع الفواتير والأنظمة الأخرى
    invoice = models.ForeignKey('sales.Invoice', on_delete=models.SET_NULL, null=True, blank=True)
    purchase_bill = models.ForeignKey('purchases.PurchaseBill', on_delete=models.SET_NULL, null=True, blank=True)
    # الروابط الجديدة (اختيارية - تفعل عند توفر الأنظمة)
    # salary_payment = models.ForeignKey('hr.SalaryPayment', on_delete=models.SET_NULL, 
    #                                   null=True, blank=True,
    #                                   verbose_name=_('دفعة راتب'))
    # inventory_transaction = models.ForeignKey('inventory.Transaction', on_delete=models.SET_NULL,
    #                                          null=True, blank=True,
    #                                          verbose_name=_('حركة مخزون'))
    # pos_transaction = models.ForeignKey('pos.Transaction', on_delete=models.SET_NULL,
    #                                    null=True, blank=True,
    #                                    verbose_name=_('عملية نقطة بيع'))
    auto_generated = models.BooleanField(default=False, verbose_name=_('مولد تلقائياً'))
    reversal_of = models.ForeignKey('self', on_delete=models.SET_NULL, 
                                   null=True, blank=True,
                                   related_name='reversals',
                                   verbose_name=_('عكس قيد'))
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("أنشئ بواسطة"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_posted = models.BooleanField(default=False, verbose_name=_("مرحل"))
    showroom = models.ForeignKey('showrooms.Showroom', on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries', verbose_name=_('المعرض'), help_text=_('ربط القيد بمعرض محدد لاحتساب أرباح/خسائر الفروع'))

    class Meta:
        verbose_name = _("قيد محاسبي")
        verbose_name_plural = _("القيود المحاسبية")
        ordering = ['-date', '-number']
        indexes = [
            models.Index(fields=['is_posted']),
            models.Index(fields=['date']),
            models.Index(fields=['entry_type']),
            models.Index(fields=['date','is_posted'], name='je_date_posted_idx'),
            models.Index(fields=['auto_generated']),
        ]
        permissions = [
            ("view_journal_reports", "Can view accounting analytical reports"),
            ("post_journal_entry", "Can post journal entries"),
            ("unpost_journal_entry", "Can unpost (reverse) journal entries"),
            ("create_journal_entry", "Can create manual journal entries"),
        ]

    def __str__(self):
        return f"{self.number} - {self.description[:50]}"
    
    @property
    def total_debit(self):
        """إجمالي المدين"""
        if not getattr(self, 'pk', None):
            return Decimal('0')
        # items علاقة عكسية من JournalEntryItem
        return self.items.filter(type='debit').aggregate(  # type: ignore[attr-defined]
            total=models.Sum('amount'))['total'] or Decimal('0')
    
    @property
    def total_credit(self):
        """إجمالي الدائن"""
        if not getattr(self, 'pk', None):
            return Decimal('0')
        # type: ignore[attr-defined]
        return self.items.filter(type='credit').aggregate(  # type: ignore[attr-defined]
            total=models.Sum('amount'))['total'] or Decimal('0')
    
    @property
    def is_balanced(self):
        """هل القيد متوازن"""
        return self.total_debit == self.total_credit
    
    def save(self, *args, **kwargs):
        # منع إنشاء أو تعديل قيد مرحل غير متوازن
        is_new = self.pk is None
        if not self.number:
            # PHASE-1 STEP-1: replaced COUNT()+1 with sequence-backed generator
            # to eliminate duplicate number collisions under concurrent load.
            from accounting.journal_number_service import generate_journal_number
            self.number = generate_journal_number()
        # تحقق من السنة المالية فقط عند محاولة ترحيل القيد
        if self.is_posted:
            try:
                self.full_clean(validate_unique=False)
            except ValidationError:
                raise
        # لا يُسمح بحفظ قيد is_posted=True سواءً كان جديداً أو قديماً ما لم يكن متوازنًا
        if self.is_posted and not self.is_balanced:
            raise ValidationError(_('لا يمكن ترحيل أو حفظ قيد مرحل غير متوازن'))
        super().save(*args, **kwargs)

    def clean(self):  # type: ignore[override]
        # التحقق من وجود سنة مالية تغطي التاريخ ومن عدم إغلاقها عند الترحيل
        if not self.is_balanced:
            raise ValidationError(_('Entry must be balanced (debit = credit)'))
        if self.is_posted:
            from django.db.models import Q
            fy = FiscalYear.objects.filter(start_date__lte=self.date, end_date__gte=self.date).first()
            if not fy:
                # في بيئات الاختبار أو التشغيل الأولي أنشئ سنة مالية تلقائياً لتغطية التاريخ
                fy = FiscalYear.objects.create(
                    name=f"FY{self.date.year}",
                    start_date=date(self.date.year, 1, 1),
                    end_date=date(self.date.year, 12, 31),
                    is_active=True,
                    is_closed=False,
                )
            if fy.is_closed:
                raise ValidationError({'date': _('لا يمكن ترحيل قيد داخل سنة مالية مغلقة')})
        return super().clean()


class JournalEntryItem(models.Model):
    """بنود القيد المحاسبي"""
    ITEM_TYPE = [
        ('debit', _('مدين')),
        ('credit', _('دائن')),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='items', verbose_name=_('القيد'))
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='journal_entries', verbose_name=_('الحساب'))
    type = models.CharField(max_length=10, choices=ITEM_TYPE, verbose_name=_('النوع'))
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name=_('المبلغ'))
    description = models.CharField(max_length=255, blank=True, verbose_name=_('البيان'))
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('مركز التكلفة'))
    master_account = models.CharField(max_length=200, blank=True, verbose_name=_('حساب أستاذ'))
    analytics = models.CharField(max_length=200, blank=True, verbose_name=_('تحليل مالي'))
    analytics_2 = models.CharField(max_length=200, blank=True, verbose_name=_('تحليل مالي مكمل'))
    analytics_3 = models.CharField(max_length=200, blank=True, verbose_name=_('تحليل مالي مكمل 1'))
    reference_document = models.CharField(_('وثيقة مرجعية'), max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        verbose_name = _('بند قيد محاسبي')
        verbose_name_plural = _('بنود القيود المحاسبية')
        indexes = [
            models.Index(fields=['journal_entry', 'type']),
            models.Index(fields=['account', 'type']),
            models.Index(fields=['cost_center']),
            models.Index(fields=['account','journal_entry'], name='jei_account_entry_idx'),
        ]
        permissions = [
            ("edit_posted_entry_items", "Can edit items of posted journal (not recommended)"),
        ]

    def __str__(self):
        return f"{self.account} - {self.type} - {self.amount}"

    def clean(self):
        # السماح بإضافة بنود لقيد مرحل أثناء الإنشاء في الاختبارات، مع منع تعديل البنود القائمة
        if self.journal_entry and getattr(self.journal_entry, 'is_posted', False) and self.pk:
            # في حالة الحاجة لتعديلات: يجب إنشاء قيد عكسي بدلاً من التعديل المباشر
            raise ValidationError({'journal_entry': _('لا يمكن تعديل بنود قيد مرحل، أنشئ قيد تسوية عكسي')})
        if self.account and self.account.requires_cost_center and not self.cost_center:
            if self.account.default_cost_center:
                self.cost_center = self.account.default_cost_center
            else:
                raise ValidationError({'cost_center': _('هذا الحساب يتطلب تحديد مركز تكلفة')})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class FiscalYear(models.Model):
    """السنة المالية"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField(max_length=100, verbose_name=_("اسم السنة المالية"))
    start_date = models.DateField(verbose_name=_("تاريخ البداية"))
    end_date = models.DateField(verbose_name=_("تاريخ النهاية"))
    is_active = models.BooleanField(default=False, verbose_name=_("السنة الحالية"))
    is_closed = models.BooleanField(default=False, verbose_name=_("مغلقة"))
    
    class Meta:
        verbose_name = _("سنة مالية")
        verbose_name_plural = _("السنوات المالية")
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
    
    def save(self, *args, **kwargs):
        self.full_clean()
        if self.is_active:
            # إزالة الفعالية من السنوات الأخرى
            FiscalYear.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def clean(self):  # type: ignore[override]
        if self.end_date < self.start_date:
            raise ValidationError({'end_date': _('End date must be after start date')})
        return super().clean()


class CostCenterBudget(models.Model):
    """موازنة مركز التكلفة"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    cost_center = models.ForeignKey(CostCenter, on_delete=models.CASCADE, verbose_name=_('مركز التكلفة'))
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, verbose_name=_('السنة المالية'))
    total_budget = models.DecimalField(_('إجمالي الموازنة'), max_digits=15, decimal_places=2)
    allocated_budget = models.DecimalField(_('الموازنة المخصصة'), max_digits=15, decimal_places=2, default=Decimal('0'))
    actual_expenses = models.DecimalField(_('المصروفات الفعلية'), max_digits=15, decimal_places=2, default=Decimal('0'))
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('موازنة مركز تكلفة')
        verbose_name_plural = _('موازنات مراكز التكلفة')
        unique_together = ['cost_center', 'fiscal_year']
    
    def __str__(self):
        return f"{self.cost_center.name} - {self.fiscal_year.name}"
    
    @property
    def remaining_budget(self):
        """الموازنة المتبقية"""
        return self.total_budget - self.actual_expenses
    
    @property
    def budget_utilization_percentage(self):
        """نسبة استغلال الموازنة"""
        if self.total_budget > 0:
            return (self.actual_expenses / self.total_budget) * 100
        return 0


class JournalEntryTemplate(models.Model):
    """قوالب القيود المحاسبية التلقائية"""
    
    TEMPLATE_TYPES = [
        ('sale_cash', _('مبيعات نقدية')),
        ('sale_credit', _('مبيعات آجلة')),
        ('purchase_cash', _('مشتريات نقدية')),
        ('purchase_credit', _('مشتريات آجلة')),
        ('payment', _('دفع نقدي')),
        ('receipt', _('إيصال نقدي')),
        ('expense', _('مصروف')),
        ('salary', _('راتب')),
        ('depreciation', _('استهلاك')),
        ('custom', _('قالب مخصص')),
    ]
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField(_('اسم القالب'), max_length=200)
    template_type = models.CharField(_('نوع القالب'), max_length=20, choices=TEMPLATE_TYPES)
    description = models.TextField(_('الوصف'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    auto_apply = models.BooleanField(_('تطبيق تلقائي'), default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('قالب قيد محاسبي')
        verbose_name_plural = _('قوالب القيود المحاسبية')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.template_type}"


# ---------------------------------------------------------------------------
# نموذج مبسط لحركة بنكية (مطلوب لتسوية البنك)
# إذا كان هناك نموذج أصلي في فرع آخر؛ يمكن دمجه لاحقاً. هذا يوفر الحد الأدنى
# لتشغيل عرض التسوية وعدّاد الحركات غير المسوّاة.
# ---------------------------------------------------------------------------
class BankTransaction(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='bank_transactions', verbose_name=_('حساب بنكي'))
    date = models.DateField(default=timezone.localdate, verbose_name=_('التاريخ'))
    description = models.CharField(max_length=255, blank=True, verbose_name=_('الوصف'))
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name=_('المبلغ'))
    is_reconciled = models.BooleanField(default=False, db_index=True, verbose_name=_('مسوّى'))
    reference = models.CharField(max_length=100, blank=True, verbose_name=_('مرجع'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('حركة بنك')
        verbose_name_plural = _('حركات البنك')
        ordering = ['-date','-id']
        indexes = [
            models.Index(fields=['account','is_reconciled']),
            models.Index(fields=['date']),
        ]

    def __str__(self):  # pragma: no cover
        sign = '+' if self.amount >= 0 else '-'
        return f"{self.date} {sign}{abs(self.amount)} ({'✓' if self.is_reconciled else '…'})"


class JournalEntryTemplateItem(models.Model):
    """بنود قالب القيد المحاسبي"""
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    template = models.ForeignKey(JournalEntryTemplate, on_delete=models.CASCADE,
                                related_name='items', verbose_name=_('القالب'))
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name=_('الحساب'))
    type = models.CharField(_('النوع'), max_length=10, choices=[('debit', _('مدين')), ('credit', _('دائن'))])
    amount_type = models.CharField(_('نوع المبلغ'), max_length=20, 
                                  choices=[
                                      ('fixed', _('مبلغ ثابت')),
                                      ('percentage', _('نسبة مئوية')),
                                      ('variable', _('متغير'))
                                  ], default='variable')
    fixed_amount = models.DecimalField(_('المبلغ الثابت'), max_digits=12, decimal_places=2, 
                                      default=Decimal('0'))
    percentage = models.DecimalField(_('النسبة المئوية'), max_digits=5, decimal_places=2,
                                   default=Decimal('0'))
    default_cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL,
                                          null=True, blank=True,
                                          verbose_name=_('مركز التكلفة الافتراضي'))
    description = models.CharField(_('البيان الافتراضي'), max_length=255, blank=True)
    sequence = models.PositiveIntegerField(_('الترتيب'), default=1)
    
    class Meta:
        verbose_name = _('بند قالب القيد')
        verbose_name_plural = _('بنود قوالب القيود')
        ordering = ['sequence']
    
    def __str__(self):
        return f"{self.template.name} - {self.account.name} - {self.type}"


# النماذج القديمة - سنحتفظ بها للتوافق مع النظام الحالي
class Revenue(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    date = models.DateField(default=timezone.localdate)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    # ربط مع النظام المحاسبي الجديد
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="revenues")
    # صاحب التوريد
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='revenues', verbose_name=_("صاحب التوريد"))

    def __str__(self):
        return f"Revenue {self.amount} on {self.date}"


class Expense(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    date = models.DateField(default=timezone.localdate)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    # ربط مع النظام المحاسبي الجديد
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses")

    def __str__(self):
        return f"Expense {self.amount} on {self.date}"


# === نظام القروض البنكية المتطور ===

class Bank(models.Model):
    """البنوك"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField(max_length=200, verbose_name=_("اسم البنك"))
    code = models.CharField(max_length=20, unique=True, verbose_name=_("رمز البنك"))
    account_number = models.CharField(max_length=50, blank=True, verbose_name=_("رقم الحساب"))
    address = models.TextField(blank=True, verbose_name=_("العنوان"))
    phone = models.CharField(max_length=20, blank=True, verbose_name=_("الهاتف"))
    email = models.EmailField(blank=True, verbose_name=_("البريد الإلكتروني"))
    contact_person = models.CharField(max_length=200, blank=True, verbose_name=_("الشخص المسؤول"))
    swift_code = models.CharField(max_length=20, blank=True, verbose_name=_("رمز Swift"))
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), 
                                         verbose_name=_("الرصيد الحالي"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاريخ التحديث"))
    
    class Meta:
        verbose_name = _("بنك")
        verbose_name_plural = _("البنوك")
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        if self.account_number:
            return f"{self.name} - {self.account_number}"
        return self.name


class ElectronicAccount(models.Model):
    """الحسابات الإلكترونية / المحافظ الرقمية"""
    
    ACCOUNT_TYPE_CHOICES = [
        ('instapay', _('إنستاباي')),
        ('vodafone_cash', _('فودافون كاش')),
        ('orange_cash', _('أورانج كاش')),
        ('etisalat_cash', _('اتصالات كاش')),
        ('we_pay', _('وي باي')),
        ('paypal', _('باي بال')),
        ('paymob', _('بايموب')),
        ('fawry', _('فوري')),
        ('other', _('أخرى')),
    ]
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name=_("اسم الحساب"))
    code = models.CharField(max_length=20, unique=True, verbose_name=_("رمز الحساب"))
    account_type = models.CharField(max_length=30, choices=ACCOUNT_TYPE_CHOICES, 
                                   verbose_name=_("نوع الحساب"))
    phone_number = models.CharField(max_length=20, blank=True, 
                                   verbose_name=_("رقم الهاتف"),
                                   help_text=_("رقم الهاتف المرتبط بالمحفظة/الحساب"))
    email = models.EmailField(blank=True, verbose_name=_("البريد الإلكتروني"))
    account_id = models.CharField(max_length=100, blank=True, 
                                 verbose_name=_("معرف الحساب"),
                                 help_text=_("رقم الحساب أو المعرف الفريد"))
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), 
                                         verbose_name=_("الرصيد الحالي"))
    linked_account = models.ForeignKey(Account, on_delete=models.SET_NULL, 
                                      null=True, blank=True,
                                      related_name='electronic_accounts',
                                      verbose_name=_("الحساب المحاسبي المرتبط"),
                                      help_text=_("الحساب في دليل الحسابات"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاريخ التحديث"))
    
    class Meta:
        verbose_name = _("حساب إلكتروني")
        verbose_name_plural = _("الحسابات الإلكترونية")
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['account_type']),
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        display = f"{self.code} - {self.name}"
        if self.phone_number:
            display += f" ({self.phone_number})"
        elif self.account_id:
            display += f" ({self.account_id})"
        return display


class Treasury(models.Model):
    """الخزائن / الصناديق"""
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name=_("اسم الخزينة"))
    code = models.CharField(max_length=20, unique=True, verbose_name=_("رمز الخزينة"))
    location = models.CharField(max_length=200, blank=True, verbose_name=_("الموقع"))
    responsible_person = models.ForeignKey(User, on_delete=models.SET_NULL,
                                          null=True, blank=True,
                                          related_name='managed_treasuries',
                                          verbose_name=_("المسؤول"))
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), 
                                         verbose_name=_("الرصيد الحالي"))
    linked_account = models.ForeignKey(Account, on_delete=models.SET_NULL, 
                                      null=True, blank=True,
                                      related_name='treasuries',
                                      verbose_name=_("الحساب المحاسبي المرتبط"))
    showroom = models.ForeignKey('showrooms.Showroom', on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name='treasuries',
                                verbose_name=_("المعرض/الفرع"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاريخ التحديث"))
    
    class Meta:
        verbose_name = _("خزينة")
        verbose_name_plural = _("الخزائن")
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['code']),
            models.Index(fields=['showroom']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class FawryMachine(models.Model):
    """ماكينات الفوري"""
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name=_("اسم الماكينة"))
    code = models.CharField(max_length=20, unique=True, verbose_name=_("رمز الماكينة"))
    machine_id = models.CharField(max_length=50, unique=True, verbose_name=_("رقم الماكينة"))
    phone_number = models.CharField(max_length=20, blank=True, verbose_name=_("رقم الهاتف المربوط"))
    location = models.CharField(max_length=200, blank=True, verbose_name=_("الموقع"))
    responsible_person = models.ForeignKey(User, on_delete=models.SET_NULL,
                                          null=True, blank=True,
                                          related_name='managed_fawry_machines',
                                          verbose_name=_("المسؤول"))
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), 
                                         verbose_name=_("الرصيد الحالي"))
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), 
                                         verbose_name=_("نسبة العمولة %"))
    linked_account = models.ForeignKey(Account, on_delete=models.SET_NULL, 
                                      null=True, blank=True,
                                      related_name='fawry_machines',
                                      verbose_name=_("الحساب المحاسبي المرتبط"))
    showroom = models.ForeignKey('showrooms.Showroom', on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name='fawry_machines',
                                verbose_name=_("المعرض/الفرع"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاريخ التحديث"))
    
    class Meta:
        verbose_name = _("ماكينة فوري")
        verbose_name_plural = _("ماكينات الفوري")
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['code']),
            models.Index(fields=['machine_id']),
            models.Index(fields=['showroom']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class VisaMachine(models.Model):
    """ماكينات نقاط البيع (الفيزا)"""
    
    MACHINE_TYPES = [
        ('visa', _('فيزا')),
        ('mastercard', _('ماستركارد')),
        ('mada', _('مدى')),
        ('multi', _('متعدد البطاقات')),
    ]
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name=_("اسم الماكينة"))
    code = models.CharField(max_length=20, unique=True, verbose_name=_("رمز الماكينة"))
    terminal_id = models.CharField(max_length=50, unique=True, verbose_name=_("رقم الترمينال"))
    merchant_id = models.CharField(max_length=50, blank=True, verbose_name=_("رقم التاجر"))
    machine_type = models.CharField(max_length=20, choices=MACHINE_TYPES, default='multi', 
                                   verbose_name=_("نوع الماكينة"))
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True,
                            related_name='visa_machines',
                            verbose_name=_("البنك المربوط"))
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), 
                                         verbose_name=_("نسبة العمولة %"))
    location = models.CharField(max_length=200, blank=True, verbose_name=_("الموقع"))
    responsible_person = models.ForeignKey(User, on_delete=models.SET_NULL,
                                          null=True, blank=True,
                                          related_name='managed_visa_machines',
                                          verbose_name=_("المسؤول"))
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), 
                                         verbose_name=_("الرصيد الحالي"))
    linked_account = models.ForeignKey(Account, on_delete=models.SET_NULL, 
                                      null=True, blank=True,
                                      related_name='visa_machines',
                                      verbose_name=_("الحساب المحاسبي المرتبط"))
    showroom = models.ForeignKey('showrooms.Showroom', on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name='visa_machines',
                                verbose_name=_("المعرض/الفرع"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاريخ التحديث"))
    
    class Meta:
        verbose_name = _("ماكينة فيزا")
        verbose_name_plural = _("ماكينات الفيزا")
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['code']),
            models.Index(fields=['terminal_id']),
            models.Index(fields=['showroom']),
            models.Index(fields=['bank']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class AccountTransfer(models.Model):
    """التحويلات بين الحسابات (خزائن، بنوك، حسابات إلكترونية، ماكينات فوري، ماكينات فيزا)"""
    
    ACCOUNT_TYPES = [
        ('treasury', _('خزينة')),
        ('bank', _('بنك')),
        ('electronic', _('حساب إلكتروني')),
        ('fawry', _('ماكينة فوري')),
        ('visa', _('ماكينة فيزا')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('قيد الانتظار')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
    ]
    
    id = models.AutoField(primary_key=True)
    transfer_number = models.CharField(max_length=50, unique=True, verbose_name=_("رقم التحويل"))
    date = models.DateField(verbose_name=_("تاريخ التحويل"))
    
    # المصدر (من)
    from_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, verbose_name=_("نوع المصدر"))
    from_treasury = models.ForeignKey(Treasury, on_delete=models.PROTECT,
                                     null=True, blank=True,
                                     related_name='transfers_out',
                                     verbose_name=_("من خزينة"))
    from_bank = models.ForeignKey(Bank, on_delete=models.PROTECT,
                                 null=True, blank=True,
                                 related_name='transfers_out',
                                 verbose_name=_("من بنك"))
    from_electronic = models.ForeignKey(ElectronicAccount, on_delete=models.PROTECT,
                                       null=True, blank=True,
                                       related_name='transfers_out',
                                       verbose_name=_("من حساب إلكتروني"))
    from_fawry = models.ForeignKey(FawryMachine, on_delete=models.PROTECT,
                                  null=True, blank=True,
                                  related_name='transfers_out',
                                  verbose_name=_("من ماكينة فوري"))
    from_visa = models.ForeignKey(VisaMachine, on_delete=models.PROTECT,
                                 null=True, blank=True,
                                 related_name='transfers_out',
                                 verbose_name=_("من ماكينة فيزا"))
    
    # الوجهة (إلى)
    to_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, verbose_name=_("نوع الوجهة"))
    to_treasury = models.ForeignKey(Treasury, on_delete=models.PROTECT,
                                   null=True, blank=True,
                                   related_name='transfers_in',
                                   verbose_name=_("إلى خزينة"))
    to_bank = models.ForeignKey(Bank, on_delete=models.PROTECT,
                               null=True, blank=True,
                               related_name='transfers_in',
                               verbose_name=_("إلى بنك"))
    to_electronic = models.ForeignKey(ElectronicAccount, on_delete=models.PROTECT,
                                     null=True, blank=True,
                                     related_name='transfers_in',
                                     verbose_name=_("إلى حساب إلكتروني"))
    to_fawry = models.ForeignKey(FawryMachine, on_delete=models.PROTECT,
                                null=True, blank=True,
                                related_name='transfers_in',
                                verbose_name=_("إلى ماكينة فوري"))
    to_visa = models.ForeignKey(VisaMachine, on_delete=models.PROTECT,
                               null=True, blank=True,
                               related_name='transfers_in',
                               verbose_name=_("إلى ماكينة فيزا"))
    
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("المبلغ"),
                                validators=[MinValueValidator(Decimal('0.01'))])
    fees = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'),
                              verbose_name=_("رسوم التحويل"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed',
                             verbose_name=_("الحالة"))
    description = models.TextField(blank=True, verbose_name=_("البيان/الوصف"))
    reference_number = models.CharField(max_length=100, blank=True, verbose_name=_("رقم المرجع"))
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT,
                                  related_name='created_transfers',
                                  verbose_name=_("أنشئ بواسطة"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاريخ التحديث"))
    
    class Meta:
        verbose_name = _("تحويل")
        verbose_name_plural = _("التحويلات")
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['from_type']),
            models.Index(fields=['to_type']),
            models.Index(fields=['status']),
            models.Index(fields=['transfer_number']),
        ]
    
    def __str__(self):
        return f"تحويل {self.transfer_number} - {self.amount}"
    
    @property
    def from_account_name(self):
        """اسم حساب المصدر"""
        if self.from_type == 'treasury' and self.from_treasury:
            return str(self.from_treasury)
        elif self.from_type == 'bank' and self.from_bank:
            return str(self.from_bank)
        elif self.from_type == 'electronic' and self.from_electronic:
            return str(self.from_electronic)
        elif self.from_type == 'fawry' and self.from_fawry:
            return str(self.from_fawry)
        elif self.from_type == 'visa' and self.from_visa:
            return str(self.from_visa)
        return None
    
    @property
    def to_account_name(self):
        """اسم حساب الوجهة"""
        if self.to_type == 'treasury' and self.to_treasury:
            return str(self.to_treasury)
        elif self.to_type == 'bank' and self.to_bank:
            return str(self.to_bank)
        elif self.to_type == 'electronic' and self.to_electronic:
            return str(self.to_electronic)
        elif self.to_type == 'fawry' and self.to_fawry:
            return str(self.to_fawry)
        elif self.to_type == 'visa' and self.to_visa:
            return str(self.to_visa)
        return None
    
    @property
    def net_amount(self):
        """المبلغ الصافي بعد الرسوم"""
        return self.amount - self.fees
    
    def save(self, *args, **kwargs):
        # توليد رقم تحويل تلقائي
        if not self.transfer_number:
            from django.utils import timezone
            today = timezone.now()
            prefix = f"TRF{today.strftime('%Y%m%d')}"
            last_transfer = AccountTransfer.objects.filter(
                transfer_number__startswith=prefix
            ).order_by('-transfer_number').first()
            if last_transfer:
                try:
                    last_num = int(last_transfer.transfer_number[-4:])
                    new_num = last_num + 1
                except:
                    new_num = 1
            else:
                new_num = 1
            self.transfer_number = f"{prefix}{new_num:04d}"
        super().save(*args, **kwargs)
    
    def clean(self):
        """التحقق من صحة البيانات"""
        from django.core.exceptions import ValidationError
        
        # التأكد من تحديد حساب المصدر
        if self.from_type == 'treasury' and not self.from_treasury:
            raise ValidationError({'from_treasury': _('يجب تحديد الخزينة المصدر')})
        elif self.from_type == 'bank' and not self.from_bank:
            raise ValidationError({'from_bank': _('يجب تحديد البنك المصدر')})
        elif self.from_type == 'electronic' and not self.from_electronic:
            raise ValidationError({'from_electronic': _('يجب تحديد الحساب الإلكتروني المصدر')})
        elif self.from_type == 'fawry' and not self.from_fawry:
            raise ValidationError({'from_fawry': _('يجب تحديد ماكينة الفوري المصدر')})
        elif self.from_type == 'visa' and not self.from_visa:
            raise ValidationError({'from_visa': _('يجب تحديد ماكينة الفيزا المصدر')})
        
        # التأكد من تحديد حساب الوجهة
        if self.to_type == 'treasury' and not self.to_treasury:
            raise ValidationError({'to_treasury': _('يجب تحديد الخزينة الوجهة')})
        elif self.to_type == 'bank' and not self.to_bank:
            raise ValidationError({'to_bank': _('يجب تحديد البنك الوجهة')})
        elif self.to_type == 'electronic' and not self.to_electronic:
            raise ValidationError({'to_electronic': _('يجب تحديد الحساب الإلكتروني الوجهة')})
        elif self.to_type == 'fawry' and not self.to_fawry:
            raise ValidationError({'to_fawry': _('يجب تحديد ماكينة الفوري الوجهة')})
        elif self.to_type == 'visa' and not self.to_visa:
            raise ValidationError({'to_visa': _('يجب تحديد ماكينة الفيزا الوجهة')})
        
        # التأكد من أن المصدر والوجهة مختلفان
        if self.from_type == self.to_type:
            if self.from_type == 'treasury' and self.from_treasury == self.to_treasury:
                raise ValidationError(_('لا يمكن التحويل من وإلى نفس الخزينة'))
            elif self.from_type == 'bank' and self.from_bank == self.to_bank:
                raise ValidationError(_('لا يمكن التحويل من وإلى نفس البنك'))
            elif self.from_type == 'electronic' and self.from_electronic == self.to_electronic:
                raise ValidationError(_('لا يمكن التحويل من وإلى نفس الحساب الإلكتروني'))
            elif self.from_type == 'fawry' and self.from_fawry == self.to_fawry:
                raise ValidationError(_('لا يمكن التحويل من وإلى نفس ماكينة الفوري'))
            elif self.from_type == 'visa' and self.from_visa == self.to_visa:
                raise ValidationError(_('لا يمكن التحويل من وإلى نفس ماكينة الفيزا'))


class Loan(models.Model):
    """القروض البنكية"""
    LOAN_STATUS = [
        ('draft', _('مسودة')),
        ('active', _('نشط')),
        ('completed', _('مكتمل')),
        ('defaulted', _('متعثر'))
    ]
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    loan_number = models.CharField(max_length=50, unique=True, verbose_name=_("رقم القرض"))
    bank = models.ForeignKey(Bank, on_delete=models.PROTECT, verbose_name=_("البنك"))
    principal_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("مبلغ القرض"), validators=[MinValueValidator(Decimal('0.01'))])
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name=_("معدل الفائدة"), validators=[MinValueValidator(Decimal('0'))])
    duration_months = models.PositiveIntegerField(verbose_name=_("مدة القرض بالشهور"))
    disbursement_date = models.DateField(verbose_name=_("تاريخ الصرف"))
    status = models.CharField(max_length=20, choices=LOAN_STATUS, default='draft', verbose_name=_("الحالة"))
    outstanding_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), verbose_name=_("الرصيد المستحق"), validators=[MinValueValidator(Decimal('0'))])
    loan_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='loans', verbose_name=_("حساب القرض"))
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='accounting_loans', verbose_name=_("أنشئ بواسطة"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    
    class Meta:
        verbose_name = _("قرض")
        verbose_name_plural = _("القروض")
        constraints = [
            models.CheckConstraint(check=models.Q(interest_rate__lte=Decimal('100')), name='loan_interest_rate_lte_100'),
        ]
    
    @property
    def monthly_installment(self):
        """القسط الشهري"""
        if self.duration_months <= 0:
            return Decimal('0.00')
        # استخدام Decimal لتقليل أخطاء التقريب المالية
        principal = Decimal(self.principal_amount)
        rate = (Decimal(self.interest_rate) / Decimal('100')) / Decimal('12')
        if rate == 0:
            return (principal / Decimal(self.duration_months)).quantize(Decimal('0.01'))
        # صيغة القسط الثابت (جدول السداد القياسي للقروض الثابتة الفائدة)
        one_plus = (Decimal('1') + rate) ** self.duration_months
        installment = principal * (rate * one_plus) / (one_plus - Decimal('1'))
        return installment.quantize(Decimal('0.01'))
    
    def __str__(self):
        return f"قرض {self.loan_number} - {self.bank.name}"


class LoanPayment(models.Model):
    """دفعات القروض"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments', verbose_name=_("القرض"))
    payment_date = models.DateField(verbose_name=_("تاريخ الدفع"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("المبلغ"), validators=[MinValueValidator(Decimal('0.01'))])
    principal_portion = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("جزء أصل الدين"), validators=[MinValueValidator(Decimal('0'))])
    interest_portion = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("جزء الفوائد"), validators=[MinValueValidator(Decimal('0'))])
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.PROTECT, null=True, blank=True, related_name='loan_payments', verbose_name=_("القيد المحاسبي"))
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='accounting_loan_payments', verbose_name=_("أنشئ بواسطة"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    
    class Meta:
        verbose_name = _("دفعة قرض")
        verbose_name_plural = _("دفعات القروض")
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount=models.F('principal_portion') + models.F('interest_portion')),
                name='loanpayment_amount_equals_parts'
            )
        ]
    
    def save(self, *args, **kwargs):
        """حفظ الدفعة مع تحديث رصيد القرض بشكل ذري لتفادي سباقات."""
        from django.db import transaction
        # نستخدم معاملة لضمان اتساق التحديث خاصة في بيئات متعددة
        with transaction.atomic():
            creating = self.pk is None
            super().save(*args, **kwargs)
            # إعادة تحميل القرض بقفل صف (في قواعد تدعم ذلك) لتفادي التحديث المتسابق
            try:
                loan_locked = type(self.loan).objects.select_for_update().get(pk=self.loan.pk)
            except Exception:  # sqlite لا يدعم select_for_update الكامل دائماً
                loan_locked = self.loan
            # عند الإنشاء فقط ننقص الرصيد (تجنب إنقاص متكرر عند تعديل السجل)
            if creating:
                loan_locked.outstanding_balance -= self.principal_portion
                if loan_locked.outstanding_balance <= 0:
                    loan_locked.outstanding_balance = Decimal('0')
                    loan_locked.status = 'completed'
                loan_locked.save(update_fields=['outstanding_balance','status'])
    
    def __str__(self):
        return f"دفعة {self.amount} - {self.loan.loan_number}"


# === الشيكات (حافظة الشيكات المحسنة) ===
class Cheque(models.Model):
    """إدارة الشيكات المتقدمة مع تتبع كامل ورسوم الشيكات المرتدة."""
    CHEQUE_TYPES = [
        ("incoming", _("وارد")),   # من عميل إلينا
        ("outgoing", _("صادر")),   # منا لمورد
    ]

    CHEQUE_STATUS = [
        ("received", _("مستلم")),
        ("issued", _("صادر")),
        ("under_collection", _("قيد التحصيل")),
        ("deposited", _("مودع بالبنك")),
        ("cleared", _("محصل")),
        ("bounced", _("مرتجع")),
        ("cancelled", _("ملغى")),
        ("replaced", _("تم استبداله")),
    ]

    number = models.CharField(_("رقم الشيك"), max_length=50, unique=True)
    bank_name = models.CharField(_("اسم البنك"), max_length=100)
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True,
                            verbose_name=_("الحساب البنكي"))
    cheque_type = models.CharField(_("نوع الشيك"), max_length=10, 
                                  choices=CHEQUE_TYPES, default="incoming")
    status = models.CharField(_("الحالة"), max_length=20, 
                            choices=CHEQUE_STATUS, default="received")
    partner = models.ForeignKey('partners.Partner', on_delete=models.SET_NULL, 
                               null=True, blank=True, verbose_name=_('الشريك'))
    # customer = models.ForeignKey('sales.Customer', on_delete=models.SET_NULL,
    #                            null=True, blank=True, verbose_name=_('العميل'))
    # supplier = models.ForeignKey('purchases.Supplier', on_delete=models.SET_NULL,
    #                            null=True, blank=True, verbose_name=_('المورد'))
    amount = models.DecimalField(_("المبلغ"), max_digits=15, decimal_places=2)
    issue_date = models.DateField(_("تاريخ الإصدار"), default=timezone.localdate)
    due_date = models.DateField(_("تاريخ الاستحقاق"), null=True, blank=True)
    collection_date = models.DateField(_("تاريخ التحصيل"), null=True, blank=True)
    deposit_date = models.DateField(_("تاريخ الإيداع"), null=True, blank=True)
    cleared_date = models.DateField(_("تاريخ الصرف"), null=True, blank=True)
    bounced_date = models.DateField(_("تاريخ الإرتداد"), null=True, blank=True)
    bounced_reason = models.TextField(_("سبب الإرتداد"), blank=True)
    bounced_fees = models.DecimalField(_("رسوم الإرتداد"), max_digits=10, 
                                      decimal_places=2, default=Decimal('0'))
    replacement_cheque = models.ForeignKey('self', on_delete=models.SET_NULL,
                                          null=True, blank=True,
                                          related_name='replaced_cheques',
                                          verbose_name=_('الشيك البديل'))
    image = models.ImageField(_("صورة الشيك"), upload_to='cheques/%Y/%m/', 
                            null=True, blank=True)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                     verbose_name=_('القيد المحاسبي'))
    alert_sent = models.BooleanField(default=False, 
                                    verbose_name=_('تم إرسال تنبيه الاستحقاق'))
    alert_days_before = models.IntegerField(default=3,
                                           verbose_name=_('التنبيه قبل (أيام)'))
    notes = models.TextField(_("ملاحظات"), blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  verbose_name=_("أنشئ بواسطة"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("شيك")
        verbose_name_plural = _("حافظة الشيكات")
        ordering = ['-due_date', '-created_at']
        indexes = [
            models.Index(fields=["number"]),
            models.Index(fields=["status", "due_date"]),
            models.Index(fields=["cheque_type", "status"]),
        ]

    def __str__(self):
        return f"{self.number} - {self.amount} - {self.get_status_display()}"
    
    @property
    def days_until_due(self):
        """عدد الأيام حتى الاستحقاق"""
        if self.due_date:
            return (self.due_date - date.today()).days
        return None
    
    @property
    def is_overdue(self):
        """هل تجاوز تاريخ الاستحقاق"""
        if self.due_date and self.status in ['received', 'issued', 'under_collection', 'deposited']:
            return date.today() > self.due_date
        return False


# === إعدادات المحاسبة العامة (VAT والحسابات الافتراضية) ===
class AccountingSettings(models.Model):
    """إعدادات عامة لوحدة المحاسبة (حسابات افتراضية وضرائب)."""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    enable_vat = models.BooleanField(_('تفعيل ضريبة القيمة المضافة VAT'), default=False)
    default_vat_rate = models.DecimalField(_('نسبة VAT الافتراضية %'), max_digits=5, decimal_places=2, default=Decimal('0'))

    # حسابات افتراضية
    inventory_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name=_('حساب المخزون')
    )
    ap_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name=_('حساب الدائنين (الموردين)')
    )
    ar_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name=_('حساب العملاء (الذمم)')
    )
    cash_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name=_('حساب النقدية/البنك')
    )
    customer_advances_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name=_('حساب سلف العملاء / دفعات مقدمة')
    )
    vat_input_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name=_('حساب ضريبة مدخلات')
    )
    vat_output_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name=_('حساب ضريبة مخرجات (للمبيعات)')
    )
    
    # === إعدادات القيود التلقائية للإيرادات والمصروفات ===
    auto_create_journal_entries = models.BooleanField(
        default=True,
        verbose_name=_('إنشاء قيود تلقائية للإيرادات والمصروفات'),
        help_text=_('عند التفعيل، يتم إنشاء قيد محاسبي تلقائياً عند تسجيل إيراد أو مصروف')
    )
    
    # حسابات افتراضية للإيرادات المتنوعة
    misc_revenue_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='settings_misc_revenue',
        verbose_name=_('حساب الإيرادات المتنوعة'),
        help_text=_('الحساب الافتراضي للإيرادات غير المصنفة')
    )
    
    # حسابات افتراضية للمصروفات المتنوعة
    misc_expense_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='settings_misc_expense',
        verbose_name=_('حساب المصروفات المتنوعة'),
        help_text=_('الحساب الافتراضي للمصروفات غير المصنفة')
    )
    
    # حسابات الخزائن
    default_treasury_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='settings_treasury',
        verbose_name=_('حساب الخزينة الافتراضي')
    )
    
    # حسابات البنوك
    default_bank_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='settings_bank',
        verbose_name=_('حساب البنك الافتراضي')
    )
    
    # حسابات المحافظ الإلكترونية
    default_electronic_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='settings_electronic',
        verbose_name=_('حساب المحافظ الإلكترونية الافتراضي')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('إعدادات المحاسبة')
        verbose_name_plural = _('إعدادات المحاسبة')

    def __str__(self):
        # Return a plain str (avoid returning lazy proxy object which triggered TypeError in audit logging during some reuse-db test runs)
        return 'إعدادات المحاسبة'

    @classmethod
    def get(cls):
        """الحصول على سجل الإعدادات (أول سجل أو إنشاؤه افتراضياً)."""
        obj = cls.objects.first()
        if obj:
            return obj
        # محاولة ربط الحسابات المعروفة أكوادها إن وجدت
        def _acc(code, name_part=''):
            try:
                return Account.objects.get(code=code)
            except Account.DoesNotExist:
                if name_part:
                    return Account.objects.filter(name__icontains=name_part).first()
            return None
        # إنشاء الحسابات الأساسية إذا لم توجد (مفيد في بيئة الاختبارات)
        inv_acc, _ = Account.objects.get_or_create(
            code='1004',
            defaults={'name': 'المخزون', 'account_type': 'asset'}
        )
        ap_acc, _ = Account.objects.get_or_create(
            code='2001',
            defaults={'name': 'الدائنون', 'account_type': 'liability'}
        )
        ar_acc = _acc('1101', 'عملاء') or _acc('1102', 'عملاء') or _acc('1100', 'عملاء')
        if not ar_acc:
            ar_acc, _ = Account.objects.get_or_create(
                code='1101',
                defaults={'name': 'العملاء', 'account_type': 'asset'}
            )
        cash_acc = _acc('1001', 'النقد') or _acc('1002', 'البنك')
        if not cash_acc:
            cash_acc, _ = Account.objects.get_or_create(
                code='1001',
                defaults={'name': 'الصندوق', 'account_type': 'asset'}
            )
        vat_in_acc, _ = Account.objects.get_or_create(
            code='1551',
            defaults={'name': 'ضريبة مدخلات', 'account_type': 'asset'}
        )
        vat_out_acc, _ = Account.objects.get_or_create(
            code='2551',
            defaults={'name': 'ضريبة مخرجات', 'account_type': 'liability'}
        )

        return cls.objects.create(
            enable_vat=False,
            default_vat_rate=0,
            inventory_account=inv_acc,
            ap_account=ap_acc,
            ar_account=ar_acc,
            cash_account=cash_acc,
            vat_input_account=vat_in_acc,
            vat_output_account=vat_out_acc,
        )


class CashFlowAccountMapping(models.Model):
    """تعيين يدوي لفئة التدفق النقدي لحساب معين لتجاوز التصنيف التلقائي.

    الفئات: تشغيلي / استثماري / تمويلي. يساعد على دقة قائمة التدفقات النقدية.
    """
    CATEGORY_CHOICES = [
        ('operating', _('تشغيلي')),
        ('investing', _('استثماري')),
        ('financing', _('تمويلي')),
    ]
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='cashflow_mapping', verbose_name=_('الحساب'))
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name=_('الفئة'))
    note = models.CharField(max_length=200, blank=True, verbose_name=_('ملاحظة'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('تعيين فئة تدفق نقدي')
        verbose_name_plural = _('تعيينات فئات التدفق النقدي')
        ordering = ['account__code']

    def __str__(self):
        return f"{self.account.code} -> {self.category}"


# === إقفال السنة المالية ===
class PeriodYearClose(models.Model):
    """تسجيل عمليات إقفال السنوات المالية.

    ينشأ سجل عند تنفيذ الإقفال لتوثيق: السنة، التاريخ، المستخدم، رقم القيد الناتج، صافي الربح.
    """
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT, related_name='year_closures', verbose_name=_('السنة المالية'))
    closed_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإقفال'))
    closed_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('تم بواسطة'))
    journal_entry = models.ForeignKey('JournalEntry', on_delete=models.PROTECT, null=True, blank=True, verbose_name=_('قيد الإقفال'))
    net_income = models.DecimalField(_('صافي الربح/الخسارة'), max_digits=15, decimal_places=2)
    notes = models.TextField(_('ملاحظات'), blank=True)
    preview_data = models.JSONField(_('تفاصيل الحركات وقت الإقفال'), default=dict, blank=True)

    class Meta:
        verbose_name = _('إقفال سنة مالية')
        verbose_name_plural = _('إقفالات السنوات المالية')
        ordering = ['-closed_at']
        constraints = [
            models.UniqueConstraint(fields=['fiscal_year'], name='uniq_year_close_once')
        ]

    def __str__(self):  # pragma: no cover
        return f"Close {self.fiscal_year.name} @ {self.closed_at:%Y-%m-%d}"


# ==============================
# نماذج توزيع التكاليف (مبدئية)
# ==============================
class CostDriver(models.Model):
    """محركات/مسببات التكلفة (عدد ساعات، وحدات، مساحة...)."""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    code = models.CharField(_('الكود'), max_length=30, unique=True)
    name = models.CharField(_('الاسم'), max_length=200)
    driver_type = models.CharField(_('نوع المحرك'), max_length=50, blank=True)
    unit = models.CharField(_('وحدة القياس'), max_length=30, blank=True)
    is_active = models.BooleanField(_('نشط'), default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('محرك تكلفة')
        verbose_name_plural = _('محركات التكلفة')
        ordering = ['code']

    def __str__(self):  # pragma: no cover
        return f"{self.code} - {self.name}"


class CostPool(models.Model):
    """مجمع تكاليف (تجميع التكاليف غير المباشرة قبل توزيعها)."""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    code = models.CharField(_('الكود'), max_length=30, unique=True)
    name = models.CharField(_('الاسم'), max_length=200)
    description = models.TextField(_('الوصف'), blank=True)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('مركز خدمة (اختياري)'))
    driver = models.ForeignKey(CostDriver, on_delete=models.PROTECT, verbose_name=_('محرك التكلفة'))
    debit_account = models.ForeignKey('Account', on_delete=models.PROTECT, null=True, blank=True, related_name='+', verbose_name=_('حساب مدين (تحميل)'))
    credit_account = models.ForeignKey('Account', on_delete=models.PROTECT, null=True, blank=True, related_name='+', verbose_name=_('حساب دائن (مصدر)'))
    is_active = models.BooleanField(_('نشط'), default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('مجمع تكاليف')
        verbose_name_plural = _('مجمعات التكاليف')
        ordering = ['code']

    def __str__(self):  # pragma: no cover
        return f"{self.code} - {self.name}"


class CostPoolConsumption(models.Model):
    """ربط مجمع تكاليف بمركز مستفيد مع كمية المحرك (تُستخدم في حساب معدل التحميل)."""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    pool = models.ForeignKey(CostPool, on_delete=models.CASCADE, related_name='consumptions', verbose_name=_('مجمع'))
    cost_center = models.ForeignKey(CostCenter, on_delete=models.CASCADE, verbose_name=_('مركز مستفيد'))
    driver_quantity = models.DecimalField(_('كمية المحرك'), max_digits=18, decimal_places=4, validators=[MinValueValidator(Decimal('0'))])
    period = models.CharField(_('فترة'), max_length=10, help_text=_('مثال: 2025-09 (شهر) أو 2025Q3'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('استهلاك مجمع')
        verbose_name_plural = _('استهلاكات المجمعات')
        indexes = [
            models.Index(fields=['pool','period']),
            models.Index(fields=['cost_center','period']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['pool','cost_center','period'], name='uniq_pool_center_period')
        ]

    def __str__(self):  # pragma: no cover
        return f"{self.pool.code}->{self.cost_center.code}:{self.period}" if self.pool_id and self.cost_center_id else str(self.id)


class CostAllocationRun(models.Model):
    """تشغيل توزيع تكاليف (يحفظ ملخصاً قابلاً للتدقيق)."""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    period = models.CharField(_('الفترة'), max_length=10, db_index=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    executed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('نُفذ بواسطة'))
    notes = models.TextField(_('ملاحظات'), blank=True)
    total_indirect_cost = models.DecimalField(_('إجمالي غير مباشر'), max_digits=18, decimal_places=2, default=Decimal('0'))
    total_allocated = models.DecimalField(_('إجمالي موزع'), max_digits=18, decimal_places=2, default=Decimal('0'))
    status = models.CharField(_('الحالة'), max_length=20, default='running', db_index=True)

    class Meta:
        verbose_name = _('تشغيل توزيع تكاليف')
        verbose_name_plural = _('تشغيلات توزيع التكاليف')
        ordering = ['-started_at']

    def __str__(self):  # pragma: no cover
        return f"AllocRun {self.period} ({self.status})"


class CostAllocationResult(models.Model):
    """نتائج مفصلة لكل مركز متأثر في تشغيل توزيع معين."""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    run = models.ForeignKey(CostAllocationRun, on_delete=models.CASCADE, related_name='results', verbose_name=_('تشغيل'))
    pool = models.ForeignKey(CostPool, on_delete=models.PROTECT, verbose_name=_('مجمع'))
    cost_center = models.ForeignKey(CostCenter, on_delete=models.PROTECT, verbose_name=_('مركز'))
    driver_quantity = models.DecimalField(_('كمية المحرك'), max_digits=18, decimal_places=4)
    driver_rate = models.DecimalField(_('معدل التحميل'), max_digits=18, decimal_places=6)
    allocated_amount = models.DecimalField(_('مبلغ موزع'), max_digits=18, decimal_places=2)
    journal_entry = models.ForeignKey('JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('قيد التوزيع'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('نتيجة توزيع')
        verbose_name_plural = _('نتائج التوزيع')
        indexes = [
            models.Index(fields=['run','cost_center']),
            models.Index(fields=['pool']),
        ]

    def __str__(self):  # pragma: no cover
        return f"Result {self.run_id}-{self.cost_center_id}-{self.allocated_amount}"


class CostPoolSourceAccount(models.Model):
    """حسابات مصدر لتجميع تكلفة مجمع معين (مصروفات غير مباشرة)."""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    pool = models.ForeignKey(CostPool, on_delete=models.CASCADE, related_name='source_accounts', verbose_name=_('مجمع'))
    account = models.ForeignKey(Account, on_delete=models.PROTECT, verbose_name=_('الحساب'))
    percentage = models.DecimalField(_('نسبة اعتبارية %'), max_digits=7, decimal_places=4, default=Decimal('0'), help_text=_('اترك 0 لاستخدام القيمة الكاملة للحساب'))
    is_active = models.BooleanField(_('نشط'), default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('حساب مصدر مجمع')
        verbose_name_plural = _('حسابات مصادر المجمعات')
        indexes = [
            models.Index(fields=['pool','is_active']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['pool','account'], name='uniq_pool_account_source')
        ]

    def __str__(self):  # pragma: no cover
        return f"{self.pool.code}->{self.account.code} ({self.percentage or '100%'})"


# منع حذف حساب له قيود محاسبية مرتبطة لحماية سلامة التقارير
@receiver(pre_delete, sender=Account)
def prevent_account_delete_with_entries(sender, instance, **kwargs):
    # type: ignore[attr-defined]
    if instance.journal_entries.exists():  # pragma: no cover - حماية تشغيلية
        raise ValidationError(_('لا يمكن حذف حساب يحتوي على حركات محاسبية'))


# تفريغ كاش أرصدة الحسابات عند أي تعديل على بنود القيود
@receiver(models.signals.post_save, sender=JournalEntryItem)
def invalidate_balance_on_item_save(sender, instance, **kwargs):  # pragma: no cover - تشغيل فقط
    try:
        from .services import invalidate_account_balance  # استيراد متأخر لتجنب الدوران
        invalidate_account_balance(instance.account.id)
        # تفريغ كاش إجمالي مصروفات مركز التكلفة إن وجد
        if instance.cost_center_id:
            cache.delete(f"cc:totexp:{instance.cost_center_id}")
    except Exception:
        pass


@receiver(models.signals.post_delete, sender=JournalEntryItem)
def invalidate_balance_on_item_delete(sender, instance, **kwargs):  # pragma: no cover
    try:
        from .services import invalidate_account_balance
        invalidate_account_balance(instance.account.id)
        if instance.cost_center_id:
            cache.delete(f"cc:totexp:{instance.cost_center_id}")
    except Exception:
        pass


# ==============================
# نظام تكاليف المنتجات (Product Costing)
# ==============================

class ProductCosting(models.Model):
    """بطاقة تكلفة المنتج - تحديد تكلفة كل منتج بشكل تفصيلي"""
    
    COSTING_METHOD_CHOICES = [
        ('standard', _('تكلفة معيارية')),
        ('actual', _('تكلفة فعلية')),
        ('average', _('متوسط متحرك')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('active', _('نشطة')),
        ('archived', _('مؤرشفة')),
    ]
    
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, 
                               related_name='costings', verbose_name=_('المنتج'))
    version = models.PositiveIntegerField(_('الإصدار'), default=1)
    costing_method = models.CharField(_('طريقة التكلفة'), max_length=20, 
                                     choices=COSTING_METHOD_CHOICES, default='standard')
    status = models.CharField(_('الحالة'), max_length=20, 
                            choices=STATUS_CHOICES, default='draft')
    
    # مكونات التكلفة الرئيسية
    direct_material_cost = models.DecimalField(_('تكلفة المواد المباشرة'), 
                                              max_digits=15, decimal_places=4, default=Decimal('0'))
    direct_labor_cost = models.DecimalField(_('تكلفة العمالة المباشرة'), 
                                           max_digits=15, decimal_places=4, default=Decimal('0'))
    overhead_cost = models.DecimalField(_('التكاليف الصناعية غير المباشرة'), 
                                       max_digits=15, decimal_places=4, default=Decimal('0'))
    other_cost = models.DecimalField(_('تكاليف أخرى'), 
                                    max_digits=15, decimal_places=4, default=Decimal('0'))
    
    # إجمالي التكلفة
    total_cost = models.DecimalField(_('إجمالي التكلفة'), 
                                    max_digits=15, decimal_places=4, default=Decimal('0'))
    
    # هامش الربح المستهدف
    target_profit_margin = models.DecimalField(_('هامش الربح المستهدف %'), 
                                              max_digits=5, decimal_places=2, default=Decimal('0'))
    suggested_price = models.DecimalField(_('السعر المقترح'), 
                                         max_digits=15, decimal_places=2, default=Decimal('0'))
    
    # بيانات إدارية
    effective_from = models.DateField(_('ساري من'), default=timezone.localdate)
    effective_to = models.DateField(_('ساري حتى'), null=True, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                  related_name='product_costings', verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('بطاقة تكلفة منتج')
        verbose_name_plural = _('بطاقات تكاليف المنتجات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'status']),
            models.Index(fields=['status', 'effective_from']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'version'], 
                name='unique_product_costing_version'
            )
        ]
    
    def __str__(self):
        return f"{self.product.name} - إصدار {self.version} ({self.get_status_display()})"
    
    @property
    def actual_profit_margin(self):
        """هامش الربح الفعلي بناءً على سعر البيع الحالي"""
        if self.total_cost == 0:
            return Decimal('0')
        current_price = self.product.price
        if current_price == 0:
            return Decimal('0')
        return ((current_price - self.total_cost) / current_price * 100).quantize(Decimal('0.01'))
    
    def calculate_total_cost(self):
        """حساب إجمالي التكلفة من المكونات"""
        self.total_cost = (
            self.direct_material_cost + 
            self.direct_labor_cost + 
            self.overhead_cost + 
            self.other_cost
        )
        return self.total_cost
    
    def calculate_suggested_price(self):
        """حساب السعر المقترح بناءً على هامش الربح المستهدف"""
        if self.target_profit_margin == 0:
            self.suggested_price = self.total_cost
        else:
            # السعر = التكلفة / (1 - نسبة الربح)
            margin_decimal = self.target_profit_margin / Decimal('100')
            if margin_decimal >= 1:
                margin_decimal = Decimal('0.99')  # حد أقصى 99%
            self.suggested_price = (self.total_cost / (Decimal('1') - margin_decimal)).quantize(Decimal('0.01'))
        return self.suggested_price
    
    def save(self, *args, **kwargs):
        # حساب الإجماليات تلقائياً
        self.calculate_total_cost()
        self.calculate_suggested_price()
        
        # عند تفعيل بطاقة تكلفة، إلغاء تفعيل البطاقات الأخرى للمنتج نفسه
        if self.status == 'active':
            ProductCosting.objects.filter(
                product=self.product, 
                status='active'
            ).exclude(pk=self.pk).update(status='archived')
            
            # تحديث تكلفة المنتج في جدول المنتجات
            if self.total_cost > 0:
                self.product.cost = self.total_cost.quantize(Decimal('0.01'))
                self.product.save(update_fields=['cost'])
        
        super().save(*args, **kwargs)


class CostComponent(models.Model):
    """مكون تكلفة تفصيلي (مواد، عمالة، مصاريف)"""
    
    COMPONENT_TYPE_CHOICES = [
        ('material', _('مادة خام')),
        ('labor', _('عمالة')),
        ('overhead', _('تكاليف صناعية غير مباشرة')),
        ('service', _('خدمة')),
        ('other', _('أخرى')),
    ]
    
    id = models.AutoField(primary_key=True)
    costing = models.ForeignKey(ProductCosting, on_delete=models.CASCADE, 
                               related_name='components', verbose_name=_('بطاقة التكلفة'))
    component_type = models.CharField(_('نوع المكون'), max_length=20, 
                                     choices=COMPONENT_TYPE_CHOICES)
    
    # بيانات المكون
    description = models.CharField(_('الوصف'), max_length=255)
    item = models.ForeignKey('inventory.Product', on_delete=models.SET_NULL, 
                            null=True, blank=True, verbose_name=_('الصنف'))
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, 
                               null=True, blank=True, verbose_name=_('الحساب'))
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, 
                                   null=True, blank=True, verbose_name=_('مركز التكلفة'))
    
    # الكمية والتكلفة
    quantity = models.DecimalField(_('الكمية'), max_digits=15, decimal_places=4, 
                                  default=Decimal('1'))
    unit = models.CharField(_('الوحدة'), max_length=50, blank=True)
    unit_cost = models.DecimalField(_('تكلفة الوحدة'), max_digits=15, decimal_places=4, 
                                   default=Decimal('0'))
    total_cost = models.DecimalField(_('إجمالي التكلفة'), max_digits=15, decimal_places=4, 
                                    default=Decimal('0'))
    
    # نسبة تخصيص (للتكاليف غير المباشرة)
    allocation_percentage = models.DecimalField(_('نسبة التخصيص %'), 
                                               max_digits=7, decimal_places=4, 
                                               default=Decimal('0'))
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    sequence = models.PositiveIntegerField(_('الترتيب'), default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('مكون تكلفة')
        verbose_name_plural = _('مكونات التكاليف')
        ordering = ['sequence', 'component_type', 'description']
        indexes = [
            models.Index(fields=['costing', 'component_type']),
            models.Index(fields=['item']),
        ]
    
    def __str__(self):
        return f"{self.description} ({self.get_component_type_display()}) - {self.total_cost}"
    
    def calculate_total_cost(self):
        """حساب إجمالي التكلفة للمكون"""
        self.total_cost = self.quantity * self.unit_cost
        return self.total_cost
    
    def save(self, *args, **kwargs):
        # حساب إجمالي التكلفة
        self.calculate_total_cost()
        
        # استخراج الوحدة من الصنف إذا كان موجوداً
        if self.item and not self.unit:
            self.unit = self.item.get_purchase_uom_display()
        
        super().save(*args, **kwargs)
        
        # تحديث بطاقة التكلفة الرئيسية
        if self.costing:
            self.costing.recalculate_from_components()


# إضافة دالة لإعادة حساب التكلفة من المكونات
def recalculate_from_components(self):
    """إعادة حساب مكونات التكلفة من البنود التفصيلية"""
    components = self.components.all()
    
    self.direct_material_cost = components.filter(
        component_type='material'
    ).aggregate(total=models.Sum('total_cost'))['total'] or Decimal('0')
    
    self.direct_labor_cost = components.filter(
        component_type='labor'
    ).aggregate(total=models.Sum('total_cost'))['total'] or Decimal('0')
    
    self.overhead_cost = components.filter(
        component_type='overhead'
    ).aggregate(total=models.Sum('total_cost'))['total'] or Decimal('0')
    
    self.other_cost = components.filter(
        component_type__in=['service', 'other']
    ).aggregate(total=models.Sum('total_cost'))['total'] or Decimal('0')
    
    self.save()

# ربط الدالة بالنموذج
ProductCosting.recalculate_from_components = recalculate_from_components


class CostingHistory(models.Model):
    """سجل تاريخي لتغييرات التكلفة"""
    
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, 
                               related_name='costing_history', verbose_name=_('المنتج'))
    old_cost = models.DecimalField(_('التكلفة القديمة'), max_digits=15, decimal_places=4)
    new_cost = models.DecimalField(_('التكلفة الجديدة'), max_digits=15, decimal_places=4)
    change_reason = models.CharField(_('سبب التغيير'), max_length=255, blank=True)
    costing = models.ForeignKey(ProductCosting, on_delete=models.SET_NULL, 
                               null=True, blank=True, verbose_name=_('بطاقة التكلفة'))
    
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                  verbose_name=_('تم التغيير بواسطة'))
    changed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('سجل تكلفة')
        verbose_name_plural = _('سجل التكاليف')
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['product', 'changed_at']),
        ]
    
    def __str__(self):
        return f"{self.product.name}: {self.old_cost} -> {self.new_cost} ({self.changed_at:%Y-%m-%d})"
    
    @property
    def change_amount(self):
        """مقدار التغيير"""
        return self.new_cost - self.old_cost
    
    @property
    def change_percentage(self):
        """نسبة التغيير"""
        if self.old_cost == 0:
            return Decimal('0')
        return ((self.new_cost - self.old_cost) / self.old_cost * 100).quantize(Decimal('0.01'))


# Signal لتسجيل تغييرات التكلفة تلقائياً
@receiver(models.signals.post_save, sender=ProductCosting)
def log_costing_change(sender, instance, created, **kwargs):
    """تسجيل تغيير التكلفة عند تفعيل بطاقة جديدة"""
    if instance.status == 'active' and not created:
        # البحث عن آخر سجل تكلفة
        last_history = CostingHistory.objects.filter(
            product=instance.product
        ).order_by('-changed_at').first()
        
        old_cost = last_history.new_cost if last_history else instance.product.cost
        
        # تسجيل التغيير إذا كان هناك فرق
        if old_cost != instance.total_cost:
            CostingHistory.objects.create(
                product=instance.product,
                old_cost=old_cost,
                new_cost=instance.total_cost,
                change_reason=f"تحديث بطاقة التكلفة - إصدار {instance.version}",
                costing=instance,
                changed_by=instance.created_by
            )


# =============================
# نماذج التحليل المالي
# =============================

class FinancialAnalysis1(models.Model):
    """التحليل المالي الأول - قائمة مرجعية"""
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20, unique=True, verbose_name=_("الكود"))
    name = models.CharField(max_length=255, verbose_name=_("الاسم"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("تحليل مالي 1")
        verbose_name_plural = _("التحليلات المالية 1")
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class FinancialAnalysis2(models.Model):
    """التحليل المالي الثاني - قائمة مرجعية"""
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20, unique=True, verbose_name=_("الكود"))
    name = models.CharField(max_length=255, verbose_name=_("الاسم"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("تحليل مالي 2")
        verbose_name_plural = _("التحليلات المالية 2")
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class AccountEntry(models.Model):
    """قيد تسجيل الحسابات - إيراد أو منصرف"""
    ENTRY_TYPES = [
        ('revenue', _('إيراد')),
        ('expense', _('منصرف')),
    ]
    
    id = models.AutoField(primary_key=True)
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES, verbose_name=_("نوع القيد"))
    date = models.DateField(default=timezone.localdate, verbose_name=_("التاريخ"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("المبلغ"),
                                validators=[MinValueValidator(Decimal('0.01'))])
    description = models.TextField(verbose_name=_("البيان"))
    
    # الحقول المطلوبة
    ledger_account = models.ForeignKey(Account, on_delete=models.PROTECT, 
                                       verbose_name=_("حساب الأستاذ"),
                                       related_name='account_entries')
    financial_analysis_1 = models.ForeignKey(FinancialAnalysis1, on_delete=models.SET_NULL,
                                             null=True, blank=True,
                                             verbose_name=_("تحليل مالي 1"))
    financial_analysis_2 = models.ForeignKey(FinancialAnalysis2, on_delete=models.SET_NULL,
                                             null=True, blank=True,
                                             verbose_name=_("تحليل مالي 2"))
    
    # الربط بالقيد المحاسبي
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, 
                                      null=True, blank=True,
                                      related_name='account_entries',
                                      verbose_name=_("القيد المحاسبي"))
    
    # مركز التكلفة
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    verbose_name=_("مركز التكلفة"))
    
    # صاحب التوريد/العملية (حقل عام يدعم أنواع متعددة)
    # يمكن أن يكون مورد، عميل، سائق، إلخ
    owner_content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("نوع صاحب العملية"),
        help_text=_("نوع الكيان (عميل، مورد، سائق، إلخ)")
    )
    owner_object_id = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name=_("معرف صاحب العملية")
    )
    owner = GenericForeignKey('owner_content_type', 'owner_object_id')
    
    # الإبقاء على حقل المورد القديم للتوافق مع البيانات الموجودة
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.SET_NULL,
                                 null=True, blank=True,
                                 related_name='revenue_entries',
                                 verbose_name=_("صاحب التوريد (قديم)"),
                                 help_text=_("استخدم حقل 'صاحب العملية' الجديد بدلاً من هذا"))
    
    # وجهة الدخول/الخروج (أين دخلت/خرجت الأموال)
    DESTINATION_TYPE_CHOICES = [
        ('treasury', _('خزينة')),
        ('bank', _('بنك')),
        ('electronic', _('حساب إلكتروني')),
        ('fawry', _('ماكينة فوري')),
        ('visa', _('ماكينة فيزا')),
    ]
    destination_type = models.CharField(max_length=20, choices=DESTINATION_TYPE_CHOICES,
                                       null=True, blank=True,
                                       verbose_name=_("نوع الوجهة"),
                                       help_text=_("أين دخلت/خرجت الأموال"))
    
    # علاقات اختيارية مع البنوك، الحسابات الإلكترونية، والخزائن
    treasury = models.ForeignKey(Treasury, on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name='account_entries',
                                verbose_name=_("الخزينة"))
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL,
                            null=True, blank=True,
                            related_name='account_entries',
                            verbose_name=_("البنك"))
    electronic_account = models.ForeignKey(ElectronicAccount, on_delete=models.SET_NULL,
                                          null=True, blank=True,
                                          related_name='account_entries',
                                          verbose_name=_("الحساب الإلكتروني"))
    fawry_machine = models.ForeignKey(FawryMachine, on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                     related_name='account_entries',
                                     verbose_name=_("ماكينة الفوري"))
    visa_machine = models.ForeignKey(VisaMachine, on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name='account_entries',
                                    verbose_name=_("ماكينة الفيزا"))
    
    # حقول التتبع
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, 
                                   related_name='created_account_entries',
                                   verbose_name=_("أنشئ بواسطة"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("قيد حساب")
        verbose_name_plural = _("قيود الحسابات")
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['entry_type', 'date']),
            models.Index(fields=['ledger_account']),
            models.Index(fields=['financial_analysis_1']),
            models.Index(fields=['financial_analysis_2']),
            models.Index(fields=['owner_content_type', 'owner_object_id']),
            models.Index(fields=['destination_type']),
            models.Index(fields=['treasury']),
            models.Index(fields=['bank']),
            models.Index(fields=['electronic_account']),
            models.Index(fields=['fawry_machine']),
            models.Index(fields=['visa_machine']),
        ]
    
    def __str__(self):
        return f"{self.get_entry_type_display()} - {self.amount} - {self.date}"
    
    @property
    def owner_name(self):
        """الحصول على اسم صاحب العملية"""
        if self.owner:
            return getattr(self.owner, 'name', None) or getattr(self.owner, 'full_name', str(self.owner))
        elif self.supplier:  # التوافق مع الحقل القديم
            return self.supplier.name
        return None
    
    @property
    def destination_name(self):
        """الحصول على اسم الوجهة"""
        if self.destination_type == 'treasury' and self.treasury:
            return str(self.treasury)
        elif self.destination_type == 'bank' and self.bank:
            return str(self.bank)
        elif self.destination_type == 'electronic' and self.electronic_account:
            return str(self.electronic_account)
        elif self.destination_type == 'fawry' and self.fawry_machine:
            return str(self.fawry_machine)
        elif self.destination_type == 'visa' and self.visa_machine:
            return str(self.visa_machine)
        return None
    
    def clean(self):
        """التحقق من تطابق نوع الوجهة مع الحقل المحدد"""
        if self.destination_type:
            if self.destination_type == 'treasury' and not self.treasury:
                raise ValidationError({'treasury': _('يجب تحديد الخزينة عند اختيار نوع الوجهة "خزينة"')})
            elif self.destination_type == 'bank' and not self.bank:
                raise ValidationError({'bank': _('يجب تحديد البنك عند اختيار نوع الوجهة "بنك"')})
            elif self.destination_type == 'electronic' and not self.electronic_account:
                raise ValidationError({'electronic_account': _('يجب تحديد الحساب الإلكتروني عند اختيار نوع الوجهة "حساب إلكتروني"')})
            elif self.destination_type == 'fawry' and not self.fawry_machine:
                raise ValidationError({'fawry_machine': _('يجب تحديد ماكينة الفوري عند اختيار نوع الوجهة "ماكينة فوري"')})
            elif self.destination_type == 'visa' and not self.visa_machine:
                raise ValidationError({'visa_machine': _('يجب تحديد ماكينة الفيزا عند اختيار نوع الوجهة "ماكينة فيزا"')})


# ==================== الميزات الجديدة المتقدمة ====================

class BankReconciliation(models.Model):
    """التسويات البنكية الذكية مع المطابقة التلقائية"""
    RECONCILIATION_STATUS = [
        ('in_progress', _('جاري التسوية')),
        ('completed', _('مكتملة')),
        ('needs_review', _('تحتاج مراجعة')),
        ('approved', _('معتمدة')),
    ]
    
    id = models.AutoField(primary_key=True)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name=_('البنك'))
    bank_statement = models.FileField(upload_to='bank_statements/%Y/%m/', 
                                     verbose_name=_('كشف الحساب البنكي'),
                                     help_text=_('ملف CSV أو Excel من البنك'))
    period_start = models.DateField(verbose_name=_('بداية الفترة'))
    period_end = models.DateField(verbose_name=_('نهاية الفترة'))
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, 
                                         verbose_name=_('الرصيد الافتتاحي'))
    closing_balance = models.DecimalField(max_digits=15, decimal_places=2,
                                         verbose_name=_('الرصيد الختامي'))
    status = models.CharField(max_length=20, choices=RECONCILIATION_STATUS, 
                            default='in_progress', verbose_name=_('الحالة'))
    auto_matched_count = models.IntegerField(default=0, verbose_name=_('عدد المطابقات التلقائية'))
    manual_matched_count = models.IntegerField(default=0, verbose_name=_('عدد المطابقات اليدوية'))
    unmatched_items = models.JSONField(default=dict, verbose_name=_('البنود غير المطابقة'))
    matched_items = models.JSONField(default=dict, verbose_name=_('البنود المطابقة'))
    difference_amount = models.DecimalField(max_digits=15, decimal_places=2, 
                                           default=Decimal('0'),
                                           verbose_name=_('فرق التسوية'))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                  related_name='reconciliations_created',
                                  verbose_name=_('أنشئ بواسطة'))
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='reconciliations_approved',
                                   verbose_name=_('اعتمد بواسطة'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))

    class Meta:
        verbose_name = _('تسوية بنكية')
        verbose_name_plural = _('التسويات البنكية')
        ordering = ['-period_end', '-created_at']
        indexes = [
            models.Index(fields=['bank', 'period_start', 'period_end']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.bank.name} - {self.period_start} إلى {self.period_end}"


class RecurringJournalEntry(models.Model):
    """القيود المحاسبية المتكررة والجدولة التلقائية"""
    FREQUENCY_CHOICES = [
        ('daily', _('يومي')),
        ('weekly', _('أسبوعي')),
        ('biweekly', _('كل أسبوعين')),
        ('monthly', _('شهري')),
        ('quarterly', _('ربع سنوي')),
        ('semiannually', _('نصف سنوي')),
        ('yearly', _('سنوي')),
    ]
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name=_('اسم القيد المتكرر'))
    template = models.ForeignKey(JournalEntryTemplate, on_delete=models.CASCADE,
                                verbose_name=_('قالب القيد'))
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES,
                                verbose_name=_('التكرار'))
    start_date = models.DateField(verbose_name=_('تاريخ البداية'))
    end_date = models.DateField(null=True, blank=True, verbose_name=_('تاريخ النهاية'))
    next_execution = models.DateField(verbose_name=_('التنفيذ التالي'))
    last_execution = models.DateTimeField(null=True, blank=True, 
                                         verbose_name=_('آخر تنفيذ'))
    auto_post = models.BooleanField(default=False, 
                                   verbose_name=_('ترحيل تلقائي'),
                                   help_text=_('إذا كان True، سيتم ترحيل القيد تلقائياً'))
    is_active = models.BooleanField(default=True, verbose_name=_('نشط'))
    notify_before_days = models.IntegerField(default=3, 
                                            verbose_name=_('التنبيه قبل (أيام)'))
    execution_count = models.IntegerField(default=0, 
                                         verbose_name=_('عدد مرات التنفيذ'))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                  verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('قيد متكرر')
        verbose_name_plural = _('القيود المتكررة')
        ordering = ['next_execution']
        indexes = [
            models.Index(fields=['is_active', 'next_execution']),
        ]

    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"

    def calculate_next_execution(self):
        """حساب موعد التنفيذ التالي"""
        if not self.last_execution:
            return self.start_date
        
        last_date = self.last_execution.date() if isinstance(self.last_execution, timezone.datetime) else self.last_execution
        
        if self.frequency == 'daily':
            return last_date + timedelta(days=1)
        elif self.frequency == 'weekly':
            return last_date + timedelta(weeks=1)
        elif self.frequency == 'biweekly':
            return last_date + timedelta(weeks=2)
        elif self.frequency == 'monthly':
            return last_date + timedelta(days=30)
        elif self.frequency == 'quarterly':
            return last_date + timedelta(days=90)
        elif self.frequency == 'semiannually':
            return last_date + timedelta(days=180)
        elif self.frequency == 'yearly':
            return last_date + timedelta(days=365)
        return last_date


class BudgetItem(models.Model):
    """الموازنات التخطيطية لكل حساب ومركز تكلفة"""
    id = models.AutoField(primary_key=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE,
                               verbose_name=_('الحساب'))
    cost_center = models.ForeignKey(CostCenter, on_delete=models.CASCADE, 
                                   null=True, blank=True,
                                   verbose_name=_('مركز التكلفة'))
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE,
                                   verbose_name=_('السنة المالية'))
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)],
                               verbose_name=_('الشهر'))
    budgeted_amount = models.DecimalField(max_digits=15, decimal_places=2,
                                         verbose_name=_('المبلغ المدرج بالموازنة'))
    actual_amount = models.DecimalField(max_digits=15, decimal_places=2, 
                                       default=Decimal('0'),
                                       verbose_name=_('المبلغ الفعلي'))
    variance_amount = models.DecimalField(max_digits=15, decimal_places=2,
                                         default=Decimal('0'),
                                         verbose_name=_('فرق المبلغ'))
    variance_percentage = models.DecimalField(max_digits=5, decimal_places=2,
                                             default=Decimal('0'),
                                             verbose_name=_('نسبة الفرق %'))
    is_locked = models.BooleanField(default=False, verbose_name=_('مقفل'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('بند موازنة')
        verbose_name_plural = _('بنود الموازنات')
        ordering = ['fiscal_year', 'month', 'account']
        unique_together = [['account', 'cost_center', 'fiscal_year', 'month']]
        indexes = [
            models.Index(fields=['fiscal_year', 'month']),
            models.Index(fields=['account']),
        ]

    def __str__(self):
        return f"{self.account.name} - {self.fiscal_year} - شهر {self.month}"

    def save(self, *args, **kwargs):
        # حساب الفرق والنسبة
        self.variance_amount = self.actual_amount - self.budgeted_amount
        if self.budgeted_amount != 0:
            self.variance_percentage = (self.variance_amount / self.budgeted_amount) * 100
        super().save(*args, **kwargs)


class Asset(models.Model):
    """الأصول الثابتة مع حساب الإهلاك التلقائي"""
    DEPRECIATION_METHOD = [
        ('straight_line', _('القسط الثابت')),
        ('declining_balance', _('القسط المتناقص')),
        ('units_of_production', _('وحدات الإنتاج')),
        ('sum_of_years', _('مجموع السنين')),
    ]
    
    ASSET_STATUS = [
        ('active', _('نشط')),
        ('disposed', _('تم التصرف فيه')),
        ('fully_depreciated', _('تم إهلاكه بالكامل')),
        ('under_maintenance', _('تحت الصيانة')),
    ]
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name=_('اسم الأصل'))
    code = models.CharField(max_length=50, unique=True, verbose_name=_('رمز الأصل'))
    account = models.ForeignKey(Account, on_delete=models.PROTECT,
                               related_name='assets',
                               verbose_name=_('حساب الأصل'))
    accumulated_depreciation_account = models.ForeignKey(Account, on_delete=models.PROTECT,
                                                        related_name='accumulated_depreciation_assets',
                                                        verbose_name=_('حساب مجمع الإهلاك'))
    depreciation_expense_account = models.ForeignKey(Account, on_delete=models.PROTECT,
                                                    related_name='depreciation_expense_assets',
                                                    verbose_name=_('حساب مصروف الإهلاك'))
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, 
                                   null=True, blank=True,
                                   verbose_name=_('مركز التكلفة'))
    purchase_date = models.DateField(verbose_name=_('تاريخ الشراء'))
    purchase_cost = models.DecimalField(max_digits=15, decimal_places=2,
                                       verbose_name=_('تكلفة الشراء'))
    salvage_value = models.DecimalField(max_digits=15, decimal_places=2,
                                       default=Decimal('0'),
                                       verbose_name=_('قيمة الخردة'))
    useful_life_years = models.IntegerField(verbose_name=_('العمر الإنتاجي (سنوات)'))
    useful_life_months = models.IntegerField(default=0, 
                                            verbose_name=_('العمر الإنتاجي (أشهر إضافية)'))
    depreciation_method = models.CharField(max_length=30, 
                                          choices=DEPRECIATION_METHOD,
                                          default='straight_line',
                                          verbose_name=_('طريقة الإهلاك'))
    depreciation_rate = models.DecimalField(max_digits=5, decimal_places=2,
                                           null=True, blank=True,
                                           verbose_name=_('معدل الإهلاك %'))
    accumulated_depreciation = models.DecimalField(max_digits=15, decimal_places=2,
                                                  default=Decimal('0'),
                                                  verbose_name=_('مجمع الإهلاك'))
    book_value = models.DecimalField(max_digits=15, decimal_places=2,
                                    verbose_name=_('القيمة الدفترية'))
    last_depreciation_date = models.DateField(null=True, blank=True,
                                             verbose_name=_('تاريخ آخر إهلاك'))
    status = models.CharField(max_length=30, choices=ASSET_STATUS,
                            default='active', verbose_name=_('الحالة'))
    location = models.CharField(max_length=200, blank=True, 
                               verbose_name=_('الموقع'))
    serial_number = models.CharField(max_length=100, blank=True,
                                    verbose_name=_('الرقم التسلسلي'))
    supplier = models.CharField(max_length=200, blank=True,
                               verbose_name=_('المورد'))
    warranty_expiry = models.DateField(null=True, blank=True,
                                      verbose_name=_('انتهاء الضمان'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('أصل ثابت')
        verbose_name_plural = _('الأصول الثابتة')
        ordering = ['code']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['purchase_date']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        # حساب القيمة الدفترية
        self.book_value = self.purchase_cost - self.accumulated_depreciation
        super().save(*args, **kwargs)

    def calculate_monthly_depreciation(self):
        """حساب الإهلاك الشهري"""
        if self.depreciation_method == 'straight_line':
            return self._calculate_straight_line_monthly()
        elif self.depreciation_method == 'sum_of_years':
            return self._calculate_sum_of_years_monthly()
        elif self.depreciation_method == 'declining_balance':
            return self._calculate_declining_balance_monthly()
        return Decimal('0')

    def _calculate_straight_line_monthly(self):
        total_months = (self.useful_life_years * 12) + self.useful_life_months
        if total_months <= 0:
            return Decimal('0')
        depreciable_amount = self.purchase_cost - self.salvage_value
        return depreciable_amount / Decimal(total_months)

    def _calculate_sum_of_years_monthly(self):
        # مجموع أرقام السنين: (n * (n + 1)) / 2
        # القسط السنوي = (العمر المتبقي / مجموع السنين) * (التكلفة - الخردة)
        # نحسب القسط الشهري بقسمة السنوي على 12
        
        years = self.useful_life_years
        if years <= 0:
            return Decimal('0')
            
        sum_of_years = (years * (years + 1)) // 2
        depreciable_amount = self.purchase_cost - self.salvage_value
        
        # تحديد السنة الحالية للأصل (1, 2, 3...)
        today = date.today()
        # حساب عدد السنوات المنقضية بدقة
        # إذا لم يتم الإهلاك من قبل، نبدأ من تاريخ الشراء
        start_date = self.purchase_date
        
        # حساب الفرق بالسنوات
        years_elapsed = today.year - start_date.year
        
        # التأكد من أننا في سنة صالحة
        current_year_of_life = years_elapsed + 1
        
        if current_year_of_life > years:
            return Decimal('0') # انتهى العمر الافتراضي
            
        # العمر المتبقي (معكوس السنة الحالية)
        # السنة 1: المتبقي n
        # السنة 2: المتبقي n-1
        remaining_life = years - current_year_of_life + 1
        
        annual_depreciation = (Decimal(remaining_life) / Decimal(sum_of_years)) * depreciable_amount
        return annual_depreciation / Decimal('12')

    def _calculate_declining_balance_monthly(self):
        # القسط المتناقص المزدوج (Double Declining Balance) عادة
        # أو استخدام المعدل المحدد إذا وجد
        # المعدل = (1 / العمر) * 2 (للمضاعف) أو النسبة المحددة
        
        if self.book_value <= self.salvage_value:
            return Decimal('0')
            
        rate = self.depreciation_rate
        if not rate:
            # افتراض القسط المتناقص المزدوج إذا لم يحدد معدل
            if self.useful_life_years > 0:
                rate = (Decimal('1') / Decimal(self.useful_life_years)) * Decimal('2')
            else:
                return Decimal('0')
        else:
            rate = rate / Decimal('100')
            
        annual_depreciation = self.book_value * rate
        # التحقق من عدم تجاوز القيمة المتبقية للخردة
        monthly = annual_depreciation / Decimal('12')
        
        if self.book_value - monthly < self.salvage_value:
            return self.book_value - self.salvage_value
            
        return monthly


class DepreciationEntry(models.Model):
    """سجل قيود الإهلاك"""
    id = models.AutoField(primary_key=True)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE,
                             related_name='depreciation_entries',
                             verbose_name=_('الأصل'))
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE,
                                     null=True, blank=True,
                                     verbose_name=_('القيد المحاسبي'))
    depreciation_date = models.DateField(verbose_name=_('تاريخ الإهلاك'))
    depreciation_amount = models.DecimalField(max_digits=15, decimal_places=2,
                                             verbose_name=_('مبلغ الإهلاك'))
    accumulated_depreciation_before = models.DecimalField(max_digits=15, decimal_places=2,
                                                         verbose_name=_('مجمع الإهلاك قبل'))
    accumulated_depreciation_after = models.DecimalField(max_digits=15, decimal_places=2,
                                                        verbose_name=_('مجمع الإهلاك بعد'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('قيد إهلاك')
        verbose_name_plural = _('قيود الإهلاك')
        ordering = ['-depreciation_date']

    def __str__(self):
        return f"{self.asset.name} - {self.depreciation_date}"


class AccountingAuditLog(models.Model):
    """سجل المراجعة المحاسبية الشامل لجميع التعديلات"""
    ACTION_TYPES = [
        ('create', _('إنشاء')),
        ('update', _('تعديل')),
        ('delete', _('حذف')),
        ('post', _('ترحيل')),
        ('unpost', _('إلغاء ترحيل')),
        ('approve', _('اعتماد')),
        ('reject', _('رفض')),
    ]
    
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                            related_name='accounting_audit_logs',
                            verbose_name=_('المستخدم'))
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES,
                                  verbose_name=_('نوع الإجراء'))
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE,
                                    related_name='accounting_audit_logs',
                                    verbose_name=_('نوع السجل'))
    object_id = models.PositiveIntegerField(verbose_name=_('معرف السجل'))
    content_object = GenericForeignKey('content_type', 'object_id')
    object_repr = models.CharField(max_length=200, verbose_name=_('تمثيل السجل'))
    changes = models.JSONField(verbose_name=_('التغييرات'))
    ip_address = models.GenericIPAddressField(null=True, blank=True,
                                             verbose_name=_('عنوان IP'))
    user_agent = models.TextField(blank=True, verbose_name=_('متصفح المستخدم'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('الوقت'))

    class Meta:
        verbose_name = _('سجل مراجعة')
        verbose_name_plural = _('سجلات المراجعة')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action_type']),
        ]

    def __str__(self):
        return f"{self.user} - {self.get_action_type_display()} - {self.object_repr}"


class AccountingApprovalWorkflow(models.Model):
    """سير عمل الموافقات المتعددة المستويات للمحاسبة"""
    WORKFLOW_STATUS = [
        ('pending', _('قيد الانتظار')),
        ('approved', _('معتمد')),
        ('rejected', _('مرفوض')),
        ('cancelled', _('ملغى')),
    ]
    
    id = models.AutoField(primary_key=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE,
                                    related_name='accounting_approval_workflows',
                                    verbose_name=_('نوع السجل'))
    object_id = models.PositiveIntegerField(verbose_name=_('معرف السجل'))
    content_object = GenericForeignKey('content_type', 'object_id')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                    related_name='accounting_approval_requests',
                                    verbose_name=_('طلب بواسطة'))
    current_approver = models.ForeignKey(User, on_delete=models.SET_NULL,
                                        null=True, blank=True,
                                        related_name='pending_approvals',
                                        verbose_name=_('المعتمد الحالي'))
    status = models.CharField(max_length=20, choices=WORKFLOW_STATUS,
                            default='pending', verbose_name=_('الحالة'))
    approval_level = models.IntegerField(default=1, 
                                        verbose_name=_('مستوى الاعتماد'))
    total_levels = models.IntegerField(default=1,
                                      verbose_name=_('إجمالي المستويات'))
    request_date = models.DateTimeField(auto_now_add=True,
                                       verbose_name=_('تاريخ الطلب'))
    approved_date = models.DateTimeField(null=True, blank=True,
                                        verbose_name=_('تاريخ الاعتماد'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))

    class Meta:
        verbose_name = _('سير عمل موافقة')
        verbose_name_plural = _('سير عمل الموافقات')
        ordering = ['-request_date']

    def __str__(self):
        return f"موافقة - {self.requested_by} - {self.get_status_display()}"


class PeriodClose(models.Model):
    """إقفال الفترات المالية"""
    PERIOD_TYPE = [
        ('monthly', _('شهري')),
        ('quarterly', _('ربع سنوي')),
        ('yearly', _('سنوي')),
    ]
    
    CLOSE_STATUS = [
        ('open', _('مفتوح')),
        ('in_progress', _('جاري الإقفال')),
        ('closed', _('مقفل')),
        ('reopened', _('أعيد فتحه')),
    ]
    
    id = models.AutoField(primary_key=True)
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE,
                                   verbose_name=_('السنة المالية'))
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPE,
                                  verbose_name=_('نوع الفترة'))
    period_number = models.IntegerField(verbose_name=_('رقم الفترة'))
    period_start = models.DateField(verbose_name=_('بداية الفترة'))
    period_end = models.DateField(verbose_name=_('نهاية الفترة'))
    status = models.CharField(max_length=20, choices=CLOSE_STATUS,
                            default='open', verbose_name=_('الحالة'))
    checklist_completed = models.BooleanField(default=False,
                                             verbose_name=_('تم إكمال قائمة التحقق'))
    closing_entries_created = models.BooleanField(default=False,
                                                  verbose_name=_('تم إنشاء قيود الإقفال'))
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                 null=True, blank=True,
                                 related_name='periods_closed',
                                 verbose_name=_('أقفل بواسطة'))
    closed_at = models.DateTimeField(null=True, blank=True,
                                    verbose_name=_('تاريخ الإقفال'))
    reopened_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='periods_reopened',
                                   verbose_name=_('أعيد فتحه بواسطة'))
    reopened_at = models.DateTimeField(null=True, blank=True,
                                      verbose_name=_('تاريخ إعادة الفتح'))
    reopen_reason = models.TextField(blank=True, 
                                    verbose_name=_('سبب إعادة الفتح'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('إقفال فترة')
        verbose_name_plural = _('إقفالات الفترات')
        ordering = ['-period_end']
        unique_together = [['fiscal_year', 'period_type', 'period_number']]

    def __str__(self):
        return f"{self.get_period_type_display()} - {self.period_start} إلى {self.period_end}"


class CustomReport(models.Model):
    """محرك التقارير المخصصة"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name=_('اسم التقرير'))
    description = models.TextField(blank=True, verbose_name=_('الوصف'))
    report_type = models.CharField(max_length=50, verbose_name=_('نوع التقرير'))
    filters = models.JSONField(default=dict, verbose_name=_('الفلاتر'))
    columns = models.JSONField(default=list, verbose_name=_('الأعمدة'))
    grouping = models.JSONField(default=list, verbose_name=_('التجميع'))
    sorting = models.JSONField(default=list, verbose_name=_('الترتيب'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                  verbose_name=_('أنشئ بواسطة'))
    is_public = models.BooleanField(default=False, 
                                   verbose_name=_('تقرير عام'))
    schedule_enabled = models.BooleanField(default=False,
                                          verbose_name=_('تفعيل الجدولة'))
    schedule_frequency = models.CharField(max_length=20, blank=True,
                                         verbose_name=_('تكرار الجدولة'))
    schedule_recipients = models.JSONField(default=list,
                                          verbose_name=_('مستلمو التقرير'))
    execution_count = models.IntegerField(default=0,
                                         verbose_name=_('عدد مرات التشغيل'))
    last_execution = models.DateTimeField(null=True, blank=True,
                                         verbose_name=_('آخر تشغيل'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('تقرير مخصص')
        verbose_name_plural = _('التقارير المخصصة')
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ReceivableAging(models.Model):
    """تقرير أعمار الديون (الذمم المدينة)"""
    id = models.AutoField(primary_key=True)
    partner = models.ForeignKey('partners.Partner', on_delete=models.CASCADE,
                                verbose_name=_('الشريك/العميل'))
    # customer = models.ForeignKey('sales.Customer', on_delete=models.CASCADE,
    #                            verbose_name=_('العميل'))
    invoice_number = models.CharField(max_length=50, verbose_name=_('رقم الفاتورة'))
    # invoice = models.ForeignKey('sales.Invoice', on_delete=models.CASCADE,
    #                            verbose_name=_('الفاتورة'))
    invoice_date = models.DateField(verbose_name=_('تاريخ الفاتورة'))
    due_date = models.DateField(verbose_name=_('تاريخ الاستحقاق'))
    total_amount = models.DecimalField(max_digits=15, decimal_places=2,
                                      verbose_name=_('المبلغ الإجمالي'))
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2,
                                     default=Decimal('0'),
                                     verbose_name=_('المبلغ المدفوع'))
    balance = models.DecimalField(max_digits=15, decimal_places=2,
                                 verbose_name=_('الرصيد المتبقي'))
    days_overdue = models.IntegerField(default=0, 
                                      verbose_name=_('أيام التأخير'))
    aging_bucket = models.CharField(max_length=20, 
                                   verbose_name=_('فئة العمر'))
    snapshot_date = models.DateField(auto_now_add=True,
                                    verbose_name=_('تاريخ اللقطة'))

    class Meta:
        verbose_name = _('عمر دين')
        verbose_name_plural = _('أعمار الديون')
        ordering = ['partner', 'due_date']
        indexes = [
            models.Index(fields=['partner', 'aging_bucket']),
            models.Index(fields=['snapshot_date']),
        ]

    def __str__(self):
        return f"{self.partner} - {self.invoice_number} - {self.aging_bucket}"
