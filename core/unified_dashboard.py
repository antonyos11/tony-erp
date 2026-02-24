"""
لوحة التحكم الموحدة للشركة + المصنع + المعارض
Unified Enterprise Dashboard

يوفر هذا النظام:
1. ملخص مبيعات كل معرض
2. حالة الإنتاج في المصنع
3. مستويات المخزون في كل موقع
4. أداء مقارن بين المعارض
5. تنبيهات موحدة
"""

from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from django.db.models import Sum, F, Q, Avg, Count, Min, Max, DecimalField, ExpressionWrapper
from django.utils import timezone
from django.conf import settings


@dataclass
class BranchPerformance:
    """أداء الفرع"""
    branch_id: int
    branch_name: str
    branch_type: str
    sales_today: Decimal = Decimal('0')
    sales_this_week: Decimal = Decimal('0')
    sales_this_month: Decimal = Decimal('0')
    sales_target: Decimal = Decimal('0')
    target_achievement: float = 0.0
    transactions_count: int = 0
    avg_transaction_value: Decimal = Decimal('0')
    stock_value: Decimal = Decimal('0')
    low_stock_items: int = 0
    pending_transfers_in: int = 0
    pending_transfers_out: int = 0


@dataclass
class ProductionStatus:
    """حالة الإنتاج"""
    orders_in_progress: int = 0
    orders_pending: int = 0
    orders_completed_today: int = 0
    orders_completed_this_week: int = 0
    total_produced_today: Decimal = Decimal('0')
    total_produced_this_week: Decimal = Decimal('0')
    capacity_utilization: float = 0.0
    overdue_orders: int = 0
    materials_shortage_orders: int = 0
    quality_issues: int = 0


@dataclass
class InventoryOverview:
    """نظرة عامة على المخزون"""
    total_stock_value: Decimal = Decimal('0')
    total_products: int = 0
    low_stock_items: int = 0
    out_of_stock_items: int = 0
    overstocked_items: int = 0
    pending_transfers: int = 0
    in_transit_value: Decimal = Decimal('0')


@dataclass
class AlertItem:
    """عنصر تنبيه"""
    id: str
    type: str
    severity: str  # danger, warning, info, success
    title: str
    message: str
    link: str = ''
    timestamp: datetime = None
    data: Dict = field(default_factory=dict)


