"""
تقارير متقدمة: أعمار الديون + الربحية متعددة الأبعاد — RITA ERP Sprint 22B
═══════════════════════════════════════════════════════════════════════════════
"""
from decimal import Decimal
from django.db.models import Sum, F, Q, Count
from django.utils import timezone


class AgingReport:
    """تقارير أعمار الديون"""

    AGING_BUCKETS = [
        ('current', 'حالي (غير مستحق)'),
        ('days_30', '1-30 يوم'),
        ('days_60', '31-60 يوم'),
        ('days_90', '61-90 يوم'),
        ('over_90', 'أكثر من 90 يوم'),
    ]

    @classmethod
    def customer_aging(cls, as_of_date=None):
        """
        أعمار ديون العملاء
        الفئات: حالي | 1-30 يوم | 31-60 يوم | 61-90 يوم | أكثر من 90
        """
        if not as_of_date:
            as_of_date = timezone.now().date()

        from apps.sales.models import SalesInvoice
        invoices = SalesInvoice.objects.filter(
            remaining_amount__gt=0,
            status__in=['confirmed', 'partial_paid'],
        ).select_related('customer')

        result = {}
        for inv in invoices:
            cust_id = inv.customer_id
            if cust_id not in result:
                result[cust_id] = {
                    'customer': inv.customer,
                    'current': Decimal('0'),
                    'days_30': Decimal('0'),
                    'days_60': Decimal('0'),
                    'days_90': Decimal('0'),
                    'over_90': Decimal('0'),
                    'total': Decimal('0'),
                }

            inv_date = inv.date.date() if hasattr(inv.date, 'date') else inv.date
            days = (as_of_date - inv_date).days
            remaining = inv.remaining_amount

            if days <= 0:
                result[cust_id]['current'] += remaining
            elif days <= 30:
                result[cust_id]['days_30'] += remaining
            elif days <= 60:
                result[cust_id]['days_60'] += remaining
            elif days <= 90:
                result[cust_id]['days_90'] += remaining
            else:
                result[cust_id]['over_90'] += remaining

            result[cust_id]['total'] += remaining

        rows = sorted(result.values(), key=lambda x: x['total'], reverse=True)

        totals = {
            'current': sum(r['current'] for r in rows),
            'days_30': sum(r['days_30'] for r in rows),
            'days_60': sum(r['days_60'] for r in rows),
            'days_90': sum(r['days_90'] for r in rows),
            'over_90': sum(r['over_90'] for r in rows),
            'total': sum(r['total'] for r in rows),
        }

        return {
            'rows': rows,
            'totals': totals,
            'as_of_date': as_of_date,
        }

    @classmethod
    def supplier_aging(cls, as_of_date=None):
        """أعمار ديون الموردين"""
        if not as_of_date:
            as_of_date = timezone.now().date()

        from apps.purchases.models import PurchaseOrder
        orders = PurchaseOrder.objects.filter(
            remaining_amount__gt=0,
            status__in=['confirmed', 'received', 'partial'],
        ).select_related('supplier')

        result = {}
        for order in orders:
            sup_id = order.supplier_id
            if sup_id not in result:
                result[sup_id] = {
                    'supplier': order.supplier,
                    'current': Decimal('0'),
                    'days_30': Decimal('0'),
                    'days_60': Decimal('0'),
                    'days_90': Decimal('0'),
                    'over_90': Decimal('0'),
                    'total': Decimal('0'),
                }

            order_date = order.date.date() if hasattr(order.date, 'date') else order.date
            days = (as_of_date - order_date).days
            remaining = order.remaining_amount

            if days <= 0:
                result[sup_id]['current'] += remaining
            elif days <= 30:
                result[sup_id]['days_30'] += remaining
            elif days <= 60:
                result[sup_id]['days_60'] += remaining
            elif days <= 90:
                result[sup_id]['days_90'] += remaining
            else:
                result[sup_id]['over_90'] += remaining

            result[sup_id]['total'] += remaining

        rows = sorted(result.values(), key=lambda x: x['total'], reverse=True)

        totals = {
            'current': sum(r['current'] for r in rows),
            'days_30': sum(r['days_30'] for r in rows),
            'days_60': sum(r['days_60'] for r in rows),
            'days_90': sum(r['days_90'] for r in rows),
            'over_90': sum(r['over_90'] for r in rows),
            'total': sum(r['total'] for r in rows),
        }

        return {
            'rows': rows,
            'totals': totals,
            'as_of_date': as_of_date,
        }


