"""
نظام الشؤون المالية - Treasury Management
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class CashPosition(models.Model):
    """موقف السيولة النقدية"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    position_date = models.DateField(_('تاريخ الموقف'), auto_now_add=True)
    
    # الأموال المتاحة
    bank_balance = models.DecimalField(_('رصيد البنك'), max_digits=15, decimal_places=2)
    cash_on_hand = models.DecimalField(_('النقد في الصندوق'), max_digits=15, decimal_places=2)
    short_term_investments = models.DecimalField(_('استثمارات قصيرة الأجل'), max_digits=15, decimal_places=2, default=0)
    
    # الالتزامات
    short_term_liabilities = models.DecimalField(_('التزامات قصيرة الأجل'), max_digits=15, decimal_places=2)
    
    # الحسابات
    total_liquidity = models.DecimalField(_('إجمالي السيولة'), max_digits=15, decimal_places=2)
    net_position = models.DecimalField(_('الموقف الصافي'), max_digits=15, decimal_places=2)
    
    # المؤشرات
    liquidity_ratio = models.DecimalField(_('نسبة السيولة'), max_digits=5, decimal_places=2)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('موقف السيولة')
        verbose_name_plural = _('مواقف السيولة')
        ordering = ['-position_date']
    
    def __str__(self):
        return f"موقف السيولة - {self.position_date}"
    
    def calculate_metrics(self):
        """حساب المؤشرات"""
        self.total_liquidity = (self.bank_balance + self.cash_on_hand + 
                               self.short_term_investments)
        self.net_position = self.total_liquidity - self.short_term_liabilities
        
        if self.short_term_liabilities > 0:
            self.liquidity_ratio = Decimal(self.total_liquidity / self.short_term_liabilities)
        
        self.save()


class CashFlow(models.Model):
    """تنبؤات التدفق النقدي"""
    
    PERIOD_CHOICES = [
        ('daily', _('يومي')),
        ('weekly', _('أسبوعي')),
        ('monthly', _('شهري')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    forecast_date = models.DateField(_('تاريخ التنبؤ'))
    period_type = models.CharField(_('نوع الفترة'), max_length=20, choices=PERIOD_CHOICES)
    
    # التدفقات النقدية
    opening_balance = models.DecimalField(_('الرصيد الافتتاحي'), max_digits=15, decimal_places=2)
    inflows = models.DecimalField(_('التدفقات الداخلة'), max_digits=15, decimal_places=2)
    outflows = models.DecimalField(_('التدفقات الخارجة'), max_digits=15, decimal_places=2)
    closing_balance = models.DecimalField(_('الرصيد الختامي'), max_digits=15, decimal_places=2)
    
    # الدقة
    accuracy_score = models.DecimalField(_('درجة الدقة'), max_digits=5, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('تنبؤ التدفق النقدي')
        verbose_name_plural = _('تنبؤات التدفق النقدي')
        ordering = ['forecast_date']
    
    def __str__(self):
        return f"تنبؤ {self.forecast_date}"


class Investment(models.Model):
    """الاستثمارات"""
    
    INVESTMENT_TYPE_CHOICES = [
        ('stocks', _('الأسهم')),
        ('bonds', _('السندات')),
        ('funds', _('الصناديق')),
        ('real_estate', _('العقارات')),
        ('deposits', _('الودائع')),
        ('other', _('أخرى')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('نشطة')),
        ('matured', _('استحقت')),
        ('liquidated', _('مصفاة')),
        ('on_hold', _('معلقة')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investment_id = models.CharField(_('رقم الاستثمار'), max_length=100, unique=True)
    investment_type = models.CharField(_('نوع الاستثمار'), max_length=50, choices=INVESTMENT_TYPE_CHOICES)
    
    # البيانات
    description = models.CharField(_('الوصف'), max_length=200)
    principal_amount = models.DecimalField(_('المبلغ الأساسي'), max_digits=15, decimal_places=2)
    investment_date = models.DateField(_('تاريخ الاستثمار'))
    maturity_date = models.DateField(_('تاريخ الاستحقاق'))
    
    # العائد
    expected_return_rate = models.DecimalField(_('معدل العائد المتوقع'), max_digits=5, decimal_places=2)
    expected_return_amount = models.DecimalField(_('مبلغ العائد المتوقع'), max_digits=15, decimal_places=2)
    actual_return_amount = models.DecimalField(_('مبلغ العائد الفعلي'), max_digits=15, decimal_places=2, default=0)
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='active')
    current_value = models.DecimalField(_('القيمة الحالية'), max_digits=15, decimal_places=2)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('استثمار')
        verbose_name_plural = _('الاستثمارات')
        ordering = ['-investment_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['maturity_date']),
        ]
    
    def __str__(self):
        return f"{self.investment_id} - {self.description}"
    
    def get_roi(self):
        """حساب العائد على الاستثمار"""
        if self.principal_amount == 0:
            return 0
        return ((self.actual_return_amount + (self.current_value - self.principal_amount)) / 
                self.principal_amount * 100)


class TreasuryTarget(models.Model):
    """أهداف الشؤون المالية"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('اسم الهدف'), max_length=200)
    description = models.TextField(_('الوصف'))
    
    # الفترة
    start_date = models.DateField(_('تاريخ البداية'))
    end_date = models.DateField(_('تاريخ النهاية'))
    
    # الأهداف
    target_liquidity = models.DecimalField(_('هدف السيولة'), max_digits=15, decimal_places=2)
    target_debt_ratio = models.DecimalField(_('هدف نسبة الدين'), max_digits=5, decimal_places=2)
    target_roi = models.DecimalField(_('هدف العائد'), max_digits=5, decimal_places=2)
    
    # الأداء الفعلي
    actual_liquidity = models.DecimalField(_('السيولة الفعلية'), max_digits=15, decimal_places=2, default=0)
    actual_debt_ratio = models.DecimalField(_('نسبة الدين الفعلية'), max_digits=5, decimal_places=2, default=0)
    actual_roi = models.DecimalField(_('العائد الفعلي'), max_digits=5, decimal_places=2, default=0)
    
    status = models.CharField(_('الحالة'), max_length=20,
                            choices=[('not_started', _('لم يبدأ')), 
                                   ('in_progress', _('قيد الإنجاز')),
                                   ('achieved', _('تحقق')), 
                                   ('failed', _('فشل'))])
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('هدف الشؤون المالية')
        verbose_name_plural = _('أهداف الشؤون المالية')
    
    def __str__(self):
        return self.name
