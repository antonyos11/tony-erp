"""
Executive Decision Cockpit
لوحة القيادة التنفيذية للإدارة العليا

توفر رؤية شاملة ومؤشرات أداء وتوصيات استراتيجية
"""

from django.db import models
from django.conf import settings
from decimal import Decimal
from typing import Dict, List
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Avg, Count, Q, F


class StrategicRecommendation(models.Model):
    """توصية استراتيجية"""
    
    CATEGORY_CHOICES = [
        ('production', 'إنتاج'),
        ('inventory', 'مخزون'),
        ('sales', 'مبيعات'),
        ('finance', 'مالية'),
        ('hr', 'موارد بشرية'),
        ('quality', 'جودة'),
        ('supplier', 'موردين'),
    ]
    
    PRIORITY_CHOICES = [
        ('critical', 'حرج'),
        ('high', 'عالي'),
        ('medium', 'متوسط'),
        ('low', 'منخفض'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'جديد'),
        ('reviewed', 'تمت المراجعة'),
        ('approved', 'موافق عليه'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('rejected', 'مرفوض'),
    ]
    
    title = models.CharField('العنوان', max_length=200)
    description = models.TextField('الوصف')
    category = models.CharField('الفئة', max_length=20, choices=CATEGORY_CHOICES)
    priority = models.CharField('الأولوية', max_length=20, choices=PRIORITY_CHOICES)
    
    # التحليل
    current_situation = models.TextField('الوضع الحالي')
    expected_impact = models.TextField('التأثير المتوقع')
    implementation_steps = models.JSONField('خطوات التنفيذ', default=list)
    
    # البيانات الداعمة
    supporting_data = models.JSONField('البيانات الداعمة', default=dict)
    estimated_cost = models.DecimalField('التكلفة المقدرة', max_digits=15, decimal_places=2, null=True, blank=True)
    expected_roi = models.DecimalField('العائد المتوقع %', max_digits=5, decimal_places=2, null=True, blank=True)
    
    # الحالة
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='new')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_recommendations', verbose_name='معين إلى')
    
    # التواريخ
    generated_date = models.DateTimeField('تاريخ التوليد', auto_now_add=True)
    reviewed_date = models.DateTimeField('تاريخ المراجعة', null=True, blank=True)
    due_date = models.DateField('تاريخ الاستحقاق', null=True, blank=True)
    completed_date = models.DateTimeField('تاريخ الإنجاز', null=True, blank=True)
    
    # المراجعة
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_recommendations', verbose_name='راجعه')
    review_notes = models.TextField('ملاحظات المراجعة', blank=True)
    
    # AI Generated
    is_ai_generated = models.BooleanField('توصية آلية', default=True)
    confidence_score = models.DecimalField('درجة الثقة', max_digits=5, decimal_places=2, default=Decimal('0'))
    
    class Meta:
        verbose_name = 'توصية استراتيجية'
        verbose_name_plural = 'التوصيات الاستراتيجية'
        ordering = ['-priority', '-generated_date']
    
    def __str__(self):
        return f"{self.title} ({self.priority})"


