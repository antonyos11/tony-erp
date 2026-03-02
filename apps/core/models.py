"""
نماذج التطبيق الأساسي — RITA ERP
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


# ===== Mixin للتدقيق =====

class AuditMixin(models.Model):
    """نموذج مجرد يضيف حقول التدقيق والحذف الناعم لكل النماذج"""
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='%(app_label)s_%(class)s_created',
        verbose_name='أنشئ بواسطة',
    )
    updated_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='%(app_label)s_%(class)s_updated',
        verbose_name='عُدِّل بواسطة',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التعديل')
    is_deleted = models.BooleanField(default=False, verbose_name='محذوف')

    class Meta:
        abstract = True


# ===== المستخدم =====

class User(AbstractUser):
    """نموذج المستخدم المخصص"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(
        'Branch',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='users',
        verbose_name='الفرع',
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='رقم الهاتف')
    is_active_employee = models.BooleanField(default=True, verbose_name='موظف نشط')

    # ── Sprint 25: Two-Factor Authentication ──
    two_factor_enabled = models.BooleanField(default=False, verbose_name='تفعيل المصادقة الثنائية')
    two_factor_method = models.CharField(
        max_length=10,
        choices=[('email', 'البريد الإلكتروني'), ('sms', 'رسالة نصية')],
        default='email',
        verbose_name='طريقة المصادقة',
    )
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='آخر IP للدخول')
    failed_login_count = models.PositiveSmallIntegerField(default=0, verbose_name='عدد محاولات الدخول الفاشلة')
    account_locked_until = models.DateTimeField(null=True, blank=True, verbose_name='الحساب مقفل حتى')

    class Meta:
        verbose_name = 'مستخدم'
        verbose_name_plural = 'المستخدمون'

    def __str__(self):
        return self.get_full_name() or self.username


# ===== الشركة =====

class Company(models.Model):
    """
    شركة / مصنع
    النظام يدعم أكثر من شركة
    كل البيانات مربوطة بشركة
    """
    code = models.CharField(max_length=20, unique=True, verbose_name="كود الشركة", default='MAIN')
    name = models.CharField(max_length=255, verbose_name="اسم الشركة")
    name_en = models.CharField(max_length=255, blank=True, verbose_name="الاسم بالإنجليزي")
    legal_name = models.CharField(max_length=500, blank=True, verbose_name="الاسم القانوني")

    # بيانات قانونية
    tax_number = models.CharField(max_length=50, blank=True, verbose_name="الرقم الضريبي")
    commercial_register = models.CharField(max_length=50, blank=True, verbose_name="السجل التجاري")
    industry_register = models.CharField(max_length=50, blank=True, verbose_name="سجل صناعي")

    # العنوان
    address = models.TextField(blank=True, verbose_name="العنوان")
    city = models.CharField(max_length=100, blank=True, verbose_name="المدينة")
    governorate = models.CharField(max_length=100, blank=True, verbose_name="المحافظة")
    country = models.CharField(max_length=100, default='مصر', verbose_name="الدولة")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="الرمز البريدي")

    # التواصل
    phone = models.CharField(max_length=20, blank=True, verbose_name="الهاتف")
    phone2 = models.CharField(max_length=20, blank=True, verbose_name="هاتف 2")
    fax = models.CharField(max_length=20, blank=True, verbose_name="فاكس")
    email = models.EmailField(blank=True, verbose_name="البريد الإلكتروني")
    website = models.URLField(blank=True, verbose_name="الموقع الإلكتروني")

    # الشعار
    logo = models.ImageField(upload_to='company/', null=True, blank=True, verbose_name="الشعار")
    logo_small = models.ImageField(upload_to='company/', null=True, blank=True, verbose_name="شعار صغير")

    # إعدادات مالية
    default_currency = models.CharField(max_length=3, default='EGP', verbose_name="العملة")
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=14, verbose_name="نسبة ضريبة القيمة المضافة")
    fiscal_year_start_month = models.IntegerField(default=1, verbose_name="شهر بداية السنة المالية")

    # إعدادات الطباعة
    invoice_header = models.TextField(blank=True, verbose_name="رأس الفاتورة")
    invoice_footer = models.TextField(blank=True, verbose_name="تذييل الفاتورة")
    invoice_terms = models.TextField(blank=True, verbose_name="شروط الفاتورة")
    quotation_terms = models.TextField(blank=True, verbose_name="شروط عرض السعر")
    warranty_terms = models.TextField(blank=True, verbose_name="شروط الضمان")

    # إعدادات المخزون
    default_valuation_method = models.CharField(
        max_length=20,
        default='weighted_average',
        choices=[
            ('weighted_average', 'متوسط مرجح'),
            ('fifo', 'FIFO'),
            ('lifo', 'LIFO'),
        ],
        verbose_name="طريقة تقييم المخزون",
    )

    # إعدادات الأمان
    session_timeout_minutes = models.IntegerField(default=480, verbose_name="انتهاء الجلسة (دقائق)")
    max_login_attempts = models.IntegerField(default=5, verbose_name="أقصى محاولات دخول")
    password_min_length = models.IntegerField(default=8, verbose_name="أقل طول كلمة مرور")

    # الإعداد الأولي
    setup_completed = models.BooleanField(default=False, verbose_name="اكتمل الإعداد الأولي")

    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "شركة"
        verbose_name_plural = "الشركات"

    def __str__(self):
        return self.name

    @classmethod
    def get_main(cls):
        """إرجاع الشركة الرئيسية — أو إنشائها إن لم توجد"""
        obj, _ = cls.objects.get_or_create(
            code='MAIN',
            defaults={'name': 'الشركة الرئيسية'},
        )
        return obj


