"""
خدمة تحليلات المبيعات المتقدمة
Sales Analytics Service

يوفر هذا الملف تحليلات متقدمة للمبيعات تشمل:
- توقع المبيعات
- تحليل الأداء
- تقارير ذكية
"""

from django.db.models import Sum, Avg, Count, F, Q, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth, TruncWeek, TruncDate, ExtractMonth
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict
import statistics

from sales.models import Invoice, InvoiceItem, InvoicePayment, SalesOrder
from inventory.models import Product
from partners.models import Customer


class SalesAnalyticsService:
    """
    خدمة التحليلات المتقدمة للمبيعات
    """
    
    @staticmethod
    def get_sales_kpis(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        الحصول على مؤشرات الأداء الرئيسية للمبيعات
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        # الفواتير في الفترة
        invoices = Invoice.objects.filter(
            date__range=[start_date.date(), end_date.date()],
            is_deleted=False
        )
        
        # إجمالي المبيعات
        total_sales = invoices.aggregate(Sum('cached_total'))['cached_total__sum'] or Decimal('0')
        
        # عدد الفواتير
        invoice_count = invoices.count()
        
        # متوسط قيمة الفاتورة
        avg_invoice = (total_sales / invoice_count) if invoice_count > 0 else Decimal('0')
        
        # المدفوعات
        payments = InvoicePayment.objects.filter(
            payment_date__range=[start_date.date(), end_date.date()]
        )
        total_collected = payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        # نسبة التحصيل
        collection_rate = (total_collected / total_sales * 100) if total_sales > 0 else Decimal('0')
        
        # أفضل المنتجات
        top_products = SalesAnalyticsService._get_top_products(start_date, end_date)
        
        # أفضل العملاء
        top_customers = SalesAnalyticsService._get_top_customers(start_date, end_date)
        
        # اتجاهات المبيعات
        trends = SalesAnalyticsService._get_sales_trends(start_date, end_date)
        
        # مقارنة بالفترة السابقة
        comparison = SalesAnalyticsService._compare_with_previous_period(
            start_date, end_date, total_sales
        )
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
            },
            'summary': {
                'total_sales': float(total_sales),
                'invoice_count': invoice_count,
                'avg_invoice_value': float(avg_invoice),
                'total_collected': float(total_collected),
                'collection_rate': float(collection_rate),
                'outstanding': float(total_sales - total_collected),
            },
            'top_products': top_products,
            'top_customers': top_customers,
            'trends': trends,
            'comparison': comparison,
        }
    
    @staticmethod
    def _get_top_products(
        start_date: datetime,
        end_date: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        الحصول على أفضل المنتجات
        """
        items = InvoiceItem.objects.filter(
            invoice__date__range=[start_date.date(), end_date.date()],
            invoice__is_deleted=False
        ).values(
            'product__id',
            'product__name',
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('unit_price')),
            order_count=Count('invoice', distinct=True),
        ).order_by('-total_revenue')[:limit]
        
        return list(items)
    
    @staticmethod
    def _get_top_customers(
        start_date: datetime,
        end_date: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        الحصول على أفضل العملاء
        """
        customers = Invoice.objects.filter(
            date__range=[start_date.date(), end_date.date()],
            is_deleted=False
        ).values(
            'customer__id',
            'customer__name',
        ).annotate(
            total_purchases=Sum('cached_total'),
            invoice_count=Count('id'),
            avg_purchase=Avg('cached_total'),
        ).order_by('-total_purchases')[:limit]
        
        return list(customers)
    
    @staticmethod
    def _get_sales_trends(
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, List]:
        """
        الحصول على اتجاهات المبيعات
        """
        invoices = Invoice.objects.filter(
            date__range=[start_date.date(), end_date.date()],
            is_deleted=False
        )
        
        # اتجاه يومي
        daily_trend = invoices.annotate(
            day=TruncDate('date')
        ).values('day').annotate(
            total=Sum('cached_total'),
            count=Count('id'),
        ).order_by('day')
        
        # اتجاه أسبوعي
        weekly_trend = invoices.annotate(
            week=TruncWeek('date')
        ).values('week').annotate(
            total=Sum('cached_total'),
            count=Count('id'),
        ).order_by('week')
        
        return {
            'daily': list(daily_trend),
            'weekly': list(weekly_trend),
        }
    
    @staticmethod
    def _compare_with_previous_period(
        start_date: datetime,
        end_date: datetime,
        current_sales: Decimal
    ) -> Dict[str, Any]:
        """
        مقارنة بالفترة السابقة
        """
        period_days = (end_date - start_date).days
        prev_end = start_date
        prev_start = prev_end - timedelta(days=period_days)
        
        prev_invoices = Invoice.objects.filter(
            date__range=[prev_start.date(), prev_end.date()],
            is_deleted=False
        )
        
        prev_sales = prev_invoices.aggregate(Sum('cached_total'))['cached_total__sum'] or Decimal('0')
        
        if prev_sales > 0:
            change = current_sales - prev_sales
            change_pct = (change / prev_sales * 100)
        else:
            change = current_sales
            change_pct = Decimal('100') if current_sales > 0 else Decimal('0')
        
        return {
            'previous_period': {
                'start': prev_start.isoformat(),
                'end': prev_end.isoformat(),
                'total_sales': float(prev_sales),
            },
            'change': float(change),
            'change_percentage': float(change_pct),
            'trend': 'up' if change > 0 else ('down' if change < 0 else 'stable'),
        }
    
    @staticmethod
    def predict_sales(
        months_ahead: int = 3
    ) -> Dict[str, Any]:
        """
        توقع المبيعات باستخدام Moving Average
        """
        # جمع بيانات المبيعات الشهرية للسنة الماضية
        one_year_ago = timezone.now() - timedelta(days=365)
        
        monthly_sales = Invoice.objects.filter(
            date__gte=one_year_ago.date(),
            is_deleted=False
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('cached_total')
        ).order_by('month')
        
        sales_data = [float(m['total']) for m in monthly_sales]
        
        if len(sales_data) < 3:
            return {
                'error': 'بيانات تاريخية غير كافية',
                'min_required': 3,
                'available': len(sales_data),
            }
        
        # حساب Moving Average
        window = min(4, len(sales_data))
        ma = statistics.mean(sales_data[-window:])
        
        # حساب الانحراف المعياري
        std_dev = statistics.stdev(sales_data) if len(sales_data) > 1 else 0
        
        # حساب معامل النمو
        if len(sales_data) >= 6:
            first_half = statistics.mean(sales_data[:len(sales_data)//2])
            second_half = statistics.mean(sales_data[len(sales_data)//2:])
            growth_rate = (second_half - first_half) / first_half if first_half > 0 else 0
        else:
            growth_rate = 0
        
        # توقعات الشهور القادمة
        predictions = []
        current_prediction = ma
        
        for i in range(months_ahead):
            # تطبيق معامل النمو
            current_prediction = current_prediction * (1 + growth_rate / 12)
            
            prediction = {
                'month': i + 1,
                'predicted_sales': round(current_prediction, 2),
                'lower_bound': round(max(0, current_prediction - 1.96 * std_dev), 2),
                'upper_bound': round(current_prediction + 1.96 * std_dev, 2),
                'confidence': 0.95,
            }
            predictions.append(prediction)
        
        return {
            'historical_months': len(sales_data),
            'moving_average': round(ma, 2),
            'standard_deviation': round(std_dev, 2),
            'growth_rate': round(growth_rate * 100, 2),
            'predictions': predictions,
        }
    
    @staticmethod
    def get_product_performance(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        تحليل أداء المنتجات
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        products = InvoiceItem.objects.filter(
            invoice__date__range=[start_date.date(), end_date.date()],
            invoice__is_deleted=False
        ).values(
            'product__id',
            'product__name',
            'product__cost_price',
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('unit_price')),
            total_cost=Sum(F('quantity') * F('product__cost_price')),
            order_count=Count('invoice', distinct=True),
        )
        
        result = []
        for p in products:
            revenue = p['total_revenue'] or Decimal('0')
            cost = p['total_cost'] or Decimal('0')
            profit = revenue - cost
            margin = (profit / revenue * 100) if revenue > 0 else Decimal('0')
            
            result.append({
                'product_id': p['product__id'],
                'product_name': p['product__name'],
                'total_quantity': p['total_quantity'],
                'total_revenue': float(revenue),
                'total_cost': float(cost),
                'profit': float(profit),
                'profit_margin': float(margin),
                'order_count': p['order_count'],
            })
        
        return sorted(result, key=lambda x: x['profit'], reverse=True)
    
    @staticmethod
    def get_sales_team_performance(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        تحليل أداء فريق المبيعات
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        performance = Invoice.objects.filter(
            date__range=[start_date.date(), end_date.date()],
            is_deleted=False,
            created_by__isnull=False
        ).values(
            'created_by__id',
            'created_by__first_name',
            'created_by__last_name',
        ).annotate(
            total_sales=Sum('cached_total'),
            invoice_count=Count('id'),
            avg_sale=Avg('cached_total'),
            customer_count=Count('customer', distinct=True),
        ).order_by('-total_sales')
        
        return list(performance)
    
    @staticmethod
    def get_collection_analysis(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        تحليل التحصيل
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        invoices = Invoice.objects.filter(
            date__range=[start_date.date(), end_date.date()],
            is_deleted=False
        )
        
        total_invoiced = invoices.aggregate(Sum('cached_total'))['cached_total__sum'] or Decimal('0')
        
        # تحليل حسب حالة السداد - باستخدام paid و cached_total
        paid = invoices.filter(paid__gte=F('cached_total') - F('discount')).aggregate(Sum('cached_total'))['cached_total__sum'] or Decimal('0')
        partial = invoices.filter(paid__gt=0, paid__lt=F('cached_total') - F('discount')).aggregate(Sum('cached_total'))['cached_total__sum'] or Decimal('0')
        unpaid = invoices.filter(paid=0).aggregate(Sum('cached_total'))['cached_total__sum'] or Decimal('0')
        
        # تحليل التأخير
        overdue = invoices.filter(
            due_date__lt=timezone.now().date(),
            paid__lt=F('cached_total') - F('discount')
        ).aggregate(
            total=Sum('cached_total'),
            count=Count('id'),
        )
        
        # متوسط أيام التحصيل
        payments = InvoicePayment.objects.filter(
            invoice__date__range=[start_date.date(), end_date.date()]
        )
        
        collection_days = []
        for payment in payments:
            if payment.invoice.date:
                days = (payment.payment_date - payment.invoice.date).days
                if days >= 0:
                    collection_days.append(days)
        
        avg_collection_days = statistics.mean(collection_days) if collection_days else 0
        
        return {
            'total_invoiced': float(total_invoiced),
            'by_status': {
                'paid': float(paid),
                'partial': float(partial),
                'unpaid': float(unpaid),
            },
            'paid_percentage': float((paid / total_invoiced * 100) if total_invoiced > 0 else 0),
            'overdue': {
                'total': float(overdue['total'] or 0),
                'count': overdue['count'] or 0,
            },
            'avg_collection_days': round(avg_collection_days, 1),
        }
