"""
Tony ERP - إصلاح تناقض بيانات Dashboard
المشكلة: الكروت العلوية تعرض أرقام مختلفة عن الرسوم البيانية أسفل

الحل: مصدر واحد للحقيقة (Single Source of Truth)
كل الحسابات تمر عبر DashboardDataService

الاستخدام:
    from core.fixes.dashboard_fix import get_dashboard_context
    stats = get_dashboard_context()
"""
import logging
from datetime import datetime, time as dt_time
from decimal import Decimal

from django.db.models import Sum, Count, Q, F, ExpressionWrapper, DecimalField
from django.utils import timezone

logger = logging.getLogger(__name__)


class DashboardDataService:
    """خدمة بيانات Dashboard موحدة - مصدر واحد للحقيقة"""

    def __init__(self, showroom_id=None, show_all=False):
        self.showroom_id = showroom_id
        self.show_all = show_all
        self._today = timezone.localdate()

    @property
    def today_start(self):
        return timezone.make_aware(datetime.combine(self._today, dt_time.min))

    @property
    def today_end(self):
        return timezone.make_aware(datetime.combine(self._today, dt_time.max))

    @property
    def month_start(self):
        first = self._today.replace(day=1)
        return timezone.make_aware(datetime.combine(first, dt_time.min))

    def _scope_qs(self, qs, showroom_field='showroom_id'):
        """تطبيق فلتر الفرع"""
        if self.showroom_id and not self.show_all:
            return qs.filter(**{showroom_field: self.showroom_id})
        return qs

    def get_sales_today(self):
        """مبيعات اليوم - باستخدام InvoiceItem مثل الداشبورد الأصلي"""
        try:
            from sales.models import InvoiceItem
            sales_expr = ExpressionWrapper(
                F('quantity') * F('price'),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            )
            qs = InvoiceItem.objects.filter(
                invoice__date=self._today
            )
            qs = self._scope_qs(qs, 'invoice__showroom_id')
            result = qs.aggregate(
                total=Sum(sales_expr),
                count=Count('invoice', distinct=True),
            )
            return {
                'total': result['total'] or Decimal('0'),
                'count': result['count'] or 0,
            }
        except Exception as e:
            logger.warning("get_sales_today error: %s", e)
            return {'total': Decimal('0'), 'count': 0}

    def get_purchases_today(self):
        """مشتريات اليوم - باستخدام PurchaseItem مثل الداشبورد الأصلي"""
        try:
            from purchases.models import PurchaseItem
            purchase_expr = ExpressionWrapper(
                F('quantity') * F('cost'),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            )
            qs = PurchaseItem.objects.filter(
                bill__date=self._today
            )
            qs = self._scope_qs(qs, 'bill__showroom_id')
            result = qs.aggregate(
                total=Sum(purchase_expr),
                count=Count('bill', distinct=True),
            )
            return {
                'total': result['total'] or Decimal('0'),
                'count': result['count'] or 0,
            }
        except Exception as e:
            logger.warning("get_purchases_today error: %s", e)
            return {'total': Decimal('0'), 'count': 0}

    def get_collections_today(self):
        """تحصيلات اليوم"""
        try:
            from payments.models import Payment
            qs = Payment.objects.filter(
                date=self._today,
                payment_type='receipt',
            ).exclude(status='cancelled')
            qs = self._scope_qs(qs)
            result = qs.aggregate(total=Sum('amount'))
            return result['total'] or Decimal('0')
        except ImportError:
            pass
        except Exception as e:
            logger.debug("get_collections_today: %s", e)

        # Fallback: try accounting
        try:
            from accounting.models import Payment
            qs = Payment.objects.filter(
                date=self._today,
                payment_type='receipt',
            ).exclude(status='cancelled')
            result = qs.aggregate(total=Sum('amount'))
            return result['total'] or Decimal('0')
        except Exception:
            return Decimal('0')

    def get_expenses_today(self):
        """مصروفات اليوم"""
        try:
            from payments.models import Payment
            qs = Payment.objects.filter(
                date=self._today,
                payment_type='payment',
            ).exclude(status='cancelled')
            qs = self._scope_qs(qs)
            result = qs.aggregate(total=Sum('amount'))
            return result['total'] or Decimal('0')
        except ImportError:
            pass
        except Exception as e:
            logger.debug("get_expenses_today: %s", e)

        try:
            from accounting.models import Expense
            qs = Expense.objects.filter(
                date=self._today,
            ).exclude(status='cancelled')
            result = qs.aggregate(total=Sum('amount'))
            return result['total'] or Decimal('0')
        except Exception:
            return Decimal('0')

    def get_sales_month(self):
        """مبيعات الشهر"""
        try:
            from sales.models import InvoiceItem
            sales_expr = ExpressionWrapper(
                F('quantity') * F('price'),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            )
            qs = InvoiceItem.objects.filter(
                invoice__date__gte=self.month_start,
                invoice__date__lte=self.today_end,
            )
            qs = self._scope_qs(qs, 'invoice__showroom_id')
            result = qs.aggregate(total=Sum(sales_expr))
            return result['total'] or Decimal('0')
        except Exception:
            return Decimal('0')

    def get_purchases_month(self):
        """مشتريات الشهر"""
        try:
            from purchases.models import PurchaseItem
            purchase_expr = ExpressionWrapper(
                F('quantity') * F('cost'),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            )
            qs = PurchaseItem.objects.filter(
                bill__date__gte=self.month_start,
                bill__date__lte=self.today_end,
            )
            qs = self._scope_qs(qs, 'bill__showroom_id')
            result = qs.aggregate(total=Sum(purchase_expr))
            return result['total'] or Decimal('0')
        except Exception:
            return Decimal('0')

    def get_all_stats(self):
        """جميع الإحصائيات - مصدر واحد للحقيقة"""
        sales = self.get_sales_today()
        purchases = self.get_purchases_today()
        collections = self.get_collections_today()
        expenses = self.get_expenses_today()

        net = sales['total'] - purchases['total']

        return {
            'today': {
                'sales': {
                    'total': float(sales['total']),
                    'count': sales['count'],
                },
                'purchases': {
                    'total': float(purchases['total']),
                    'count': purchases['count'],
                },
                'collections': float(collections),
                'expenses': float(expenses),
                'net': float(net),
            },
            'month': {
                'sales': float(self.get_sales_month()),
                'purchases': float(self.get_purchases_month()),
            },
            'generated_at': timezone.now().isoformat(),
        }


def get_dashboard_context(showroom_id=None, show_all=False):
    """
    دالة مختصرة لاستخدامها في views

    في dashboard view:
        from core.fixes.dashboard_fix import get_dashboard_context
        stats = get_dashboard_context(active_showroom_id, show_all)
        context['unified_stats'] = stats
    """
    service = DashboardDataService(showroom_id=showroom_id, show_all=show_all)
    return service.get_all_stats()
