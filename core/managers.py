"""
مدراء الاستعلامات المحسنة (Optimized QuerySet Managers)
توفر استعلامات محسنة للأداء مع التخزين المؤقت والتجميع الفعال

الإصدار: 1.0
التاريخ: ديسمبر 2025
"""

from django.db import models
from django.db.models import Sum, Count, Avg, Q, F, Value, Case, When
from django.db.models.functions import Coalesce, TruncDate, TruncMonth, TruncYear
from django.core.cache import cache
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta


class CachedQuerySetMixin:
    """
    خلط للاستعلامات مع دعم التخزين المؤقت
    """
    CACHE_TIMEOUT = 300  # 5 دقائق
    
    def cached(self, cache_key, timeout=None):
        """
        تخزين نتيجة الاستعلام مؤقتاً
        
        Args:
            cache_key: مفتاح التخزين
            timeout: مدة التخزين بالثواني
        
        Returns:
            نتيجة الاستعلام
        """
        result = cache.get(cache_key)
        if result is None:
            result = list(self.all())
            cache.set(cache_key, result, timeout or self.CACHE_TIMEOUT)
        return result
    
    def invalidate_cache(self, cache_key):
        """إلغاء التخزين المؤقت"""
        cache.delete(cache_key)


class DateRangeQuerySetMixin:
    """
    خلط للاستعلامات مع فلترة التواريخ
    """
    date_field = 'date'  # الحقل الافتراضي للتاريخ
    
    def date_range(self, start_date=None, end_date=None):
        """فلترة بنطاق التواريخ"""
        qs = self
        if start_date:
            qs = qs.filter(**{f'{self.date_field}__gte': start_date})
        if end_date:
            qs = qs.filter(**{f'{self.date_field}__lte': end_date})
        return qs
    
    def today(self):
        """سجلات اليوم"""
        return self.filter(**{self.date_field: date.today()})
    
    def yesterday(self):
        """سجلات الأمس"""
        return self.filter(**{self.date_field: date.today() - timedelta(days=1)})
    
    def this_week(self):
        """سجلات هذا الأسبوع"""
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        return self.filter(**{f'{self.date_field}__gte': start_of_week})
    
    def this_month(self):
        """سجلات هذا الشهر"""
        today = date.today()
        return self.filter(
            **{f'{self.date_field}__year': today.year},
            **{f'{self.date_field}__month': today.month}
        )
    
    def this_year(self):
        """سجلات هذا العام"""
        return self.filter(**{f'{self.date_field}__year': date.today().year})
    
    def last_n_days(self, n):
        """سجلات آخر n يوم"""
        return self.filter(**{f'{self.date_field}__gte': date.today() - timedelta(days=n)})


class StatusQuerySetMixin:
    """
    خلط للاستعلامات مع فلترة الحالة
    """
    status_field = 'status'
    
    def active(self):
        """السجلات النشطة"""
        return self.filter(is_active=True)
    
    def inactive(self):
        """السجلات غير النشطة"""
        return self.filter(is_active=False)
    
    def by_status(self, status):
        """فلترة بحالة معينة"""
        return self.filter(**{self.status_field: status})
    
    def drafts(self):
        """المسودات"""
        return self.by_status('draft')
    
    def posted(self):
        """المرحلة"""
        return self.by_status('posted')
    
    def completed(self):
        """المكتملة"""
        return self.by_status('completed')
    
    def cancelled(self):
        """الملغاة"""
        return self.by_status('cancelled')


class AggregationQuerySetMixin:
    """
    خلط للاستعلامات مع التجميعات
    """
    
    def total_amount(self, field='amount'):
        """إجمالي المبالغ"""
        return self.aggregate(
            total=Coalesce(Sum(field), Decimal('0'))
        )['total']
    
    def count_by_status(self, status_field='status'):
        """عدد السجلات حسب الحالة"""
        return self.values(status_field).annotate(
            count=Count('id')
        ).order_by(status_field)
    
    def sum_by_date(self, amount_field='amount', date_field='date'):
        """إجماليات حسب التاريخ"""
        return self.values(date_field).annotate(
            total=Sum(amount_field)
        ).order_by(date_field)
    
    def sum_by_month(self, amount_field='amount', date_field='date'):
        """إجماليات شهرية"""
        return self.annotate(
            month=TruncMonth(date_field)
        ).values('month').annotate(
            total=Sum(amount_field)
        ).order_by('month')
    
    def sum_by_year(self, amount_field='amount', date_field='date'):
        """إجماليات سنوية"""
        return self.annotate(
            year=TruncYear(date_field)
        ).values('year').annotate(
            total=Sum(amount_field)
        ).order_by('year')


# ============================================
# استعلامات محسنة للمحاسبة
# ============================================

