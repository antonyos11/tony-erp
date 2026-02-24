"""
نماذج إدارة المخاطر والتأمين
Risk Management and Insurance System
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid


class RiskCategory(models.Model):
    """فئة المخاطر"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('اسم الفئة'), max_length=200)
    description = models.TextField(_('الوصف'), blank=True)
    color_code = models.CharField(_('كود اللون'), max_length=7, default='#3498db')
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('فئة المخاطر')
        verbose_name_plural = _('فئات المخاطر')
    
    def __str__(self):
        return self.name


class Risk(models.Model):
    """تسجيل المخاطر"""
    PROBABILITY_CHOICES = [
        (1, _('منخفضة جداً')),
        (2, _('منخفضة')),
        (3, _('متوسطة')),
        (4, _('عالية')),
        (5, _('عالية جداً')),
    ]
    
    IMPACT_CHOICES = [
        (1, _('منخفضة جداً')),
        (2, _('منخفضة')),
        (3, _('متوسطة')),
        (4, _('عالية')),
        (5, _('عالية جداً')),
    ]
    
    STATUS_CHOICES = [
        ('identified', _('محددة')),
        ('assessed', _('مقيمة')),
        ('mitigating', _('قيد التخفيف')),
        ('monitored', _('مراقبة')),
        ('closed', _('مغلقة')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(RiskCategory, on_delete=models.SET_NULL, null=True, related_name='risks')
    title = models.CharField(_('العنوان'), max_length=300)
    description = models.TextField(_('الوصف'))
    probability = models.IntegerField(_('احتمالية الحدوث'), choices=PROBABILITY_CHOICES)
    impact = models.IntegerField(_('مستوى التأثير'), choices=IMPACT_CHOICES)
    risk_score = models.IntegerField(_('درجة المخاطر'), default=0)
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='identified')
    owner = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='owned_risks')
    identified_date = models.DateField(_('تاريخ التحديد'))
    mitigation_plan = models.TextField(_('خطة التخفيف'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('مخاطرة')
        verbose_name_plural = _('المخاطر')
        ordering = ['-risk_score', '-created_at']
    
    def save(self, *args, **kwargs):
        self.risk_score = self.probability * self.impact
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title

    @property
    def risk_level(self):
        if self.risk_score >= 12:
            return 'high'
        elif self.risk_score >= 6:
            return 'medium'
        else:
            return 'low'

    @property
    def risk_level_display(self):
        levels = {'high': _('عالية'), 'medium': _('متوسطة'), 'low': _('منخفضة')}
        return levels.get(self.risk_level, _('غير محدد'))


class InsurancePolicy(models.Model):
    """وثيقة تأمين"""
    POLICY_TYPES = [
        ('property', _('الممتلكات')),
        ('liability', _('المسؤولية')),
        ('workers_comp', _('تعويض العمال')),
        ('auto', _('السيارات')),
        ('health', _('الصحة')),
        ('professional', _('المسؤولية المهنية')),
        ('cyber', _('الأمان السيبراني')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('نشطة')),
        ('inactive', _('غير نشطة')),
        ('expired', _('منتهية الصلاحية')),
        ('pending', _('قيد الانتظار')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_number = models.CharField(_('رقم الوثيقة'), max_length=100, unique=True)
    policy_type = models.CharField(_('نوع الوثيقة'), max_length=20, choices=POLICY_TYPES)
    insurer_name = models.CharField(_('اسم شركة التأمين'), max_length=200)
    coverage_amount = models.DecimalField(_('مبلغ التغطية'), max_digits=15, decimal_places=2)
    premium = models.DecimalField(_('قسط التأمين'), max_digits=15, decimal_places=2)
    deductible = models.DecimalField(_('الخصم'), max_digits=15, decimal_places=2, default=0)
    start_date = models.DateField(_('تاريخ البداية'))
    end_date = models.DateField(_('تاريخ النهاية'))
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='active')
    coverage_details = models.TextField(_('تفاصيل التغطية'), blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('وثيقة تأمين')
        verbose_name_plural = _('وثائق التأمين')
        ordering = ['-end_date']
    
    def __str__(self):
        return f"{self.policy_number} - {self.insurer_name}"
    
    def is_expiring_soon(self):
        from datetime import timedelta
        from django.utils import timezone
        return 0 <= (self.end_date - timezone.now().date()).days <= 30


class InsuranceClaim(models.Model):
    """مطالبة تأمين"""
    STATUS_CHOICES = [
        ('submitted', _('مُقدَّمة')),
        ('under_review', _('قيد المراجعة')),
        ('approved', _('موافق عليها')),
        ('rejected', _('مرفوضة')),
        ('paid', _('مدفوعة')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(InsurancePolicy, on_delete=models.CASCADE, related_name='claims')
    claim_number = models.CharField(_('رقم المطالبة'), max_length=100, unique=True)
    claim_date = models.DateField(_('تاريخ المطالبة'))
    incident_date = models.DateField(_('تاريخ الحادثة'))
    claim_amount = models.DecimalField(_('مبلغ المطالبة'), max_digits=15, decimal_places=2)
    approved_amount = models.DecimalField(_('المبلغ المعتمد'), max_digits=15, decimal_places=2, default=0)
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='submitted')
    description = models.TextField(_('وصف المطالبة'))
    attachment = models.FileField(_('المرفقات'), upload_to='insurance_claims/', blank=True)
    submitted_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='insurance_claims')
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('مطالبة تأمين')
        verbose_name_plural = _('مطالبات التأمين')
        ordering = ['-claim_date']
    
    def __str__(self):
        return self.claim_number


class CoverageAnalysis(models.Model):
    """تحليل التغطية والفجوات"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_('العنوان'), max_length=300)
    analysis_date = models.DateField(_('تاريخ التحليل'), auto_now_add=True)
    identified_risks = models.ManyToManyField(Risk, related_name='coverage_analyses')
    policies = models.ManyToManyField(InsurancePolicy, related_name='coverage_analyses')
    coverage_gaps = models.TextField(_('الفجوات في التغطية'))
    recommendations = models.TextField(_('التوصيات'))
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = _('تحليل التغطية')
        verbose_name_plural = _('تحليلات التغطية')
    
    def __str__(self):
        return self.title
