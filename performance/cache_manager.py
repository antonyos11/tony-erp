"""
Tony ERP - Performance and Caching Enhancements
تحسينات الأداء والذاكرة المؤقتة
"""
from django.core.cache import cache
from django.db.models import Prefetch, Q
from django.views.decorators.cache import cache_page
from functools import wraps
import hashlib
import json
from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)


def smart_cache(timeout: int = 300, key_prefix: str = ''):
    """
    ديكوريتر للتخزين المؤقت الذكي
    
    Args:
        timeout: مدة التخزين بالثواني (افتراضي 5 دقائق)
        key_prefix: بادئة لمفتاح التخزين
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # إنشاء مفتاح فريد بناءً على المعاملات
            cache_key = generate_cache_key(func.__name__, args, kwargs, key_prefix)
            
            # محاولة الحصول على القيمة من الذاكرة المؤقتة
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # تنفيذ الدالة وحفظ النتيجة
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            logger.debug(f"Cache miss for {func.__name__}, cached for {timeout}s")
            
            return result
        
        return wrapper
    return decorator


def generate_cache_key(func_name: str, args: tuple, kwargs: dict, prefix: str = '') -> str:
    """إنشاء مفتاح تخزين مؤقت فريد"""
    # تحويل المعاملات إلى نص قابل للتجزئة
    key_parts = [prefix, func_name]
    
    # إضافة args
    for arg in args:
        if hasattr(arg, 'pk'):  # كائن Django Model
            key_parts.append(f"{arg.__class__.__name__}:{arg.pk}")
        else:
            key_parts.append(str(arg))
    
    # إضافة kwargs
    for k, v in sorted(kwargs.items()):
        if hasattr(v, 'pk'):
            key_parts.append(f"{k}={v.__class__.__name__}:{v.pk}")
        else:
            key_parts.append(f"{k}={v}")
    
    # إنشاء hash للمفتاح
    key_string = ':'.join(key_parts)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    return f"cache:{prefix}:{func_name}:{key_hash}"


def invalidate_cache(pattern: str):
    """حذف مفاتيح التخزين المؤقت بناءً على نمط"""
    try:
        # هذا يعمل مع Redis
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        
        keys = conn.keys(pattern)
        if keys:
            conn.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys matching {pattern}")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache: {e}")


class QueryOptimizer:
    """محسّن الاستعلامات"""
    
    @staticmethod
    def optimize_queryset(queryset, select_related: list = None, prefetch_related: list = None):
        """
        تحسين QuerySet بإضافة select_related و prefetch_related
        
        Args:
            queryset: QuerySet للتحسين
            select_related: قائمة الحقول للـ select_related
            prefetch_related: قائمة الحقول للـ prefetch_related
        """
        if select_related:
            queryset = queryset.select_related(*select_related)
        
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        
        return queryset
    
    @staticmethod
    def get_optimized_invoice_queryset():
        """الحصول على queryset محسّن للفواتير"""
        from sales.models import Invoice
        
        return Invoice.objects.select_related(
            'customer',
            'created_by',
            'branch'
        ).prefetch_related(
            'items',
            'items__product',
            'payments'
        )
    
    @staticmethod
    def get_optimized_product_queryset():
        """الحصول على queryset محسّن للمنتجات"""
        from inventory.models import Product
        
        return Product.objects.select_related(
            'category',
            'unit',
            'brand'
        ).prefetch_related(
            'variants',
            'stock_locations'
        )


class CacheManager:
    """مدير الذاكرة المؤقتة"""
    
    # مفاتيح التخزين المؤقت
    DASHBOARD_STATS = 'dashboard:stats:{user_id}'
    PRODUCT_LIST = 'products:list:{page}:{filters}'
    INVOICE_LIST = 'invoices:list:{page}:{filters}'
    USER_PERMISSIONS = 'user:permissions:{user_id}'
    SYSTEM_SETTINGS = 'system:settings'
    
    @classmethod
    def get_dashboard_stats(cls, user_id: int) -> dict:
        """الحصول على إحصائيات لوحة التحكم من الذاكرة المؤقتة"""
        cache_key = cls.DASHBOARD_STATS.format(user_id=user_id)
        return cache.get(cache_key)
    
    @classmethod
    def set_dashboard_stats(cls, user_id: int, stats: dict, timeout: int = 300):
        """حفظ إحصائيات لوحة التحكم في الذاكرة المؤقتة"""
        cache_key = cls.DASHBOARD_STATS.format(user_id=user_id)
        cache.set(cache_key, stats, timeout)
    
    @classmethod
    def invalidate_dashboard_stats(cls, user_id: int):
        """حذف إحصائيات لوحة التحكم من الذاكرة المؤقتة"""
        cache_key = cls.DASHBOARD_STATS.format(user_id=user_id)
        cache.delete(cache_key)
    
    @classmethod
    def get_user_permissions(cls, user_id: int) -> dict:
        """الحصول على صلاحيات المستخدم من الذاكرة المؤقتة"""
        cache_key = cls.USER_PERMISSIONS.format(user_id=user_id)
        return cache.get(cache_key)
    
    @classmethod
    def set_user_permissions(cls, user_id: int, permissions: dict, timeout: int = 3600):
        """حفظ صلاحيات المستخدم في الذاكرة المؤقتة"""
        cache_key = cls.USER_PERMISSIONS.format(user_id=user_id)
        cache.set(cache_key, permissions, timeout)
    
    @classmethod
    def invalidate_user_permissions(cls, user_id: int):
        """حذف صلاحيات المستخدم من الذاكرة المؤقتة"""
        cache_key = cls.USER_PERMISSIONS.format(user_id=user_id)
        cache.delete(cache_key)


class DatabaseOptimizer:
    """محسّن قاعدة البيانات"""
    
    @staticmethod
    def analyze_slow_queries():
        """تحليل الاستعلامات البطيئة"""
        from django.db import connection
        
        slow_queries = []
        
        for query in connection.queries:
            time = float(query['time'])
            if time > 0.1:  # أكثر من 100ms
                slow_queries.append({
                    'sql': query['sql'],
                    'time': time
                })
        
        return slow_queries
    
    @staticmethod
    def get_query_stats():
        """الحصول على إحصائيات الاستعلامات"""
        from django.db import connection
        
        total_queries = len(connection.queries)
        total_time = sum(float(q['time']) for q in connection.queries)
        
        return {
            'total_queries': total_queries,
            'total_time': total_time,
            'avg_time': total_time / total_queries if total_queries > 0 else 0
        }


def batch_process(queryset, batch_size: int = 1000, callback: Callable = None):
    """
    معالجة QuerySet على دفعات لتحسين الأداء
    
    Args:
        queryset: QuerySet للمعالجة
        batch_size: حجم الدفعة
        callback: دالة للاستدعاء لكل دفعة
    """
    total = queryset.count()
    processed = 0
    
    while processed < total:
        batch = queryset[processed:processed + batch_size]
        
        if callback:
            callback(batch)
        
        processed += batch_size
        
        # تنظيف الذاكرة
        from django.db import reset_queries
        reset_queries()
    
    return processed


# ديكوريتورات لتحسين الأداء
def log_performance(func: Callable) -> Callable:
    """تسجيل أداء الدالة"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        if execution_time > 1.0:  # أكثر من ثانية
            logger.warning(
                f"Slow function: {func.__name__} took {execution_time:.2f}s"
            )
        else:
            logger.debug(
                f"Function: {func.__name__} took {execution_time:.4f}s"
            )
        
        return result
    
    return wrapper


# Context Processors للتخزين المؤقت
def cached_system_settings(request):
    """Context processor للإعدادات المحفوظة مؤقتاً"""
    settings = cache.get(CacheManager.SYSTEM_SETTINGS)
    
    if not settings:
        try:
            from core.models import SystemSetting
            settings = {
                setting.key: setting.value
                for setting in SystemSetting.objects.all()
            }
            cache.set(CacheManager.SYSTEM_SETTINGS, settings, 3600)
        except Exception as e:
            logger.error(f"Failed to load system settings: {e}")
            settings = {}
    
    return {'system_settings': settings}
