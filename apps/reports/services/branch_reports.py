"""
تقارير الفروع والرقابة — RITA ERP
Sprint 7
"""
from decimal import Decimal
from datetime import timedelta

from django.db.models import Sum, Q, F, Count, Avg
from django.utils import timezone

from apps.core.models import Branch
from apps.sales.models import SalesInvoice, SalesInvoiceLine, SalesReturn, Customer
from apps.accounts.models import JournalLine, Account


class BranchReports:
    """تقارير الفروع"""

    @classmethod
    def branch_scorecard(cls, start_date, end_date):
        """
        تقرير تقييم الفروع
        مبيعات، أرباح، خصومات، مرتجعات، تحصيل — لكل فرع
        """
        branches = Branch.objects.filter(is_active=True)

        result = []
        for branch in branches:
            invoices = SalesInvoice.objects.filter(
                branch=branch,
                date__date__gte=start_date,
                date__date__lte=end_date,
                status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
            )

            totals = invoices.aggregate(
                total_sales=Sum('total'),
                total_discount=Sum('discount_amount'),
                total_paid=Sum('paid_amount'),
                total_remaining=Sum('remaining_amount'),
                invoice_count=Count('id'),
            )

            # ربح الفرع
            profit = SalesInvoiceLine.objects.filter(
                invoice__in=invoices
            ).aggregate(total=Sum('profit'))['total'] or Decimal('0')

            # مرتجعات الفرع
            returns = SalesReturn.objects.filter(
                branch=branch,
                date__date__gte=start_date,
                date__date__lte=end_date,
                status='completed',
            ).aggregate(
                return_count=Count('id'),
                return_total=Sum('total'),
            )

            sales = totals['total_sales'] or Decimal('0')
            paid = totals['total_paid'] or Decimal('0')
            collection_rate = (
                (paid / sales * 100).quantize(Decimal('0.01'))
                if sales > 0 else Decimal('0')
            )

            # تقييم الأداء
            if sales >= Decimal('100000') and collection_rate >= 80:
                score = '🟢 ممتاز'
                score_color = 'success'
            elif sales >= Decimal('50000') and collection_rate >= 60:
                score = '🟡 جيد'
                score_color = 'warning'
            else:
                score = '🔴 يحتاج تحسين'
                score_color = 'danger'

            result.append({
                'branch_name': branch.name,
                'branch_type': branch.get_branch_type_display(),
                'invoice_count': totals['invoice_count'] or 0,
                'total_sales': sales,
                'total_discount': totals['total_discount'] or Decimal('0'),
                'total_profit': profit,
                'total_paid': paid,
                'total_remaining': totals['total_remaining'] or Decimal('0'),
                'collection_rate': collection_rate,
                'return_count': returns['return_count'] or 0,
                'return_total': returns['return_total'] or Decimal('0'),
                'score': score,
                'score_color': score_color,
            })

        result.sort(key=lambda x: float(x['total_sales']), reverse=True)
        return result

    @classmethod
    def abnormal_discounts_report(cls, start_date, end_date):
        """
        تقرير الخصومات غير الطبيعية
        """
        invoices = SalesInvoice.objects.filter(
            date__date__gte=start_date,
            date__date__lte=end_date,
            status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
            discount_amount__gt=0,
        ).select_related('customer', 'branch', 'salesperson').order_by('-discount_amount')

        # متوسط الخصم
        avg_discount = invoices.aggregate(avg=Avg('discount_percentage'))['avg'] or 0
        threshold = max(float(avg_discount) * 2, 10)  # عتبة: ضعف المتوسط أو 10% أيهما أكبر

        result = []
        for inv in invoices:
            if float(inv.discount_percentage) > threshold or inv.discount_amount > inv.subtotal * Decimal('0.2'):
                result.append({
                    'invoice_number': inv.invoice_number,
                    'date': inv.date,
                    'customer': str(inv.customer),
                    'branch': inv.branch.name if inv.branch else '-',
                    'salesperson': str(inv.salesperson) if inv.salesperson else '-',
                    'subtotal': inv.subtotal,
                    'discount_pct': inv.discount_percentage,
                    'discount_amount': inv.discount_amount,
                    'total': inv.total,
                    'flag': '🔴 خصم مرتفع جداً' if inv.discount_amount > inv.subtotal * Decimal('0.3') else '🟡 خصم غير طبيعي',
                    'flag_color': 'danger' if inv.discount_amount > inv.subtotal * Decimal('0.3') else 'warning',
                })

        return {
            'items': result,
            'avg_discount': Decimal(str(avg_discount)).quantize(Decimal('0.01')),
            'threshold': Decimal(str(threshold)).quantize(Decimal('0.01')),
        }

    @classmethod
    def aging_report(cls, partner_type='customer'):
        """
        أعمار الديون
        0-30, 31-60, 61-90, 90+
        """
        now = timezone.now()

        if partner_type == 'customer':
            invoices = SalesInvoice.objects.filter(
                status__in=['confirmed', 'partial_paid'],
                remaining_amount__gt=0,
            ).select_related('customer', 'branch')
        else:
            from apps.purchases.models import PurchaseOrder
            invoices = PurchaseOrder.objects.filter(
                status__in=['confirmed', 'received', 'partial'],
                remaining_amount__gt=0,
            ).select_related('supplier', 'branch')

        buckets = {
            'b_0_30': Decimal('0'),
            'b_31_60': Decimal('0'),
            'b_61_90': Decimal('0'),
            'b_90_plus': Decimal('0'),
        }

        items = []
        for inv in invoices:
            days = (now - inv.date).days if hasattr(inv.date, 'date') else (now.date() - inv.date).days

            if days <= 30:
                bucket = 'b_0_30'
                bucket_label = '0-30'
                bucket_color = 'success'
            elif days <= 60:
                bucket = 'b_31_60'
                bucket_label = '31-60'
                bucket_color = 'info'
            elif days <= 90:
                bucket = 'b_61_90'
                bucket_label = '61-90'
                bucket_color = 'warning'
            else:
                bucket = 'b_90_plus'
                bucket_label = '90+'
                bucket_color = 'danger'

            buckets[bucket] += inv.remaining_amount

            if partner_type == 'customer':
                partner_name = str(inv.customer)
                doc_number = inv.invoice_number
            else:
                partner_name = str(inv.supplier)
                doc_number = inv.order_number

            items.append({
                'partner': partner_name,
                'document': doc_number,
                'date': inv.date,
                'total': inv.total if hasattr(inv, 'total') else Decimal('0'),
                'paid': inv.paid_amount,
                'remaining': inv.remaining_amount,
                'days': days,
                'bucket': bucket_label,
                'bucket_color': bucket_color,
                'branch': inv.branch.name if inv.branch else '-',
            })

        items.sort(key=lambda x: -x['days'])
        total_outstanding = sum(buckets.values())

        return {
            'partner_type': 'عملاء' if partner_type == 'customer' else 'موردين',
            'items': items,
            'buckets': buckets,
            'total_outstanding': total_outstanding,
            'total_count': len(items),
        }
