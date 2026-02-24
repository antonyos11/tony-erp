from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, EmailValidator
from decimal import Decimal
from django.utils import timezone
from django.db.models import Q
from django.core.validators import MinValueValidator, MaxValueValidator

# Customer Management Models
class CustomerType(models.Model):
    """أنواع العملاء"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField(max_length=100, verbose_name="اسم النوع")
    description = models.TextField(blank=True, verbose_name="وصف")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), verbose_name="نسبة خصم افتراضية")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "نوع العميل"
        verbose_name_plural = "أنواع العملاء"
    
    def __str__(self):
        return self.name

class CustomerSource(models.Model):
    """مصادر العملاء"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField(max_length=100, verbose_name="اسم المصدر")
    description = models.TextField(blank=True, verbose_name="وصف")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    class Meta:
        verbose_name = "مصدر العميل"
        verbose_name_plural = "مصادر العملاء"
    
    def __str__(self):
        return self.name

class Customer(models.Model):
    """العملاء الأساسيون"""
    GENDER_CHOICES = [
        ('male', 'ذكر'),
        ('female', 'أنثى'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    STATUS_CHOICES = [
        ('active', 'نشط'),
        ('inactive', 'غير نشط'),
        ('blacklisted', 'في القائمة السوداء'),
    ]
    
    # Basic Information
    customer_code = models.CharField(max_length=20, unique=True, verbose_name="كود العميل")
    first_name = models.CharField(max_length=100, verbose_name="الاسم الأول")
    last_name = models.CharField(max_length=100, verbose_name="اسم العائلة")
    company_name = models.CharField(max_length=200, blank=True, verbose_name="اسم الشركة")
    
    # Contact Information
    phone = models.CharField(max_length=20, verbose_name="الهاتف")
    mobile = models.CharField(max_length=20, blank=True, verbose_name="الموبايل")
    email = models.EmailField(blank=True, verbose_name="البريد الإلكتروني")
    website = models.URLField(blank=True, verbose_name="الموقع الإلكتروني")
    
    # Address Information
    address_line1 = models.CharField(max_length=255, blank=True, verbose_name="العنوان 1")
    address_line2 = models.CharField(max_length=255, blank=True, verbose_name="العنوان 2")
    city = models.CharField(max_length=100, blank=True, verbose_name="المدينة")
    state = models.CharField(max_length=100, blank=True, verbose_name="المحافظة")
    postal_code = models.CharField(max_length=20, blank=True, verbose_name="الرمز البريدي")
    country = models.CharField(max_length=100, default="مصر", verbose_name="البلد")
    
    # Personal Information
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="تاريخ الميلاد")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, verbose_name="الجنس")
    national_id = models.CharField(max_length=50, blank=True, verbose_name="الرقم القومي")
    
    # Business Information
    customer_type = models.ForeignKey(CustomerType, on_delete=models.PROTECT, null=True, verbose_name="نوع العميل")
    source = models.ForeignKey(CustomerSource, on_delete=models.PROTECT, null=True, verbose_name="مصدر العميل")
    tax_number = models.CharField(max_length=50, blank=True, verbose_name="الرقم الضريبي")
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), verbose_name="حد الائتمان")
    payment_terms = models.CharField(max_length=100, blank=True, verbose_name="شروط الدفع")
    
    # Status and Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="الحالة")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    assigned_to = models.ForeignKey(User, on_delete=models.PROTECT, null=True, verbose_name="مسؤول الحساب")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    last_contact_date = models.DateTimeField(null=True, blank=True, verbose_name="آخر تاريخ تواصل")
    
    class Meta:
        verbose_name = "عميل"
        verbose_name_plural = "العملاء"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone'], name='crm_customer_phone_idx'),
            models.Index(fields=['mobile'], name='crm_customer_mobile_idx'),
            models.Index(fields=['first_name'], name='crm_customer_fname_idx'),
            models.Index(fields=['last_name'], name='crm_customer_lname_idx'),
            models.Index(fields=['company_name'], name='crm_customer_company_idx'),
            models.Index(fields=['first_name', 'last_name'], name='crm_customer_fullname_idx'),
        ]
    
    def __str__(self):
        return f"{self.customer_code} - {self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def full_address(self):
        parts = [self.address_line1, self.address_line2, self.city, self.state, self.country]
        return ", ".join([part for part in parts if part])

    def save(self, *args, **kwargs):
        """توليد كود عميل فريد إذا لم يُحدد.
        يعتمد على أعلى رقم متاح بصيغة CUS00001 مع تجاوز الفجوات وضمان عدم التكرار.
        """
        if not self.customer_code:
            prefix = 'CUS'
            # جلب آخر كود بالتسلسل (ترتيب أبجدي يعمل لأن الأرقام مصفَّرة يساراً)
            last = Customer.objects.filter(customer_code__startswith=prefix).order_by('-customer_code').first()
            next_num = 1
            if last:
                import re
                m = re.match(r'^CUS(\d+)$', last.customer_code)
                if m:
                    next_num = int(m.group(1)) + 1
            # تأكيد التفرد (في حال وجود فراغات أو تداخل أثناء السباق)
            while Customer.objects.filter(customer_code=f"{prefix}{next_num:05d}").exists():
                next_num += 1
            self.customer_code = f"{prefix}{next_num:05d}"
        super().save(*args, **kwargs)

