"""
Views التطبيق الأساسي — RITA ERP
"""
import json
from decimal import Decimal
from datetime import timedelta

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Sum, Q, F, Count


class DashboardView(LoginRequiredMixin, TemplateView):
    """لوحة التحكم الرئيسية — بيانات حقيقية"""
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'لوحة التحكم'

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # ---- lazy imports ----
        from apps.sales.models import SalesInvoice, SalesInvoiceLine, Customer
        from apps.inventory.models import StockLevel, Product
        from apps.inventory.services.valuation import InventoryValuation
        from apps.production.models import ProductionOrder
        from apps.accounts.models import Account, JournalLine

        # ===== 1. بطاقات KPIs =====
        # مبيعات اليوم
        sales_today = SalesInvoice.objects.filter(
            date__gte=today_start,
            status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')

        # مبيعات الشهر
        sales_month = SalesInvoice.objects.filter(
            date__gte=month_start,
            status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')

        # صافي ربح الشهر (مجموع ربح أسطر الفواتير)
        profit_month = SalesInvoiceLine.objects.filter(
            invoice__date__gte=month_start,
            invoice__status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
        ).aggregate(total=Sum('profit'))['total'] or Decimal('0')

        # هامش الربح %
        cost_month = SalesInvoiceLine.objects.filter(
            invoice__date__gte=month_start,
            invoice__status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
        ).aggregate(
            revenue=Sum('subtotal'),
            cost=Sum(F('cost_price') * F('quantity')),
        )
        revenue_val = cost_month['revenue'] or Decimal('0')
        profit_margin = (
            (profit_month / revenue_val * 100).quantize(Decimal('0.1'))
            if revenue_val > 0 else Decimal('0')
        )

        # عدد فواتير اليوم
        invoices_today = SalesInvoice.objects.filter(date__gte=today_start).count()

        # رصيد الخزينة (حسابات الأصول التي تبدأ بـ 1101 أو اسمها خزينة)
        cash_balance = Decimal('0')
        cash_accounts = Account.objects.filter(
            Q(code__startswith='1101') | Q(name__icontains='خزينة') | Q(name__icontains='صندوق'),
            is_detail=True, is_active=True,
        )
        for acc in cash_accounts:
            totals = JournalLine.objects.filter(
                account=acc, entry__status='posted'
            ).aggregate(d=Sum('debit'), c=Sum('credit'))
            cash_balance += (totals['d'] or Decimal('0')) - (totals['c'] or Decimal('0'))

        # قيمة المخزون
        stock_value = InventoryValuation.get_total_inventory_value()

        # أوامر إنتاج جارية
        active_production = ProductionOrder.objects.filter(
            status__in=['confirmed', 'in_progress', 'quality_check']
        ).count()

        # عملاء نشطين (عملاء لديهم فاتورة خلال آخر 90 يوم)
        active_customers = Customer.objects.filter(
            invoices__date__gte=now - timedelta(days=90)
        ).distinct().count()

        # ---- لون KPIs ----
        def kpi_color(value, green_threshold, yellow_threshold):
            """🟢 أخضر / 🟡 أصفر / 🔴 أحمر"""
            if value >= green_threshold:
                return 'success'
            elif value >= yellow_threshold:
                return 'warning'
            return 'danger'

        context['stats'] = {
            'sales_today': sales_today,
            'sales_month': sales_month,
            'profit_month': profit_month,
            'profit_margin': profit_margin,
            'profit_margin_color': kpi_color(profit_margin, 25, 15),
            'invoices_today': invoices_today,
            'cash_balance': cash_balance,
            'stock_value': stock_value,
            'active_production': active_production,
            'active_customers': active_customers,
        }

        # ===== 2. رسم بياني — مبيعات آخر 7 أيام =====
        chart_labels = []
        chart_data = []
        for i in range(6, -1, -1):
            day = (now - timedelta(days=i)).date()
            day_start = timezone.datetime.combine(day, timezone.datetime.min.time(), tzinfo=now.tzinfo)
            day_end = day_start + timedelta(days=1)
            day_sales = SalesInvoice.objects.filter(
                date__gte=day_start, date__lt=day_end,
                status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
            ).aggregate(total=Sum('total'))['total'] or 0
            chart_labels.append(day.strftime('%d/%m'))
            chart_data.append(float(day_sales))

        context['chart_labels'] = json.dumps(chart_labels)
        context['chart_data'] = json.dumps(chart_data)

        # ===== 3. أفضل 5 منتجات مبيعاً =====
        top_products = (
            SalesInvoiceLine.objects.filter(
                invoice__date__gte=month_start,
                invoice__status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
            )
            .values('product__code', 'product__name')
            .annotate(
                total_qty=Sum('quantity'),
                total_revenue=Sum('subtotal'),
                total_profit=Sum('profit'),
            )
            .order_by('-total_revenue')[:5]
        )
        context['top_products'] = list(top_products)

        # ===== 4. تنبيهات =====
        alerts = []

        # 4a منتجات تحت حد إعادة الطلب
        from apps.inventory.services.stock_engine import StockEngine
        low_stock = StockEngine.get_low_stock_products()
        if low_stock:
            alerts.append({
                'type': 'danger',
                'icon': 'exclamation-triangle-fill',
                'title': f'🔴 {len(low_stock)} منتج تحت حد إعادة الطلب',
                'items': [f"{p['product'].name} (متاح: {p['current_stock']})" for p in low_stock[:5]],
            })

        # 4b فواتير غير مدفوعة
        unpaid = SalesInvoice.objects.filter(
            status__in=['confirmed', 'partial_paid'],
            remaining_amount__gt=0,
        )
        unpaid_count = unpaid.count()
        unpaid_total = unpaid.aggregate(t=Sum('remaining_amount'))['t'] or Decimal('0')
        if unpaid_count > 0:
            alerts.append({
                'type': 'warning',
                'icon': 'cash-coin',
                'title': f'🟡 {unpaid_count} فاتورة غير مدفوعة ({unpaid_total:,.2f} ج.م)',
                'items': [],
            })

        # 4c أوامر إنتاج متأخرة
        overdue_prod = ProductionOrder.objects.filter(
            status__in=['confirmed', 'in_progress'],
            expected_date__lt=now.date(),
        )
        overdue_count = overdue_prod.count()
        if overdue_count > 0:
            alerts.append({
                'type': 'danger',
                'icon': 'clock-history',
                'title': f'🔴 {overdue_count} أمر إنتاج متأخر',
                'items': [f"{o.order_number} — {o.product.name}" for o in overdue_prod[:5]],
            })

        if not alerts:
            alerts.append({
                'type': 'success',
                'icon': 'check-circle-fill',
                'title': '🟢 لا توجد تنبيهات — كل شيء يعمل بسلاسة',
                'items': [],
            })

        context['alerts'] = alerts

        return context

