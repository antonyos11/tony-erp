"""
Admin Dashboard Widgets for E-commerce
=======================================
Sales statistics, order management, and reports
Week 4 - Final Polish
"""

from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from django.contrib.admin import AdminSite

from ecommerce.models import (
    Order, OrderItem, OnlineProduct, ProductCategory,
    PaymentGateway, ProductReview
)

# Aliases for compatibility
Product = OnlineProduct
Category = ProductCategory
PaymentTransaction = PaymentGateway


class DashboardStats:
    """إحصائيات لوحة التحكم"""
    
    def __init__(self, date_from=None, date_to=None):
        self.date_from = date_from or (timezone.now() - timedelta(days=30))
        self.date_to = date_to or timezone.now()
    
    def get_overview(self):
        """إحصائيات عامة"""
        orders = Order.objects.filter(
            created_at__gte=self.date_from,
            created_at__lte=self.date_to
        )
        
        return {
            'total_orders': orders.count(),
            'total_revenue': orders.filter(
                payment_status='paid'
            ).aggregate(total=Sum('total'))['total'] or Decimal('0'),
            'average_order_value': orders.filter(
                payment_status='paid'
            ).aggregate(avg=Avg('total'))['avg'] or Decimal('0'),
            'pending_orders': orders.filter(status='pending').count(),
            'processing_orders': orders.filter(status='processing').count(),
            'shipped_orders': orders.filter(status='shipped').count(),
            'delivered_orders': orders.filter(status='delivered').count(),
            'cancelled_orders': orders.filter(status='cancelled').count(),
        }
    
    def get_today_stats(self):
        """إحصائيات اليوم"""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        today_orders = Order.objects.filter(
            created_at__date=today
        )
        yesterday_orders = Order.objects.filter(
            created_at__date=yesterday
        )
        
        today_revenue = today_orders.filter(
            payment_status='paid'
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        yesterday_revenue = yesterday_orders.filter(
            payment_status='paid'
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        # Calculate growth
        if yesterday_revenue > 0:
            revenue_growth = ((today_revenue - yesterday_revenue) / yesterday_revenue) * 100
        else:
            revenue_growth = 100 if today_revenue > 0 else 0
        
        return {
            'today_orders': today_orders.count(),
            'today_revenue': today_revenue,
            'yesterday_orders': yesterday_orders.count(),
            'yesterday_revenue': yesterday_revenue,
            'revenue_growth': round(revenue_growth, 1),
            'orders_growth': today_orders.count() - yesterday_orders.count(),
        }
    
    def get_sales_chart_data(self, period='daily'):
        """بيانات رسم المبيعات"""
        orders = Order.objects.filter(
            created_at__gte=self.date_from,
            created_at__lte=self.date_to,
            payment_status='paid'
        )
        
        if period == 'daily':
            data = orders.annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                revenue=Sum('total'),
                count=Count('id')
            ).order_by('date')
        elif period == 'weekly':
            data = orders.annotate(
                date=TruncWeek('created_at')
            ).values('date').annotate(
                revenue=Sum('total'),
                count=Count('id')
            ).order_by('date')
        else:  # monthly
            data = orders.annotate(
                date=TruncMonth('created_at')
            ).values('date').annotate(
                revenue=Sum('total'),
                count=Count('id')
            ).order_by('date')
        
        return list(data)
    
    def get_top_products(self, limit=10):
        """أكثر المنتجات مبيعاً"""
        return OrderItem.objects.filter(
            order__created_at__gte=self.date_from,
            order__created_at__lte=self.date_to,
            order__payment_status='paid'
        ).values(
            'product__id',
            'product__name',
            'product__slug'
        ).annotate(
            total_sold=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price'))
        ).order_by('-total_sold')[:limit]
    
    def get_top_categories(self, limit=5):
        """أكثر الفئات مبيعاً"""
        return OrderItem.objects.filter(
            order__created_at__gte=self.date_from,
            order__created_at__lte=self.date_to,
            order__payment_status='paid'
        ).values(
            'product__category__id',
            'product__category__name'
        ).annotate(
            total_sold=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price'))
        ).order_by('-total_revenue')[:limit]
    
    def get_payment_methods_breakdown(self):
        """توزيع طرق الدفع"""
        return Order.objects.filter(
            created_at__gte=self.date_from,
            created_at__lte=self.date_to,
            payment_status='paid'
        ).values('payment_method').annotate(
            count=Count('id'),
            total=Sum('total')
        ).order_by('-count')
    
    def get_governorates_breakdown(self):
        """توزيع المحافظات"""
        return Order.objects.filter(
            created_at__gte=self.date_from,
            created_at__lte=self.date_to
        ).values('shipping_governorate').annotate(
            count=Count('id'),
            total=Sum('total')
        ).order_by('-count')[:10]
    
    def get_order_status_breakdown(self):
        """توزيع حالات الطلبات"""
        return Order.objects.filter(
            created_at__gte=self.date_from,
            created_at__lte=self.date_to
        ).values('status').annotate(
            count=Count('id')
        ).order_by('-count')
    
    def get_low_stock_products(self, threshold=5):
        """المنتجات منخفضة المخزون"""
        return Product.objects.filter(
            is_active=True,
            stock__lte=F('low_stock_threshold')
        ).values(
            'id', 'name', 'slug', 'stock', 'low_stock_threshold'
        ).order_by('stock')[:20]
    
    def get_recent_orders(self, limit=10):
        """أحدث الطلبات"""
        return Order.objects.select_related(
            'user'
        ).prefetch_related(
            'items__product'
        ).order_by('-created_at')[:limit]
    
    def get_pending_actions(self):
        """الإجراءات المطلوبة"""
        return {
            'pending_orders': Order.objects.filter(status='pending').count(),
            'low_stock_products': Product.objects.filter(
                is_active=True,
                stock__lte=F('low_stock_threshold')
            ).count(),
            'pending_reviews': ProductReview.objects.filter(
                is_approved=False
            ).count() if hasattr(ProductReview, 'is_approved') else 0,
            'failed_payments': PaymentTransaction.objects.filter(
                status='failed',
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
        }


class SalesReport:
    """تقارير المبيعات"""
    
    def __init__(self, date_from, date_to):
        self.date_from = date_from
        self.date_to = date_to
    
    def generate_summary(self):
        """ملخص المبيعات"""
        orders = Order.objects.filter(
            created_at__gte=self.date_from,
            created_at__lte=self.date_to,
            payment_status='paid'
        )
        
        return {
            'period': f"{self.date_from.strftime('%Y-%m-%d')} - {self.date_to.strftime('%Y-%m-%d')}",
            'total_orders': orders.count(),
            'total_revenue': orders.aggregate(total=Sum('total'))['total'] or Decimal('0'),
            'total_vat': orders.aggregate(vat=Sum('tax'))['vat'] or Decimal('0'),
            'total_shipping': orders.aggregate(ship=Sum('shipping_cost'))['ship'] or Decimal('0'),
            'total_discounts': orders.aggregate(disc=Sum('discount'))['disc'] or Decimal('0'),
            'average_order_value': orders.aggregate(avg=Avg('total'))['avg'] or Decimal('0'),
        }
    
    def generate_daily_breakdown(self):
        """تفصيل يومي"""
        return Order.objects.filter(
            created_at__gte=self.date_from,
            created_at__lte=self.date_to,
            payment_status='paid'
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            orders=Count('id'),
            revenue=Sum('total'),
            vat=Sum('tax'),
            avg_order=Avg('total')
        ).order_by('date')
    
    def generate_product_sales(self):
        """مبيعات المنتجات"""
        return OrderItem.objects.filter(
            order__created_at__gte=self.date_from,
            order__created_at__lte=self.date_to,
            order__payment_status='paid'
        ).values(
            'product__id',
            'product__name',
            'product__sku' if hasattr(Product, 'sku') else 'product__id'
        ).annotate(
            quantity_sold=Sum('quantity'),
            revenue=Sum(F('quantity') * F('price')),
            avg_price=Avg('price')
        ).order_by('-revenue')
    
    def generate_customer_report(self):
        """تقرير العملاء"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        return Order.objects.filter(
            created_at__gte=self.date_from,
            created_at__lte=self.date_to,
            payment_status='paid'
        ).values(
            'user__id',
            'user__email',
            'user__first_name',
            'user__last_name'
        ).annotate(
            total_orders=Count('id'),
            total_spent=Sum('total'),
            avg_order=Avg('total')
        ).order_by('-total_spent')[:50]
    
    def export_csv(self):
        """تصدير CSV"""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'رقم الطلب', 'التاريخ', 'العميل', 'الإجمالي',
            'الضريبة', 'الشحن', 'الخصم', 'طريقة الدفع', 'الحالة'
        ])
        
        # Data
        orders = Order.objects.filter(
            created_at__gte=self.date_from,
            created_at__lte=self.date_to
        ).select_related('user').order_by('-created_at')
        
        for order in orders:
            writer.writerow([
                order.order_number,
                order.created_at.strftime('%Y-%m-%d %H:%M'),
                order.user.email if order.user else 'ضيف',
                order.total,
                getattr(order, 'tax', 0),
                getattr(order, 'shipping_cost', 0),
                getattr(order, 'discount', 0),
                order.payment_method,
                order.status
            ])
        
        return output.getvalue()


def get_dashboard_context():
    """Get full dashboard context for admin view"""
    stats = DashboardStats()
    
    return {
        'overview': stats.get_overview(),
        'today': stats.get_today_stats(),
        'sales_chart': stats.get_sales_chart_data('daily'),
        'top_products': list(stats.get_top_products(5)),
        'top_categories': list(stats.get_top_categories(5)),
        'payment_methods': list(stats.get_payment_methods_breakdown()),
        'order_statuses': list(stats.get_order_status_breakdown()),
        'low_stock': list(stats.get_low_stock_products(10)),
        'recent_orders': stats.get_recent_orders(5),
        'pending_actions': stats.get_pending_actions(),
    }