# Contact Management
class ContactPerson(models.Model):
    """جهات الاتصال للعملاء"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    customer = models.ForeignKey(Customer, related_name='contacts', on_delete=models.CASCADE, verbose_name="العميل")
    name = models.CharField(max_length=200, verbose_name="الاسم")
    position = models.CharField(max_length=100, blank=True, verbose_name="المنصب")
    phone = models.CharField(max_length=20, blank=True, verbose_name="الهاتف")
    mobile = models.CharField(max_length=20, blank=True, verbose_name="الموبايل")
    email = models.EmailField(blank=True, verbose_name="البريد الإلكتروني")
    is_primary = models.BooleanField(default=False, verbose_name="جهة اتصال رئيسية")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "جهة الاتصال"
        verbose_name_plural = "جهات الاتصال"
    
    def __str__(self):
        return f"{self.name} - {self.customer.full_name}"

# Opportunity Management
class OpportunityStage(models.Model):
    """مراحل الفرصة التجارية"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField(max_length=100, verbose_name="اسم المرحلة")
    order = models.PositiveIntegerField(verbose_name="الترتيب")
    probability = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="احتمالية النجاح %")
    is_won = models.BooleanField(default=False, verbose_name="مرحلة ربح")
    is_lost = models.BooleanField(default=False, verbose_name="مرحلة خسارة")
    
    class Meta:
        verbose_name = "مرحلة الفرصة"
        verbose_name_plural = "مراحل الفرصة"
        ordering = ['order']
    
    def __str__(self):
        return self.name

class Opportunity(models.Model):
    """الفرص التجارية"""
    PRIORITY_CHOICES = [
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
        ('urgent', 'عاجل'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    name = models.CharField(max_length=200, verbose_name="اسم الفرصة")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="العميل")
    contact_person = models.ForeignKey(ContactPerson, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="جهة الاتصال")
    
    # Financial Information
    estimated_value = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="القيمة المقدرة")
    probability = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="احتمالية النجاح %")
    expected_close_date = models.DateField(verbose_name="التاريخ المتوقع للإغلاق")
    
    # Status and Tracking
    stage = models.ForeignKey(OpportunityStage, on_delete=models.PROTECT, verbose_name="المرحلة")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name="الأولوية")
    assigned_to = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="مسؤول المبيعات")
    
    # Details
    description = models.TextField(blank=True, verbose_name="وصف الفرصة")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإغلاق")
    # من أغلق الصفقة (يرتبط بموظف الموارد البشرية)
    closed_by = models.ForeignKey('hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="أُغلقت بواسطة")
    
    class Meta:
        verbose_name = "فرصة تجارية"
        verbose_name_plural = "فرص تجارية"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.customer.full_name}"
    
    @property
    def is_overdue(self):
        return self.expected_close_date < timezone.now().date() and not self.stage.is_won and not self.stage.is_lost


class CommissionScheme(models.Model):
    """
    سياسة عمولة المبيعات.
    - يمكن تحديد سياسة افتراضية للجميع أو سياسة خاصة لكل موظف مبيعات.
    """
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField(max_length=200, verbose_name="اسم السياسة")
    employee = models.ForeignKey('hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="الموظف")
    percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="نسبة العمولة %")
    start_date = models.DateField(null=True, blank=True, verbose_name="تاريخ البداية")
    end_date = models.DateField(null=True, blank=True, verbose_name="تاريخ النهاية")
    is_active = models.BooleanField(default=True, verbose_name="نشطة")
    is_default = models.BooleanField(default=False, verbose_name="افتراضية")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "سياسة عمولة"
        verbose_name_plural = "سياسات العمولات"

    def __str__(self):
        who = self.employee.arabic_name if self.employee else 'افتراضي'
        return f"{self.name} - {who} ({self.percentage}%)"

    @classmethod
    def get_for_employee(cls, employee, on_date=None):
        """إرجاع أنسب سياسة فعّالة للموظف (أولوية لسياسة الموظف ثم الافتراضية)."""
        if on_date is None:
            on_date = timezone.now().date()
        qs = cls.objects.filter(is_active=True).filter(
            Q(start_date__isnull=True) | Q(start_date__lte=on_date),
            Q(end_date__isnull=True) | Q(end_date__gte=on_date)
        )
        # سياسة محددة للموظف
        if employee:
            emp_scheme = qs.filter(employee=employee).order_by('-start_date').first()
            if emp_scheme:
                return emp_scheme
        # سياسة افتراضية
        default_scheme = qs.filter(is_default=True, employee__isnull=True).order_by('-start_date').first()
        return default_scheme