class ProfitabilityReport:
    """تقارير الربحية بأبعاد متعددة"""

    @classmethod
    def _base_invoice_qs(cls, start_date, end_date):
        from apps.sales.models import SalesInvoice
        return SalesInvoice.objects.filter(
            date__date__gte=start_date,
            date__date__lte=end_date,
            status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
        )

    @classmethod
    def by_product(cls, start_date, end_date):
        """ربحية حسب المنتج"""
        from apps.sales.models import SalesInvoiceLine
        lines = SalesInvoiceLine.objects.filter(
            invoice__date__date__gte=start_date,
            invoice__date__date__lte=end_date,
            invoice__status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
        ).select_related('product')

        result = {}
        for line in lines:
            pid = line.product_id
            if pid not in result:
                result[pid] = {
                    'product': line.product,
                    'quantity': Decimal('0'),
                    'revenue': Decimal('0'),
                    'cost': Decimal('0'),
                    'profit': Decimal('0'),
                }
            result[pid]['quantity'] += line.quantity
            result[pid]['revenue'] += line.total
            cost = getattr(line, 'cost_price', Decimal('0')) or Decimal('0')
            result[pid]['cost'] += cost * line.quantity
            result[pid]['profit'] += getattr(line, 'profit', Decimal('0')) or Decimal('0')

        rows = sorted(result.values(), key=lambda x: x['profit'], reverse=True)
        return {
            'rows': rows,
            'start_date': start_date,
            'end_date': end_date,
            'dimension': 'المنتج',
        }

    @classmethod
    def by_branch(cls, start_date, end_date):
        """ربحية حسب الفرع"""
        invoices = cls._base_invoice_qs(start_date, end_date).select_related('branch')

        result = {}
        for inv in invoices:
            bid = inv.branch_id
            if bid not in result:
                result[bid] = {
                    'branch': inv.branch,
                    'revenue': Decimal('0'),
                    'discount': Decimal('0'),
                    'tax': Decimal('0'),
                    'total': Decimal('0'),
                    'count': 0,
                }
            result[bid]['revenue'] += inv.subtotal or Decimal('0')
            result[bid]['discount'] += inv.discount_amount or Decimal('0')
            result[bid]['tax'] += inv.tax_amount or Decimal('0')
            result[bid]['total'] += inv.total or Decimal('0')
            result[bid]['count'] += 1

        rows = sorted(result.values(), key=lambda x: x['total'], reverse=True)
        return {
            'rows': rows,
            'start_date': start_date,
            'end_date': end_date,
            'dimension': 'الفرع',
        }

    @classmethod
    def by_customer(cls, start_date, end_date):
        """ربحية حسب العميل"""
        from apps.sales.models import SalesInvoiceLine
        invoices = cls._base_invoice_qs(start_date, end_date).select_related('customer')

        result = {}
        for inv in invoices:
            cid = inv.customer_id
            if cid not in result:
                result[cid] = {
                    'customer': inv.customer,
                    'revenue': Decimal('0'),
                    'cost': Decimal('0'),
                    'profit': Decimal('0'),
                    'count': 0,
                }
            result[cid]['revenue'] += inv.total or Decimal('0')
            result[cid]['count'] += 1

        # حساب التكلفة والربح من الأسطر
        from apps.sales.models import SalesInvoiceLine
        lines = SalesInvoiceLine.objects.filter(
            invoice__date__date__gte=start_date,
            invoice__date__date__lte=end_date,
            invoice__status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
        ).select_related('invoice__customer')
        for line in lines:
            cid = line.invoice.customer_id
            if cid in result:
                cost = getattr(line, 'cost_price', Decimal('0')) or Decimal('0')
                result[cid]['cost'] += cost * line.quantity
                result[cid]['profit'] += getattr(line, 'profit', Decimal('0')) or Decimal('0')

        rows = sorted(result.values(), key=lambda x: x['revenue'], reverse=True)
        return {
            'rows': rows,
            'start_date': start_date,
            'end_date': end_date,
            'dimension': 'العميل',
        }

    @classmethod
    def by_sales_channel(cls, start_date, end_date):
        """ربحية حسب قناة البيع"""
        invoices = cls._base_invoice_qs(start_date, end_date)

        result = {}
        for inv in invoices:
            ch = inv.sale_channel
            if ch not in result:
                result[ch] = {
                    'channel': ch,
                    'channel_display': inv.get_sale_channel_display(),
                    'revenue': Decimal('0'),
                    'count': 0,
                }
            result[ch]['revenue'] += inv.total or Decimal('0')
            result[ch]['count'] += 1

        rows = sorted(result.values(), key=lambda x: x['revenue'], reverse=True)
        return {
            'rows': rows,
            'start_date': start_date,
            'end_date': end_date,
            'dimension': 'قناة البيع',
        }

    @classmethod
    def by_cost_center(cls, start_date, end_date):
        """ربحية حسب مركز التكلفة"""
        from apps.accounts.models import CostCenter, JournalLine
        from django.db.models import Sum

        cost_centers = CostCenter.objects.filter(is_active=True)
        rows = []
        for cc in cost_centers:
            qs = JournalLine.objects.filter(
                cost_center=cc,
                entry__date__gte=start_date,
                entry__date__lte=end_date,
                entry__status='posted',
            )
            totals = qs.aggregate(total_debit=Sum('debit'), total_credit=Sum('credit'))
            total_debit = totals['total_debit'] or Decimal('0')
            total_credit = totals['total_credit'] or Decimal('0')
            rows.append({
                'cost_center': cc,
                'revenue': total_credit,
                'cost': total_debit,
                'profit': total_credit - total_debit,
            })

        rows.sort(key=lambda x: x['profit'], reverse=True)
        return {
            'rows': rows,
            'start_date': start_date,
            'end_date': end_date,
            'dimension': 'مركز التكلفة',
        }
