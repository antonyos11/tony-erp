"""
Mixins لتحسين الأداء في Views
Performance Optimization Mixins - Tony ERB
"""

from django.db.models import Sum, Count, F, Value, DecimalField, Prefetch
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type
import logging

logger = logging.getLogger(__name__)


class OptimizedQuerysetMixin:
    """
    Mixin لتحسين استعلامات قاعدة البيانات.
    يوفر طرق مساعدة لتجنب مشكلة N+1 Query.
    """
    
    # تحديد الحقول للـ select_related و prefetch_related
    select_related_fields: List[str] = []
    prefetch_related_fields: List[str] = []
    
    def get_optimized_queryset(self, queryset):
        """
        تحسين الـ queryset بإضافة select_related و prefetch_related.
        """
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        
        if self.prefetch_related_fields:
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)
        
        return queryset


class PaginatedFilterMixin:
    """
    Mixin موحّد للفلترة والـ Pagination.
    يمكن استخدامه في أي View يحتاج لعرض قوائم.
    """
    
    default_page_size: int = 25
    allowed_page_sizes: List[int] = [10, 25, 50, 100]
    
    def get_page_size(self, request) -> int:
        """الحصول على حجم الصفحة من الطلب."""
        try:
            page_size = int(request.GET.get('page_size', self.default_page_size))
            if page_size in self.allowed_page_sizes:
                return page_size
        except (ValueError, TypeError):
            pass
        return self.default_page_size
    
    def paginate_queryset(self, queryset, request) -> Dict[str, Any]:
        """
        تقسيم الـ queryset إلى صفحات.
        
        Returns:
            dict مع page_obj و paginator
        """
        page_size = self.get_page_size(request)
        paginator = Paginator(queryset, page_size)
        page = request.GET.get('page', 1)
        
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        return {
            'page_obj': page_obj,
            'paginator': paginator,
            'page_size': page_size,
        }


class ProductQueryOptimizer:
    """
    محسّن استعلامات المنتجات والمخزون.
    يحل مشكلة N+1 Query عند حساب المخزون والقيمة.
    """
    
    @staticmethod
    def annotate_stock_totals(queryset):
        """
        إضافة حساب المخزون الإجمالي كـ annotation.
        بدلاً من استدعاء current_stock لكل منتج.
        """
        from django.db.models.functions import Cast
        
        return queryset.annotate(
            total_stock=Coalesce(
                Sum(
                    Cast(
                        F('stocks__quantity'),
                        output_field=DecimalField(max_digits=18, decimal_places=2)
                    )
                ),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            ),
            stock_value=Coalesce(
                Sum(
                    F('stocks__quantity') * Cast(
                        F('cost'),
                        output_field=DecimalField(max_digits=18, decimal_places=2)
                    )
                ),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            )
        )
    
    @staticmethod
    def with_low_stock_flag(queryset):
        """
        إضافة علامة انخفاض المخزون كـ annotation.
        """
        from django.db.models import Case, When, BooleanField
        
        annotated = ProductQueryOptimizer.annotate_stock_totals(queryset)
        return annotated.annotate(
            is_low=Case(
                When(total_stock__lte=F('min_stock'), then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            )
        )


class InvoiceQueryOptimizer:
    """
    محسّن استعلامات الفواتير.
    """
    
    @staticmethod
    def with_totals(queryset):
        """
        حساب المجاميع للفواتير عبر SQL.
        """
        return queryset.annotate(
            items_total=Coalesce(
                Sum(F('items__quantity') * F('items__price')),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=14, decimal_places=2)
            ),
            calculated_total=F('items_total') - F('discount'),
            remaining_amount=F('items_total') - F('discount') - F('paid')
        )
    
    @staticmethod
    def with_items_count(queryset):
        """
        إضافة عدد البنود لكل فاتورة.
        """
        return queryset.annotate(
            items_count=Count('items')
        )
    
    @staticmethod
    def optimized_list(queryset):
        """
        استعلام محسّن لقائمة الفواتير.
        """
        return queryset.select_related(
            'customer',
            'payment_method',
            'deleted_by'
        ).prefetch_related(
            'items__product',
            'items__location',
            'payments'
        )


class PurchaseQueryOptimizer:
    """
    محسّن استعلامات المشتريات.
    """
    
    @staticmethod
    def with_totals(queryset):
        """
        حساب المجاميع لفواتير الشراء.
        """
        return queryset.annotate(
            items_total=Coalesce(
                Sum(F('items__quantity') * F('items__cost')),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=14, decimal_places=2)
            ),
            calculated_total=F('items_total') - F('discount'),
            remaining_amount=F('items_total') - F('discount') - F('paid')
        )
    
    @staticmethod
    def optimized_list(queryset):
        """
        استعلام محسّن لقائمة فواتير الشراء.
        """
        return queryset.select_related(
            'supplier',
            'payment_method',
            'deleted_by'
        ).prefetch_related(
            'items__product',
            'items__location'
        )


class CustomerQueryOptimizer:
    """
    محسّن استعلامات العملاء.
    """
    
    @staticmethod
    def with_balance(queryset):
        """
        حساب رصيد العميل عبر SQL.
        """
        return queryset.annotate(
            total_invoices=Coalesce(
                Sum('invoices__cached_total') - Sum('invoices__discount'),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=14, decimal_places=2)
            ),
            total_paid=Coalesce(
                Sum('invoice_payments__amount'),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=14, decimal_places=2)
            ),
            balance=F('total_invoices') - F('total_paid')
        )
    
    @staticmethod
    def with_stats(queryset):
        """
        إضافة إحصائيات للعملاء.
        """
        return queryset.annotate(
            invoices_count=Count('invoices', distinct=True),
            payments_count=Count('invoice_payments', distinct=True)
        )


class CachedPropertyMixin:
    """
    Mixin لتخزين الخصائص المحسوبة مؤقتاً.
    """
    
    _cache: Dict[str, Any] = {}
    
    def get_cached(self, key: str, calculator, ttl: int = 60):
        """
        الحصول على قيمة مخزنة مؤقتاً أو حسابها.
        
        Args:
            key: مفتاح التخزين
            calculator: دالة لحساب القيمة
            ttl: مدة الصلاحية بالثواني
        """
        import time
        
        cache_key = f"{id(self)}_{key}"
        cached = self._cache.get(cache_key)
        
        if cached:
            value, timestamp = cached
            if time.time() - timestamp < ttl:
                return value
        
        value = calculator()
        self._cache[cache_key] = (value, time.time())
        return value
    
    def clear_cache(self, key: Optional[str] = None):
        """مسح التخزين المؤقت."""
        if key:
            cache_key = f"{id(self)}_{key}"
            self._cache.pop(cache_key, None)
        else:
            # مسح كل القيم المرتبطة بهذا الكائن
            prefix = f"{id(self)}_"
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]


def bulk_prefetch_related(queryset, *prefetch_args):
    """
    دالة مساعدة لـ prefetch_related مع Prefetch objects مخصصة.
    
    Example:
        qs = bulk_prefetch_related(
            Invoice.objects.all(),
            Prefetch('items', queryset=InvoiceItem.objects.select_related('product')),
            'customer'
        )
    """
    return queryset.prefetch_related(*prefetch_args)
