from django.db import models
from django.core.cache import cache
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from decimal import Decimal


class Currency(models.Model):
    """العملات المدعومة"""
    CURRENCY_CODES = [
        # العملات العربية
        ('EGP', 'الجنيه المصري'),
        ('SAR', 'الريال السعودي'),
        ('AED', 'الدرهم الإماراتي'),
        ('KWD', 'الدينار الكويتي'),
        ('QAR', 'الريال القطري'),
        ('OMR', 'الريال العماني'),
        ('BHD', 'الدينار البحريني'),
        ('JOD', 'الدينار الأردني'),
        ('LBP', 'الليرة اللبنانية'),
        ('SYP', 'الليرة السورية'),
        ('IQD', 'الدينار العراقي'),
        ('YER', 'الريال اليمني'),
        ('SDG', 'الجنيه السوداني'),
        ('MAD', 'الدرهم المغربي'),
        ('TND', 'الدينار التونسي'),
        ('DZD', 'الدينار الجزائري'),
        ('LYD', 'الدينار الليبي'),
        ('MRU', 'الأوقية الموريتانية'),
        ('SOS', 'الشلن الصومالي'),
        ('DJF', 'الفرنك الجيبوتي'),
        ('KMF', 'الفرنك القمري'),
        # العملات العالمية الرئيسية
        ('USD', 'الدولار الأمريكي'),
        ('EUR', 'اليورو'),
        ('GBP', 'الجنيه الإسترليني'),
        ('JPY', 'الين الياباني'),
        ('CHF', 'الفرنك السويسري'),
        ('CAD', 'الدولار الكندي'),
        ('AUD', 'الدولار الأسترالي'),
        ('NZD', 'الدولار النيوزيلندي'),
        ('CNY', 'اليوان الصيني'),
        ('HKD', 'الدولار الهونج كونجي'),
        ('SGD', 'الدولار السنغافوري'),
        ('SEK', 'الكرونة السويدية'),
        ('NOK', 'الكرونة النرويجية'),
        ('DKK', 'الكرونة الدنماركية'),
        ('ISK', 'الكرونة الآيسلندية'),
        # عملات أوروبية
        ('PLN', 'الزلوتي البولندي'),
        ('CZK', 'الكورونا التشيكية'),
        ('HUF', 'الفورنت المجري'),
        ('RON', 'الليو الروماني'),
        ('BGN', 'الليف البلغاري'),
        ('HRK', 'الكونا الكرواتية'),
        ('RSD', 'الدينار الصربي'),
        ('UAH', 'الهريفنيا الأوكرانية'),
        ('GEL', 'اللاري الجورجي'),
        # عملات آسيوية
        ('INR', 'الروبية الهندية'),
        ('PKR', 'الروبية الباكستانية'),
        ('BDT', 'التاكا البنجلاديشية'),
        ('LKR', 'الروبية السريلانكية'),
        ('NPR', 'الروبية النيبالية'),
        ('THB', 'البات التايلاندي'),
        ('MYR', 'الرينجيت الماليزي'),
        ('IDR', 'الروبية الإندونيسية'),
        ('PHP', 'البيزو الفلبيني'),
        ('VND', 'الدونج الفيتنامي'),
        ('KRW', 'الوون الكوري'),
        ('TWD', 'الدولار التايواني'),
        ('MMK', 'الكيات الميانماري'),
        ('KHR', 'الريال الكمبودي'),
        ('LAK', 'الكيب اللاوسي'),
        ('MNT', 'التوغريك المنغولي'),
        ('KZT', 'التينغة الكازاخستانية'),
        ('UZS', 'السوم الأوزبكستاني'),
        ('AFN', 'الأفغاني الأفغانستاني'),
        ('IRR', 'الريال الإيراني'),
        ('TRY', 'الليرة التركية'),
        ('ILS', 'الشيكل الإسرائيلي'),
        # عملات أفريقية
        ('ZAR', 'الراند الجنوب أفريقي'),
        ('NGN', 'النايرا النيجيرية'),
        ('GHS', 'السيدي الغاني'),
        ('KES', 'الشلن الكيني'),
        ('TZS', 'الشلن التنزاني'),
        ('UGX', 'الشلن الأوغندي'),
        ('ETB', 'البر الإثيوبي'),
        ('XOF', 'فرنك غرب أفريقيا'),
        ('XAF', 'فرنك وسط أفريقيا'),
        ('RWF', 'الفرنك الرواندي'),
        ('MZN', 'الميتيكال الموزمبيقي'),
        ('AOA', 'الكوانزا الأنغولية'),
        ('CDF', 'الفرنك الكونغولي'),
        # عملات أمريكا اللاتينية
        ('BRL', 'الريال البرازيلي'),
        ('MXN', 'البيزو المكسيكي'),
        ('ARS', 'البيزو الأرجنتيني'),
        ('CLP', 'البيزو التشيلي'),
        ('COP', 'البيزو الكولومبي'),
        ('PEN', 'السول البيروفي'),
        ('UYU', 'البيزو الأوروغوياني'),
        ('BOB', 'البوليفيانو البوليفي'),
        ('PYG', 'الغواراني الباراغوياني'),
        ('DOP', 'البيزو الدومينيكاني'),
        ('CRC', 'الكولون الكوستاريكي'),
        ('GTQ', 'الكيتزال الغواتيمالي'),
        ('HNL', 'اللمبيرا الهندوراسية'),
        ('NIO', 'الكوردوبا النيكاراغوية'),
        ('PAB', 'البالبوا البنمية'),
        ('JMD', 'الدولار الجامايكي'),
        ('TTD', 'الدولار الترينيدادي'),
        # عملات أخرى
        ('RUB', 'الروبل الروسي'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    code = models.CharField('رمز العملة', max_length=3, choices=CURRENCY_CODES, unique=True)
    name = models.CharField('اسم العملة', max_length=100)
    symbol = models.CharField('رمز العملة', max_length=10)
    is_active = models.BooleanField('نشط', default=True)
    is_default = models.BooleanField('العملة الافتراضية', default=False)
    # إضافة حقول جديدة
    exchange_rate = models.DecimalField('سعر الصرف مقابل العملة الأساسية', max_digits=18, decimal_places=6, default=Decimal('1'),
                                      help_text='سعر الصرف مقابل العملة الافتراضية')
    decimal_places = models.PositiveIntegerField('عدد الخانات العشرية', default=2)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'عملة'
        verbose_name_plural = 'العملات'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def clean(self):
        """التحقق من صحة البيانات قبل الحفظ"""
        from django.core.exceptions import ValidationError
        
        # التأكد من أن العملة الافتراضية نشطة
        if self.is_default and not self.is_active:
            raise ValidationError('العملة الافتراضية يجب أن تكون نشطة')
        
        # التأكد من أن سعر الصرف موجب
        if self.exchange_rate <= 0:
            raise ValidationError('سعر الصرف يجب أن يكون أكبر من الصفر')
    
    def save(self, *args, **kwargs):
        # تأكد من وجود عملة افتراضية واحدة فقط
        if self.is_default:
            # إلغاء الافتراضية من باقي العملات
            Currency.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
            # إذا كانت العملة الافتراضية، فسعر صرفها يجب أن يكون 1
            self.exchange_rate = 1
        
        super().save(*args, **kwargs)
        
        # مسح الكاش عند التحديث
        cache.delete('default_currency')
        cache.delete('active_currencies')
        cache.delete(f'currency_{self.code}')
    
    @classmethod
    def get_default(cls):
        """الحصول على العملة الافتراضية"""
        currency = cache.get('default_currency')
        if not currency:
            currency = cls.objects.filter(is_default=True, is_active=True).first()
            if not currency:
                # إنشاء الجنيه المصري كعملة افتراضية
                currency, created = cls.objects.get_or_create(
                    code='EGP',
                    defaults={
                        'name': 'الجنيه المصري',
                        'symbol': 'ج.م',
                        'is_default': True,
                        'is_active': True,
                        'exchange_rate': 1.000000,
                        'decimal_places': 2
                    }
                )
            cache.set('default_currency', currency, 3600)  # كاش لساعة واحدة
        return currency
    
    @classmethod
    def get_active_currencies(cls):
        """الحصول على جميع العملات النشطة"""
        currencies = cache.get('active_currencies')
        if not currencies:
            currencies = list(cls.objects.filter(is_active=True).order_by('name'))
            cache.set('active_currencies', currencies, 1800)  # كاش لـ 30 دقيقة
        return currencies
    
    def convert_to_default(self, amount):
        """تحويل مبلغ من هذه العملة إلى العملة الافتراضية"""
        if self.is_default:
            return amount
        return amount / self.exchange_rate
    
    def convert_from_default(self, amount):
        """تحويل مبلغ من العملة الافتراضية إلى هذه العملة"""
        if self.is_default:
            return amount
        return amount * self.exchange_rate
    
    @property
    def is_base_currency(self):
        """هل هذه هي العملة الأساسية (الافتراضية)"""
        return self.is_default


class Company(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    name = models.CharField(max_length=255, verbose_name='اسم الشركة')
    logo = models.ImageField(upload_to='logos/', blank=True, null=True, verbose_name='الشعار')
    address = models.CharField(max_length=500, blank=True, verbose_name='العنوان')
    phone = models.CharField(max_length=50, blank=True, verbose_name='الهاتف')
    mobile = models.CharField(max_length=50, blank=True, verbose_name='الموبايل')
    email = models.EmailField(blank=True, verbose_name='البريد الإلكتروني')
    tax_id = models.CharField(max_length=100, blank=True, verbose_name='الرقم الضريبي')
    commercial_register = models.CharField(max_length=100, blank=True, verbose_name='السجل التجاري')
    invoice_prefix = models.CharField(max_length=20, default='INV', verbose_name='بادئة الفواتير')
    slogan = models.CharField(max_length=255, blank=True, verbose_name='شعار الشركة النصي')
    footer_text = models.TextField(blank=True, verbose_name='نص تذييل المطبوعات')
    
    # مواقع التواصل الاجتماعي
    website = models.URLField(blank=True, verbose_name='الموقع الإلكتروني')
    facebook = models.URLField(blank=True, verbose_name='فيسبوك')
    instagram = models.URLField(blank=True, verbose_name='انستجرام')
    twitter = models.URLField(blank=True, verbose_name='تويتر/X')
    whatsapp = models.CharField(max_length=50, blank=True, verbose_name='واتساب')
    tiktok = models.URLField(blank=True, verbose_name='تيك توك')
    youtube = models.URLField(blank=True, verbose_name='يوتيوب')
    linkedin = models.URLField(blank=True, verbose_name='لينكدإن')
    
    default_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, 
                                       verbose_name='العملة الافتراضية', null=True, blank=True)

    # إعدادات الضريبة
    default_vat_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=14.00,
        verbose_name='نسبة ضريبة القيمة المضافة %',
        help_text='نسبة VAT الافتراضية التي تظهر في الفواتير الضريبية'
    )

    class Meta:
        verbose_name = 'الشركة'
        verbose_name_plural = 'بيانات الشركة'

    def __str__(self) -> str:
        return self.name
    
    def get_currency(self):
        """الحصول على العملة المستخدمة"""
        if self.default_currency:
            return self.default_currency
        return Currency.get_default()

    def save(self, *args, **kwargs):
        """حفظ الشركة وتفريغ الكاش لعرض الشعار/الاسم فوراً"""
        super().save(*args, **kwargs)
        cache.delete('company_singleton')
        try:
            from core.company_service import invalidate_company_cache
            invalidate_company_cache()
        except Exception:
            pass


class CompanyPhone(models.Model):
    """أرقام هواتف الشركة المتعددة"""
    
    PHONE_TYPE_CHOICES = [
        ('main', 'رئيسي'),
        ('sales', 'المبيعات'),
        ('purchases', 'المشتريات'),
        ('complaints', 'الشكاوى'),
        ('support', 'الدعم الفني'),
        ('fax', 'فاكس'),
        ('whatsapp', 'واتساب'),
        ('hotline', 'خط ساخن'),
        ('other', 'أخرى'),
    ]
    
    id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, 
                               related_name='phones', verbose_name='الشركة')
    phone_type = models.CharField(max_length=20, choices=PHONE_TYPE_CHOICES, 
                                  default='main', verbose_name='نوع الرقم')
    phone_number = models.CharField(max_length=50, verbose_name='رقم الهاتف')
    contact_person = models.CharField(max_length=100, blank=True, verbose_name='الشخص المسؤول')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    show_on_print = models.BooleanField(default=True, verbose_name='يظهر على المطبوعات')
    show_on_store = models.BooleanField(default=True, verbose_name='يظهر على المتجر')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='ترتيب العرض')
    
    class Meta:
        verbose_name = 'رقم هاتف الشركة'
        verbose_name_plural = 'أرقام هواتف الشركة'
        ordering = ['sort_order', 'phone_type']
    
    def __str__(self):
        return f"{self.get_phone_type_display()}: {self.phone_number}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            from core.company_service import invalidate_company_cache
            invalidate_company_cache()
        except Exception:
            pass
    
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        try:
            from core.company_service import invalidate_company_cache
            invalidate_company_cache()
        except Exception:
            pass


