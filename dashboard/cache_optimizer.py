"""
نظام كاش متقدم للرسوم البيانية ولوحة المعلومات
Dashboard Cache System
"""

from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from functools import wraps
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


def cache_dashboard_data(timeout=300, key_prefix='dashboard'):
    """
    ديكوريتر لكاش بيانات لوحة المعلومات
    
    Args:
        timeout: مدة الكاش بالثواني (افتراضي: 5 دقائق)
        key_prefix: بادئة مفتاح الكاش
    """
    def decorator(func):
        @wraps(func)
        def wrapper(user, *args, **kwargs):
            # إنشاء مفتاح كاش فريد للمستخدم
            cache_key = f"{key_prefix}_{user.id}_{func.__name__}"
            
            # إضافة معاملات إضافية للمفتاح إذا وجدت
            if args or kwargs:
                params_hash = hashlib.md5(
                    json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True).encode()
                ).hexdigest()
                cache_key = f"{cache_key}_{params_hash}"
            
            # محاولة الحصول على البيانات من الكاش
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                logger.debug(f"تم استرجاع البيانات من الكاش: {cache_key}")
                return cached_data
            
            # تنفيذ الدالة والحصول على البيانات
            logger.debug(f"توليد بيانات جديدة: {cache_key}")
            data = func(user, *args, **kwargs)
            
            # حفظ في الكاش
            cache.set(cache_key, data, timeout)
            
            return data
        
        return wrapper
    return decorator


def invalidate_dashboard_cache(user):
    """
    إلغاء كاش لوحة المعلومات لمستخدم معين
    
    Args:
        user: المستخدم
    """
    patterns = [
        f"dashboard_{user.id}_*",
        f"charts_{user.id}_*",
        f"kpi_{user.id}_*"
    ]
    
    for pattern in patterns:
        cache.delete_pattern(pattern)
    
    logger.info(f"تم إلغاء كاش لوحة المعلومات للمستخدم {user.id}")