class ExecutiveDashboardService:
    """خدمة لوحة القيادة التنفيذية"""
    
    def __init__(self):
        self.default_period_days = 30
    
    def get_executive_summary(self, period_days: int = None) -> Dict:
        """الحصول على ملخص تنفيذي شامل"""
        period_days = period_days or self.default_period_days
        
        return {
            'overview': self._get_business_overview(period_days),
            'financial': self._get_financial_kpis(period_days),
            'operations': self._get_operational_kpis(period_days),
            'sales': self._get_sales_kpis(period_days),
            'inventory': self._get_inventory_kpis(period_days),
            'hr': self._get_hr_kpis(period_days),
            'quality': self._get_quality_kpis(period_days),
            'alerts': self._get_critical_alerts(),
            'recommendations': self._get_top_recommendations(),
            'trends': self._analyze_trends(period_days),
            'period_days': period_days,
            'generated_at': timezone.now().isoformat()
        }
    
    def _get_business_overview(self, period_days: int) -> Dict:
        """نظرة عامة على الأعمال"""
        from sales.models import Invoice
        from purchases.models import PurchaseBill
        from production.models import ProductionOrder
        
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # المبيعات
        sales_data = Invoice.objects.filter(
            invoice_date__gte=start_date
        ).aggregate(
            total_revenue=Sum('total_amount'),
            count=Count('id')
        )
        
        # المشتريات
        purchases_data = PurchaseBill.objects.filter(
            date__gte=start_date
        ).aggregate(
            total_cost=Sum(F('items__quantity') * F('items__cost')),
            count=Count('id')
        )
        
        # الإنتاج
        production_data = ProductionOrder.objects.filter(
            date__gte=start_date
        ).aggregate(
            total_units=Sum('quantity_to_produce'),
            count=Count('id')
        )
        
        # حساب الربح التقريبي
        revenue = sales_data['total_revenue'] or Decimal('0')
        cost = purchases_data['total_cost'] or Decimal('0')
        gross_profit = revenue - cost
        profit_margin = (gross_profit / revenue * 100) if revenue > 0 else Decimal('0')
        
        return {
            'revenue': float(revenue),
            'cost': float(cost),
            'gross_profit': float(gross_profit),
            'profit_margin': float(profit_margin),
            'total_orders': sales_data['count'] or 0,
            'total_purchases': purchases_data['count'] or 0,
            'total_production': production_data['count'] or 0,
            'units_produced': production_data['total_units'] or 0
        }
    
    def _get_financial_kpis(self, period_days: int) -> Dict:
        """مؤشرات الأداء المالية"""
        from accounting.models import Account, JournalEntryLine
        from accounting.break_even import breakeven_analyzer
        
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # حساب الإيرادات والمصروفات
        revenue_accounts = Account.objects.filter(type='revenue')
        expense_accounts = Account.objects.filter(type='expense')
        
        revenues = JournalEntryLine.objects.filter(
            journal__date__gte=start_date,
            journal__is_posted=True,
            account__in=revenue_accounts
        ).aggregate(total=Sum('credit'))['total'] or Decimal('0')
        
        expenses = JournalEntryLine.objects.filter(
            journal__date__gte=start_date,
            journal__is_posted=True,
            account__in=expense_accounts
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0')
        
        net_profit = revenues - expenses
        
        # نقطة التعادل
        breakeven = breakeven_analyzer.calculate_company_breakeven(period_days)
        
        # التدفق النقدي
        cash_accounts = Account.objects.filter(
            Q(code__startswith='1.1.1') | Q(name__icontains='نقدية')
        )
        
        cash_balance = cash_accounts.aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0')
        
        return {
            'revenues': float(revenues),
            'expenses': float(expenses),
            'net_profit': float(net_profit),
            'profit_margin': float((net_profit / revenues * 100)) if revenues > 0 else 0,
            'cash_balance': float(cash_balance),
            'breakeven': {
                'revenue_required': breakeven['breakeven']['revenue_required'],
                'status': breakeven['performance']['status'],
                'safety_margin': breakeven['performance']['safety_margin_percent']
            }
        }
    
    def _get_operational_kpis(self, period_days: int) -> Dict:
        """مؤشرات الأداء التشغيلية"""
        from production.models import ProductionOrder, ProductionWorkCenter
        
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # الطاقة الإنتاجية
        work_centers = ProductionWorkCenter.objects.filter(is_active=True)
        total_capacity = sum(
            float(wc.capacity_per_hour * wc.working_hours_per_day)
            for wc in work_centers
        )
        
        # الإنتاج الفعلي
        actual_production = ProductionOrder.objects.filter(
            date__gte=start_date,
            status='completed'
        ).aggregate(
            total=Sum('quantity_produced')
        )['total'] or 0
        
        capacity_utilization = (actual_production / (total_capacity * period_days) * 100) if total_capacity > 0 else 0
        
        # معدل كفاءة الإنتاج
        orders = ProductionOrder.objects.filter(
            date__gte=start_date,
            status='completed'
        )
        
        efficiency = 0
        if orders.exists():
            efficiency_sum = sum(
                (order.quantity_produced / order.quantity_to_produce * 100)
                for order in orders if order.quantity_to_produce > 0
            )
            efficiency = efficiency_sum / orders.count()
        
        return {
            'capacity_utilization': float(capacity_utilization),
            'production_efficiency': float(efficiency),
            'total_capacity_per_day': float(total_capacity),
            'active_work_centers': work_centers.count(),
            'completed_orders': orders.count()
        }
    
    def _get_sales_kpis(self, period_days: int) -> Dict:
        """مؤشرات أداء المبيعات"""
        from sales.models import Invoice, InvoiceItem
        from crm.models import Customer
        
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # المبيعات
        invoices = Invoice.objects.filter(invoice_date__gte=start_date)
        
        total_sales = invoices.aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        
        # متوسط قيمة الطلب
        avg_order_value = (total_sales['total'] / total_sales['count']) if total_sales['count'] > 0 else Decimal('0')
        
        # العملاء الجدد
        new_customers = Customer.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=period_days)
        ).count()
        
        # أفضل المنتجات مبيعاً
        top_products = InvoiceItem.objects.filter(
            invoice__invoice_date__gte=start_date
        ).values('product__name').annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price'))
        ).order_by('-total_revenue')[:5]
        
        return {
            'total_sales': float(total_sales['total'] or 0),
            'total_orders': total_sales['count'] or 0,
            'avg_order_value': float(avg_order_value),
            'new_customers': new_customers,
            'top_products': [
                {
                    'product': p['product__name'],
                    'quantity': p['total_quantity'],
                    'revenue': float(p['total_revenue'])
                }
                for p in top_products
            ]
        }
    
    def _get_inventory_kpis(self, period_days: int) -> Dict:
        """مؤشرات أداء المخزون"""
        from inventory.models import Stock, Product
        from sales.models import InvoiceItem
        
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # قيمة المخزون الإجمالية
        total_stock_value = Stock.objects.aggregate(
            total=Sum(F('quantity') * F('product__cost'))
        )['total'] or Decimal('0')
        
        # معدل دوران المخزون
        cogs = InvoiceItem.objects.filter(
            invoice__invoice_date__gte=start_date
        ).aggregate(
            total=Sum(F('quantity') * F('product__cost'))
        )['total'] or Decimal('0')
        
        inventory_turnover = (cogs / total_stock_value) if total_stock_value > 0 else Decimal('0')
        
        # المنتجات الراكدة
        slow_moving = Product.objects.filter(
            stock__quantity__gt=0
        ).annotate(
            sales_count=Count('invoiceitem', filter=Q(invoiceitem__invoice__invoice_date__gte=start_date))
        ).filter(sales_count=0).count()
        
        # المنتجات أقل من الحد الأدنى
        low_stock = Stock.objects.filter(
            quantity__lt=F('product__min_stock'),
            quantity__gt=0
        ).count()
        
        return {
            'total_stock_value': float(total_stock_value),
            'inventory_turnover': float(inventory_turnover),
            'slow_moving_products': slow_moving,
            'low_stock_items': low_stock
        }
    
    def _get_hr_kpis(self, period_days: int) -> Dict:
        """مؤشرات أداء الموارد البشرية"""
        from hr.models import Employee, AttendanceRecord
        
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # إجمالي الموظفين
        total_employees = Employee.objects.filter(status='active').count()
        
        # معدل الحضور
        total_working_days = period_days * total_employees
        actual_attendance = AttendanceRecord.objects.filter(
            date__gte=start_date,
            record_type='check_in'
        ).count()
        
        attendance_rate = (actual_attendance / total_working_days * 100) if total_working_days > 0 else 0
        
        return {
            'total_employees': total_employees,
            'attendance_rate': float(attendance_rate),
            'active_employees': total_employees
        }
    
    def _get_quality_kpis(self, period_days: int) -> Dict:
        """مؤشرات أداء الجودة"""
        from quality_control.models import QualityInspection, QualityIssue
        
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # فحوصات الجودة
        inspections = QualityInspection.objects.filter(
            inspection_date__gte=start_date
        )
        
        total_inspections = inspections.count()
        passed_inspections = inspections.filter(status='passed').count()
        
        pass_rate = (passed_inspections / total_inspections * 100) if total_inspections > 0 else 100
        
        # مشاكل الجودة
        open_issues = QualityIssue.objects.filter(
            status__in=['open', 'investigating']
        ).count()
        
        critical_issues = QualityIssue.objects.filter(
            status__in=['open', 'investigating'],
            severity='critical'
        ).count()
        
        return {
            'quality_pass_rate': float(pass_rate),
            'total_inspections': total_inspections,
            'open_issues': open_issues,
            'critical_issues': critical_issues
        }
    
    def _get_critical_alerts(self) -> List[Dict]:
        """الحصول على التنبيهات الحرجة"""
        from inventory.models import Stock
        from quality_control.models import QualityIssue
        from production.models import ProductionOrder
        
        alerts = []
        
        # تنبيهات المخزون
        low_stock = Stock.objects.filter(
            quantity__lt=F('product__min_stock'),
            quantity__gt=0
        ).select_related('product')[:5]
        
        for stock in low_stock:
            alerts.append({
                'type': 'inventory',
                'severity': 'high',
                'message': f'مخزون {stock.product.name} أقل من الحد الأدنى',
                'details': {
                    'product': stock.product.name,
                    'current': float(stock.quantity),
                    'minimum': stock.product.min_stock
                }
            })
        
        # تنبيهات الجودة الحرجة
        critical_issues = QualityIssue.objects.filter(
            severity='critical',
            status__in=['open', 'investigating']
        )[:3]
        
        for issue in critical_issues:
            alerts.append({
                'type': 'quality',
                'severity': 'critical',
                'message': f'مشكلة جودة حرجة: {issue.title}',
                'details': {
                    'issue_code': issue.code,
                    'severity': issue.severity
                }
            })
        
        # تنبيهات الإنتاج المتأخرة
        delayed_orders = ProductionOrder.objects.filter(
            expected_completion_date__lt=timezone.now().date(),
            status__in=['confirmed', 'in_progress']
        )[:3]
        
        for order in delayed_orders:
            alerts.append({
                'type': 'production',
                'severity': 'medium',
                'message': f'أمر إنتاج {order.order_number} متأخر',
                'details': {
                    'order_number': order.order_number,
                    'expected_date': order.expected_completion_date.isoformat() if order.expected_completion_date else None
                }
            })
        
        return alerts
    
    def _get_top_recommendations(self) -> List[Dict]:
        """الحصول على أهم التوصيات"""
        recommendations = StrategicRecommendation.objects.filter(
            status__in=['new', 'reviewed']
        ).order_by('-priority', '-confidence_score')[:5]
        
        return [
            {
                'title': rec.title,
                'category': rec.category,
                'priority': rec.priority,
                'expected_impact': rec.expected_impact,
                'confidence_score': float(rec.confidence_score)
            }
            for rec in recommendations
        ]
    
    def _analyze_trends(self, period_days: int) -> Dict:
        """تحليل الاتجاهات"""
        from sales.models import Invoice
        
        # مقارنة مع الفترة السابقة
        current_start = timezone.now().date() - timedelta(days=period_days)
        previous_start = current_start - timedelta(days=period_days)
        
        current_sales = Invoice.objects.filter(
            invoice_date__gte=current_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        previous_sales = Invoice.objects.filter(
            invoice_date__gte=previous_start,
            invoice_date__lt=current_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('1')
        
        sales_growth = ((current_sales - previous_sales) / previous_sales * 100) if previous_sales > 0 else Decimal('0')
        
        return {
            'sales_growth': float(sales_growth),
            'trend': 'up' if sales_growth > 0 else 'down',
            'current_period_sales': float(current_sales),
            'previous_period_sales': float(previous_sales)
        }
    
    def generate_strategic_recommendations(self) -> List[StrategicRecommendation]:
        """توليد توصيات استراتيجية تلقائية"""
        recommendations = []
        
        # توصيات الإنتاج
        recommendations.extend(self._generate_production_recommendations())
        
        # توصيات المخزون
        recommendations.extend(self._generate_inventory_recommendations())
        
        # توصيات المبيعات
        recommendations.extend(self._generate_sales_recommendations())
        
        return recommendations
    
    def _generate_production_recommendations(self) -> List[StrategicRecommendation]:
        """توليد توصيات الإنتاج"""
        from production.models import ProductionOrder, ProductionWorkCenter
        
        recommendations = []
        
        # تحليل الطاقة الإنتاجية
        work_centers = ProductionWorkCenter.objects.filter(is_active=True)
        
        for wc in work_centers:
            if wc.efficiency_rate < 70:
                rec = StrategicRecommendation.objects.create(
                    title=f'تحسين كفاءة {wc.name}',
                    description=f'خط الإنتاج {wc.name} يعمل بكفاءة {wc.efficiency_rate}% فقط',
                    category='production',
                    priority='high',
                    current_situation=f'الكفاءة الحالية: {wc.efficiency_rate}%',
                    expected_impact='زيادة الإنتاجية بنسبة 20-30%',
                    implementation_steps=[
                        'تحليل أسباب انخفاض الكفاءة',
                        'صيانة وفحص المعدات',
                        'تدريب العمال',
                        'تحسين العمليات'
                    ],
                    confidence_score=Decimal('85')
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _generate_inventory_recommendations(self) -> List[StrategicRecommendation]:
        """توليد توصيات المخزون"""
        from inventory.models import Stock, Product
        from sales.models import InvoiceItem
        
        recommendations = []
        
        # المنتجات الراكدة
        slow_moving = Product.objects.filter(
            stock__quantity__gt=0
        ).annotate(
            sales_count=Count('invoiceitem', filter=Q(
                invoiceitem__invoice__invoice_date__gte=timezone.now() - timedelta(days=90)
            ))
        ).filter(sales_count=0)[:5]
        
        if slow_moving.exists():
            rec = StrategicRecommendation.objects.create(
                title='تصفية المنتجات الراكدة',
                description=f'يوجد {slow_moving.count()} منتج راكد بدون مبيعات منذ 90 يوم',
                category='inventory',
                priority='medium',
                current_situation='مخزون راكد يحتل مساحة وتكلفة تخزين',
                expected_impact='تحرير رأس مال مجمد وتقليل تكاليف التخزين',
                implementation_steps=[
                    'عمل عروض وخصومات للمنتجات الراكدة',
                    'إيقاف إنتاج المنتجات غير المطلوبة',
                    'بيع بأسعار مخفضة للجملة'
                ],
                supporting_data={
                    'products': [p.name for p in slow_moving]
                },
                confidence_score=Decimal('90')
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _generate_sales_recommendations(self) -> List[StrategicRecommendation]:
        """توليد توصيات المبيعات"""
        from sales.models import InvoiceItem
        
        recommendations = []
        
        # أفضل المنتجات
        top_products = InvoiceItem.objects.filter(
            invoice__invoice_date__gte=timezone.now() - timedelta(days=30)
        ).values('product').annotate(
            total_revenue=Sum(F('quantity') * F('price'))
        ).order_by('-total_revenue')[:3]
        
        if top_products.exists():
            product_names = ', '.join([f"منتج {p['product']}" for p in top_products])
            
            rec = StrategicRecommendation.objects.create(
                title='زيادة إنتاج المنتجات الأكثر مبيعاً',
                description=f'المنتجات ({product_names}) تحقق أعلى إيرادات',
                category='sales',
                priority='high',
                current_situation='هناك طلب عالي على بعض المنتجات',
                expected_impact='زيادة الإيرادات بنسبة 15-25%',
                implementation_steps=[
                    'زيادة الطاقة الإنتاجية لهذه المنتجات',
                    'زيادة المخزون الاحتياطي',
                    'التسويق المكثف لهذه المنتجات'
                ],
                confidence_score=Decimal('92')
            )
            recommendations.append(rec)
        
        return recommendations


# Singleton instance
executive_service = ExecutiveDashboardService()
