"""
Subscription Management System
نظام إدارة الباقات والاشتراكات

متوفر بعدة أنظمة وباقات للاشتراك تناسب كافة أحجام العمل
"""

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import datetime, timedelta


class SubscriptionPlan(models.Model):
    """باقات الاشتراك"""
    
    PLAN_TYPE_CHOICES = [
        ('starter', 'باقة المبتدئين'),
        ('business', 'باقة الأعمال'),
        ('enterprise', 'باقة المؤسسات'),
        ('custom', 'باقة مخصصة'),
    ]
    
    BILLING_PERIOD_CHOICES = [
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('semi_annual', 'نصف سنوي'),
        ('annual', 'سنوي'),
    ]
    
    name = models.CharField('اسم الباقة', max_length=100)
    code = models.CharField('كود الباقة', max_length=50, unique=True)
    plan_type = models.CharField('نوع الباقة', max_length=20, choices=PLAN_TYPE_CHOICES)
    
    description = models.TextField('الوصف')
    features = models.JSONField('المميزات', default=dict)
    
    # التسعير
    monthly_price = models.DecimalField('السعر الشهري', max_digits=10, decimal_places=2)
    quarterly_price = models.DecimalField('السعر الربع سنوي', max_digits=10, decimal_places=2, null=True, blank=True)
    semi_annual_price = models.DecimalField('السعر النصف سنوي', max_digits=10, decimal_places=2, null=True, blank=True)
    annual_price = models.DecimalField('السعر السنوي', max_digits=10, decimal_places=2, null=True, blank=True)
    
    # الحدود
    max_users = models.IntegerField('أقصى عدد مستخدمين', default=5)
    max_products = models.IntegerField('أقصى عدد منتجات', default=1000)
    max_invoices_per_month = models.IntegerField('أقصى فواتير شهرياً', default=100)
    max_storage_gb = models.IntegerField('مساحة التخزين (GB)', default=10)
    
    # المميزات
    has_api_access = models.BooleanField('الوصول للـ API', default=False)
    has_mobile_app = models.BooleanField('تطبيق الموبايل', default=False)
    has_advanced_reports = models.BooleanField('تقارير متقدمة', default=False)
    has_ai_features = models.BooleanField('مميزات الذكاء الاصطناعي', default=False)
    has_whatsapp_integration = models.BooleanField('تكامل واتساب', default=False)
    has_ecommerce = models.BooleanField('متجر إلكتروني', default=False)
    has_multi_branch = models.BooleanField('فروع متعددة', default=False)
    has_priority_support = models.BooleanField('دعم فني أولوية', default=False)
    
    # الترتيب والحالة
    display_order = models.IntegerField('ترتيب العرض', default=0)
    is_active = models.BooleanField('نشط', default=True)
    is_featured = models.BooleanField('مميز', default=False)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'باقة اشتراك'
        verbose_name_plural = 'باقات الاشتراك'
        ordering = ['display_order', 'monthly_price']
    
    def __str__(self):
        return f"{self.name} - {self.monthly_price} ج.م/شهر"
    
    def get_price_for_period(self, billing_period: str) -> Decimal:
        """الحصول على السعر حسب فترة الدفع"""
        prices = {
            'monthly': self.monthly_price,
            'quarterly': self.quarterly_price or (self.monthly_price * 3 * Decimal('0.95')),
            'semi_annual': self.semi_annual_price or (self.monthly_price * 6 * Decimal('0.90')),
            'annual': self.annual_price or (self.monthly_price * 12 * Decimal('0.85')),
        }
        return prices.get(billing_period, self.monthly_price)


