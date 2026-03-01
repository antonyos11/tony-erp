"""
تقارير المبيعات الذكية — RITA ERP
Sprint 7
"""
from decimal import Decimal
from datetime import timedelta

from django.db.models import Sum, F, Q, Count, Avg
from django.utils import timezone

from apps.sales.models import SalesInvoice, SalesInvoiceLine, Customer


class SalesReports:
    """تقارير المبيعات"""

    @classmethod
    def sales_summary(cls, start_date, end_date, branch=None, salesperson=None, channel=None):
        """
        ملخص مبيعات بفلترة متقدمة
        يحسب: إجمالي مبيعات، خصومات، ضريبة، صافي، تكلفة، ربح
        """
        filters = Q(
            date__date__gte=start_date,
            date__date__lte=end_date,
            status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
        )
        if branch:
            filters &= Q(branch=branch)
        if salesperson:
            filters &= Q(salesperson=salesperson)
        if channel:
            filters &= Q(sale_channel=channel)

        invoices = SalesInvoice.objects.filter(filters)

        totals = invoices.aggregate(
            total_subtotal=Sum('subtotal'),
            total_discount=Sum('discount_amount'),
            total_tax=Sum('tax_amount'),
            total_sales=Sum('total'),
            total_paid=Sum('paid_amount'),
            total_remaining=Sum('remaining_amount'),
            invoice_count=Count('id'),
        )

        # حساب التكلفة و الربح من الأسطر
        line_totals = SalesInvoiceLine.objects.filter(
            invoice__in=invoices,
        ).aggregate(
            total_cost=Sum(F('cost_price') * F('quantity')),
            total_profit=Sum('profit'),
        )

        subtotal = totals['total_subtotal'] or Decimal('0')
        total_cost = line_totals['total_cost'] or Decimal('0')
        total_profit = line_totals['total_profit'] or Decimal('0')

        return {
            'period': f'{start_date} إلى {end_date}',
            'invoice_count': totals['invoice_count'] or 0,
            'subtotal': subtotal,
            'discount': totals['total_discount'] or Decimal('0'),
            'tax': totals['total_tax'] or Decimal('0'),
            'total_sales': totals['total_sales'] or Decimal('0'),
            'total_paid': totals['total_paid'] or Decimal('0'),
            'total_remaining': totals['total_remaining'] or Decimal('0'),
            'total_cost': total_cost,
            'gross_profit': total_profit,
            'profit_margin': (
                (total_profit / subtotal * 100).quantize(Decimal('0.01'))
                if subtotal > 0 else Decimal('0')
            ),
        }

    @classmethod
    def sales_by_product(cls, start_date, end_date, branch=None):
        """
        مبيعات حسب المنتج
        كل منتج: كمية، إيراد، تكلفة، ربح، هامش ربح
        """
        filters = Q(
            invoice__date__date__gte=start_date,
            invoice__date__date__lte=end_date,
            invoice__status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
        )
        if branch:
            filters &= Q(invoice__branch=branch)

        products = (
            SalesInvoiceLine.objects.filter(filters)
            .values('product__code', 'product__name')
            .annotate(
                total_qty=Sum('quantity'),
                total_revenue=Sum('subtotal'),
                total_cost=Sum(F('cost_price') * F('quantity')),
                total_profit=Sum('profit'),
            )
            .order_by('-total_revenue')
        )

        result = []
        for p in products:
            revenue = p['total_revenue'] or Decimal('0')
            profit = p['total_profit'] or Decimal('0')
            margin = (profit / revenue * 100).quantize(Decimal('0.01')) if revenue > 0 else Decimal('0')
            result.append({
                **p,
                'profit_margin': margin,
                'margin_color': 'success' if margin >= 20 else ('warning' if margin >= 10 else 'danger'),
            })

        return result

    @classmethod
    def sales_by_customer(cls, start_date, end_date):
        """مبيعات حسب العميل"""
        filters = Q(
            date__date__gte=start_date,
            date__date__lte=end_date,
            status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
        )

        customers = (
            SalesInvoice.objects.filter(filters)
            .values('customer__code', 'customer__name', 'customer__customer_type')
            .annotate(
                invoice_count=Count('id'),
                total_sales=Sum('total'),
                total_paid=Sum('paid_amount'),
                total_remaining=Sum('remaining_amount'),
                total_discount=Sum('discount_amount'),
            )
            .order_by('-total_sales')
        )
        return list(customers)

    @classmethod
    def sales_by_salesperson(cls, start_date, end_date):
        """
        أداء البائعين
        كل بائع: مبيعات، خصومات، ربح فعلي
        """
        filters = Q(
            date__date__gte=start_date,
            date__date__lte=end_date,
            status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
            salesperson__isnull=False,
        )

        salespersons = (
            SalesInvoice.objects.filter(filters)
            .values('salesperson__username', 'salesperson__first_name', 'salesperson__last_name')
            .annotate(
                invoice_count=Count('id'),
                total_sales=Sum('total'),
                total_discount=Sum('discount_amount'),
            )
            .order_by('-total_sales')
        )

        result = []
        for sp in salespersons:
            # حساب الربح من الأسطر
            sp_invoices = SalesInvoice.objects.filter(
                filters, salesperson__username=sp['salesperson__username']
            )
            profit = SalesInvoiceLine.objects.filter(
                invoice__in=sp_invoices
            ).aggregate(total=Sum('profit'))['total'] or Decimal('0')

            name = f"{sp['salesperson__first_name']} {sp['salesperson__last_name']}".strip()
            result.append({
                'salesperson': name or sp['salesperson__username'],
                'invoice_count': sp['invoice_count'],
                'total_sales': sp['total_sales'] or Decimal('0'),
                'total_discount': sp['total_discount'] or Decimal('0'),
                'total_profit': profit,
            })

        return result

    @classmethod
    def profitability_report(cls, start_date, end_date):
        """
        تقرير ربحية المبيعات
        منتج يبيع كتير بس خسران ❌ vs منتج قليل بس مربح ✅
        """
        filters = Q(
            invoice__date__date__gte=start_date,
            invoice__date__date__lte=end_date,
            invoice__status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
        )

        products = (
            SalesInvoiceLine.objects.filter(filters)
            .values('product__code', 'product__name')
            .annotate(
                total_qty=Sum('quantity'),
                total_revenue=Sum('subtotal'),
                total_cost=Sum(F('cost_price') * F('quantity')),
                total_profit=Sum('profit'),
            )
            .order_by('profit')  # الأقل ربحية أولاً
        )

        result = []
        for p in products:
            revenue = p['total_revenue'] or Decimal('0')
            profit = p['total_profit'] or Decimal('0')
            margin = (profit / revenue * 100).quantize(Decimal('0.01')) if revenue > 0 else Decimal('0')

            if profit <= 0:
                status = '❌ خسارة'
                status_color = 'danger'
            elif margin < 10:
                status = '⚠️ هامش ضعيف'
                status_color = 'warning'
            elif margin < 25:
                status = '✅ مقبول'
                status_color = 'info'
            else:
                status = '🌟 ممتاز'
                status_color = 'success'

            result.append({
                **p,
                'profit_margin': margin,
                'status': status,
                'status_color': status_color,
            })

        # ترتيب: الأسوأ أولاً
        result.sort(key=lambda x: x['total_profit'] or 0)
        return result

    @classmethod
    def daily_sales_trend(cls, days=30):
        """
        اتجاه المبيعات اليومي — لرسم بياني
        """
        now = timezone.now()
        result = []

        for i in range(days - 1, -1, -1):
            day = (now - timedelta(days=i)).date()
            day_start = timezone.datetime.combine(day, timezone.datetime.min.time(), tzinfo=now.tzinfo)
            day_end = day_start + timedelta(days=1)

            totals = SalesInvoice.objects.filter(
                date__gte=day_start, date__lt=day_end,
                status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
            ).aggregate(
                total_sales=Sum('total'),
                invoice_count=Count('id'),
            )

            result.append({
                'date': day.strftime('%Y-%m-%d'),
                'label': day.strftime('%d/%m'),
                'total_sales': float(totals['total_sales'] or 0),
                'invoice_count': totals['invoice_count'] or 0,
            })

        return result
