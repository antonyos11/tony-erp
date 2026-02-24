"""
White Label Models
نماذج نظام العلامة البيضاء

يدعم multi-tenancy كامل مع تخصيص شامل
"""

from django.db import models
from django.db.models import JSONField
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _


class Tenant(models.Model):
    """
    مستأجر (عميل SaaS)
    
    كل مستأجر له بياناته المنفصلة وإعداداته الخاصة
    """
    
    # معلومات أساسية
    name = models.CharField('اسم المستأجر', max_length=200)
    slug = models.SlugField('معرف URL', unique=True, max_length=100)
    domain = models.CharField('النطاق', max_length=255, unique=True, null=True, blank=True)
    
    # بيانات الشركة
    company_name = models.CharField('اسم الشركة', max_length=200)
    company_name_ar = models.CharField('اسم الشركة بالعربية', max_length=200, blank=True)
    tax_id = models.CharField('الرقم الضريبي', max_length=50, blank=True)
    commercial_registration = models.CharField('السجل التجاري', max_length=50, blank=True)
    
    # بيانات الاتصال
    email = models.EmailField('البريد الإلكتروني')
    phone = models.CharField('الهاتف', max_length=20)
    address = models.TextField('العنوان', blank=True)
    city = models.CharField('المدينة', max_length=100, blank=True)
    country = models.CharField('الدولة', max_length=100, default='Egypt')
    
    # حالة الاشتراك
    is_active = models.BooleanField('نشط', default=True)
    subscription_plan = models.CharField('خطة الاشتراك', max_length=50, default='basic')
    subscription_start = models.DateField('بداية الاشتراك', auto_now_add=True)
    subscription_end = models.DateField('نهاية الاشتراك', null=True, blank=True)
    trial_end = models.DateField('نهاية الفترة التجريبية', null=True, blank=True)
    
    # حدود الاستخدام
    max_users = models.IntegerField('الحد الأقصى للمستخدمين', default=10)
    max_branches = models.IntegerField('الحد الأقصى للفروع', default=3)
    max_products = models.IntegerField('الحد الأقصى للمنتجات', default=1000)
    max_storage_mb = models.IntegerField('الحد الأقصى للتخزين (MB)', default=1024)
    
    # الميزات المفعلة
    enabled_modules = JSONField('الوحدات المفعلة', default=list)
    custom_features = JSONField('ميزات مخصصة', default=dict)
    
    # الإعدادات العامة
    timezone = models.CharField('المنطقة الزمنية', max_length=50, default='Asia/Riyadh')
    language = models.CharField('اللغة', max_length=10, default='ar')
    currency = models.CharField('العملة', max_length=3, default='EGP')
    
    # تواريخ
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        db_table = 'tenants'
        verbose_name = 'مستأجر'
        verbose_name_plural = 'المستأجرون'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def is_trial_expired(self):
        """التحقق من انتهاء الفترة التجريبية"""
        if not self.trial_end:
            return False
        from django.utils import timezone
        return timezone.now().date() > self.trial_end
    
    def is_subscription_active(self):
        """التحقق من نشاط الاشتراك"""
        if not self.is_active:
            return False
        if self.subscription_end:
            from django.utils import timezone
            return timezone.now().date() <= self.subscription_end
        return True
    
    def get_usage_stats(self):
        """إحصائيات الاستخدام"""
        from django.contrib.auth.models import User
        from branches.models import Branch
        from inventory.models import Product
        
        return {
            'users': User.objects.filter(tenant=self).count(),
            'branches': Branch.objects.filter(tenant=self).count(),
            'products': Product.objects.filter(tenant=self).count(),
        }
    
    def is_module_enabled(self, module_name):
        """التحقق من تفعيل وحدة"""
        return module_name in self.enabled_modules