class AppSettings(models.Model):
    """إعدادات الواجهة والهوية (Singleton)"""
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    brand_colors = models.JSONField(default=dict, blank=True)
    kpi_visible_keys = models.CharField(max_length=255, default='sales,purchases,profit,low_stock')
    # Audit configuration
    audit_retention_days = models.PositiveIntegerField(default=90)
    audit_sensitive_fields = models.JSONField(default=list, blank=True)
    audit_ignore_apps = models.JSONField(default=list, blank=True)
    audit_ignore_models = models.JSONField(default=list, blank=True)
    audit_alert_rules = models.JSONField(default=list, blank=True)
    safety_incident_alert_threshold = models.PositiveIntegerField(default=3, help_text='الحد الشهري للحوادث لإطلاق تنبيه سلامة')
    safety_alert_emails = models.JSONField(default=list, blank=True, help_text='عناوين بريد لإشعارات السلامة')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'إعدادات التطبيق'
        verbose_name_plural = 'إعدادات التطبيق'

    def __str__(self):
        return f"AppSettings ({self.pk})"

    @classmethod
    def get(cls):
        from django.db import IntegrityError, transaction
        obj = cache.get('app_settings_singleton')
        if obj is not None:
            return obj
        # Try to reuse any existing row to avoid duplicate-ID races
        existing = cls.objects.order_by('pk').first()
        if existing:
            cache.set('app_settings_singleton', existing, 300)
            return existing
        # Create a fresh row; guard against concurrent creation
        try:
            with transaction.atomic():
                obj = cls.objects.create(pk=1)
        except IntegrityError:
            # Another thread/process created it; fetch the first available
            obj = cls.objects.order_by('pk').first()
            if obj is None:
                # As a last resort create without forcing PK
                obj = cls.objects.create()
        cache.set('app_settings_singleton', obj, 300)
        return obj

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.set('app_settings_singleton', self, 300)


