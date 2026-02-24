"""
مؤشرات الأداء الرئيسية المحسّنة - KPIs
Enhanced Key Performance Indicators
"""

from django.db.models import Sum, Count, Avg, F, Q, Max, Min
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal


class EnhancedKPICalculator:
    """حاسبة مؤشرات الأداء المحسّنة"""
    
    def __init__(self, user=None, branch=None, date_range=None):
        self.user = user
        self.branch = branch
        self.date_range = date_range or self._get_default_date_range()
    
    def _get_default_date_range(self):
        """الحصول على النطاق الزمني الافتراضي (الشهر الحالي)"""
        today = timezone.now().date()
        start_date = today.replace(day=1)
        return {'start': start_date, 'end': today}
    
    def get_all_kpis(self):
        """الحصول على جميع مؤشرات الأداء"""
        return {
            'sales': self.get_sales_kpis(),
            'inventory': self.get_inventory_kpis(),
            'financial': self.get_financial_kpis(),
            'customer': self.get_customer_kpis(),
            'operational': self.get_operational_kpis()
        }
    
    def get_sales_kpis(self):
        """مؤشرات المبيعات"""
        from sales.models import Invoice
        
        # المبيعات الحالية
        current_sales = Invoice.objects.filter(
            date__range=[self.date_range['start'], self.date_range['end']],
            is_approved=True, is_deleted=False
        )
        
        # المبيعات السابقة (نفس الفترة من الشهر الماضي)
        days_diff = (self.date_range['end'] - self.date_range['start']).days
        prev_start = self.date_range['start'] - timedelta(days=30)
        prev_end = prev_start + timedelta(days=days_diff)
        
        previous_sales = Invoice.objects.filter(
            date__range=[prev_start, prev_end],
            is_approved=True, is_deleted=False
        )
        
        # الحسابات
        current_total = current_sales.aggregate(total=Sum('cached_total'))['total'] or 0
        previous_total = previous_sales.aggregate(total=Sum('cached_total'))['total'] or 0
        
        growth_rate = 0
        if previous_total > 0:
            growth_rate = ((current_total - previous_total) / previous_total) * 100
        
        current_count = current_sales.count()
        avg_invoice = current_total / current_count if current_count > 0 else 0
        
        return {
            'total_sales': float(current_total),
            'previous_sales': float(previous_total),
            'growth_rate': round(growth_rate, 2),
            'invoice_count': current_count,
            'avg_invoice_value': round(float(avg_invoice), 2),
            'daily_avg': round(float(current_total / days_diff), 2) if days_diff > 0 else 0
        }
    
    def get_inventory_kpis(self):
        """مؤشرات المخزون"""
        from inventory.models import Product, Stock
        
        products = Product.objects.filter(is_active=True)
        
        # قيمة المخزون الحالية (مجموع الكميات × تكلفة المنتج)
        inventory_value = Stock.objects.filter(
            product__is_active=True
        ).aggregate(
            total=Sum(F('quantity') * F('product__cost'))
        )['total'] or 0
        
        # إجمالي الكمية في المخزن
        total_stock = Stock.objects.filter(
            product__is_active=True
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # معدل دوران المخزون (تقريبي)
        turnover_ratio = 0
        
        # المنتجات قليلة المخزون والنافذة
        from django.db.models import Subquery, OuterRef, IntegerField
        from django.db.models.functions import Coalesce
        
        stock_subquery = Stock.objects.filter(
            product_id=OuterRef('pk')
        ).values('product_id').annotate(
            total_qty=Sum('quantity')
        ).values('total_qty')[:1]
        
        annotated_products = products.annotate(
            total_stock=Coalesce(Subquery(stock_subquery, output_field=IntegerField()), 0)
        )
        
        low_stock = annotated_products.filter(
            total_stock__lte=F('min_stock'),
            total_stock__gt=0
        ).count()
        
        # المنتجات النافذة
        out_of_stock = annotated_products.filter(
            total_stock__lte=0
        ).count()
        
        return {
            'inventory_value': round(float(inventory_value), 2),
            'turnover_ratio': round(turnover_ratio, 2),
            'low_stock_count': low_stock,
            'out_of_stock_count': out_of_stock,
            'total_products': products.count(),
            'avg_product_value': round(float(inventory_value / products.count()), 2) if products.count() > 0 else 0
        }
    
    def get_financial_kpis(self):
        """مؤشرات مالية"""
        from sales.models import Invoice
        
        # الإيرادات
        revenue = Invoice.objects.filter(
            date__range=[self.date_range['start'], self.date_range['end']],
            is_approved=True, is_deleted=False
        ).aggregate(total=Sum('cached_total'))['total'] or 0
        
        # التكاليف
        from purchases.models import PurchaseOrderItem
        costs = PurchaseOrderItem.objects.filter(
            order__date__range=[self.date_range['start'], self.date_range['end']],
            order__status__in=['confirmed', 'completed', 'partial']
        ).aggregate(total=Sum(F('quantity') * F('cost')))['total'] or 0
        
        # هامش الربح الإجمالي
        gross_profit = revenue - costs
        profit_margin = (gross_profit / revenue * 100) if revenue > 0 else 0
        
        # المستحقات (فواتير غير مدفوعة بالكامل)
        receivables = Invoice.objects.filter(
            is_approved=True, is_deleted=False,
            paid__lt=F('cached_total') - F('discount')
        ).aggregate(total=Sum(F('cached_total') - F('discount') - F('paid')))['total'] or 0
        
        # المدفوعات المستحقة
        payables = PurchaseOrderItem.objects.filter(
            order__status__in=['confirmed', 'partial']
        ).aggregate(total=Sum(F('quantity') * F('cost')))['total'] or 0
        
        return {
            'revenue': round(float(revenue), 2),
            'costs': round(float(costs), 2),
            'gross_profit': round(float(gross_profit), 2),
            'profit_margin': round(profit_margin, 2),
            'receivables': round(float(receivables), 2),
            'payables': round(float(payables), 2),
            'net_position': round(float(receivables - payables), 2)
        }
    
    def get_customer_kpis(self):
        """مؤشرات العملاء"""
        from sales.models import Invoice
        from partners.models import Customer
        
        # إجمالي العملاء (Customer ليس فيه is_active، نحسب الكل)
        total_customers = Customer.objects.count()
        
        # العملاء النشطين (الذين اشتروا في الفترة)
        active_customers = Invoice.objects.filter(
            date__range=[self.date_range['start'], self.date_range['end']],
            is_approved=True, is_deleted=False
        ).values('customer').distinct().count()
        
        # العملاء الجدد (بناءً على أول فاتورة لكل عميل)
        from django.db.models import Min as MinAgg
        new_customers = Invoice.objects.values('customer').annotate(
            first_invoice=MinAgg('date')
        ).filter(
            first_invoice__range=[self.date_range['start'], self.date_range['end']]
        ).count()
        
        # العملاء المتكررين
        repeat_customers = Invoice.objects.filter(
            date__range=[self.date_range['start'], self.date_range['end']],
            is_approved=True, is_deleted=False
        ).values('customer').annotate(
            count=Count('id')
        ).filter(count__gt=1).count()
        
        repeat_rate = (repeat_customers / active_customers * 100) if active_customers > 0 else 0
        
        # متوسط قيمة العميل
        customer_value = Invoice.objects.filter(
            date__range=[self.date_range['start'], self.date_range['end']],
            is_approved=True, is_deleted=False
        ).values('customer').annotate(
            total=Sum('cached_total')
        ).aggregate(avg=Avg('total'))['avg'] or 0
        
        return {
            'total_customers': total_customers,
            'active_customers': active_customers,
            'new_customers': new_customers,
            'repeat_customers': repeat_customers,
            'repeat_rate': round(repeat_rate, 2),
            'avg_customer_value': round(float(customer_value), 2)
        }
    
    def get_operational_kpis(self):
        """مؤشرات تشغيلية"""
        from sales.models import Invoice
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # متوسط وقت معالجة الطلب
        approved_invoices = Invoice.objects.filter(
            date__range=[self.date_range['start'], self.date_range['end']],
            is_approved=True, is_deleted=False,
            approved_at__isnull=False
        )
        avg_processing_time = None
        if approved_invoices.exists():
            try:
                avg_processing_time = approved_invoices.annotate(
                    processing_time=F('approved_at') - F('date')
                ).aggregate(avg=Avg('processing_time'))['avg']
            except Exception:
                avg_processing_time = None
        
        # معدل الرفض (الفواتير المحذوفة)
        total_orders = Invoice.objects.filter(
            date__range=[self.date_range['start'], self.date_range['end']]
        ).count()
        
        deleted_orders = Invoice.objects.filter(
            date__range=[self.date_range['start'], self.date_range['end']],
            is_deleted=True
        ).count()
        
        rejection_rate = (deleted_orders / total_orders * 100) if total_orders > 0 else 0
        
        # إنتاجية الموظف (المبيعات لكل موظف)
        active_employees = User.objects.filter(is_active=True).count()
        total_sales = Invoice.objects.filter(
            date__range=[self.date_range['start'], self.date_range['end']],
            is_approved=True, is_deleted=False
        ).aggregate(total=Sum('cached_total'))['total'] or 0
        
        employee_productivity = total_sales / active_employees if active_employees > 0 else 0
        
        processing_hours = 0
        if avg_processing_time:
            try:
                processing_hours = round(avg_processing_time.total_seconds() / 3600, 2)
            except (AttributeError, TypeError):
                processing_hours = 0
        return {
            'avg_processing_hours': processing_hours,
            'rejection_rate': round(rejection_rate, 2),
            'employee_productivity': round(float(employee_productivity), 2),
            'active_employees': active_employees
        }
    
    def get_comparison_data(self):
        """بيانات المقارنة مع الفترة السابقة"""
        current_kpis = self.get_all_kpis()
        
        # تغيير النطاق الزمني للفترة السابقة
        days_diff = (self.date_range['end'] - self.date_range['start']).days
        prev_start = self.date_range['start'] - timedelta(days=30)
        prev_end = prev_start + timedelta(days=days_diff)
        
        prev_calculator = EnhancedKPICalculator(
            user=self.user,
            branch=self.branch,
            date_range={'start': prev_start, 'end': prev_end}
        )
        
        previous_kpis = prev_calculator.get_all_kpis()
        
        # حساب التغييرات
        comparison = {}
        for category in current_kpis:
            comparison[category] = {}
            for key, current_value in current_kpis[category].items():
                previous_value = previous_kpis[category].get(key, 0)
                
                if isinstance(current_value, (int, float)):
                    change = current_value - previous_value
                    change_percent = (change / previous_value * 100) if previous_value > 0 else 0
                    
                    comparison[category][key] = {
                        'current': current_value,
                        'previous': previous_value,
                        'change': round(change, 2),
                        'change_percent': round(change_percent, 2)
                    }
        
        return comparison


# ===== Celery Tasks =====
import logging
logger = logging.getLogger(__name__)

try:
    from celery import shared_task
    from django.core.cache import cache
    
    @shared_task(name='dashboard.enhanced_kpis.update_kpis')
    def update_kpis():
        """تحديث مؤشرات الأداء - مهمة Celery مجدولة"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # تحديث KPIs لجميع المستخدمين النشطين
            active_users = User.objects.filter(is_active=True, is_staff=True)[:50]
            
            for user in active_users:
                calculator = EnhancedKPICalculator(user=user)
                kpis = calculator.get_all_kpis()
                
                # تخزين في الكاش لمدة ساعة
                cache_key = f"kpis_{user.id}"
                cache.set(cache_key, kpis, 3600)
            
            logger.info(f"تم تحديث KPIs لـ {active_users.count()} مستخدم")
            return {'status': 'success', 'users_updated': active_users.count()}
            
        except Exception as e:
            logger.error(f"خطأ في تحديث KPIs: {str(e)}")
            return {'status': 'error', 'message': str(e)}
            
except ImportError:
    pass