class CommissionAccrual(models.Model):
    """
    قيود استحقاق عمولات المبيعات المرتبطة بعروض الأسعار/الفرص.
    """
    STATUS_CHOICES = [
        ('accrued', 'مستحقة'),
        ('paid', 'مدفوعة'),
        ('cancelled', 'ملغاة'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking

    employee = models.ForeignKey('hr.Employee', on_delete=models.PROTECT, verbose_name="الموظف")
    opportunity = models.ForeignKey('Opportunity', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="الفرصة")
    quotation = models.ForeignKey('Quotation', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="عرض السعر")
    percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="النسبة %")
    base_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="قيمة الأساس")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="مبلغ العمولة")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='accrued', verbose_name="الحالة")
    accrued_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الاستحقاق")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الدفع")
    journal_entry = models.ForeignKey('accounting.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="قيد محاسبي")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="أُنشئ بواسطة")

    class Meta:
        verbose_name = "عمولة مستحقة"
        verbose_name_plural = "عمولات مستحقة"
        ordering = ['-accrued_at']

    def __str__(self):
        return f"عمولة {self.amount} للموظف {self.employee.arabic_name}"

    @classmethod
    def create_for_quotation(cls, quotation, employee, created_by=None):
        """
        إنشاء استحقاق عمولة لعرض سعر مقبول بناءً على سياسة الموظف.
        """
        if not quotation:
            return None
        from .models import CommissionScheme  # محلي لتجنب الاستيراد الدائري
        scheme = CommissionScheme.get_for_employee(employee)
        if not scheme:
            return None  # لا توجد سياسة مفعلّة، لا يتم إنشاء عمولة
        # تأكد من أن الإجمالي محسوب
        try:
            quotation.calculate_totals()
        except Exception:
            pass
        base = quotation.total_amount or Decimal('0')
        amount = (base * (scheme.percentage / Decimal('100'))).quantize(Decimal('0.01'))
        return cls.objects.create(
            employee=employee,
            opportunity=quotation.opportunity,
            quotation=quotation,
            percentage=scheme.percentage,
            base_amount=base,
            amount=amount,
            created_by=created_by
        )

    def mark_paid(self, paid_by=None, description: str | None = None):
        """
        وسم العمولة كمصروفة وإنشاء قيد محاسبي بسيط: مدين مصروف (مكافآت) ودائن نقدية/بنك.
        يتطلب تهيئة حسابات HRSettings.bonus_expense_account و AccountingSettings.cash_account.
        يعود بالكائن JournalEntry أو None إذا لم يتمكن من الإنشاء.
        """
        if self.status == 'paid':
            return self.journal_entry  # already paid

        from accounting.models import AccountingSettings, JournalEntry, JournalEntryItem
        from hr.models import HRSettings

        hr_settings = HRSettings.objects.first()
        acct_settings = AccountingSettings.get()

        if not hr_settings or not hr_settings.bonus_expense_account:
            raise ValueError('حساب مصروف المكافآت غير مُعد في إعدادات الموارد البشرية.')
        if not acct_settings or not acct_settings.cash_account:
            raise ValueError('حساب النقدية/البنك غير مُعد في إعدادات المحاسبة.')

        je = JournalEntry.objects.create(
            date=timezone.now().date(),
            entry_type='payment',
            description=description or f"صرف عمولة للمندوب {self.employee.arabic_name}",
            reference=f"CRM-COMM-{self.id}",
            created_by=paid_by,
        )
        # مدين: مصروف مكافآت، دائن: نقدية/بنك
        JournalEntryItem.objects.create(
            journal_entry=je,
            account=hr_settings.bonus_expense_account,
            type='debit',
            amount=self.amount,
            description=f"عمولة مبيعات - {self.employee.arabic_name}",
        )
        JournalEntryItem.objects.create(
            journal_entry=je,
            account=acct_settings.cash_account,
            type='credit',
            amount=self.amount,
            description=f"صرف عمولة - {self.employee.arabic_name}",
        )

        # تحديث حالة العمولة
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.journal_entry = je
        self.save(update_fields=['status', 'paid_at', 'journal_entry'])
        return je

# Activity Management
class ActivityType(models.Model):
    """أنواع الأنشطة"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField(max_length=100, verbose_name="اسم النوع")
    icon = models.CharField(max_length=50, blank=True, verbose_name="الأيكونة")
    color = models.CharField(max_length=7, default='#007bff', verbose_name="اللون")
    
    class Meta:
        verbose_name = "نوع النشاط"
        verbose_name_plural = "أنواع الأنشطة"
    
    def __str__(self):
        return self.name

class Activity(models.Model):
    """الأنشطة والمهام"""
    STATUS_CHOICES = [
        ('planned', 'مخطط'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    PRIORITY_CHOICES = [
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
        ('urgent', 'عاجل'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200, verbose_name="عنوان النشاط")
    activity_type = models.ForeignKey(ActivityType, on_delete=models.PROTECT, verbose_name="نوع النشاط")
    description = models.TextField(blank=True, verbose_name="وصف النشاط")
    
    # Relations
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="العميل")
    opportunity = models.ForeignKey(Opportunity, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="الفرصة")
    contact_person = models.ForeignKey(ContactPerson, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="جهة الاتصال")
    
    # Scheduling
    scheduled_date = models.DateTimeField(verbose_name="الموعد المحدد")
    duration_minutes = models.PositiveIntegerField(default=60, verbose_name="المدة بالدقائق")
    
    # Status and Assignment
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned', verbose_name="الحالة")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name="الأولوية")
    assigned_to = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="المكلف")
    
    # Results
    outcome = models.TextField(blank=True, verbose_name="النتيجة")
    follow_up_required = models.BooleanField(default=False, verbose_name="يتطلب متابعة")
    follow_up_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ المتابعة")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإكمال")
    
    class Meta:
        verbose_name = "نشاط"
        verbose_name_plural = "الأنشطة"
        ordering = ['-scheduled_date']
    
    def __str__(self):
        return f"{self.title} - {self.customer.full_name if self.customer else 'عام'}"
    
    @property
    def is_overdue(self):
        return self.scheduled_date < timezone.now() and self.status not in ['completed', 'cancelled']

# Quotation Management
class Quotation(models.Model):
    """عروض الأسعار"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('sent', 'مرسل'),
        ('accepted', 'مقبول'),
        ('rejected', 'مرفوض'),
        ('expired', 'منتهي الصلاحية'),
        ('converted', 'محول لفاتورة'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    # Basic Information
    quotation_number = models.CharField(max_length=50, unique=True, verbose_name="رقم العرض")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="العميل")
    opportunity = models.ForeignKey(Opportunity, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="الفرصة")
    contact_person = models.ForeignKey(ContactPerson, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="جهة الاتصال")
    
    # Dates
    quotation_date = models.DateField(default=timezone.localdate, verbose_name="تاريخ العرض")
    valid_until = models.DateField(verbose_name="صالح حتى")
    
    # Financial Information
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), verbose_name="المجموع الفرعي")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), verbose_name="نسبة الخصم", validators=[MinValueValidator(0), MaxValueValidator(100)])
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), verbose_name="مبلغ الخصم")
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), verbose_name="نسبة الضريبة", validators=[MinValueValidator(0), MaxValueValidator(100)])
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), verbose_name="مبلغ الضريبة")
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), verbose_name="المبلغ الإجمالي")
    
    # Status and Notes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="الحالة")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    terms_and_conditions = models.TextField(blank=True, verbose_name="الشروط والأحكام")
    
    # Assignment
    prepared_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="معد بواسطة")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإرسال")
    responded_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الرد")
    
    class Meta:
        verbose_name = "عرض سعر"
        verbose_name_plural = "عروض الأسعار"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.quotation_number} - {self.customer.full_name}"
    
    @property
    def is_expired(self):
        return self.valid_until < timezone.now().date()
    
    def calculate_totals(self):
        """حساب المجاميع مع دعم خصم/ضريبة على مستوى الصنف.
        القاعدة:
        - المجموع الفرعي = مجموع (الكمية * سعر الوحدة) لكل صنف.
        - إذا وُجد خصم على أي صنف (>0) يُستخدم مجموع خصومات الأصناف، وإلا يُطبّق الخصم العام.
        - إذا وُجدت ضريبة على أي صنف (>0) يُستخدم مجموع ضرائب الأصناف، وإلا تُطبّق الضريبة العامة بعد الخصم.
        """
        items = list(self.items.all())
        subtotal = sum((it.quantity * it.unit_price) for it in items)
        has_line_discount = any((getattr(it, 'discount_percentage', 0) or 0) > 0 for it in items)
        has_line_tax = any((getattr(it, 'tax_percentage', 0) or 0) > 0 for it in items)

        # جمع خصومات/ضرائب الأصناف إن وُجدت الحقول
        per_line_discount_total = sum(getattr(it, 'discount_amount', 0) or 0 for it in items)
        per_line_tax_total = sum(getattr(it, 'tax_amount', 0) or 0 for it in items)

        q2 = Decimal('0.01')
        self.subtotal = (subtotal or Decimal('0')).quantize(q2)
        if has_line_discount:
            self.discount_amount = (per_line_discount_total or Decimal('0')).quantize(q2)
        else:
            self.discount_amount = (self.subtotal * (self.discount_percentage / 100)).quantize(q2)

        amount_after_discount = (self.subtotal - self.discount_amount).quantize(q2)

        if has_line_tax:
            self.tax_amount = (per_line_tax_total or Decimal('0')).quantize(q2)
        else:
            self.tax_amount = (amount_after_discount * (self.tax_percentage / 100)).quantize(q2)

        self.total_amount = (amount_after_discount + self.tax_amount).quantize(q2)
        self.save(update_fields=['subtotal', 'discount_amount', 'tax_amount', 'total_amount'])

