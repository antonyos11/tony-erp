from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from decimal import Decimal


class Partner(models.Model):
    """شريك أعمال عام - عملاء وموردين"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    PARTNER_TYPES = [
        ('customer', _('%(label)s') % {'label': 'عميل'}),
        ('supplier', _('مورد')),
        ('both', _('عميل ومورد')),
    ]

    name = models.CharField(_('الاسم'), max_length=255)
    email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    phone = models.CharField(_('الهاتف'), max_length=50, blank=True)
    address = models.CharField(_('العنوان'), max_length=255, blank=True)
    partner_type = models.CharField(_('نوع الشريك'), max_length=20, choices=PARTNER_TYPES, default='customer')
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('شريك')
        verbose_name_plural = _('الشركاء')
        ordering = ['name']

    def __str__(self):
        # احترازياً نحول إلى str في حال تم تمرير كائن ترجمة كسول بالخطأ
        return str(self.name)


class Customer(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    partner = models.OneToOneField(Partner, null=True, blank=True, on_delete=models.CASCADE, related_name='customer_profile', verbose_name=_('الشريك المرتبط'))
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255, blank=True)
    is_key_account = models.BooleanField(default=False, verbose_name=_('عميل رئيسي'))

    def __str__(self):
        return str(self.name)

    class Meta:
        indexes = [
            models.Index(fields=["is_key_account"], name="customer_key_idx"),
        ]


class Supplier(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    # ربط اختياري مع سجل Partner الموحد (مماثل للعميل)
    partner = models.OneToOneField(Partner, null=True, blank=True, on_delete=models.CASCADE, related_name='supplier_profile', verbose_name=_('الشريك المرتبط'))
    code = models.CharField(_('الكود'), max_length=50, unique=True, blank=True, null=True, help_text=_('كود فريد للمورد'))
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255, blank=True)

    # معلومات نوع التوريد والمادة الخام الرئيسية
    SUPPLY_TYPES = [
        ('raw_materials', _('خامات')),
        ('packaging', _('مواد تعبئة')),
        ('services', _('خدمات')),
        ('spare_parts', _('قطع غيار')),
        ('other', _('أخرى')),
    ]
    supply_type = models.CharField(_('نوع التوريد'), max_length=30, blank=True, choices=SUPPLY_TYPES)
    raw_material = models.CharField(_('المادة الخام / الصنف الرئيسي'), max_length=255, blank=True, help_text=_('وصف مختصر أو اسم المادة الأساسية التي يوردها'))

    # معلومات السجل التجاري
    commercial_register = models.CharField(_('السجل التجاري'), max_length=100, blank=True, help_text=_('رقم السجل التجاري للمورد'))
    tax_number = models.CharField(_('الرقم الضريبي'), max_length=100, blank=True, help_text=_('الرقم الضريبي أو رقم ضريبة القيمة المضافة'))

    # حقول محاسبية أساسية (اختيارية حالياً – تستخدم عند تفعيل دفتر موردين تفصيلي لاحقاً)
    account = models.ForeignKey('accounting.Account', null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_('حساب المورد (فرعي)'), help_text=_('اتركه فارغاً لاستخدام حساب الدائنين العام بالإعدادات'))
    opening_balance = models.DecimalField(_('رصيد افتتاحي دائن'), max_digits=15, decimal_places=2, default=0)
    credit_limit = models.DecimalField(_('حد ائتماني'), max_digits=15, decimal_places=2, default=0)
    payment_terms_days = models.PositiveIntegerField(_('أيام سماح السداد'), default=0)
    is_active = models.BooleanField(_('نشط'), default=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        indexes = [
            models.Index(fields=['is_active'], name='supplier_active_idx'),
        ]


class SupplierDocument(models.Model):
    """وثائق ومستندات الموردين"""
    
    DOCUMENT_TYPES = [
        ('commercial_register', _('السجل التجاري')),
        ('tax_card', _('البطاقة الضريبية')),
        ('vat_certificate', _('شهادة ضريبة القيمة المضافة')),
        ('contract', _('عقد توريد')),
        ('quality_certificate', _('شهادة جودة')),
        ('insurance', _('بوليصة تأمين')),
        ('bank_account', _('بيانات حساب بنكي')),
        ('authorization', _('تفويض / توكيل')),
        ('id_copy', _('صورة الهوية / جواز السفر')),
        ('other', _('أخرى')),
    ]
    
    id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.CASCADE, 
        related_name='documents',
        verbose_name=_('المورد')
    )
    document_type = models.CharField(
        _('نوع المستند'), 
        max_length=50, 
        choices=DOCUMENT_TYPES
    )
    document_number = models.CharField(
        _('رقم المستند'), 
        max_length=100, 
        blank=True,
        help_text=_('مثل: رقم السجل التجاري أو رقم البطاقة الضريبية')
    )
    title = models.CharField(
        _('عنوان المستند'), 
        max_length=255,
        help_text=_('وصف مختصر للمستند')
    )
    file = models.FileField(
        _('الملف'),
        upload_to='suppliers/documents/%Y/%m/',
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'gif']
        )],
        help_text=_('الصيغ المدعومة: PDF, Word, Excel, صور')
    )
    issue_date = models.DateField(
        _('تاريخ الإصدار'), 
        null=True, 
        blank=True
    )
    expiry_date = models.DateField(
        _('تاريخ الانتهاء'), 
        null=True, 
        blank=True,
        help_text=_('اتركه فارغاً إذا كان المستند لا ينتهي')
    )
    notes = models.TextField(
        _('ملاحظات'), 
        blank=True
    )
    uploaded_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('رفع بواسطة')
    )
    uploaded_at = models.DateTimeField(
        _('تاريخ الرفع'), 
        auto_now_add=True
    )
    is_verified = models.BooleanField(
        _('تم التحقق منه'), 
        default=False,
        help_text=_('هل تم مراجعة والتحقق من صحة المستند؟')
    )
    
    class Meta:
        verbose_name = _('مستند مورد')
        verbose_name_plural = _('مستندات الموردين')
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['supplier', 'document_type']),
            models.Index(fields=['expiry_date']),
        ]
    
    def __str__(self):
        return f"{self.supplier.name} - {self.get_document_type_display()}"
    
    @property
    def is_expired(self):
        """التحقق من انتهاء صلاحية المستند"""
        if self.expiry_date:
            from django.utils import timezone
            return self.expiry_date < timezone.now().date()
        return False
    
    @property
    def days_until_expiry(self):
        """عدد الأيام المتبقية حتى انتهاء الصلاحية"""
        if self.expiry_date and not self.is_expired:
            from django.utils import timezone
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None


class PartnerContact(models.Model):
    """جهات اتصال الشريك - يدعم أرقام متعددة مع اسم المسؤول لكل رقم"""
    id = models.AutoField(primary_key=True)
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='contacts',
        verbose_name=_('الشريك')
    )
    contact_name = models.CharField(
        _('اسم المسؤول'),
        max_length=255,
        blank=True,
        help_text=_('اسم الشخص المسؤول عن هذا الرقم')
    )
    phone = models.CharField(
        _('رقم الهاتف'),
        max_length=50,
        help_text=_('رقم الهاتف أو الموبايل')
    )
    is_primary = models.BooleanField(
        _('رقم أساسي'),
        default=False,
        help_text=_('هل هذا هو رقم الاتصال الأساسي؟')
    )
    notes = models.CharField(
        _('ملاحظات'),
        max_length=255,
        blank=True,
        help_text=_('مثل: مدير المبيعات، قسم المشتريات')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('جهة اتصال')
        verbose_name_plural = _('جهات الاتصال')
        ordering = ['-is_primary', 'contact_name']
        indexes = [
            models.Index(fields=['partner', 'is_primary']),
        ]

    def __str__(self):
        name_part = f"{self.contact_name} - " if self.contact_name else ""
        return f"{name_part}{self.phone}"

    def save(self, *args, **kwargs):
        # إذا تم تحديد هذا الرقم كأساسي، إلغاء الأساسي من الأرقام الأخرى
        if self.is_primary:
            PartnerContact.objects.filter(
                partner=self.partner, is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)


# --- ربط تلقائي بين Partner و Customer ---
from django.db.models.signals import post_save
from django.dispatch import receiver
from accounting.models import AccountingSettings, Account, AccountType

@receiver(post_save, sender=Partner)
def create_customer_record(sender, instance: Partner, created, **kwargs):
    """إنشاء/مزامنة سجل Customer مرتبط بـ Partner عند كون الشريك عميل.

    - إذا كان الشريك جديد ومن النوع (customer/both) ولم يوجد Customer مرتبط: ننشئ Customer مرتبط.
    - إذا وُجد Customer سابق بالاسم فقط (قبل التحديث الحالي) نربطه إن لم يكن مرتبطاً.
    """
    if instance.partner_type in ('customer', 'both'):
        # ابحث عن Customer مرتبط مباشرة
        cust = getattr(instance, 'customer_profile', None)
        # نحاول الربط فقط دون إنشاء سجل جديد لتجنب تضارب التفرد في سيناريوهات الاختبار/البيانات الأولية
        if not cust:
            old = Customer.objects.filter(partner__isnull=True, name=instance.name).first()
            if old:
                old.partner = instance
                old.save(update_fields=['partner'])


@receiver(post_save, sender=Partner)
def create_supplier_record(sender, instance: Partner, created, **kwargs):
    """إنشاء/مزامنة سجل Supplier عند كون الشريك مورداً.

    منطق مشابه للعميل لدعم التكامل التدريجي. لا يتم تعديل الحقول المحاسبية تلقائياً.
    """
    if instance.partner_type in ('supplier', 'both'):
        supp = getattr(instance, 'supplier_profile', None)
        if created and not supp:
            # نحاول إنشاء حساب فرعي تلقائياً تحت حساب الدائنين العام إن وُجد ولم يُنشأ لاحقاً
            ap_sub_account = None
            try:
                settings = AccountingSettings.get()
                parent_ap = settings.ap_account
                if parent_ap:
                    # توليد كود فرعي بسيط: كود الحساب الرئيسي + تسلسل من 3 أرقام
                    base = parent_ap.code
                    # اجلب أعلى تسلسل مستخدم بنفس البادئة
                    existing_codes = Account.objects.filter(code__startswith=base).values_list('code', flat=True)
                    seq = 1
                    while True:
                        candidate = f"{base}-{seq:03d}"
                        if candidate not in existing_codes:
                            break
                        seq += 1
                    ap_sub_account = Account.objects.create(
                        code=candidate,
                        name=f"مورد: {instance.name}",
                        account_type=parent_ap.account_type,
                        parent=parent_ap,
                        can_post=True,
                    )
            except Exception:
                # فشل صامت: لا نمنع إنشاء المورد لو فشل الحساب
                ap_sub_account = None

            Supplier.objects.create(
                partner=instance,
                name=instance.name,
                email=instance.email,
                phone=instance.phone,
                address=instance.address,
                account=ap_sub_account,
            )
        else:
            if not supp:
                old = Supplier.objects.filter(partner__isnull=True, name=instance.name).first()
                if old:
                    old.partner = instance
                    old.save(update_fields=['partner'])


class SupplierProduct(models.Model):
    """
    ربط المورد بالمنتج مع السعر
    - يسمح بوجود نفس المنتج من موردين مختلفين بأسعار مختلفة
    - يمكن تحديد مورد مفضل لكل منتج
    """
    id = models.AutoField(primary_key=True)

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name=_('المورد')
    )

    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        related_name='suppliers',
        verbose_name=_('المنتج')
    )

    # كود المنتج عند المورد (قد يختلف عن كودنا)
    supplier_sku = models.CharField(
        _('كود المنتج عند المورد'),
        max_length=100,
        blank=True,
        help_text=_('الكود الذي يستخدمه المورد لهذا المنتج')
    )

    # السعر من المورد
    price = models.DecimalField(
        _('سعر الشراء'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0'),
        help_text=_('سعر الشراء من هذا المورد')
    )

    # العملة (اختياري - للمستقبل)
    currency = models.CharField(
        _('العملة'),
        max_length=3,
        default='EGP',
        help_text=_('EGP, USD, EUR, etc.')
    )

    # الحد الأدنى للطلب
    minimum_order_quantity = models.DecimalField(
        _('الحد الأدنى للطلب'),
        max_digits=15,
        decimal_places=3,
        default=Decimal('0'),
        blank=True,
        help_text=_('أقل كمية يمكن طلبها من هذا المورد')
    )

    # وحدة القياس للشراء من هذا المورد
    UOM_CHOICES = [
        ('unit', 'وحدة'),
        ('kg', 'كيلوجرام'),
        ('g', 'جرام'),
        ('m', 'متر'),
        ('cm', 'سنتيمتر'),
        ('l', 'لتر'),
        ('ml', 'مللي لتر'),
        ('m2', 'متر مربع'),
        ('m3', 'متر مكعب'),
        ('pcs', 'قطعة'),
        ('pack', 'عبوة'),
        ('box', 'صندوق'),
        ('roll', 'رول'),
        ('ton', 'طن'),
    ]
    uom = models.CharField(
        _('وحدة القياس'),
        max_length=10,
        choices=UOM_CHOICES,
        default='unit',
        help_text=_('الوحدة التي يبيع بها المورد هذا المنتج')
    )

    # مدة التوريد (بالأيام)
    lead_time_days = models.PositiveIntegerField(
        _('مدة التوريد (أيام)'),
        default=0,
        blank=True,
        help_text=_('عدد الأيام من الطلب حتى التسليم')
    )

    # هل هذا المورد مفضل لهذا المنتج؟
    is_preferred = models.BooleanField(
        _('مورد مفضل'),
        default=False,
        help_text=_('هل هذا هو المورد المفضل لهذا المنتج؟')
    )

    # نشط/غير نشط
    is_active = models.BooleanField(
        _('نشط'),
        default=True
    )

    # ملاحظات
    notes = models.TextField(
        _('ملاحظات'),
        blank=True
    )

    # تواريخ
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    last_purchase_date = models.DateField(
        _('آخر تاريخ شراء'),
        null=True,
        blank=True
    )
    last_purchase_price = models.DecimalField(
        _('آخر سعر شراء'),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('آخر سعر تم الشراء به فعلياً')
    )

    class Meta:
        verbose_name = _('منتج مورد')
        verbose_name_plural = _('منتجات الموردين')
        unique_together = [['supplier', 'product']]
        ordering = ['supplier', 'product']
        indexes = [
            models.Index(fields=['supplier', 'product']),
            models.Index(fields=['product', 'is_preferred']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.supplier.name} - {self.product.name} ({self.price} {self.currency})"

    def save(self, *args, **kwargs):
        # إذا تم تحديد هذا المورد كمفضل، إلغاء التفضيل من الموردين الآخرين لنفس المنتج
        if self.is_preferred:
            SupplierProduct.objects.filter(
                product=self.product,
                is_preferred=True
            ).exclude(id=self.id).update(is_preferred=False)

        super().save(*args, **kwargs)

    @classmethod
    def get_preferred_supplier(cls, product):
        """الحصول على المورد المفضل لمنتج معين"""
        return cls.objects.filter(
            product=product,
            is_preferred=True,
            is_active=True
        ).first()

    @classmethod
    def get_best_price(cls, product):
        """الحصول على أفضل سعر لمنتج معين من جميع الموردين النشطين"""
        best = cls.objects.filter(
            product=product,
            is_active=True
        ).order_by('price').first()

        return best.price if best else None