class AccountQuerySet(models.QuerySet, CachedQuerySetMixin):
    """استعلامات محسنة للحسابات"""
    
    def active(self):
        return self.filter(is_active=True)
    
    def by_type(self, account_type):
        return self.filter(account_type=account_type)
    
    def assets(self):
        return self.by_type('asset')
    
    def liabilities(self):
        return self.by_type('liability')
    
    def equity(self):
        return self.by_type('equity')
    
    def revenue(self):
        return self.by_type('revenue')
    
    def expenses(self):
        return self.by_type('expense')
    
    def postable(self):
        """الحسابات القابلة للقيد"""
        return self.filter(can_post=True, is_active=True)
    
    def with_balance(self):
        """إضافة الرصيد لكل حساب"""
        return self.annotate(
            debit_total=Coalesce(
                Sum('journal_entries__amount', filter=Q(journal_entries__type='debit')),
                Decimal('0')
            ),
            credit_total=Coalesce(
                Sum('journal_entries__amount', filter=Q(journal_entries__type='credit')),
                Decimal('0')
            )
        ).annotate(
            balance=Case(
                When(account_type__in=['asset', 'expense'], then=F('debit_total') - F('credit_total')),
                default=F('credit_total') - F('debit_total')
            )
        )
    
    def tree(self):
        """ترتيب شجري حسب المسار"""
        return self.order_by('path')


class JournalEntryQuerySet(models.QuerySet, DateRangeQuerySetMixin, StatusQuerySetMixin):
    """استعلامات محسنة للقيود المحاسبية"""
    
    date_field = 'date'
    
    def posted(self):
        return self.filter(is_posted=True)
    
    def unposted(self):
        return self.filter(is_posted=False)
    
    def by_type(self, entry_type):
        return self.filter(entry_type=entry_type)
    
    def with_totals(self):
        """إضافة إجماليات المدين والدائن"""
        return self.annotate(
            total_debit=Coalesce(
                Sum('items__amount', filter=Q(items__type='debit')),
                Decimal('0')
            ),
            total_credit=Coalesce(
                Sum('items__amount', filter=Q(items__type='credit')),
                Decimal('0')
            )
        )
    
    def balanced(self):
        """القيود المتوازنة فقط"""
        return self.with_totals().filter(total_debit=F('total_credit'))


# ============================================
# استعلامات محسنة للمخزون
# ============================================

class ProductQuerySet(models.QuerySet, CachedQuerySetMixin):
    """استعلامات محسنة للمنتجات"""
    
    def active(self):
        return self.filter(is_active=True) if hasattr(self.model, 'is_active') else self
    
    def in_stock(self):
        """المنتجات المتوفرة"""
        return self.annotate(
            total_qty=Coalesce(Sum('stocks__quantity'), 0)
        ).filter(total_qty__gt=0)
    
    def out_of_stock(self):
        """المنتجات غير المتوفرة"""
        return self.annotate(
            total_qty=Coalesce(Sum('stocks__quantity'), 0)
        ).filter(total_qty__lte=0)
    
    def low_stock(self):
        """المنتجات ذات المخزون المنخفض"""
        return self.annotate(
            total_qty=Coalesce(Sum('stocks__quantity'), 0)
        ).filter(total_qty__lte=F('min_stock'))
    
    def with_stock_value(self):
        """المنتجات مع قيمة المخزون"""
        return self.annotate(
            total_qty=Coalesce(Sum('stocks__quantity'), 0),
            stock_value=F('total_qty') * F('cost')
        )
    
    def search(self, query):
        """بحث في المنتجات"""
        return self.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(barcode__icontains=query)
        )


class StockQuerySet(models.QuerySet):
    """استعلامات محسنة للمخزون"""
    
    def by_location(self, location):
        return self.filter(location=location)
    
    def by_product(self, product):
        return self.filter(product=product)
    
    def available(self):
        """المخزون المتوفر فقط"""
        return self.filter(quantity__gt=0)
    
    def total_by_product(self):
        """إجمالي الكميات حسب المنتج"""
        return self.values('product').annotate(
            total_qty=Sum('quantity')
        ).order_by('product')
    
    def total_by_location(self):
        """إجمالي الكميات حسب الموقع"""
        return self.values('location').annotate(
            total_qty=Sum('quantity'),
            product_count=Count('product', distinct=True)
        ).order_by('location')
    
    def with_value(self):
        """المخزون مع القيمة"""
        return self.select_related('product').annotate(
            value=F('quantity') * F('product__cost')
        )


# ============================================
# استعلامات محسنة للمبيعات
# ============================================

