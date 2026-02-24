from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class License(models.Model):
    """الترخيص"""
    license_number = models.CharField('رقم الترخيص', max_length=100, unique=True)
    license_type = models.CharField('نوع الترخيص', max_length=50, choices=[
        ('business', 'تجاري'), ('health', 'صحي'), ('industrial', 'صناعي'), 
        ('food', 'غذائي'), ('environmental', 'بيئي'), ('safety', 'سلامة'), ('other', 'أخرى')
    ])
    
    name = models.CharField('الاسم', max_length=200)
    description = models.TextField('الوصف', blank=True)
    
    issuing_authority = models.CharField('الجهة المصدرة', max_length=200)
    issue_date = models.DateField('تاريخ الإصدار')
    expiry_date = models.DateField('تاريخ الانتهاء')
    
    status = models.CharField('الحالة', max_length=20, choices=[
        ('active', 'نشط'), ('expired', 'منتهي'), ('suspended', 'موقوف'),
        ('pending_renewal', 'معلق التجديد'), ('cancelled', 'ملغي')
    ], default='active')
    
    renewal_required = models.BooleanField('يتطلب تجديد', default=True)
    renewal_fee = models.DecimalField('رسوم التجديد', max_digits=10, decimal_places=2, default=0)
    
    # المرفقات
    document_url = models.URLField('رابط المستند', blank=True)
    notes = models.TextField('ملاحظات', blank=True)
    
    # المسؤول
    responsible_person = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='licenses')
    
    # التنبيهات
    reminder_days_before_expiry = models.IntegerField('تذكير قبل (أيام)', default=30)
    last_reminder_sent = models.DateField('آخر تذكير', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'ترخيص'
        verbose_name_plural = 'التراخيص'
        ordering = ['expiry_date']
    
    def __str__(self):
        return f"{self.license_number} - {self.name}"


class LicenseRenewal(models.Model):
    """تجديد ترخيص"""
    license = models.ForeignKey(License, on_delete=models.CASCADE, related_name='renewals')
    renewal_date = models.DateField('تاريخ التجديد')
    new_expiry_date = models.DateField('تاريخ الانتهاء الجديد')
    
    renewal_fee = models.DecimalField('رسوم التجديد', max_digits=10, decimal_places=2)
    payment_status = models.CharField('حالة السداد', max_length=20, choices=[
        ('pending', 'معلق'), ('paid', 'مدفوع'), ('refunded', 'مسترد')
    ], default='pending')
    
    notes = models.TextField('ملاحظات', blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'تجديد ترخيص'
        verbose_name_plural = 'تجديدات التراخيص'
        ordering = ['-renewal_date']
    
    def __str__(self):
        return f"تجديد {self.license.license_number} - {self.renewal_date}"


class GovernmentPermit(models.Model):
    """تصريح حكومي"""
    permit_number = models.CharField('رقم التصريح', max_length=100, unique=True)
    permit_type = models.CharField('نوع التصريح', max_length=100)
    
    title = models.CharField('العنوان', max_length=200)
    description = models.TextField('الوصف')
    
    government_entity = models.CharField('الجهة الحكومية', max_length=200)
    application_date = models.DateField('تاريخ التقديم')
    approval_date = models.DateField('تاريخ الموافقة', null=True, blank=True)
    
    status = models.CharField('الحالة', max_length=20, choices=[
        ('draft', 'مسودة'), ('submitted', 'مقدم'), ('under_review', 'قيد المراجعة'),
        ('approved', 'معتمد'), ('rejected', 'مرفوض'), ('expired', 'منتهي')
    ], default='draft')
    
    validity_period_days = models.IntegerField('فترة الصلاحية (أيام)', null=True, blank=True)
    expiry_date = models.DateField('تاريخ الانتهاء', null=True, blank=True)
    
    application_fee = models.DecimalField('رسوم التقديم', max_digits=10, decimal_places=2, default=0)
    notes = models.TextField('ملاحظات', blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'تصريح حكومي'
        verbose_name_plural = 'التصاريح الحكومية'
        ordering = ['-application_date']
    
    def __str__(self):
        return f"{self.permit_number} - {self.title}"
