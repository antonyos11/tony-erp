"""
نظام الملكية الفكرية والبراءات
Intellectual Property and Patents System
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class Patent(models.Model):
    """براءات الاختراع"""
    
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('filed', _('مودعة')),
        ('pending', _('قيد الفحص')),
        ('approved', _('موافق عليها')),
        ('expired', _('منتهية')),
        ('rejected', _('مرفوضة')),
        ('abandoned', _('مهجورة')),
    ]
    
    PATENT_TYPE_CHOICES = [
        ('invention', _('براءة اختراع')),
        ('design', _('براءة تصميم')),
        ('utility_model', _('نموذج منفعة')),
        ('trademark', _('علامة تجارية')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patent_number = models.CharField(_('رقم البراءة'), max_length=100, unique=True)
    application_number = models.CharField(_('رقم الطلب'), max_length=100, unique=True)
    
    # معلومات البراءة
    title = models.CharField(_('العنوان'), max_length=200)
    description = models.TextField(_('الوصف'))
    patent_type = models.CharField(_('نوع البراءة'), max_length=50, choices=PATENT_TYPE_CHOICES)
    
    # التخصص
    technical_field = models.CharField(_('المجال التقني'), max_length=200)
    classification = models.CharField(_('التصنيف'), max_length=100, blank=True,
                                     help_text='مثل: G06F, H04L')
    
    # المخترعون والملاك
    inventors = models.TextField(_('المخترعون/الملكية الفكرية'))
    patent_owner = models.CharField(_('صاحب البراءة'), max_length=200)
    
    # التواريخ
    filing_date = models.DateField(_('تاريخ الإيداع'))
    publication_date = models.DateField(_('تاريخ النشر'), null=True, blank=True)
    approval_date = models.DateField(_('تاريخ الموافقة'), null=True, blank=True)
    expiry_date = models.DateField(_('تاريخ الانتهاء'))
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # الملفات
    specification_document = models.FileField(_('وثيقة المواصفات'), upload_to='patents/')
    drawings = models.FileField(_('الرسومات'), upload_to='patents/', blank=True)
    claims = models.TextField(_('المطالبات'), blank=True)
    
    # الأسواق المحمية
    protected_countries = models.TextField(_('الدول المحمية'), 
                                          help_text='قائمة بأسماء الدول مفصولة بفواصل')
    
    # السجلات والرسوم
    registration_fee_paid = models.BooleanField(_('تم دفع رسم التسجيل'), default=False)
    annual_fees_paid = models.BooleanField(_('تم دفع الرسوم السنوية'), default=False)
    next_renewal_date = models.DateField(_('تاريخ التجديد التالي'), null=True, blank=True)
    
    # الملاحظات
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('براءة اختراع')
        verbose_name_plural = _('براءات الاختراع')
        ordering = ['-filing_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['patent_type']),
            models.Index(fields=['expiry_date']),
        ]
    
    def __str__(self):
        return f"{self.patent_number} - {self.title}"
    
    def is_expiring_soon(self, days=90):
        """التحقق من انتهاء البراءة قريباً"""
        from django.utils import timezone
        from datetime import timedelta
        
        threshold_date = timezone.now().date() + timedelta(days=days)
        return self.expiry_date <= threshold_date and self.status in ['approved']


class Trademark(models.Model):
    """العلامات التجارية"""
    
    STATUS_CHOICES = [
        ('registered', _('مسجلة')),
        ('pending', _('قيد التسجيل')),
        ('renewed', _('مجددة')),
        ('expired', _('منتهية')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trademark_number = models.CharField(_('رقم العلامة'), max_length=100, unique=True)
    name = models.CharField(_('اسم العلامة'), max_length=200)
    
    # الوصف
    description = models.TextField(_('الوصف'))
    logo_image = models.ImageField(_('صورة الشعار'), upload_to='trademarks/')
    
    # التصنيف
    goods_and_services = models.TextField(_('السلع والخدمات'))
    nice_classification = models.CharField(_('تصنيف نيس'), max_length=100)
    
    # صاحب الحق
    owner = models.CharField(_('صاحب الحق'), max_length=200)
    owner_address = models.TextField(_('عنوان صاحب الحق'))
    
    # التواريخ
    registration_date = models.DateField(_('تاريخ التسجيل'))
    renewal_date = models.DateField(_('تاريخ التجديد'), null=True, blank=True)
    expiry_date = models.DateField(_('تاريخ الانتهاء'))
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES)
    
    # الحماية العالمية
    protected_countries = models.TextField(_('الدول المحمية'))
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('علامة تجارية')
        verbose_name_plural = _('العلامات التجارية')
        ordering = ['-registration_date']
    
    def __str__(self):
        return f"{self.trademark_number} - {self.name}"


class CopyrightWork(models.Model):
    """أعمال حقوق النشر"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_('العنوان'), max_length=200)
    work_type = models.CharField(_('نوع العمل'), max_length=100,
                                choices=[('software', _('برمجية')), 
                                        ('book', _('كتاب')),
                                        ('music', _('موسيقى')), 
                                        ('film', _('فيلم')),
                                        ('other', _('أخرى'))])
    
    description = models.TextField(_('الوصف'))
    
    # المؤلف والناشر
    author = models.CharField(_('المؤلف'), max_length=200)
    publisher = models.CharField(_('الناشر'), max_length=200, blank=True)
    
    # الملف
    work_file = models.FileField(_('ملف العمل'), upload_to='copyrights/', blank=True)
    
    # التواريخ
    creation_date = models.DateField(_('تاريخ الإنشاء'))
    registration_date = models.DateField(_('تاريخ التسجيل'), auto_now_add=True)
    
    # المدة
    copyright_duration = models.IntegerField(_('مدة حق النشر (سنة)'))
    expiry_date = models.DateField(_('تاريخ الانتهاء'))
    
    # الترخيص
    is_licensed = models.BooleanField(_('مرخص'), default=False)
    license_agreement = models.FileField(_('اتفاق الترخيص'), upload_to='copyrights/', blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('عمل محمي بحق النشر')
        verbose_name_plural = _('الأعمال المحمية بحق النشر')
    
    def __str__(self):
        return self.title


class IPLicense(models.Model):
    """رخص الملكية الفكرية"""
    
    LICENSE_TYPE_CHOICES = [
        ('patent_license', _('رخصة براءة')),
        ('trademark_license', _('رخصة علامة')),
        ('copyright_license', _('رخصة نشر')),
        ('technology_license', _('رخصة تقنية')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license_number = models.CharField(_('رقم الرخصة'), max_length=100, unique=True)
    license_type = models.CharField(_('نوع الرخصة'), max_length=50, choices=LICENSE_TYPE_CHOICES)
    
    # الطرفان
    licensor = models.CharField(_('منح الرخصة'), max_length=200)
    licensee = models.CharField(_('متلقي الرخصة'), max_length=200)
    
    # الموضوع
    subject_matter = models.TextField(_('موضوع الرخصة'))
    
    # الشروط
    territory = models.CharField(_('الإقليم'), max_length=200)
    exclusive = models.BooleanField(_('حصرية'), default=False)
    
    # المالية
    royalty_rate = models.DecimalField(_('معدل الملكية %'), max_digits=5, decimal_places=2)
    advance_payment = models.DecimalField(_('الدفع المسبق'), max_digits=15, decimal_places=2, default=0)
    
    # التواريخ
    start_date = models.DateField(_('تاريخ البداية'))
    end_date = models.DateField(_('تاريخ النهاية'))
    
    # الملف
    license_agreement = models.FileField(_('اتفاق الرخصة'), upload_to='licenses/')
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('رخصة ملكية فكرية')
        verbose_name_plural = _('رخص الملكية الفكرية')
    
    def __str__(self):
        return f"{self.license_number} - {self.licensor} to {self.licensee}"
