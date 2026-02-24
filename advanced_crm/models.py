"""
نظام CRM المتقدم
Advanced CRM System
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import uuid


class SalesStage(models.Model):
    """مراحل الدورة البيعية"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('اسم المرحلة'), max_length=100)
    description = models.TextField(_('الوصف'), blank=True)
    sequence = models.IntegerField(_('الترتيب'))
    conversion_probability = models.DecimalField(_('احتمال التحويل %'), max_digits=5, decimal_places=2)
    color = models.CharField(_('اللون'), max_length=7, default='#3498db')
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('مرحلة البيع')
        verbose_name_plural = _('مراحل البيع')
        ordering = ['sequence']
    
    def __str__(self):
        return self.name


class Opportunity(models.Model):
    """الفرص التجارية"""
    
    STATUS_CHOICES = [
        ('new', _('جديدة')),
        ('qualified', _('معتمدة')),
        ('proposal_sent', _('تم إرسال عرض')),
        ('negotiation', _('قيد التفاوض')),
        ('won', _('فازت')),
        ('lost', _('خسرت')),
        ('on_hold', _('معلقة')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity_id = models.CharField(_('رقم الفرصة'), max_length=100, unique=True)
    
    # الفرصة
    title = models.CharField(_('العنوان'), max_length=200)
    description = models.TextField(_('الوصف'))
    
    # العميل والتواصل
    customer = models.ForeignKey('partners.Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='advanced_opportunities')
    contact = models.ForeignKey('crm.ContactPerson', on_delete=models.SET_NULL, null=True, blank=True, related_name='advanced_opportunities')
    
    # التفاصيل المالية
    expected_value = models.DecimalField(_('القيمة المتوقعة'), max_digits=15, decimal_places=2)
    currency = models.CharField(_('العملة'), max_length=3, default='EGP')
    weighted_value = models.DecimalField(_('القيمة المرجحة'), max_digits=15, decimal_places=2)
    
    # المرحلة
    stage = models.ForeignKey(SalesStage, on_delete=models.PROTECT)
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='new')
    
    # التواريخ
    created_date = models.DateField(_('تاريخ الإنشاء'), auto_now_add=True)
    expected_close_date = models.DateField(_('تاريخ الإغلاق المتوقع'))
    closed_date = models.DateField(_('تاريخ الإغلاق الفعلي'), null=True, blank=True)
    
    # المسؤول
    owner = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='opportunities')
    
    # المنتجات/الخدمات
    products = models.ManyToManyField('inventory.Product', blank=True)
    
    # الملفات المرفقة
    attachments = models.FileField(_('الملفات'), upload_to='opportunities/', blank=True)
    
    # التنبيهات والتنبؤات
    is_at_risk = models.BooleanField(_('في خطر'), default=False)
    risk_reason = models.TextField(_('سبب الخطر'), blank=True)
    
    success_probability = models.DecimalField(_('احتمال النجاح %'), max_digits=5, decimal_places=2)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('فرصة تجارية')
        verbose_name_plural = _('الفرص التجارية')
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['stage']),
            models.Index(fields=['expected_close_date']),
        ]
    
    def __str__(self):
        return f"{self.opportunity_id} - {self.title}"
    
    def calculate_weighted_value(self):
        """حساب القيمة المرجحة"""
        conversion_prob = self.stage.conversion_probability / 100
        self.weighted_value = self.expected_value * conversion_prob
        self.success_probability = self.stage.conversion_probability
        self.save()


class ActivityLog(models.Model):
    """سجل الأنشطة (نقاط التماس)"""
    
    ACTIVITY_TYPE_CHOICES = [
        ('call', _('مكالمة')),
        ('email', _('بريد إلكتروني')),
        ('meeting', _('اجتماع')),
        ('visit', _('زيارة')),
        ('task', _('مهمة')),
        ('note', _('ملاحظة')),
        ('proposal', _('عرض')),
        ('contract', _('عقد')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # الارتباطات
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='activities')
    contact = models.ForeignKey('crm.ContactPerson', on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    
    # النشاط
    activity_type = models.CharField(_('نوع النشاط'), max_length=20, choices=ACTIVITY_TYPE_CHOICES)
    subject = models.CharField(_('الموضوع'), max_length=200)
    description = models.TextField(_('الوصف'))
    
    # التواريخ
    activity_date = models.DateTimeField(_('تاريخ النشاط'))
    created_date = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    # المسؤول
    performed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    
    # النتائج
    outcome = models.CharField(_('النتيجة'), max_length=200, blank=True)
    follow_up_required = models.BooleanField(_('متابعة مطلوبة'), default=False)
    follow_up_date = models.DateField(_('تاريخ المتابعة'), null=True, blank=True)
    
    # الملفات
    attachments = models.FileField(_('الملفات'), upload_to='activities/', blank=True)
    
    class Meta:
        verbose_name = _('سجل نشاط')
        verbose_name_plural = _('سجلات الأنشطة')
        ordering = ['-activity_date']
        indexes = [
            models.Index(fields=['opportunity']),
            models.Index(fields=['activity_date']),
        ]
    
    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.subject}"


class ForecastRecord(models.Model):
    """سجل التنبؤات"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    forecast_date = models.DateField(_('تاريخ التنبؤ'))
    period = models.CharField(_('الفترة'), max_length=20)
    
    # التنبؤات
    total_pipeline = models.DecimalField(_('إجمالي خط الأنابيب'), max_digits=15, decimal_places=2)
    weighted_pipeline = models.DecimalField(_('خط الأنابيب المرجح'), max_digits=15, decimal_places=2)
    expected_revenue = models.DecimalField(_('الإيرادات المتوقعة'), max_digits=15, decimal_places=2)
    
    # الأداء
    accuracy_percentage = models.DecimalField(_('دقة التنبؤ %'), max_digits=5, decimal_places=2, null=True, blank=True)
    actual_revenue = models.DecimalField(_('الإيرادات الفعلية'), max_digits=15, decimal_places=2, default=0)
    
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('سجل التنبؤ')
        verbose_name_plural = _('سجلات التنبؤات')
        ordering = ['-forecast_date']
    
    def __str__(self):
        return f"تنبؤ {self.forecast_date}"