class DashboardDataOptimizer:
    """محسّن بيانات لوحة المعلومات"""
    
    @staticmethod
    @cache_dashboard_data(timeout=300, key_prefix='charts')
    def get_sales_chart_data(user, days=30):
        """
        الحصول على بيانات رسم المبيعات مع الكاش
        
        Args:
            user: المستخدم
            days: عدد الأيام للتحليل
        
        Returns:
            dict مع بيانات الرسم
        """
        from django.db.models import Sum, Count
        from django.db.models.functions import TruncDate
        from sales.models import Invoice
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        # استعلام محسّن
        data = Invoice.objects.filter(
            date__gte=start_date,
            is_approved=True, is_deleted=False
        ).values('date').annotate(
            total=Sum('cached_total'),
            count=Count('id')
        ).order_by('date')
        
        return {
            'labels': [item['date'].strftime('%Y-%m-%d') for item in data],
            'sales': [float(item['total']) for item in data],
            'count': [item['count'] for item in data]
        }
    
    @staticmethod
    @cache_dashboard_data(timeout=600, key_prefix='kpi')
    def get_kpi_data(user):
        """
        الحصول على مؤشرات الأداء الرئيسية مع الكاش
        
        Args:
            user: المستخدم
        
        Returns:
            dict مع KPIs
        """
        from django.db.models import Sum, Count, Avg, F, Q
        from sales.models import Invoice
        from inventory.models import Product
        from datetime import datetime
        
        today = timezone.now().date()
        this_month = today.replace(day=1)
        last_month = (this_month - timedelta(days=1)).replace(day=1)
        
        # المبيعات اليوم
        today_sales = Invoice.objects.filter(
            date=today,
            is_approved=True, is_deleted=False
        ).aggregate(total=Sum('cached_total'))['total'] or 0
        
        # المبيعات هذا الشهر
        month_sales = Invoice.objects.filter(
            date__gte=this_month,
            is_approved=True, is_deleted=False
        ).aggregate(total=Sum('cached_total'))['total'] or 0
        
        # المبيعات الشهر الماضي
        last_month_sales = Invoice.objects.filter(
            date__gte=last_month,
            date__lt=this_month,
            is_approved=True, is_deleted=False
        ).aggregate(total=Sum('cached_total'))['total'] or 0
        
        # معدل النمو
        growth_rate = 0
        if last_month_sales > 0:
            growth_rate = ((month_sales - last_month_sales) / last_month_sales) * 100
        
        # المنتجات الناقصة (باستخدام min_stock)
        low_stock = Product.objects.filter(
            is_active=True,
            min_stock__gt=0
        ).count()  # simplified: count products with min_stock set
        
        # الفواتير غير المعتمدة
        pending_invoices = Invoice.objects.filter(
            is_approved=False, is_deleted=False
        ).count()
        
        # متوسط قيمة الفاتورة
        avg_invoice = Invoice.objects.filter(
            date__gte=this_month,
            is_approved=True, is_deleted=False
        ).aggregate(avg=Avg('cached_total'))['avg'] or 0
        
        return {
            'today_sales': float(today_sales),
            'month_sales': float(month_sales),
            'growth_rate': round(growth_rate, 2),
            'low_stock_count': low_stock,
            'pending_invoices': pending_invoices,
            'avg_invoice_value': float(avg_invoice),
            'last_updated': timezone.now().isoformat()
        }
    
    @staticmethod
    @cache_dashboard_data(timeout=900, key_prefix='inventory')
    def get_inventory_chart_data(user):
        """
        بيانات رسم المخزون مع الكاش
        
        Args:
            user: المستخدم
        
        Returns:
            dict مع بيانات المخزون
        """
        from inventory.models import Product, Stock
        from django.db.models import Sum, Count, F, Case, When, IntegerField, Subquery, OuterRef
        from django.db.models.functions import Coalesce
        
        # Subquery لحساب إجمالي المخزون لكل منتج
        stock_subq = Stock.objects.filter(
            product_id=OuterRef('pk')
        ).values('product_id').annotate(
            total_qty=Sum('quantity')
        ).values('total_qty')[:1]
        
        products_with_stock = Product.objects.filter(
            is_active=True
        ).annotate(
            total_stock=Coalesce(Subquery(stock_subq, output_field=IntegerField()), 0)
        )
        
        # المخزون حسب الفئة
        by_category = products_with_stock.values(
            'category__name'
        ).annotate(
            total_value=Sum(F('total_stock') * F('cost')),
            count=Count('id')
        ).order_by('-total_value')[:10]
        
        # حالة المخزون
        stock_status = {
            'out_of_stock': products_with_stock.filter(total_stock__lte=0).count(),
            'low_stock': products_with_stock.filter(total_stock__gt=0, total_stock__lte=F('min_stock')).count(),
            'normal_stock': products_with_stock.filter(total_stock__gt=F('min_stock')).count(),
        }
        
        return {
            'by_category': {
                'labels': [item['category__name'] or 'غير مصنف' for item in by_category],
                'values': [float(item['total_value'] or 0) for item in by_category],
                'counts': [item['count'] for item in by_category]
            },
            'stock_status': {
                'labels': ['نفذ', 'منخفض', 'عادي'],
                'values': [
                    stock_status['out_of_stock'],
                    stock_status['low_stock'],
                    stock_status['normal_stock']
                ]
            }
        }


# دوال مساعدة للاستخدام المباشر
def get_cached_dashboard_data(user):
    """الحصول على جميع بيانات لوحة المعلومات مع الكاش"""
    optimizer = DashboardDataOptimizer()
    
    return {
        'kpis': optimizer.get_kpi_data(user),
        'sales_chart': optimizer.get_sales_chart_data(user, days=30),
        'inventory_chart': optimizer.get_inventory_chart_data(user)
    }


def clear_user_cache(user):
    """مسح كاش المستخدم عند تحديث البيانات"""
    invalidate_dashboard_cache(user)


# ===== Celery Tasks =====
try:
    from celery import shared_task
    
    @shared_task(name='dashboard.cache_optimizer.cleanup_old_cache')
    def cleanup_old_cache():
        """تنظيف الكاش القديم - مهمة Celery مجدولة"""
        try:
            # مسح الكاش القديم
            cache.clear()
            logger.info("تم تنظيف الكاش بنجاح")
            return {'status': 'success', 'message': 'تم تنظيف الكاش'}
        except Exception as e:
            logger.error(f"خطأ في تنظيف الكاش: {str(e)}")
            return {'status': 'error', 'message': str(e)}
            
except ImportError:
    # Celery غير متوفر
    pass