class QuotationItem(models.Model):
    """أصناف عرض السعر"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    quotation = models.ForeignKey(Quotation, related_name='items', on_delete=models.CASCADE, verbose_name="عرض السعر")
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, verbose_name="المنتج")
    description = models.TextField(blank=True, verbose_name="الوصف")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="الكمية", validators=[MinValueValidator(Decimal('0.01'))])
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="سعر الوحدة", validators=[MinValueValidator(Decimal('0'))])
    # خصم/ضريبة على مستوى الصنف
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), verbose_name="نسبة خصم الصنف", validators=[MinValueValidator(0), MaxValueValidator(100)])
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), verbose_name="مبلغ خصم الصنف")
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), verbose_name="نسبة ضريبة الصنف", validators=[MinValueValidator(0), MaxValueValidator(100)])
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), verbose_name="مبلغ ضريبة الصنف")
    total = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="الإجمالي")
    
    class Meta:
        verbose_name = "صنف عرض السعر"
        verbose_name_plural = "أصناف عرض السعر"
    
    def __str__(self):
        return f"{self.product.name} - {self.quotation.quotation_number}"
    
    def save(self, *args, **kwargs):
        # تأمين النسب ضمن 0..100 والقيم غير السالبة
        q2 = Decimal('0.01')
        dp = (self.discount_percentage or Decimal('0'))
        tp = (self.tax_percentage or Decimal('0'))
        if dp < 0:
            dp = Decimal('0')
        if dp > 100:
            dp = Decimal('100')
        if tp < 0:
            tp = Decimal('0')
        if tp > 100:
            tp = Decimal('100')
        self.discount_percentage = dp
        self.tax_percentage = tp

        qty = self.quantity or Decimal('0')
        price = self.unit_price or Decimal('0')
        if qty < 0:
            qty = Decimal('0')
        if price < 0:
            price = Decimal('0')
        self.quantity = qty
        self.unit_price = price

        # الإجمالي للصف قبل الخصم والضريبة
        line_subtotal = (qty * price)
        # حساب الخصم/الضريبة للصنف
        self.discount_amount = (line_subtotal * (dp / 100)).quantize(q2)
        taxable_base = (line_subtotal - self.discount_amount).quantize(q2)
        self.tax_amount = (taxable_base * (tp / 100)).quantize(q2)
        # احتفظ بالحقل total كمجموع قبل الخصومات والضرائب حفاظًا على التوافق
        self.total = line_subtotal.quantize(q2)
        super().save(*args, **kwargs)

# Support Ticket System
class TicketCategory(models.Model):
    """فئات التذاكر"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField(max_length=100, verbose_name="اسم الفئة")
    description = models.TextField(blank=True, verbose_name="وصف")
    color = models.CharField(max_length=7, default='#007bff', verbose_name="اللون")
    
    class Meta:
        verbose_name = "فئة التذكرة"
        verbose_name_plural = "فئات التذاكر"
    
    def __str__(self):
        return self.name

