"""
نماذج نظام الضرائب
Tax System Models
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid


class TaxType(models.Model):
    """أنواع الضرائب"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(_('الكود'), max_length=50, unique=True)
    name = models.CharField(_('الاسم'), max_length=200)
    description = models.TextField(_('الوصف'), blank=True)
    tax_rate = models.DecimalField(_('معدل الضريبة %'), max_digits=5, decimal_places=2,
                                  validators=[MinValueValidator(0), MaxValueValidator(100)])
    applicable_on = models.CharField(_('تطبق على'), max_length=50,
                                    choices=[('sales', _('المبيعات')), ('purchases', _('المشتريات')),
                                            ('both', _('الاثنين'))])
    active = models.BooleanField(_('نشطة'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('نوع ضريبة')
        verbose_name_plural = _('أنواع الضرائب')
    
    def __str__(self):
        return f"{self.name} ({self.tax_rate}%)"


class TaxCalculation(models.Model):
    """حسابات الضريبة"""
    
    TYPE_CHOICES = [
        ('vat', _('ضريبة القيمة المضافة')),
        ('income_tax', _('ضريبة الدخل')),
        ('corporate_tax', _('ضريبة الشركات')),
        ('withholding_tax', _('ضريبة الخصم')),
        ('stamp_duty', _('رسم الدمغة')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tax_type = models.ForeignKey(TaxType, on_delete=models.CASCADE)
    calculation_type = models.CharField(_('نوع الحساب'), max_length=50, choices=TYPE_CHOICES)
    
    # البيانات الأساسية
    taxable_amount = models.DecimalField(_('المبلغ الخاضع للضريبة'), max_digits=15, decimal_places=2)
    tax_rate = models.DecimalField(_('معدل الضريبة %'), max_digits=5, decimal_places=2)
    tax_amount = models.DecimalField(_('مبلغ الضريبة'), max_digits=15, decimal_places=2)
    
    # التفاصيل
    invoice = models.ForeignKey('sales.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='tax_calculations')
    journal_entry = models.ForeignKey('accounting.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True)
    
    calculation_date = models.DateField(_('تاريخ الحساب'), auto_now_add=True)
    
    # الحالة
    is_paid = models.BooleanField(_('تم دفعها'), default=False)
    payment_date = models.DateField(_('تاريخ الدفع'), null=True, blank=True)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('حساب ضريبة')
        verbose_name_plural = _('حسابات الضرائب')
        ordering = ['-calculation_date']
        indexes = [
            models.Index(fields=['tax_type']),
            models.Index(fields=['calculation_date']),
            models.Index(fields=['is_paid']),
        ]
    
    def __str__(self):
        return f"{self.get_calculation_type_display()} - {self.tax_amount}"


class TaxReport(models.Model):
    """تقارير ضريبية"""
    
    REPORT_TYPE_CHOICES = [
        ('vat_return', _('إقرار ضريبة القيمة المضافة')),
        ('income_tax_return', _('إقرار ضريبة الدخل')),
        ('withholding_return', _('إقرار الضرائب المستقطعة')),
        ('annual_return', _('الإقرار السنوي')),
    ]
    
    PERIOD_CHOICES = [
        ('monthly', _('شهري')),
        ('quarterly', _('ربع سنوي')),
        ('semi_annual', _('نصف سنوي')),
        ('annual', _('سنوي')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(_('نوع التقرير'), max_length=50, choices=REPORT_TYPE_CHOICES)
    period_type = models.CharField(_('نوع الفترة'), max_length=20, choices=PERIOD_CHOICES)
    
    # الفترة
    period_start = models.DateField(_('بداية الفترة'))
    period_end = models.DateField(_('نهاية الفترة'))
    
    # البيانات المالية
    total_taxable_income = models.DecimalField(_('إجمالي الدخل الخاضع'), max_digits=15, decimal_places=2)
    total_deductions = models.DecimalField(_('إجمالي الخصومات'), max_digits=15, decimal_places=2, default=0)
    taxable_profit = models.DecimalField(_('الربح الخاضع'), max_digits=15, decimal_places=2)
    total_tax_liability = models.DecimalField(_('إجمالي الالتزام الضريبي'), max_digits=15, decimal_places=2)
    tax_paid = models.DecimalField(_('الضريبة المدفوعة'), max_digits=15, decimal_places=2, default=0)
    tax_payable = models.DecimalField(_('الضريبة المستحقة'), max_digits=15, decimal_places=2)
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=50,
                            choices=[('draft', _('مسودة')), ('submitted', _('مرسلة')), 
                                   ('approved', _('موافق عليها')), ('rejected', _('مرفوضة'))])
    
    # الملفات
    report_document = models.FileField(_('وثيقة التقرير'), upload_to='tax_reports/', blank=True)
    submission_date = models.DateField(_('تاريخ الإرسال'), null=True, blank=True)
    reference_number = models.CharField(_('رقم المرجع'), max_length=100, blank=True)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('تقرير ضريبي')
        verbose_name_plural = _('التقارير الضريبية')
        ordering = ['-period_end']
        unique_together = ['report_type', 'period_start', 'period_end']
        indexes = [
            models.Index(fields=['report_type', 'period_end']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.period_end}"
    
    def calculate_tax_liability(self):
        """حساب الالتزام الضريبي"""
        self.taxable_profit = self.total_taxable_income - self.total_deductions
        # يتم حساب الضريبة حسب القوانين
        self.tax_payable = self.total_tax_liability - self.tax_paid
        self.save()


class TaxCompliance(models.Model):
    """الامتثال الضريبي"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # البيانات الأساسية
    taxpayer_id = models.CharField(_('رقم المكلف'), max_length=50)
    taxpayer_name = models.CharField(_('اسم المكلف'), max_length=200)
    
    # الالتزامات
    last_return_filed_date = models.DateField(_('تاريخ آخر إقرار'))
    next_return_due_date = models.DateField(_('تاريخ استحقاق الإقرار التالي'))
    tax_balance = models.DecimalField(_('الرصيد الضريبي'), max_digits=15, decimal_places=2)
    
    # الامتثال
    is_current = models.BooleanField(_('محدث'), default=True)
    compliance_status = models.CharField(_('حالة الامتثال'), max_length=50,
                                        choices=[('compliant', _('ممتثل')), 
                                                ('non_compliant', _('غير ممتثل')),
                                                ('pending', _('قيد الانتظار'))])
    
    # التنبيهات
    last_audit_date = models.DateField(_('تاريخ آخر تدقيق'), null=True, blank=True)
    audit_findings = models.TextField(_('نتائج التدقيق'), blank=True)
    
    updated_at = models.DateTimeField(_('آخر تحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('امتثال ضريبي')
        verbose_name_plural = _('الامتثال الضريبي')
    
    def __str__(self):
        return f"{self.taxpayer_name} - {self.compliance_status}"
