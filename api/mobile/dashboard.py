"""
Mobile Dashboard API
API لوحة التحكم للموبايل

توفر ملخص سريع وخفيف للبيانات الأساسية
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class MobileDashboardViewSet(viewsets.ViewSet):
    """لوحة التحكم للموبايل"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def summary(self, request) -> Response:
        """
        ملخص سريع
        
        GET /api/mobile/dashboard/summary/
        """
        user = request.user
        
        # تحديد الفترة (آخر 7 أيام افتراضياً)
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now().date() - timedelta(days=days)
        
        summary = {
            'sales': self._get_sales_summary(start_date, user),
            'inventory': self._get_inventory_summary(user),
            'production': self._get_production_summary(start_date, user),
            'alerts': self._get_alerts_summary(user),
            'period': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': timezone.now().date().isoformat()
            }
        }
        
        return Response(summary)
    
    @action(detail=False, methods=['get'])
    def quick_stats(self, request) -> Response:
        """
        إحصائيات سريعة (مضغوطة للغاية)
        
        GET /api/mobile/dashboard/quick_stats/
        """
        from sales.models import Invoice
        from inventory.models import Stock
        from production.models import ProductionOrder
        
        today = timezone.now().date()
        
        # مبيعات اليوم
        today_sales = Invoice.objects.filter(
            invoice_date=today
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        
        # المخزون المنخفض
        low_stock = Stock.objects.filter(
            quantity__lt=F('product__min_stock'),
            quantity__gt=0
        ).count()
        
        # الإنتاج النشط
        active_production = ProductionOrder.objects.filter(
            status__in=['confirmed', 'in_progress']
        ).count()
        
        return Response({
            'today_sales': float(today_sales['total'] or 0),
            'today_orders': today_sales['count'] or 0,
            'low_stock_items': low_stock,
            'active_production': active_production
        })
    
    def _get_sales_summary(self, start_date, user) -> dict:
        """ملخص المبيعات"""
        from sales.models import Invoice
        
        invoices = Invoice.objects.filter(invoice_date__gte=start_date)
        
        # تصفية حسب صلاحيات المستخدم
        if not user.is_superuser:
            # يمكن إضافة تصفية حسب الفرع أو المعرض
            pass
        
        data = invoices.aggregate(
            total_revenue=Sum('total_amount'),
            count=Count('id')
        )
        
        avg = (data['total_revenue'] / data['count']) if data['count'] > 0 else Decimal('0')
        
        return {
            'total_revenue': float(data['total_revenue'] or 0),
            'total_orders': data['count'] or 0,
            'avg_order_value': float(avg)
        }
    
    def _get_inventory_summary(self, user) -> dict:
        """ملخص المخزون"""
        from inventory.models import Stock
        
        # إجمالي المخزون
        total_value = Stock.objects.aggregate(
            value=Sum(F('quantity') * F('product__cost'))
        )['value'] or Decimal('0')
        
        # المنتجات المنخفضة
        low_stock = Stock.objects.filter(
            quantity__lt=F('product__min_stock'),
            quantity__gt=0
        ).count()
        
        # المنتجات الخارجة
        out_of_stock = Stock.objects.filter(quantity=0).count()
        
        return {
            'total_value': float(total_value),
            'low_stock_items': low_stock,
            'out_of_stock_items': out_of_stock
        }
    
    def _get_production_summary(self, start_date, user) -> dict:
        """ملخص الإنتاج"""
        from production.models import ProductionOrder
        
        orders = ProductionOrder.objects.filter(date__gte=start_date)
        
        active = orders.filter(status__in=['confirmed', 'in_progress']).count()
        completed = orders.filter(status='completed').count()
        
        total_produced = orders.filter(status='completed').aggregate(
            total=Sum('quantity_produced')
        )['total'] or 0
        
        return {
            'active_orders': active,
            'completed_orders': completed,
            'units_produced': total_produced
        }
    
    def _get_alerts_summary(self, user) -> dict:
        """ملخص التنبيهات"""
        from inventory.models import Stock
        from quality_control.models import QualityIssue
        
        # تنبيهات المخزون
        inventory_alerts = Stock.objects.filter(
            quantity__lt=F('product__min_stock'),
            quantity__gt=0
        ).count()
        
        # تنبيهات الجودة
        quality_alerts = QualityIssue.objects.filter(
            status__in=['open', 'investigating'],
            severity__in=['high', 'critical']
        ).count()
        
        return {
            'inventory': inventory_alerts,
            'quality': quality_alerts,
            'total': inventory_alerts + quality_alerts
        }