class SupportTicket(models.Model):
    """تذاكر الدعم الفني"""
    STATUS_CHOICES = [
        ('open', 'مفتوح'),
        ('in_progress', 'قيد المعالجة'),
        ('pending', 'في الانتظار'),
        ('resolved', 'محلول'),
        ('closed', 'مغلق'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    PRIORITY_CHOICES = [
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
        ('urgent', 'عاجل'),
    ]
    
    # Basic Information
    ticket_number = models.CharField(max_length=20, unique=True, verbose_name="رقم التذكرة")
    title = models.CharField(max_length=200, verbose_name="العنوان")
    description = models.TextField(verbose_name="الوصف")
    
    # Relations
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="العميل")
    contact_person = models.ForeignKey(ContactPerson, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="جهة الاتصال")
    category = models.ForeignKey(TicketCategory, on_delete=models.PROTECT, verbose_name="الفئة")
    
    # Status and Priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name="الحالة")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name="الأولوية")
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, verbose_name="مكلف الحل")
    created_by = models.ForeignKey(User, related_name='created_tickets', on_delete=models.PROTECT, verbose_name="منشأ بواسطة")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الحل")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإغلاق")
    
    class Meta:
        verbose_name = "تذكرة دعم"
        verbose_name_plural = "تذاكر الدعم"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.ticket_number} - {self.title}"

class TicketComment(models.Model):
    """تعليقات التذاكر"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    ticket = models.ForeignKey(SupportTicket, related_name='comments', on_delete=models.CASCADE, verbose_name="التذكرة")
    comment = models.TextField(verbose_name="التعليق")
    is_internal = models.BooleanField(default=False, verbose_name="تعليق داخلي")
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="المعلق")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التعليق")
    
    class Meta:
        verbose_name = "تعليق التذكرة"
        verbose_name_plural = "تعليقات التذاكر"
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.ticket.ticket_number} - تعليق {self.created_at}"

# Marketing Campaign
class Campaign(models.Model):
    """الحملات التسويقية"""
    CAMPAIGN_TYPES = [
        ('email', 'بريد إلكتروني'),
        ('sms', 'رسالة نصية'),
        ('phone', 'مكالمة هاتفية'),
        ('social', 'وسائل التواصل'),
        ('event', 'فعالية'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('active', 'نشط'),
        ('paused', 'متوقف'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="اسم الحملة")
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPES, verbose_name="نوع الحملة")
    description = models.TextField(blank=True, verbose_name="وصف الحملة")
    
    # Targeting
    target_customers = models.ManyToManyField(Customer, blank=True, verbose_name="العملاء المستهدفون")
    customer_type = models.ForeignKey(CustomerType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="نوع العميل المستهدف")
    
    # Campaign Details
    message_content = models.TextField(blank=True, verbose_name="محتوى الرسالة")
    budget = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), verbose_name="الميزانية")
    
    # Status and Dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="الحالة")
    start_date = models.DateTimeField(verbose_name="تاريخ البداية")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ النهاية")
    
    # Assignment
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="منشأ بواسطة")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "حملة تسويقية"
        verbose_name_plural = "حملات تسويقية"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class CampaignResponse(models.Model):
    """استجابات الحملات"""
    RESPONSE_TYPES = [
        ('interested', 'مهتم'),
        ('not_interested', 'غير مهتم'),
        ('meeting_scheduled', 'موعد محدد'),
        ('purchase', 'شراء'),
        ('no_response', 'لا يوجد رد'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    campaign = models.ForeignKey(Campaign, related_name='responses', on_delete=models.CASCADE, verbose_name="الحملة")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="العميل")
    response_type = models.CharField(max_length=20, choices=RESPONSE_TYPES, verbose_name="نوع الاستجابة")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    response_date = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الاستجابة")
    
    class Meta:
        verbose_name = "استجابة الحملة"
        verbose_name_plural = "استجابات الحملات"
        unique_together = ['campaign', 'customer']
    
    def __str__(self):
        return f"{self.campaign.name} - {self.customer.full_name}"


# =====================================================
# نماذج البريد الإلكتروني
# =====================================================

class EmailTemplate(models.Model):
    """قوالب البريد الإلكتروني"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name="اسم القالب")
    subject = models.CharField(max_length=255, verbose_name="الموضوع")
    body = models.TextField(verbose_name="المحتوى")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="أنشأ بواسطة")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "قالب بريد إلكتروني"
        verbose_name_plural = "قوالب البريد الإلكتروني"
    
    def __str__(self):
        return self.name


