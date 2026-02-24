"""
نماذج إدارة الميزانيات
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()


class FiscalYear(models.Model):
    """السنة المالية"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('active', 'نشطة'),
        ('closed', 'مغلقة'),
    ]
    
    name = models.CharField('اسم السنة', max_length=100)
    code = models.CharField('الرمز', max_length=20, unique=True)
    start_date = models.DateField('تاريخ البداية')
    end_date = models.DateField('تاريخ النهاية')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    is_current = models.BooleanField('السنة الحالية', default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = 'سنة مالية'
        verbose_name_plural = 'السنوات المالية'
        ordering = ['-start_date']
    
    def __str__(self):
        return self.name


class Budget(models.Model):
    """الميزانية"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('submitted', 'مُقدمة'),
        ('approved', 'معتمدة'),
        ('rejected', 'مرفوضة'),
        ('active', 'نشطة'),
        ('closed', 'مغلقة'),
    ]
    
    BUDGET_TYPE_CHOICES = [
        ('annual', 'سنوية'),
        ('quarterly', 'ربع سنوية'),
        ('monthly', 'شهرية'),
        ('project', 'مشروع'),
        ('department', 'قسم'),
    ]
    
    name = models.CharField('اسم الميزانية', max_length=200)
    code = models.CharField('رمز الميزانية', max_length=50, unique=True)
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT, 
                                   related_name='budgets', verbose_name='السنة المالية')
    
    budget_type = models.CharField('نوع الميزانية', max_length=20, choices=BUDGET_TYPE_CHOICES, default='annual')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    start_date = models.DateField('من تاريخ')
    end_date = models.DateField('إلى تاريخ')
    
    total_amount = models.DecimalField('الإجمالي المخطط', max_digits=18, decimal_places=2, default=0)
    
    department = models.ForeignKey('hr.Department', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='budgets', verbose_name='القسم')
    cost_center = models.ForeignKey('accounting.CostCenter', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='budgets', verbose_name='مركز التكلفة')
    
    description = models.TextField('الوصف', blank=True)
    notes = models.TextField('ملاحظات', blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_budgets')
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='approved_budgets')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'ميزانية'
        verbose_name_plural = 'الميزانيات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_total_planned(self):
        return self.lines.aggregate(total=models.Sum('planned_amount'))['total'] or Decimal('0')
    
    def get_total_actual(self):
        return self.lines.aggregate(total=models.Sum('actual_amount'))['total'] or Decimal('0')
    
    def get_variance(self):
        return self.get_total_planned() - self.get_total_actual()
    
    def get_utilization_percentage(self):
        planned = self.get_total_planned()
        if planned > 0:
            return (self.get_total_actual() / planned) * 100
        return Decimal('0')


class BudgetLine(models.Model):
    """بند ميزانية"""
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='lines', verbose_name='الميزانية')
    account = models.ForeignKey('accounting.Account', on_delete=models.PROTECT, 
                               related_name='budget_lines', verbose_name='الحساب')
    
    description = models.CharField('الوصف', max_length=300, blank=True)
    
    planned_amount = models.DecimalField('المبلغ المخطط', max_digits=18, decimal_places=2, default=0)
    actual_amount = models.DecimalField('المبلغ الفعلي', max_digits=18, decimal_places=2, default=0)
    committed_amount = models.DecimalField('المبلغ المرتبط', max_digits=18, decimal_places=2, default=0)
    
    # التوزيع الشهري (اختياري)
    jan = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    feb = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    mar = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    apr = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    may = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    jun = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    jul = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    aug = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sep = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    oct = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    nov = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    dec = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    notes = models.TextField('ملاحظات', blank=True)
    
    class Meta:
        verbose_name = 'بند ميزانية'
        verbose_name_plural = 'بنود الميزانية'
        unique_together = ['budget', 'account']
    
    def __str__(self):
        return f"{self.budget.code} - {self.account.name}"
    
    @property
    def variance(self):
        return self.planned_amount - self.actual_amount
    
    @property
    def variance_percentage(self):
        if self.planned_amount > 0:
            return ((self.planned_amount - self.actual_amount) / self.planned_amount) * 100
        return Decimal('0')
    
    @property
    def available_amount(self):
        return self.planned_amount - self.actual_amount - self.committed_amount


class BudgetAlert(models.Model):
    """تنبيهات الميزانية"""
    ALERT_TYPE_CHOICES = [
        ('warning', 'تحذير'),
        ('exceeded', 'تجاوز'),
        ('approaching', 'اقتراب'),
    ]
    
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='alerts')
    budget_line = models.ForeignKey(BudgetLine, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    
    alert_type = models.CharField('نوع التنبيه', max_length=20, choices=ALERT_TYPE_CHOICES)
    message = models.TextField('الرسالة')
    threshold_percentage = models.DecimalField('نسبة الحد', max_digits=5, decimal_places=2)
    current_percentage = models.DecimalField('النسبة الحالية', max_digits=5, decimal_places=2)
    
    is_read = models.BooleanField('مقروء', default=False)
    is_resolved = models.BooleanField('تم الحل', default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='read_budget_alerts')
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'تنبيه ميزانية'
        verbose_name_plural = 'تنبيهات الميزانية'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.budget}"


class BudgetTransfer(models.Model):
    """تحويل بين بنود الميزانية"""
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
    ]
    
    from_line = models.ForeignKey(BudgetLine, on_delete=models.PROTECT, related_name='transfers_out', verbose_name='من بند')
    to_line = models.ForeignKey(BudgetLine, on_delete=models.PROTECT, related_name='transfers_in', verbose_name='إلى بند')
    amount = models.DecimalField('المبلغ', max_digits=18, decimal_places=2)
    
    reason = models.TextField('السبب')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='requested_budget_transfers')
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_budget_transfers')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'تحويل ميزانية'
        verbose_name_plural = 'تحويلات الميزانية'
    
    def __str__(self):
        return f"تحويل {self.amount} من {self.from_line} إلى {self.to_line}"