class CustomerSubscription(models.Model):
    """اشتراكات العملاء"""
    
    STATUS_CHOICES = [
        ('trial', 'تجريبي'),
        ('active', 'نشط'),
        ('suspended', 'موقوف'),
        ('expired', 'منتهي'),
        ('cancelled', 'ملغي'),
    ]
    
    customer = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='subscriptions', verbose_name='العميل')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, verbose_name='الباقة')
    
    subscription_number = models.CharField('رقم الاشتراك', max_length=50, unique=True)
    billing_period = models.CharField('فترة الدفع', max_length=20, choices=SubscriptionPlan.BILLING_PERIOD_CHOICES)
    
    # التواريخ
    start_date = models.DateField('تاريخ البدء')
    end_date = models.DateField('تاريخ الانتهاء')
    trial_ends_at = models.DateField('انتهاء الفترة التجريبية', null=True, blank=True)
    
    # التسعير
    price = models.DecimalField('السعر', max_digits=10, decimal_places=2)
    discount = models.DecimalField('الخصم', max_digits=10, decimal_places=2, default=Decimal('0'))
    final_price = models.DecimalField('السعر النهائي', max_digits=10, decimal_places=2)
    
    # الحالة
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='trial')
    auto_renew = models.BooleanField('تجديد تلقائي', default=True)
    
    # الاستخدام
    current_users = models.IntegerField('المستخدمون الحاليون', default=1)
    current_products = models.IntegerField('المنتجات الحالية', default=0)
    current_invoices_this_month = models.IntegerField('الفواتير هذا الشهر', default=0)
    current_storage_gb = models.DecimalField('المساحة المستخدمة (GB)', max_digits=8, decimal_places=2, default=Decimal('0'))
    
    notes = models.TextField('ملاحظات', blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'اشتراك عميل'
        verbose_name_plural = 'اشتراكات العملاء'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.customer.username} - {self.plan.name}"
    
    def is_active(self) -> bool:
        """هل الاشتراك نشط؟"""
        return self.status == 'active' and self.end_date >= datetime.now().date()
    
    def days_remaining(self) -> int:
        """الأيام المتبقية"""
        if self.end_date:
            delta = self.end_date - datetime.now().date()
            return max(0, delta.days)
        return 0
    
    def check_limits(self) -> dict:
        """فحص حدود الاستخدام"""
        return {
            'users_exceeded': self.current_users > self.plan.max_users,
            'products_exceeded': self.current_products > self.plan.max_products,
            'invoices_exceeded': self.current_invoices_this_month > self.plan.max_invoices_per_month,
            'storage_exceeded': self.current_storage_gb > self.plan.max_storage_gb,
        }
    
    def renew(self, periods: int = 1):
        """تجديد الاشتراك"""
        if self.billing_period == 'monthly':
            self.end_date = self.end_date + timedelta(days=30 * periods)
        elif self.billing_period == 'quarterly':
            self.end_date = self.end_date + timedelta(days=90 * periods)
        elif self.billing_period == 'semi_annual':
            self.end_date = self.end_date + timedelta(days=180 * periods)
        elif self.billing_period == 'annual':
            self.end_date = self.end_date + timedelta(days=365 * periods)
        
        self.status = 'active'
        self.save()


class SubscriptionPayment(models.Model):
    """مدفوعات الاشتراكات"""
    
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'بطاقة ائتمان'),
        ('bank_transfer', 'تحويل بنكي'),
        ('cash', 'نقدي'),
        ('mada', 'مدى'),
        ('apple_pay', 'Apple Pay'),
        ('stc_pay', 'STC Pay'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('completed', 'مكتمل'),
        ('failed', 'فشل'),
        ('refunded', 'مسترد'),
    ]
    
    subscription = models.ForeignKey(CustomerSubscription, on_delete=models.CASCADE, related_name='payments')
    
    payment_number = models.CharField('رقم الدفعة', max_length=50, unique=True)
    amount = models.DecimalField('المبلغ', max_digits=10, decimal_places=2)
    payment_method = models.CharField('طريقة الدفع', max_length=20, choices=PAYMENT_METHOD_CHOICES)
    
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    transaction_id = models.CharField('رقم المعاملة', max_length=100, blank=True)
    payment_date = models.DateTimeField('تاريخ الدفع', null=True, blank=True)
    
    invoice_number = models.CharField('رقم الفاتورة', max_length=50, blank=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'دفعة اشتراك'
        verbose_name_plural = 'دفعات الاشتراكات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.payment_number} - {self.amount} ج.م"