class EmailLog(models.Model):
    """سجل البريد الإلكتروني"""
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('sent', 'تم الإرسال'),
        ('failed', 'فشل'),
        ('opened', 'تم الفتح'),
        ('clicked', 'تم النقر'),
    ]
    id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True, verbose_name="العميل")
    to_email = models.EmailField(verbose_name="إلى")
    cc_emails = models.TextField(blank=True, verbose_name="نسخة")
    subject = models.CharField(max_length=255, verbose_name="الموضوع")
    body = models.TextField(verbose_name="المحتوى")
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="القالب")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="الحالة")
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="أرسل بواسطة")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإرسال")
    opened_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الفتح")
    error_message = models.TextField(blank=True, verbose_name="رسالة الخطأ")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "سجل بريد"
        verbose_name_plural = "سجلات البريد"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.to_email} - {self.subject}"


class EmailSettings(models.Model):
    """إعدادات البريد الإلكتروني"""
    id = models.AutoField(primary_key=True)
    smtp_host = models.CharField(max_length=255, verbose_name="خادم SMTP")
    smtp_port = models.IntegerField(default=587, verbose_name="منفذ SMTP")
    smtp_user = models.CharField(max_length=255, verbose_name="اسم المستخدم")
    smtp_password = models.CharField(max_length=255, verbose_name="كلمة المرور")
    from_email = models.EmailField(verbose_name="البريد المرسل")
    from_name = models.CharField(max_length=100, verbose_name="اسم المرسل")
    use_tls = models.BooleanField(default=True, verbose_name="استخدام TLS")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    class Meta:
        verbose_name = "إعدادات البريد"
        verbose_name_plural = "إعدادات البريد"


# =====================================================
# نماذج الواتساب
# =====================================================

class WhatsAppTemplate(models.Model):
    """قوالب الواتساب"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name="اسم القالب")
    content = models.TextField(verbose_name="المحتوى")
    has_media = models.BooleanField(default=False, verbose_name="يحتوي وسائط")
    media_url = models.URLField(blank=True, verbose_name="رابط الوسائط")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="أنشأ بواسطة")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "قالب واتساب"
        verbose_name_plural = "قوالب الواتساب"
    
    def __str__(self):
        return self.name


class WhatsAppConversation(models.Model):
    """محادثات الواتساب"""
    STATUS_CHOICES = [
        ('active', 'نشطة'),
        ('closed', 'مغلقة'),
        ('pending', 'قيد الانتظار'),
    ]
    id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="العميل")
    phone_number = models.CharField(max_length=20, verbose_name="رقم الهاتف")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="الحالة")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="مسند إلى")
    last_message_at = models.DateTimeField(null=True, blank=True, verbose_name="آخر رسالة")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "محادثة واتساب"
        verbose_name_plural = "محادثات الواتساب"
        ordering = ['-last_message_at']
    
    def __str__(self):
        return f"{self.customer.full_name} - {self.phone_number}"


class WhatsAppMessage(models.Model):
    """رسائل الواتساب"""
    DIRECTION_CHOICES = [
        ('inbound', 'واردة'),
        ('outbound', 'صادرة'),
    ]
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('sent', 'تم الإرسال'),
        ('delivered', 'تم التسليم'),
        ('read', 'تم القراءة'),
        ('failed', 'فشل'),
    ]
    id = models.AutoField(primary_key=True)
    conversation = models.ForeignKey(WhatsAppConversation, on_delete=models.CASCADE, related_name='messages', verbose_name="المحادثة")
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, verbose_name="الاتجاه")
    content = models.TextField(verbose_name="المحتوى")
    media_url = models.URLField(blank=True, verbose_name="رابط الوسائط")
    media_type = models.CharField(max_length=50, blank=True, verbose_name="نوع الوسائط")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="الحالة")
    template = models.ForeignKey(WhatsAppTemplate, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="القالب")
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="أرسل بواسطة")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإرسال")
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ التسليم")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ القراءة")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "رسالة واتساب"
        verbose_name_plural = "رسائل الواتساب"
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.conversation.customer.full_name} - {self.direction}"


class WhatsAppBulkMessage(models.Model):
    """رسائل الواتساب الجماعية"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('scheduled', 'مجدولة'),
        ('sending', 'جاري الإرسال'),
        ('completed', 'مكتملة'),
        ('failed', 'فشلت'),
    ]
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name="اسم الحملة")
    template = models.ForeignKey(WhatsAppTemplate, on_delete=models.SET_NULL, null=True, verbose_name="القالب")
    content = models.TextField(verbose_name="المحتوى")
    recipients = models.ManyToManyField(Customer, verbose_name="المستلمين")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="الحالة")
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name="موعد الإرسال")
    total_count = models.IntegerField(default=0, verbose_name="العدد الإجمالي")
    sent_count = models.IntegerField(default=0, verbose_name="عدد المرسل")
    failed_count = models.IntegerField(default=0, verbose_name="عدد الفاشل")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="أنشأ بواسطة")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإكتمال")
    
    class Meta:
        verbose_name = "رسالة جماعية"
        verbose_name_plural = "الرسائل الجماعية"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class WhatsAppSettings(models.Model):
    """إعدادات الواتساب"""
    id = models.AutoField(primary_key=True)
    api_key = models.CharField(max_length=255, verbose_name="مفتاح API")
    phone_number_id = models.CharField(max_length=100, verbose_name="معرف رقم الهاتف")
    business_account_id = models.CharField(max_length=100, verbose_name="معرف حساب الأعمال")
    webhook_token = models.CharField(max_length=255, verbose_name="رمز Webhook")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    class Meta:
        verbose_name = "إعدادات الواتساب"
        verbose_name_plural = "إعدادات الواتساب"


# =====================================================
# نماذج المتابعات
# =====================================================