# ===== الفرع =====

class Branch(models.Model):
    """الفروع والتوكيلات"""
    BRANCH_TYPE_CHOICES = [
        ('owned', 'فرع مملوك'),
        ('franchise', 'توكيل'),
        ('distributor', 'موزع'),
    ]

    name = models.CharField(max_length=200, verbose_name='اسم الفرع')
    branch_type = models.CharField(
        max_length=20,
        choices=BRANCH_TYPE_CHOICES,
        default='owned',
        verbose_name='نوع الفرع',
    )
    governorate = models.CharField(max_length=100, blank=True, verbose_name='المحافظة')
    area = models.CharField(max_length=100, blank=True, verbose_name='المنطقة')
    address = models.TextField(blank=True, verbose_name='العنوان')
    phone = models.CharField(max_length=20, blank=True, verbose_name='الهاتف')
    manager = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='managed_branches',
        verbose_name='المدير',
    )
    discount_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='نسبة الخصم (للتوكيلات)',
    )
    contract_start = models.DateField(null=True, blank=True, verbose_name='بداية العقد')
    contract_end = models.DateField(null=True, blank=True, verbose_name='نهاية العقد')
    contract_terms = models.TextField(blank=True, verbose_name='شروط العقد')
    has_warehouse = models.BooleanField(default=False, verbose_name='لديه مخزن')
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'فرع'
        verbose_name_plural = 'الفروع'

    def __str__(self):
        return self.name


# ===== المخزن =====

class Warehouse(models.Model):
    """المخازن"""
    WAREHOUSE_TYPE_CHOICES = [
        ('factory', 'مصنع'),
        ('branch', 'فرع'),
        ('raw_materials', 'خامات'),
        ('finished', 'منتجات تامة'),
        ('wip', 'إنتاج تحت التشغيل'),
    ]

    name = models.CharField(max_length=200, verbose_name='اسم المخزن')
    warehouse_type = models.CharField(
        max_length=20,
        choices=WAREHOUSE_TYPE_CHOICES,
        default='branch',
        verbose_name='نوع المخزن',
    )
    branch = models.ForeignKey(
        'Branch',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='warehouses',
        verbose_name='الفرع',
    )
    keeper = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='kept_warehouses',
        verbose_name='أمين المخزن',
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'مخزن'
        verbose_name_plural = 'المخازن'

    def __str__(self):
        return self.name

