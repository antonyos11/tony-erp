"""
نماذج إدارة العقود
Contract Management Models
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import uuid


class Contract(models.Model):
    """العقود"""
    
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('pending_approval', _('قيد الموافقة')),
        ('approved', _('موافق عليه')),
        ('active', _('نشط')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغى')),
        ('on_hold', _('معلق')),
    ]
    
    CONTRACT_TYPE_CHOICES = [
        ('sales', _('عقد بيع')),
        ('purchase', _('عقد شراء')),
        ('service', _('عقد خدمة')),
        ('employment', _('عقد عمل')),
        ('lease', _('عقد إيجار')),
        ('partnership', _('عقد شراكة')),
        ('nda', _('اتفاقية سرية')),
        ('other', _('أخرى')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract_number = models.CharField(_('رقم العقد'), max_length=100, unique=True)
    contract_type = models.CharField(_('نوع العقد'), max_length=50, choices=CONTRACT_TYPE_CHOICES)
    title = models.CharField(_('العنوان'), max_length=200)
    
    # الأطراف
    party_a = models.CharField(_('الطرف الأول'), max_length=200)
    party_b = models.CharField(_('الطرف الثاني'), max_length=200)
    
    # البيانات المالية
    contract_value = models.DecimalField(_('قيمة العقد'), max_digits=15, decimal_places=2)
    currency = models.CharField(_('العملة'), max_length=3, default='EGP')
    
    # التواريخ
    start_date = models.DateField(_('تاريخ البداية'))
    end_date = models.DateField(_('تاريخ النهاية'))
    
    # الوثائق
    document = models.FileField(_('ملف العقد'), upload_to='contracts/')
    document_hash = models.CharField(_('بصمة الملف'), max_length=255, blank=True)
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=50, choices=STATUS_CHOICES, default='draft')
    
    # التوقيع الرقمي
    is_digitally_signed = models.BooleanField(_('موقع رقمياً'), default=False)
    signature_date = models.DateField(_('تاريخ التوقيع'), null=True, blank=True)
    signed_by = models.CharField(_('موقع من قبل'), max_length=200, blank=True)
    
    # التفاصيل
    description = models.TextField(_('الوصف'), blank=True)
    terms_and_conditions = models.TextField(_('الشروط والأحكام'), blank=True)
    
    # المتابعة
    owner = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='owned_contracts')
    approver = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_contracts')
    approval_date = models.DateField(_('تاريخ الموافقة'), null=True, blank=True)
    
    # الملفات المرفقة
    attachments = models.FileField(_('ملفات إضافية'), upload_to='contracts/attachments/', blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('عقد')
        verbose_name_plural = _('العقود')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['contract_type']),
            models.Index(fields=['end_date']),
        ]
    
    def __str__(self):
        return f"{self.contract_number} - {self.title}"
    
    def is_expiring_soon(self, days=30):
        """التحقق من انتهاء العقد قريباً"""
        from django.utils import timezone
        from datetime import timedelta
        
        threshold_date = timezone.now().date() + timedelta(days=days)
        return self.end_date <= threshold_date and self.status in ['active', 'approved']


class ContractMilestone(models.Model):
    """مراحل العقد"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='milestones')
    
    name = models.CharField(_('اسم المرحلة'), max_length=200)
    description = models.TextField(_('الوصف'), blank=True)
    due_date = models.DateField(_('تاريخ الاستحقاق'))
    completion_date = models.DateField(_('تاريخ الإنجاز'), null=True, blank=True)
    
    milestone_value = models.DecimalField(_('قيمة المرحلة'), max_digits=15, decimal_places=2, null=True, blank=True)
    
    status = models.CharField(_('الحالة'), max_length=20,
                            choices=[('pending', _('قيد الانتظار')), 
                                   ('in_progress', _('قيد الإنجاز')),
                                   ('completed', _('مكتملة')), 
                                   ('delayed', _('متأخرة'))])
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('مرحلة عقد')
        verbose_name_plural = _('مراحل العقود')
        ordering = ['due_date']
    
    def __str__(self):
        return f"{self.contract.contract_number} - {self.name}"


class ContractAmendment(models.Model):
    """تعديلات العقد"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='amendments')
    
    amendment_number = models.CharField(_('رقم التعديل'), max_length=100)
    amendment_date = models.DateField(_('تاريخ التعديل'))
    
    description = models.TextField(_('وصف التعديل'))
    old_terms = models.TextField(_('الشروط القديمة'))
    new_terms = models.TextField(_('الشروط الجديدة'))
    
    amendment_document = models.FileField(_('وثيقة التعديل'), upload_to='contracts/amendments/')
    
    is_signed = models.BooleanField(_('موقع عليه'), default=False)
    signature_date = models.DateField(_('تاريخ التوقيع'), null=True, blank=True)
    
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('تعديل عقد')
        verbose_name_plural = _('تعديلات العقود')
        ordering = ['-amendment_date']
        unique_together = ['contract', 'amendment_number']
    
    def __str__(self):
        return f"{self.contract.contract_number} - {self.amendment_number}"


class ContractClause(models.Model):
    """بنود العقد"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='clauses')
    
    clause_number = models.CharField(_('رقم البند'), max_length=50)
    title = models.CharField(_('العنوان'), max_length=200)
    content = models.TextField(_('المحتوى'))
    
    category = models.CharField(_('الفئة'), max_length=100, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('بند عقد')
        verbose_name_plural = _('بنود العقود')
        unique_together = ['contract', 'clause_number']
    
    def __str__(self):
        return f"{self.contract.contract_number} - {self.clause_number}"