class FollowUp(models.Model):
    """متابعات العملاء"""
    PRIORITY_CHOICES = [
        ('low', 'منخفضة'),
        ('medium', 'متوسطة'),
        ('high', 'عالية'),
        ('urgent', 'عاجلة'),
    ]
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('in_progress', 'جاري التنفيذ'),
        ('completed', 'مكتملة'),
        ('cancelled', 'ملغاة'),
    ]
    TYPE_CHOICES = [
        ('call', 'اتصال'),
        ('visit', 'زيارة'),
        ('email', 'بريد إلكتروني'),
        ('whatsapp', 'واتساب'),
        ('meeting', 'اجتماع'),
        ('other', 'أخرى'),
    ]
    id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='followups', verbose_name="العميل")
    follow_up_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="نوع المتابعة")
    subject = models.CharField(max_length=255, verbose_name="الموضوع")
    description = models.TextField(blank=True, verbose_name="الوصف")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name="الأولوية")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="الحالة")
    due_date = models.DateTimeField(verbose_name="تاريخ الاستحقاق")
    reminder_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ التذكير")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_followups', verbose_name="مسند إلى")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_followups', verbose_name="أنشأ بواسطة")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإكمال")
    result = models.TextField(blank=True, verbose_name="النتيجة")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "متابعة"
        verbose_name_plural = "المتابعات"
        ordering = ['due_date']
    
    def __str__(self):
        return f"{self.customer.full_name} - {self.subject}"


# =====================================================
# نماذج المهام والمواعيد
# =====================================================

class Task(models.Model):
    """مهام CRM"""
    PRIORITY_CHOICES = [
        ('low', 'منخفضة'),
        ('medium', 'متوسطة'),
        ('high', 'عالية'),
        ('urgent', 'عاجلة'),
    ]
    STATUS_CHOICES = [
        ('todo', 'للعمل'),
        ('in_progress', 'جاري العمل'),
        ('review', 'للمراجعة'),
        ('done', 'منجزة'),
        ('cancelled', 'ملغاة'),
    ]
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, verbose_name="العنوان")
    description = models.TextField(blank=True, verbose_name="الوصف")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True, verbose_name="العميل")
    opportunity = models.ForeignKey('Opportunity', on_delete=models.CASCADE, null=True, blank=True, verbose_name="الفرصة")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name="الأولوية")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo', verbose_name="الحالة")
    due_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الاستحقاق")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='crm_tasks', verbose_name="مسند إلى")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='crm_created_tasks', verbose_name="أنشأ بواسطة")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإكمال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "مهمة"
        verbose_name_plural = "المهام"
        ordering = ['-priority', 'due_date']
    
    def __str__(self):
        return self.title


class Appointment(models.Model):
    """المواعيد"""
    STATUS_CHOICES = [
        ('scheduled', 'مجدول'),
        ('confirmed', 'مؤكد'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
        ('no_show', 'لم يحضر'),
    ]
    TYPE_CHOICES = [
        ('meeting', 'اجتماع'),
        ('call', 'مكالمة'),
        ('visit', 'زيارة'),
        ('demo', 'عرض تجريبي'),
        ('other', 'أخرى'),
    ]
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, verbose_name="العنوان")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="العميل")
    contact_person = models.ForeignKey(ContactPerson, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="جهة الاتصال")
    appointment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='meeting', verbose_name="نوع الموعد")
    start_datetime = models.DateTimeField(verbose_name="تاريخ ووقت البداية")
    end_datetime = models.DateTimeField(verbose_name="تاريخ ووقت النهاية")
    location = models.CharField(max_length=255, blank=True, verbose_name="المكان")
    description = models.TextField(blank=True, verbose_name="الوصف")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled', verbose_name="الحالة")
    reminder_sent = models.BooleanField(default=False, verbose_name="تم إرسال التذكير")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="المسؤول")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='crm_created_appointments', verbose_name="أنشأ بواسطة")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "موعد"
        verbose_name_plural = "المواعيد"
        ordering = ['start_datetime']
    
    def __str__(self):
        return f"{self.title} - {self.customer.full_name}"


# =====================================================
# نماذج العقود
# =====================================================

class ContractType(models.Model):
    """أنواع العقود"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name="اسم النوع")
    description = models.TextField(blank=True, verbose_name="الوصف")
    default_duration_months = models.IntegerField(default=12, verbose_name="المدة الافتراضية (شهور)")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    class Meta:
        verbose_name = "نوع عقد"
        verbose_name_plural = "أنواع العقود"
    
    def __str__(self):
        return self.name


class Contract(models.Model):
    """عقود العملاء"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('pending', 'قيد الموافقة'),
        ('active', 'نشط'),
        ('expired', 'منتهي'),
        ('cancelled', 'ملغي'),
        ('renewed', 'تم التجديد'),
    ]
    id = models.AutoField(primary_key=True)
    contract_number = models.CharField(max_length=50, unique=True, verbose_name="رقم العقد")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='contracts', verbose_name="العميل")
    contract_type = models.ForeignKey(ContractType, on_delete=models.PROTECT, verbose_name="نوع العقد")
    title = models.CharField(max_length=255, verbose_name="عنوان العقد")
    description = models.TextField(blank=True, verbose_name="الوصف")
    value = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="قيمة العقد")
    start_date = models.DateField(verbose_name="تاريخ البداية")
    end_date = models.DateField(verbose_name="تاريخ النهاية")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="الحالة")
    auto_renew = models.BooleanField(default=False, verbose_name="تجديد تلقائي")
    renewal_reminder_days = models.IntegerField(default=30, verbose_name="تذكير قبل التجديد (أيام)")
    signed_date = models.DateField(null=True, blank=True, verbose_name="تاريخ التوقيع")
    signed_by = models.CharField(max_length=200, blank=True, verbose_name="الموقع")
    attachment = models.FileField(upload_to='contracts/', blank=True, verbose_name="مرفق العقد")
    terms_conditions = models.TextField(blank=True, verbose_name="الشروط والأحكام")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='crm_created_contracts', verbose_name="أنشأ بواسطة")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='crm_approved_contracts', verbose_name="اعتمد بواسطة")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "عقد"
        verbose_name_plural = "العقود"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.contract_number} - {self.customer.full_name}"
    
    def save(self, *args, **kwargs):
        if not self.contract_number:
            prefix = 'CON'
            last = Contract.objects.filter(contract_number__startswith=prefix).order_by('-contract_number').first()
            next_num = 1
            if last:
                import re
                m = re.match(r'^CON(\d+)$', last.contract_number)
                if m:
                    next_num = int(m.group(1)) + 1
            self.contract_number = f"{prefix}{next_num:05d}"
        super().save(*args, **kwargs)