class Country(models.Model):
    """الدول"""
    id = models.AutoField(primary_key=True)
    name = models.CharField('اسم الدولة', max_length=100)
    name_en = models.CharField('الاسم بالإنجليزية', max_length=100, blank=True)
    code = models.CharField('رمز الدولة', max_length=3, unique=True)
    phone_code = models.CharField('كود الهاتف', max_length=10, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='العملة')
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'دولة'
        verbose_name_plural = 'الدول'
        ordering = ['name']

    def __str__(self):
        return self.name


class State(models.Model):
    """المحافظات/الولايات"""
    id = models.AutoField(primary_key=True)
    name = models.CharField('اسم المحافظة', max_length=100)
    name_en = models.CharField('الاسم بالإنجليزية', max_length=100, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states', verbose_name='الدولة')
    code = models.CharField('رمز المحافظة', max_length=10, blank=True)
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'محافظة'
        verbose_name_plural = 'المحافظات'
        ordering = ['name']
        unique_together = ['country', 'name']

    def __str__(self):
        return f"{self.name} - {self.country.name}"


class Branch(models.Model):
    """الفروع"""
    id = models.AutoField(primary_key=True)
    name = models.CharField('اسم الفرع', max_length=100)
    code = models.CharField('كود الفرع', max_length=20, unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches', verbose_name='الشركة', null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='الدولة')
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المحافظة')
    address = models.CharField('العنوان', max_length=500, blank=True)
    phone = models.CharField('الهاتف', max_length=50, blank=True)
    email = models.EmailField('البريد الإلكتروني', blank=True)
    is_main = models.BooleanField('الفرع الرئيسي', default=False)
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'فرع'
        verbose_name_plural = 'الفروع'
        ordering = ['-is_main', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_main:
            Branch.objects.filter(is_main=True).exclude(pk=self.pk).update(is_main=False)
        super().save(*args, **kwargs)


class Page(models.Model):
    """إدارة الصفحات والأقسام"""
    MODULE_CHOICES = [
        ('dashboard', 'لوحة التحكم'),
        ('accounting', 'الحسابات'),
        ('inventory', 'المخزون'),
        ('sales', 'المبيعات'),
        ('purchases', 'المشتريات'),
        ('hr', 'الموارد البشرية'),
        ('crm', 'العملاء'),
        ('production', 'الإنتاج'),
        ('fleet', 'الأسطول'),
        ('pos', 'نقاط البيع'),
        ('reports', 'التقارير'),
        ('settings', 'الإعدادات'),
        ('projects', 'المشاريع'),
        ('contracting', 'المقاولات'),
        ('shipping', 'الشحن'),
        ('eservices', 'الخدمات الإلكترونية'),
        ('ecommerce', 'المتجر الإلكتروني'),
    ]
    
    id = models.AutoField(primary_key=True)
    name = models.CharField('اسم الصفحة', max_length=100)
    code = models.CharField('كود الصفحة', max_length=50, unique=True)
    url = models.CharField('الرابط', max_length=200, blank=True)
    module = models.CharField('الموديول', max_length=50, choices=MODULE_CHOICES, default='settings')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name='القسم الأب')
    icon = models.CharField('الأيقونة', max_length=50, blank=True)
    order = models.PositiveIntegerField('الترتيب', default=0)
    is_active = models.BooleanField('نشط', default=True)
    is_menu_item = models.BooleanField('عنصر قائمة', default=True)
    description = models.TextField('وصف الصفحة', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'صفحة'
        verbose_name_plural = 'الصفحات'
        ordering = ['module', 'order', 'name']

    def __str__(self):
        return self.name
    
    def get_full_path(self):
        """الحصول على المسار الكامل للصفحة"""
        if self.parent:
            return f"{self.parent.name} / {self.name}"
        return self.name


class PagePermission(models.Model):
    """صلاحيات الوصول للصفحات حسب الأدوار"""
    id = models.AutoField(primary_key=True)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='permissions', verbose_name='الصفحة')
    role = models.ForeignKey('users.UserRole', on_delete=models.CASCADE, related_name='page_permissions', verbose_name='الدور')
    can_view = models.BooleanField('عرض', default=True)
    can_create = models.BooleanField('إنشاء', default=False)
    can_edit = models.BooleanField('تعديل', default=False)
    can_delete = models.BooleanField('حذف', default=False)
    can_export = models.BooleanField('تصدير', default=False)
    can_print = models.BooleanField('طباعة', default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'صلاحية صفحة'
        verbose_name_plural = 'صلاحيات الصفحات'
        unique_together = ['page', 'role']
        ordering = ['page__module', 'page__order']

    def __str__(self):
        return f"{self.role.display_name} - {self.page.name}"


class AuditLog(models.Model):
    """سجل عمليات النظام: من قام وبماذا ومتى وعلى أي كائن."""
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_LOGIN = 'login'
    ACTION_LOGOUT = 'logout'
    ACTION_CHOICES = [
        (ACTION_CREATE, 'إنشاء'),
        (ACTION_UPDATE, 'تعديل'),
        (ACTION_DELETE, 'حذف'),
        (ACTION_LOGIN, 'تسجيل دخول'),
        (ACTION_LOGOUT, 'تسجيل خروج'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='المستخدم'
    )
    action = models.CharField('الإجراء', max_length=20, choices=ACTION_CHOICES)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=255, null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    model_name = models.CharField('اسم النموذج', max_length=100, blank=True)
    app_label = models.CharField('اسم التطبيق', max_length=100, blank=True)
    object_repr = models.CharField('وصف الكائن', max_length=255, blank=True)
    changes = models.JSONField('التغييرات', default=dict, blank=True)
    ip_address = models.GenericIPAddressField('عنوان IP', null=True, blank=True)
    user_agent = models.CharField('المتصفح/العميل', max_length=255, blank=True)
    created_at = models.DateTimeField('التاريخ', default=timezone.now, db_index=True)

    class Meta:
        verbose_name = 'سجل النظام'
        verbose_name_plural = 'سجلات النظام'
        ordering = ['-created_at']

    def __str__(self):
        target = self.model_name or 'System'
        return f"{self.get_action_display()} - {target} - {self.created_at:%Y-%m-%d %H:%M:%S}"

    @staticmethod
    def build_object_meta(instance):
        ct = ContentType.objects.get_for_model(instance.__class__)
        return {
            'content_type_id': ct.id,
            'model_name': instance.__class__.__name__,
            'app_label': ct.app_label,
            'object_id': str(getattr(instance, 'pk', '') or ''),
            'object_repr': str(instance)[:255],
        }