class UnifiedDashboardService:
    """خدمة لوحة التحكم الموحدة"""
    
    def __init__(self):
        from branches.models import Branch, BranchTransfer
        from inventory.models import Product, Stock, Location
        from production.models import ProductionOrder, ProductionWorkCenter
        from sales.models import Invoice, InvoiceItem
        from purchases.models import PurchaseOrder
        
        self.Branch = Branch
        self.BranchTransfer = BranchTransfer
        self.Product = Product
        self.Stock = Stock
        self.Location = Location
        self.ProductionOrder = ProductionOrder
        self.ProductionWorkCenter = ProductionWorkCenter
        self.Invoice = Invoice
        self.InvoiceItem = InvoiceItem
        self.PurchaseOrder = PurchaseOrder
    
    def get_full_dashboard(self) -> Dict:
        """
        الحصول على لوحة التحكم الكاملة
        """
        return {
            'company_overview': self.get_company_overview(),
            'branches_performance': self.get_branches_performance(),
            'production_status': self.get_production_status(),
            'inventory_overview': self.get_inventory_overview(),
            'alerts': self.get_all_alerts(),
            'quick_stats': self.get_quick_stats(),
            'charts_data': self.get_charts_data(),
            'timestamp': timezone.now().isoformat()
        }
    
    def get_company_overview(self) -> Dict:
        """
        نظرة عامة على الشركة
        """
        today = timezone.now().date()
        this_week_start = today - timedelta(days=today.weekday())
        this_month_start = today.replace(day=1)
        
        # المبيعات
        sales_today = self._get_total_sales(today, today)
        sales_week = self._get_total_sales(this_week_start, today)
        sales_month = self._get_total_sales(this_month_start, today)
        
        # الإنتاج
        produced_today = self._get_total_produced(today, today)
        produced_week = self._get_total_produced(this_week_start, today)
        
        # المخزون
        total_stock_value = self._get_total_stock_value()
        
        # الموظفين النشطين
        from branches.models import BranchStaff
        active_staff = BranchStaff.objects.filter(is_active=True).count()
        
        return {
            'sales': {
                'today': float(sales_today),
                'this_week': float(sales_week),
                'this_month': float(sales_month)
            },
            'production': {
                'today': float(produced_today),
                'this_week': float(produced_week)
            },
            'inventory': {
                'total_value': float(total_stock_value)
            },
            'workforce': {
                'active_staff': active_staff
            }
        }
    
    def get_branches_performance(self, limit: int = 10) -> List[Dict]:
        """
        أداء الفروع/المعارض
        """
        branches = self.Branch.objects.filter(
            is_active=True,
            branch_type__in=['showroom', 'store', 'branch']
        )[:limit]
        
        today = timezone.now().date()
        this_week_start = today - timedelta(days=today.weekday())
        this_month_start = today.replace(day=1)
        
        performance_list = []
        
        for branch in branches:
            # المبيعات
            sales_today = self._get_branch_sales(branch, today, today)
            sales_week = self._get_branch_sales(branch, this_week_start, today)
            sales_month = self._get_branch_sales(branch, this_month_start, today)
            
            # عدد المعاملات
            transactions = self._get_branch_transactions_count(branch, today, today)
            
            # متوسط قيمة المعاملة
            avg_value = sales_today / transactions if transactions > 0 else Decimal('0')
            
            # قيمة المخزون
            stock_value = self._get_branch_stock_value(branch.id)
            
            # المنتجات منخفضة المخزون
            low_stock = self._get_branch_low_stock_count(branch.id)
            
            # التحويلات المعلقة
            pending_in = self.BranchTransfer.objects.filter(
                to_branch=branch,
                status__in=['pending', 'approved', 'in_transit']
            ).count()
            
            pending_out = self.BranchTransfer.objects.filter(
                from_branch=branch,
                status__in=['pending', 'approved']
            ).count()
            
            # نسبة تحقيق الهدف (افتراضي)
            target = Decimal('10000')  # يمكن جعله قابل للتكوين
            achievement = float(sales_month / target * 100) if target > 0 else 0
            
            performance_list.append({
                'branch_id': branch.id,
                'branch_name': branch.name,
                'branch_code': branch.code,
                'branch_type': branch.get_branch_type_display(),
                'sales_today': float(sales_today),
                'sales_this_week': float(sales_week),
                'sales_this_month': float(sales_month),
                'target_achievement': min(achievement, 100),
                'transactions_count': transactions,
                'avg_transaction_value': float(avg_value),
                'stock_value': float(stock_value),
                'low_stock_items': low_stock,
                'pending_transfers_in': pending_in,
                'pending_transfers_out': pending_out
            })
        
        # ترتيب حسب المبيعات
        performance_list.sort(key=lambda x: x['sales_this_month'], reverse=True)
        
        return performance_list
    
    def get_production_status(self) -> Dict:
        """
        حالة الإنتاج في المصنع
        """
        today = timezone.now().date()
        this_week_start = today - timedelta(days=today.weekday())
        
        # أوامر الإنتاج
        in_progress = self.ProductionOrder.objects.filter(status='in_progress').count()
        pending = self.ProductionOrder.objects.filter(status__in=['draft', 'pending', 'approved']).count()
        
        completed_today = self.ProductionOrder.objects.filter(
            status='completed',
            actual_end_date=today
        ).count()
        
        completed_week = self.ProductionOrder.objects.filter(
            status='completed',
            actual_end_date__gte=this_week_start,
            actual_end_date__lte=today
        ).count()
        
        # الكمية المنتجة
        produced_today = self.ProductionOrder.objects.filter(
            status='completed',
            actual_end_date=today
        ).aggregate(total=Sum('actual_quantity'))['total'] or Decimal('0')
        
        produced_week = self.ProductionOrder.objects.filter(
            status='completed',
            actual_end_date__gte=this_week_start,
            actual_end_date__lte=today
        ).aggregate(total=Sum('actual_quantity'))['total'] or Decimal('0')
        
        # الأوامر المتأخرة
        overdue = self.ProductionOrder.objects.filter(
            status__in=['pending', 'in_progress', 'approved'],
            scheduled_end_date__lt=today
        ).count()
        
        # استخدام الطاقة
        utilization = self._calculate_capacity_utilization()
        
        # مشاكل الجودة (تحتاج ربط مع نظام الجودة)
        quality_issues = 0
        
        return {
            'orders_in_progress': in_progress,
            'orders_pending': pending,
            'orders_completed_today': completed_today,
            'orders_completed_this_week': completed_week,
            'total_produced_today': float(produced_today),
            'total_produced_this_week': float(produced_week),
            'capacity_utilization': utilization,
            'overdue_orders': overdue,
            'quality_issues': quality_issues
        }
    
    def get_inventory_overview(self) -> Dict:
        """
        نظرة عامة على المخزون
        """
        # إجمالي قيمة المخزون
        total_value = self.Stock.objects.aggregate(
            total=Sum(F('quantity') * F('product__cost'))
        )['total'] or Decimal('0')
        
        # عدد المنتجات
        total_products = self.Product.objects.filter(is_active=True).count() if hasattr(self.Product, 'is_active') else self.Product.objects.count()
        
        # المنتجات منخفضة المخزون
        low_stock = self.Stock.objects.filter(
            quantity__gt=0,
            quantity__lte=F('product__min_stock')
        ).values('product').distinct().count()
        
        # المنتجات نفدت
        out_of_stock = self.Stock.objects.filter(
            quantity__lte=0
        ).values('product').distinct().count()
        
        # التحويلات المعلقة
        pending_transfers = self.BranchTransfer.objects.filter(
            status__in=['pending', 'approved', 'in_transit']
        ).count()
        
        # قيمة البضائع في الطريق
        from branches.models import BranchTransferItem
        in_transit = BranchTransferItem.objects.filter(
            transfer__status='in_transit'
        ).aggregate(
            total=Sum(F('quantity') * F('unit_cost'))
        )['total'] or Decimal('0')
        
        return {
            'total_stock_value': float(total_value),
            'total_products': total_products,
            'low_stock_items': low_stock,
            'out_of_stock_items': out_of_stock,
            'pending_transfers': pending_transfers,
            'in_transit_value': float(in_transit)
        }
    
    def get_all_alerts(self, max_alerts: int = 20) -> List[Dict]:
        """
        جمع جميع التنبيهات
        """
        alerts = []
        today = timezone.now().date()
        
        # 1. تنبيهات الإنتاج
        overdue_orders = self.ProductionOrder.objects.filter(
            status__in=['pending', 'in_progress'],
            scheduled_end_date__lt=today
        ).count()
        
        if overdue_orders > 0:
            alerts.append({
                'id': 'prod_overdue',
                'type': 'production',
                'severity': 'danger',
                'title': 'أوامر إنتاج متأخرة',
                'message': f'{overdue_orders} أمر إنتاج تجاوز موعده المحدد',
                'link': '/production/orders/?status=overdue',
                'count': overdue_orders
            })
        
        # 2. تنبيهات المخزون
        low_stock_count = self.Stock.objects.filter(
            quantity__gt=0,
            quantity__lte=F('product__min_stock')
        ).count()
        
        if low_stock_count > 0:
            alerts.append({
                'id': 'inv_low_stock',
                'type': 'inventory',
                'severity': 'warning',
                'title': 'منتجات منخفضة المخزون',
                'message': f'{low_stock_count} منتج بحاجة لإعادة طلب',
                'link': '/inventory/low-stock/',
                'count': low_stock_count
            })
        
        out_of_stock = self.Stock.objects.filter(quantity__lte=0).count()
        if out_of_stock > 0:
            alerts.append({
                'id': 'inv_out_of_stock',
                'type': 'inventory',
                'severity': 'danger',
                'title': 'منتجات نفدت من المخزون',
                'message': f'{out_of_stock} منتج غير متوفر',
                'link': '/inventory/out-of-stock/',
                'count': out_of_stock
            })
        
        # 3. تنبيهات التحويلات
        pending_transfers = self.BranchTransfer.objects.filter(
            status='pending'
        ).count()
        
        if pending_transfers > 0:
            alerts.append({
                'id': 'transfer_pending',
                'type': 'transfer',
                'severity': 'info',
                'title': 'تحويلات تحتاج موافقة',
                'message': f'{pending_transfers} تحويل بانتظار الموافقة',
                'link': '/branches/transfers/?status=pending',
                'count': pending_transfers
            })
        
        # 4. تنبيهات المشتريات
        try:
            pending_purchases = self.PurchaseOrder.objects.filter(
                status='pending'
            ).count()
            
            if pending_purchases > 0:
                alerts.append({
                    'id': 'purchase_pending',
                    'type': 'purchase',
                    'severity': 'info',
                    'title': 'طلبات شراء معلقة',
                    'message': f'{pending_purchases} طلب شراء بانتظار الموافقة',
                    'link': '/purchases/orders/?status=pending',
                    'count': pending_purchases
                })
        except:
            pass
        
        # 5. تنبيهات المعارض بدون مبيعات اليوم
        showrooms_no_sales = []
        for branch in self.Branch.objects.filter(
            is_active=True,
            branch_type__in=['showroom', 'store']
        ):
            sales = self._get_branch_sales(branch, today, today)
            if sales == 0:
                showrooms_no_sales.append(branch.name)
        
        if showrooms_no_sales:
            alerts.append({
                'id': 'showroom_no_sales',
                'type': 'sales',
                'severity': 'warning',
                'title': 'معارض بدون مبيعات اليوم',
                'message': f'{len(showrooms_no_sales)} معرض لم يسجل مبيعات',
                'link': '/sales/daily-report/',
                'count': len(showrooms_no_sales),
                'details': showrooms_no_sales[:5]
            })
        
        return alerts[:max_alerts]
    
    def get_quick_stats(self) -> Dict:
        """
        إحصائيات سريعة
        """
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # مقارنة المبيعات
        sales_today = self._get_total_sales(today, today)
        sales_yesterday = self._get_total_sales(yesterday, yesterday)
        
        sales_change = 0
        if sales_yesterday > 0:
            sales_change = float((sales_today - sales_yesterday) / sales_yesterday * 100)
        
        # عدد الطلبات
        orders_today = self.Invoice.objects.filter(
            date=today
        ).count()
        
        orders_yesterday = self.Invoice.objects.filter(
            date=yesterday
        ).count()
        
        orders_change = 0
        if orders_yesterday > 0:
            orders_change = float((orders_today - orders_yesterday) / orders_yesterday * 100)
        
        # الإنتاج
        production_today = self._get_total_produced(today, today)
        production_yesterday = self._get_total_produced(yesterday, yesterday)
        
        production_change = 0
        if production_yesterday > 0:
            production_change = float((production_today - production_yesterday) / production_yesterday * 100)
        
        return {
            'sales': {
                'value': float(sales_today),
                'change': sales_change,
                'trend': 'up' if sales_change > 0 else ('down' if sales_change < 0 else 'same')
            },
            'orders': {
                'value': orders_today,
                'change': orders_change,
                'trend': 'up' if orders_change > 0 else ('down' if orders_change < 0 else 'same')
            },
            'production': {
                'value': float(production_today),
                'change': production_change,
                'trend': 'up' if production_change > 0 else ('down' if production_change < 0 else 'same')
            }
        }
    
    def get_charts_data(self) -> Dict:
        """
        بيانات الرسوم البيانية
        """
        today = timezone.now().date()
        
        # بيانات المبيعات آخر 7 أيام
        sales_chart = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            amount = self._get_total_sales(day, day)
            sales_chart.append({
                'date': day.isoformat(),
                'day_name': day.strftime('%A'),
                'value': float(amount)
            })
        
        # بيانات الإنتاج آخر 7 أيام
        production_chart = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            amount = self._get_total_produced(day, day)
            production_chart.append({
                'date': day.isoformat(),
                'day_name': day.strftime('%A'),
                'value': float(amount)
            })
        
        # توزيع المخزون حسب الفروع
        inventory_by_branch = []
        for branch in self.Branch.objects.filter(
            is_active=True,
            location__isnull=False
        )[:10]:
            value = self._get_branch_stock_value(branch.id)
            inventory_by_branch.append({
                'branch_name': branch.name,
                'value': float(value)
            })
        
        # توزيع المبيعات حسب المعارض
        sales_by_branch = []
        this_month_start = today.replace(day=1)
        for branch in self.Branch.objects.filter(
            is_active=True,
            branch_type__in=['showroom', 'store']
        )[:10]:
            amount = self._get_branch_sales(branch, this_month_start, today)
            sales_by_branch.append({
                'branch_name': branch.name,
                'value': float(amount)
            })
        
        return {
            'sales_trend': sales_chart,
            'production_trend': production_chart,
            'inventory_by_branch': inventory_by_branch,
            'sales_by_branch': sales_by_branch
        }
    
    # ==================== Helper Methods ====================
    
    def _get_total_sales(self, from_date: date, to_date: date) -> Decimal:
        """إجمالي المبيعات (صافي بعد الخصم)"""
        amount_expr = ExpressionWrapper(F('quantity') * F('price'), output_field=DecimalField(max_digits=18, decimal_places=2))
        items_qs = self.InvoiceItem.objects.filter(
            invoice__date__gte=from_date,
            invoice__date__lte=to_date
        )
        gross = items_qs.aggregate(total=Sum(amount_expr))['total'] or Decimal('0')
        discounts = self.Invoice.objects.filter(
            date__gte=from_date,
            date__lte=to_date
        ).aggregate(total=Sum('discount'))['total'] or Decimal('0')
        net = gross - discounts
        return net if net > 0 else Decimal('0')
    
    def _get_branch_sales(self, branch, from_date: date, to_date: date) -> Decimal:
        """مبيعات فرع معين (يتم الربط عبر الموقع المخزني للفرع)"""
        amount_expr = ExpressionWrapper(F('quantity') * F('price'), output_field=DecimalField(max_digits=18, decimal_places=2))
        filters = Q(invoice__date__gte=from_date, invoice__date__lte=to_date)
        # حاول مطابقة المعرض عبر موقع المخزون المرتبط بالفرع
        if getattr(branch, 'location_id', None):
            filters &= Q(invoice__showroom__location_id=branch.location_id)
        else:
            # لا يوجد موقع، لا يمكن نسب مبيعات للفرع
            return Decimal('0')
        
        items_qs = self.InvoiceItem.objects.filter(filters)
        gross = items_qs.aggregate(total=Sum(amount_expr))['total'] or Decimal('0')
        discounts = self.Invoice.objects.filter(
            date__gte=from_date,
            date__lte=to_date,
            showroom__location_id=branch.location_id
        ).aggregate(total=Sum('discount'))['total'] or Decimal('0')
        net = gross - discounts
        return net if net > 0 else Decimal('0')
    
    def _get_branch_transactions_count(self, branch, from_date: date, to_date: date) -> int:
        """عدد معاملات فرع"""
        if not getattr(branch, 'location_id', None):
            return 0
        return self.Invoice.objects.filter(
            showroom__location_id=branch.location_id,
            date__gte=from_date,
            date__lte=to_date
        ).count()
    
    def _get_total_produced(self, from_date: date, to_date: date) -> Decimal:
        """إجمالي الإنتاج"""
        result = self.ProductionOrder.objects.filter(
            status='completed',
            actual_end_date__gte=from_date,
            actual_end_date__lte=to_date
        ).aggregate(total=Sum('actual_quantity'))
        return result['total'] or Decimal('0')
    
    def _get_total_stock_value(self) -> Decimal:
        """إجمالي قيمة المخزون"""
        result = self.Stock.objects.aggregate(
            total=Sum(F('quantity') * F('product__cost'))
        )
        return result['total'] or Decimal('0')
    
    def _get_branch_stock_value(self, branch_id: int) -> Decimal:
        """قيمة مخزون فرع"""
        branch = self.Branch.objects.get(id=branch_id)
        if not branch.location:
            return Decimal('0')
        
        result = self.Stock.objects.filter(
            location=branch.location
        ).aggregate(
            total=Sum(F('quantity') * F('product__cost'))
        )
        return result['total'] or Decimal('0')
    
    def _get_branch_low_stock_count(self, branch_id: int) -> int:
        """عدد المنتجات منخفضة المخزون في فرع"""
        branch = self.Branch.objects.get(id=branch_id)
        if not branch.location:
            return 0
        
        return self.Stock.objects.filter(
            location=branch.location,
            quantity__gt=0,
            quantity__lte=F('product__min_stock')
        ).count()
    
    def _calculate_capacity_utilization(self) -> float:
        """حساب نسبة استخدام الطاقة الإنتاجية"""
        today = timezone.now().date()
        
        work_centers = self.ProductionWorkCenter.objects.filter(is_active=True)
        if not work_centers.exists():
            return 0.0
        
        total_capacity = Decimal('0')
        total_used = Decimal('0')
        
        for wc in work_centers:
            total_capacity += wc.working_hours_per_day
            
            # الساعات المستخدمة اليوم
            used = self.ProductionOrder.objects.filter(
                work_center=wc,
                status='in_progress'
            ).aggregate(total=Sum('estimated_time'))['total'] or Decimal('0')
            
            total_used += used
        
        if total_capacity == 0:
            return 0.0
        
        return float(min(total_used / total_capacity * 100, 100))
