from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class WarrantyPolicy(models.Model):
    """سياسة الضمان"""
    name = models.CharField('اسم السياسة', max_length=200)
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='warranty_policies')
    duration_months = models.IntegerField('مدة الضمان (شهور)')
    coverage_type = models.CharField('نوع التغطية', max_length=50, choices=[
        ('full', 'كاملة'), ('limited', 'محدودة'), ('parts_only', 'قطع غيار فقط'), ('labor_only', 'عمالة فقط')
    ])
    terms_conditions = models.TextField('الشروط والأحكام')
    cost = models.DecimalField('تكلفة الضمان', max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'سياسة ضمان'
        verbose_name_plural = 'سياسات الضمان'
    
    def __str__(self):
        return f"{self.name} - {self.product.name}"


class Warranty(models.Model):
    """الضمان"""
    warranty_number = models.CharField('رقم الضمان', max_length=100, unique=True)
    policy = models.ForeignKey(WarrantyPolicy, on_delete=models.PROTECT, verbose_name='السياسة')
    customer = models.ForeignKey('crm.Customer', on_delete=models.CASCADE, related_name='warranties')
    sale_order = models.ForeignKey('sales.SaleOrder', on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE)
    serial_number = models.CharField('الرقم التسلسلي', max_length=100, blank=True)
    
    start_date = models.DateField('تاريخ البداية')
    end_date = models.DateField('تاريخ الانتهاء')
    status = models.CharField('الحالة', max_length=20, choices=[
        ('active', 'نشط'), ('expired', 'منتهي'), ('cancelled', 'ملغي'), ('claimed', 'تم المطالبة')
    ], default='active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'ضمان'
        verbose_name_plural = 'الضمانات'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.warranty_number} - {self.customer.name}"


class WarrantyClaim(models.Model):
    """مطالبة ضمان"""
    claim_number = models.CharField('رقم المطالبة', max_length=100, unique=True)
    warranty = models.ForeignKey(Warranty, on_delete=models.CASCADE, related_name='claims')
    claim_date = models.DateField('تاريخ المطالبة', auto_now_add=True)
    issue_description = models.TextField('وصف المشكلة')
    status = models.CharField('الحالة', max_length=20, choices=[
        ('pending', 'معلق'), ('approved', 'معتمد'), ('rejected', 'مرفوض'), 
        ('in_progress', 'قيد المعالجة'), ('completed', 'مكتمل')
    ], default='pending')
    
    repair_cost = models.DecimalField('تكلفة الإصلاح', max_digits=10, decimal_places=2, default=0)
    parts_cost = models.DecimalField('تكلفة القطع', max_digits=10, decimal_places=2, default=0)
    labor_cost = models.DecimalField('تكلفة العمالة', max_digits=10, decimal_places=2, default=0)
    
    resolution = models.TextField('الحل', blank=True)
    completed_date = models.DateField('تاريخ الإنجاز', null=True, blank=True)
    
    handled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'مطالبة ضمان'
        verbose_name_plural = 'مطالبات الضمان'
        ordering = ['-claim_date']
    
    def __str__(self):
        return f"{self.claim_number}"