class InvoiceQuerySet(models.QuerySet, DateRangeQuerySetMixin, StatusQuerySetMixin, AggregationQuerySetMixin):
    """استعلامات محسنة للفواتير"""
    
    date_field = 'date'
    
    def not_deleted(self):
        return self.filter(is_deleted=False)
    
    def paid(self):
        """الفواتير المدفوعة بالكامل"""
        return self.filter(paid__gte=F('cached_total') - F('discount'))
    
    def unpaid(self):
        """الفواتير غير المدفوعة"""
        return self.filter(paid=Decimal('0'))
    
    def partially_paid(self):
        """الفواتير المدفوعة جزئياً"""
        return self.filter(
            paid__gt=Decimal('0'),
            paid__lt=F('cached_total') - F('discount')
        )
    
    def overdue(self):
        """الفواتير المتأخرة"""
        return self.filter(
            due_date__lt=date.today(),
            paid__lt=F('cached_total') - F('discount')
        )
    
    def by_customer(self, customer):
        return self.filter(customer=customer)
    
    def with_remaining(self):
        """إضافة المبلغ المتبقي"""
        return self.annotate(
            remaining=F('cached_total') - F('discount') - F('paid')
        )
    
    def total_sales(self):
        """إجمالي المبيعات"""
        return self.aggregate(
            total=Coalesce(Sum(F('cached_total') - F('discount')), Decimal('0'))
        )['total']
    
    def total_collected(self):
        """إجمالي التحصيلات"""
        return self.aggregate(
            total=Coalesce(Sum('paid'), Decimal('0'))
        )['total']
    
    def total_outstanding(self):
        """إجمالي المستحقات"""
        return self.with_remaining().aggregate(
            total=Coalesce(Sum('remaining'), Decimal('0'))
        )['total']


# ============================================
# استعلامات محسنة للمشتريات
# ============================================

class PurchaseBillQuerySet(models.QuerySet, DateRangeQuerySetMixin, StatusQuerySetMixin):
    """استعلامات محسنة لفواتير الشراء"""
    
    date_field = 'date'
    
    def not_deleted(self):
        return self.filter(is_deleted=False)
    
    def by_supplier(self, supplier):
        return self.filter(supplier=supplier)
    
    def with_remaining(self):
        """إضافة المبلغ المتبقي"""
        # نحتاج حساب الإجمالي أولاً
        return self.annotate(
            items_total=Coalesce(Sum(F('items__quantity') * F('items__cost')), Decimal('0')),
            remaining=F('items_total') - F('discount') - F('paid')
        )
    
    def unpaid(self):
        """الفواتير غير المدفوعة"""
        return self.filter(paid=Decimal('0'))
    
    def paid(self):
        """الفواتير المدفوعة"""
        return self.with_remaining().filter(remaining__lte=Decimal('0'))


class PurchaseOrderQuerySet(models.QuerySet, DateRangeQuerySetMixin, StatusQuerySetMixin):
    """استعلامات محسنة لأوامر الشراء"""
    
    date_field = 'date'
    
    def pending(self):
        """أوامر الشراء المعلقة"""
        return self.filter(status__in=['draft', 'confirmed'])
    
    def by_supplier(self, supplier):
        return self.filter(supplier=supplier)
    
    def overdue(self):
        """الأوامر المتأخرة"""
        return self.filter(
            expected_date__lt=date.today(),
            status__in=['draft', 'confirmed', 'partial']
        )


# ============================================
# استعلامات محسنة للموارد البشرية
# ============================================

class EmployeeQuerySet(models.QuerySet, CachedQuerySetMixin):
    """استعلامات محسنة للموظفين"""
    
    def active(self):
        return self.filter(status='active')
    
    def inactive(self):
        return self.exclude(status='active')
    
    def by_department(self, department):
        return self.filter(department=department)
    
    def by_position(self, position):
        return self.filter(position=position)
    
    def with_attendance_today(self):
        """الموظفين مع حضور اليوم"""
        return self.prefetch_related(
            models.Prefetch(
                'attendance_records',
                queryset=self.model._meta.get_field('attendance_records').related_model.objects.filter(
                    date=date.today()
                )
            )
        )


# ============================================
# مدراء مخصصة
# ============================================

class OptimizedManager(models.Manager):
    """مدير أساسي محسن"""
    
    def get_queryset(self):
        return super().get_queryset()
    
    def with_relations(self, *relations):
        """تحميل العلاقات مسبقاً"""
        return self.get_queryset().select_related(*relations)
    
    def with_prefetch(self, *prefetches):
        """تحميل العلاقات المتعددة مسبقاً"""
        return self.get_queryset().prefetch_related(*prefetches)


class AccountManager(OptimizedManager):
    """مدير محسن للحسابات"""
    
    def get_queryset(self):
        return AccountQuerySet(self.model, using=self._db).select_related('parent')
    
    def active(self):
        return self.get_queryset().active()
    
    def postable(self):
        return self.get_queryset().postable()
    
    def with_balance(self):
        return self.get_queryset().with_balance()


class InvoiceManager(OptimizedManager):
    """مدير محسن للفواتير"""
    
    def get_queryset(self):
        return InvoiceQuerySet(self.model, using=self._db).select_related('customer')
    
    def not_deleted(self):
        return self.get_queryset().not_deleted()
    
    def overdue(self):
        return self.get_queryset().overdue()
    
    def this_month(self):
        return self.get_queryset().this_month()


class ProductManager(OptimizedManager):
    """مدير محسن للمنتجات"""
    
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)
    
    def in_stock(self):
        return self.get_queryset().in_stock()
    
    def low_stock(self):
        return self.get_queryset().low_stock()
    
    def search(self, query):
        return self.get_queryset().search(query)