class TenantBranding(models.Model):
    """
    العلامة التجارية للمستأجر
    
    تخصيص كامل للشعار، الألوان، والنصوص
    """
    
    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name='branding',
        verbose_name='المستأجر'
    )
    
    # الشعار
    logo = models.ImageField('الشعار', upload_to='tenant_logos/', null=True, blank=True)
    logo_dark = models.ImageField('الشعار (وضع داكن)', upload_to='tenant_logos/', null=True, blank=True)
    favicon = models.ImageField('أيقونة المتصفح', upload_to='tenant_favicons/', null=True, blank=True)
    
    # الألوان (Hex codes)
    primary_color = models.CharField('اللون الأساسي', max_length=7, default='#1976d2')
    secondary_color = models.CharField('اللون الثانوي', max_length=7, default='#dc004e')
    accent_color = models.CharField('لون التمييز', max_length=7, default='#f50057')
    background_color = models.CharField('لون الخلفية', max_length=7, default='#ffffff')
    text_color = models.CharField('لون النص', max_length=7, default='#000000')
    
    # الخطوط
    font_family = models.CharField('نوع الخط', max_length=100, default='Cairo, sans-serif')
    font_url = models.URLField('رابط الخط', blank=True)
    
    # النصوص المخصصة
    app_title = models.CharField('عنوان التطبيق', max_length=100, blank=True)
    app_title_ar = models.CharField('عنوان التطبيق بالعربية', max_length=100, blank=True)
    tagline = models.CharField('الشعار', max_length=200, blank=True)
    tagline_ar = models.CharField('الشعار بالعربية', max_length=200, blank=True)
    
    # صفحة تسجيل الدخول
    login_background = models.ImageField('خلفية تسجيل الدخول', upload_to='tenant_backgrounds/', null=True, blank=True)
    login_title = models.CharField('عنوان صفحة الدخول', max_length=100, blank=True)
    login_message = models.TextField('رسالة صفحة الدخول', blank=True)
    
    # التذييل
    footer_text = models.TextField('نص التذييل', blank=True)
    copyright_text = models.CharField('نص حقوق النشر', max_length=200, blank=True)
    
    # روابط التواصل الاجتماعي
    website_url = models.URLField('الموقع الإلكتروني', blank=True)
    facebook_url = models.URLField('فيسبوك', blank=True)
    twitter_url = models.URLField('تويتر', blank=True)
    linkedin_url = models.URLField('لينكدإن', blank=True)
    instagram_url = models.URLField('إنستغرام', blank=True)
    
    # CSS مخصص
    custom_css = models.TextField('CSS مخصص', blank=True)
    custom_js = models.TextField('JavaScript مخصص', blank=True)
    
    # تواريخ
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        db_table = 'tenant_branding'
        verbose_name = 'علامة تجارية'
        verbose_name_plural = 'العلامات التجارية'
    
    def __str__(self):
        return f'Branding - {self.tenant.name}'
    
    def get_logo_url(self, dark_mode=False):
        """الحصول على رابط الشعار"""
        if dark_mode and self.logo_dark:
            return self.logo_dark.url
        return self.logo.url if self.logo else None
    
    def get_app_title(self, language='ar'):
        """الحصول على عنوان التطبيق"""
        if language == 'ar' and self.app_title_ar:
            return self.app_title_ar
        return self.app_title or self.tenant.company_name


