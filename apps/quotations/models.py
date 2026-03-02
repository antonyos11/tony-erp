"""
نماذج عروض الأسعار — RITA ERP
"""
from django.db import models
from apps.core.models import AuditMixin


class Quotation(AuditMixin):
    """عرض سعر"""
    QUOTATION_STATUSES = [
        ('draft', 'مسودة'),
        ('sent', 'مُرسل'),
        ('negotiation', 'قيد التفاوض'),
        ('revised', 'معدّل'),
        ('accepted', 'مقبول'),
        ('rejected', 'مرفوض'),
        ('expired', 'منتهي'),
        ('converted', 'تحوّل لفاتورة'),
        ('cancelled', 'ملغي'),
    ]

    quotation_number = models.CharField(max_length=50, unique=True, verbose_name="رقم عرض السعر")
    date = models.DateTimeField(verbose_name="التاريخ")
    valid_until = models.DateField(verbose_name="صالح حتى")
    revision_number = models.IntegerField(default=0, verbose_name="رقم التعديل")

    # العميل — ممكن عميل موجود أو بيانات عميل جديد
    customer = models.ForeignKey(
        'sales.Customer', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="العميل",
    )
    # بيانات عميل سريع (لو مش مسجل)
    prospect_name = models.CharField(max_length=255, blank=True, verbose_name="اسم العميل المحتمل")
    prospect_phone = models.CharField(max_length=20, blank=True, verbose_name="هاتف العميل المحتمل")
    prospect_email = models.EmailField(blank=True, verbose_name="إيميل العميل المحتمل")
    prospect_address = models.TextField(blank=True, verbose_name="عنوان العميل المحتمل")
    prospect_company = models.CharField(max_length=255, blank=True, verbose_name="شركة العميل المحتمل")

    # بيانات العرض
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name="الفرع")
    salesperson = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='quotations', verbose_name="البائع",
    )
    status = models.CharField(max_length=20, choices=QUOTATION_STATUSES, default='draft', verbose_name="الحالة")

    # الأسعار
    price_list = models.ForeignKey(
        'sales.PriceList', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="قائمة الأسعار",
    )
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="الإجمالي")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة خصم %")
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="قيمة الخصم")
    taxable_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="المبلغ الخاضع")
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="الضريبة")
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="الإجمالي النهائي")
    is_taxable = models.BooleanField(default=True, verbose_name="خاضع للضريبة")

    # التوصيل
    delivery_required = models.BooleanField(default=False, verbose_name="يحتاج توصيل")
    delivery_address = models.TextField(blank=True, verbose_name="عنوان التوصيل")
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="رسوم التوصيل")
    estimated_delivery_days = models.IntegerField(default=0, verbose_name="أيام التوصيل المتوقعة")

    # الشروط والملاحظات
    terms_and_conditions = models.TextField(blank=True, verbose_name="الشروط والأحكام")
    internal_notes = models.TextField(blank=True, verbose_name="ملاحظات داخلية")
    customer_notes = models.TextField(blank=True, verbose_name="ملاحظات للعميل")
    payment_terms = models.CharField(max_length=255, blank=True, verbose_name="شروط الدفع")

    # الربط بالفاتورة
    converted_invoice = models.ForeignKey(
        'sales.SalesInvoice', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="الفاتورة المحوّلة",
    )

    # متابعة
    follow_up_date = models.DateField(null=True, blank=True, verbose_name="تاريخ المتابعة")
    rejection_reason = models.TextField(blank=True, verbose_name="سبب الرفض")
    lost_to_competitor = models.CharField(max_length=255, blank=True, verbose_name="خسرنا لصالح")

    class Meta:
        verbose_name = "عرض سعر"
        verbose_name_plural = "عروض الأسعار"
        ordering = ['-date']

    def __str__(self):
        customer_name = self.customer.name if self.customer else self.prospect_name
        return f"{self.quotation_number} - {customer_name}"

    @property
    def is_expired(self):
        from django.utils import timezone
        return (
            self.valid_until < timezone.now().date()
            and self.status not in ('accepted', 'converted', 'cancelled')
        )

    @property
    def customer_display_name(self):
        return self.customer.name if self.customer else self.prospect_name


class QuotationLine(models.Model):
    """سطر عرض سعر"""
    quotation = models.ForeignKey(
        Quotation, on_delete=models.CASCADE,
        related_name='lines', verbose_name="العرض",
    )
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, verbose_name="المنتج")
    description = models.CharField(max_length=500, blank=True, verbose_name="الوصف")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="الكمية")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="سعر الوحدة")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="خصم %")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="قيمة الخصم")
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="الإجمالي")

    # مقاسات مخصصة (للمراتب)
    custom_width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="العرض (سم)")
    custom_length = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="الطول (سم)")
    custom_height = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="الارتفاع (سم)")

    # تقدير التكلفة
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="التكلفة التقديرية")
    estimated_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="الربح التقديري")

    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    sort_order = models.IntegerField(default=0, verbose_name="الترتيب")

    class Meta:
        verbose_name = "سطر عرض سعر"
        verbose_name_plural = "سطور عرض السعر"
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.quotation.quotation_number} - {self.product.name}"


class QuotationFollowUp(AuditMixin):
    """متابعة عرض السعر"""
    FOLLOW_UP_TYPES = [
        ('call', 'مكالمة'),
        ('whatsapp', 'واتساب'),
        ('email', 'إيميل'),
        ('visit', 'زيارة'),
        ('meeting', 'اجتماع'),
    ]
    FOLLOW_UP_RESULTS = [
        ('interested', 'مهتم'),
        ('thinking', 'يفكر'),
        ('needs_revision', 'يحتاج تعديل'),
        ('negotiating', 'يفاوض'),
        ('will_buy', 'سيشتري'),
        ('lost', 'خسرناه'),
        ('no_answer', 'لا يرد'),
    ]

    quotation = models.ForeignKey(
        Quotation, on_delete=models.CASCADE,
        related_name='follow_ups', verbose_name="العرض",
    )
    date = models.DateTimeField(verbose_name="التاريخ")
    follow_up_type = models.CharField(max_length=20, choices=FOLLOW_UP_TYPES, verbose_name="نوع المتابعة")
    result = models.CharField(max_length=20, choices=FOLLOW_UP_RESULTS, verbose_name="النتيجة")
    notes = models.TextField(verbose_name="الملاحظات")
    next_follow_up_date = models.DateField(null=True, blank=True, verbose_name="تاريخ المتابعة القادمة")

    class Meta:
        verbose_name = "متابعة"
        verbose_name_plural = "المتابعات"
        ordering = ['-date']

    def __str__(self):
        return f"{self.quotation.quotation_number} - {self.get_follow_up_type_display()}"