class ContractRenewal(models.Model):
    """تجديدات العقود"""
    id = models.AutoField(primary_key=True)
    original_contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='renewals', verbose_name="العقد الأصلي")
    new_contract = models.ForeignKey(Contract, on_delete=models.SET_NULL, null=True, blank=True, related_name='renewal_from', verbose_name="العقد الجديد")
    renewal_date = models.DateField(verbose_name="تاريخ التجديد")
    new_value = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="القيمة الجديدة")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="بواسطة")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "تجديد عقد"
        verbose_name_plural = "تجديدات العقود"
    
    def __str__(self):
        return f"تجديد {self.original_contract.contract_number}"


# =====================================================
# نماذج الخطط والباقات
# =====================================================

class ServicePlan(models.Model):
    """الخطط والباقات"""
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('semi_annual', 'نصف سنوي'),
        ('annual', 'سنوي'),
    ]
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name="اسم الخطة")
    description = models.TextField(blank=True, verbose_name="الوصف")
    price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="السعر")
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly', verbose_name="دورة الفوترة")
    features = models.JSONField(default=list, verbose_name="المميزات")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    is_popular = models.BooleanField(default=False, verbose_name="الأكثر شيوعاً")
    order = models.IntegerField(default=0, verbose_name="الترتيب")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "خطة"
        verbose_name_plural = "الخطط والباقات"
        ordering = ['order', 'price']
    
    def __str__(self):
        return self.name


class CustomerSubscription(models.Model):
    """اشتراكات العملاء"""
    STATUS_CHOICES = [
        ('active', 'نشط'),
        ('suspended', 'معلق'),
        ('cancelled', 'ملغي'),
        ('expired', 'منتهي'),
    ]
    id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='subscriptions', verbose_name="العميل")
    plan = models.ForeignKey(ServicePlan, on_delete=models.PROTECT, verbose_name="الخطة")
    start_date = models.DateField(verbose_name="تاريخ البداية")
    end_date = models.DateField(verbose_name="تاريخ النهاية")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="الحالة")
    auto_renew = models.BooleanField(default=True, verbose_name="تجديد تلقائي")
    next_billing_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الفاتورة القادمة")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "اشتراك"
        verbose_name_plural = "الاشتراكات"
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.customer.full_name} - {self.plan.name}"


# =====================================================
# نماذج الإعدادات الإضافية
# =====================================================

class RejectionReason(models.Model):
    """أسباب الرفض"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name="سبب الرفض")
    description = models.TextField(blank=True, verbose_name="الوصف")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    class Meta:
        verbose_name = "سبب رفض"
        verbose_name_plural = "أسباب الرفض"
    
    def __str__(self):
        return self.name


class BusinessActivity(models.Model):
    """الأنشطة التجارية"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name="اسم النشاط")
    description = models.TextField(blank=True, verbose_name="الوصف")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    class Meta:
        verbose_name = "نشاط تجاري"
        verbose_name_plural = "الأنشطة التجارية"
    
    def __str__(self):
        return self.name


class Region(models.Model):
    """المحافظات والمناطق"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name="اسم المنطقة")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name="المنطقة الأب")
    code = models.CharField(max_length=20, blank=True, verbose_name="الكود")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    class Meta:
        verbose_name = "منطقة"
        verbose_name_plural = "المحافظات والمناطق"
        ordering = ['name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} - {self.name}"
        return self.name


class CRMSettings(models.Model):
    """إعدادات CRM العامة"""
    id = models.AutoField(primary_key=True)
    company_name = models.CharField(max_length=200, verbose_name="اسم الشركة")
    company_logo = models.ImageField(upload_to='crm/logo/', blank=True, verbose_name="شعار الشركة")
    default_currency = models.CharField(max_length=10, default='EGP', verbose_name="العملة الافتراضية")
    quotation_validity_days = models.IntegerField(default=30, verbose_name="صلاحية عرض السعر (أيام)")
    auto_followup_days = models.IntegerField(default=7, verbose_name="المتابعة التلقائية (أيام)")
    enable_email_notifications = models.BooleanField(default=True, verbose_name="تفعيل إشعارات البريد")
    enable_whatsapp_notifications = models.BooleanField(default=False, verbose_name="تفعيل إشعارات الواتساب")
    enable_sms_notifications = models.BooleanField(default=False, verbose_name="تفعيل إشعارات SMS")
    
    class Meta:
        verbose_name = "إعدادات CRM"
        verbose_name_plural = "إعدادات CRM"