class TenantSettings(models.Model):
    """
    إعدادات المستأجر
    
    إعدادات نظام مخصصة لكل عميل
    """
    
    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name='settings',
        verbose_name='المستأجر'
    )
    
    # إعدادات الفواتير
    invoice_prefix = models.CharField('بادئة رقم الفاتورة', max_length=10, default='INV')
    invoice_number_start = models.IntegerField('بداية ترقيم الفواتير', default=1)
    invoice_terms = models.TextField('شروط وأحكام الفاتورة', blank=True)
    invoice_footer = models.TextField('تذييل الفاتورة', blank=True)
    
    # إعدادات الضرائب
    tax_enabled = models.BooleanField('تفعيل الضريبة', default=True)
    tax_rate = models.DecimalField('نسبة الضريبة', max_digits=5, decimal_places=2, default=15)
    tax_number = models.CharField('الرقم الضريبي', max_length=50, blank=True)
    
    # إعدادات المخزون
    allow_negative_stock = models.BooleanField('السماح بالمخزون السالب', default=False)
    auto_reorder = models.BooleanField('إعادة الطلب التلقائي', default=False)
    low_stock_threshold = models.IntegerField('حد المخزون المنخفض', default=10)
    
    # إعدادات التسعير
    default_markup = models.DecimalField('هامش الربح الافتراضي', max_digits=5, decimal_places=2, default=30)
    dynamic_pricing = models.BooleanField('التسعير الديناميكي', default=False)
    price_rounding = models.CharField('تقريب الأسعار', max_length=10, default='0.01')
    
    # إعدادات الإنتاج
    production_auto_start = models.BooleanField('بدء الإنتاج تلقائياً', default=False)
    production_quality_check = models.BooleanField('فحص الجودة إلزامي', default=True)
    
    # إعدادات الموافقات
    require_po_approval = models.BooleanField('الموافقة على أوامر الشراء', default=True)
    po_approval_limit = models.DecimalField('حد الموافقة على الشراء', max_digits=15, decimal_places=2, default=10000)
    require_invoice_approval = models.BooleanField('الموافقة على الفواتير', default=False)
    
    # إعدادات الإشعارات
    email_notifications = models.BooleanField('إشعارات البريد', default=True)
    sms_notifications = models.BooleanField('إشعارات SMS', default=False)
    push_notifications = models.BooleanField('إشعارات Push', default=True)
    
    # إعدادات النسخ الاحتياطي
    auto_backup = models.BooleanField('نسخ احتياطي تلقائي', default=True)
    backup_frequency = models.CharField('تكرار النسخ الاحتياطي', max_length=20, default='daily')
    backup_retention_days = models.IntegerField('مدة الاحتفاظ بالنسخ', default=30)
    
    # إعدادات الأمان
    password_expiry_days = models.IntegerField('انتهاء كلمة المرور (أيام)', default=90)
    max_login_attempts = models.IntegerField('محاولات الدخول القصوى', default=5)
    session_timeout_minutes = models.IntegerField('انتهاء الجلسة (دقائق)', default=60)
    require_2fa = models.BooleanField('المصادقة الثنائية إلزامية', default=False)
    
    # إعدادات API
    api_enabled = models.BooleanField('تفعيل API', default=True)
    api_rate_limit = models.IntegerField('حد API (طلب/دقيقة)', default=100)
    webhook_url = models.URLField('Webhook URL', blank=True)
    
    # إعدادات مخصصة (JSON)
    custom_settings = JSONField('إعدادات مخصصة', default=dict)
    
    # تواريخ
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        db_table = 'tenant_settings'
        verbose_name = 'إعدادات المستأجر'
        verbose_name_plural = 'إعدادات المستأجرين'
    
    def __str__(self):
        return f'Settings - {self.tenant.name}'
    
    def get_setting(self, key, default=None):
        """الحصول على إعداد مخصص"""
        return self.custom_settings.get(key, default)
    
    def set_setting(self, key, value):
        """تعيين إعداد مخصص"""
        self.custom_settings[key] = value
        self.save(update_fields=['custom_settings', 'updated_at'])


class TenantDomain(models.Model):
    """
    نطاقات المستأجر
    
    يسمح بربط عدة نطاقات بنفس المستأجر
    """
    
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='domains',
        verbose_name='المستأجر'
    )
    
    domain = models.CharField('النطاق', max_length=255, unique=True)
    is_primary = models.BooleanField('نطاق رئيسي', default=False)
    is_active = models.BooleanField('نشط', default=True)
    
    # SSL
    ssl_enabled = models.BooleanField('SSL مفعل', default=False)
    ssl_certificate = models.TextField('شهادة SSL', blank=True)
    ssl_expiry = models.DateField('انتهاء SSL', null=True, blank=True)
    
    # تواريخ
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        db_table = 'tenant_domains'
        verbose_name = 'نطاق'
        verbose_name_plural = 'النطاقات'
        unique_together = [['tenant', 'domain']]
    
    def __str__(self):
        return self.domain
