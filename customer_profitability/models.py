from django.db import models
from decimal import Decimal


class CustomerProfitabilityAnalysis(models.Model):
    """تحليل ربحية العميل"""
    customer = models.ForeignKey('partners.Customer', on_delete=models.CASCADE, related_name='profitability_analyses')
    analysis_period_start = models.DateField('بداية فترة التحليل')
    analysis_period_end = models.DateField('نهاية فترة التحليل')
    
    # الإيرادات
    total_revenue = models.DecimalField('إجمالي الإيرادات', max_digits=15, decimal_places=2, default=0)
    total_orders = models.IntegerField('عدد الطلبات', default=0)
    average_order_value = models.DecimalField('متوسط قيمة الطلب', max_digits=15, decimal_places=2, default=0)
    
    # التكاليف
    cost_of_goods_sold = models.DecimalField('تكلفة البضاعة المباعة', max_digits=15, decimal_places=2, default=0)
    service_cost = models.DecimalField('تكلفة الخدمة', max_digits=15, decimal_places=2, default=0)
    marketing_cost = models.DecimalField('تكلفة التسويق', max_digits=15, decimal_places=2, default=0)
    support_cost = models.DecimalField('تكلفة الدعم', max_digits=15, decimal_places=2, default=0)
    
    # الربحية
    gross_profit = models.DecimalField('إجمالي الربح', max_digits=15, decimal_places=2, default=0)
    net_profit = models.DecimalField('صافي الربح', max_digits=15, decimal_places=2, default=0)
    profit_margin = models.DecimalField('هامش الربح %', max_digits=5, decimal_places=2, default=0)
    
    # CLV
    customer_lifetime_value = models.DecimalField('قيمة العميل مدى الحياة', max_digits=15, decimal_places=2, default=0)
    customer_acquisition_cost = models.DecimalField('تكلفة اكتساب العميل', max_digits=15, decimal_places=2, default=0)
    
    # التصنيف
    tier = models.CharField('التصنيف', max_length=10, choices=[
        ('A', 'A - ممتاز'), ('B', 'B - جيد'), ('C', 'C - متوسط'), ('D', 'D - ضعيف')
    ], default='C')
    
    # التوصيات
    recommendations = models.TextField('التوصيات', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'تحليل ربحية عميل'
        verbose_name_plural = 'تحليلات ربحية العملاء'
        ordering = ['-net_profit']
    
    def __str__(self):
        return f"{self.customer.name} - {self.tier}"
    
    def calculate_profitability(self):
        """حساب الربحية"""
        self.gross_profit = self.total_revenue - self.cost_of_goods_sold
        total_costs = self.cost_of_goods_sold + self.service_cost + self.marketing_cost + self.support_cost
        self.net_profit = self.total_revenue - total_costs
        
        if self.total_revenue > 0:
            self.profit_margin = (self.net_profit / self.total_revenue) * 100
        
        if self.total_orders > 0:
            self.average_order_value = self.total_revenue / self.total_orders
        
        # تصنيف العميل
        if self.net_profit > 100000:
            self.tier = 'A'
        elif self.net_profit > 50000:
            self.tier = 'B'
        elif self.net_profit > 10000:
            self.tier = 'C'
        else:
            self.tier = 'D'
        
        self.save()


class CustomerValueScore(models.Model):
    """نقاط قيمة العميل"""
    customer = models.OneToOneField('partners.Customer', on_delete=models.CASCADE, related_name='value_score')
    
    # المقاييس
    recency_score = models.IntegerField('نقاط الحداثة', default=0, help_text='آخر عملية شراء')
    frequency_score = models.IntegerField('نقاط التكرار', default=0, help_text='عدد المشتريات')
    monetary_score = models.IntegerField('نقاط القيمة النقدية', default=0, help_text='إجمالي الإنفاق')
    
    total_score = models.IntegerField('إجمالي النقاط', default=0)
    segment = models.CharField('الشريحة', max_length=20, choices=[
        ('champion', 'بطل'), ('loyal', 'مخلص'), ('potential', 'محتمل'), 
        ('at_risk', 'معرض للخطر'), ('lost', 'مفقود')
    ], default='potential')
    
    last_calculated = models.DateTimeField('آخر حساب', auto_now=True)
    
    class Meta:
        verbose_name = 'نقاط قيمة العميل'
        verbose_name_plural = 'نقاط قيمة العملاء'
    
    def __str__(self):
        return f"{self.customer.name} - {self.segment}"
