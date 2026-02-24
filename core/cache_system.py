"""
نظام الكاش المتقدم
Advanced Caching System
"""

import hashlib
import pickle
from functools import wraps
from typing import Any, Optional, Callable, Union
from datetime import timedelta

from django.core.cache import cache, caches
from django.conf import settings
from django.http import HttpRequest
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Cache Keys Management
# =============================================================================

class CacheKeys:
    """
    إدارة مفاتيح الكاش
    """
    
    # Prefixes
    PREFIX_PAGE = 'page'
    PREFIX_QUERY = 'query'
    PREFIX_USER = 'user'
    PREFIX_VIEW = 'view'
    PREFIX_API = 'api'
    PREFIX_REPORT = 'report'
    PREFIX_DASHBOARD = 'dashboard'
    
    @staticmethod
    def make_key(*parts, prefix: str = '') -> str:
        """إنشاء مفتاح كاش"""
        key_parts = [prefix] if prefix else []
        for part in parts:
            if isinstance(part, dict):
                # ترتيب القاموس وتحويله لسلسلة
                sorted_items = sorted(part.items())
                part = hashlib.md5(str(sorted_items).encode()).hexdigest()[:12]
            elif isinstance(part, (list, tuple)):
                part = hashlib.md5(str(part).encode()).hexdigest()[:12]
            key_parts.append(str(part))
        
        return ':'.join(key_parts)
    
    @classmethod
    def user_key(cls, user_id: int, *parts) -> str:
        """مفتاح خاص بمستخدم"""
        return cls.make_key(user_id, *parts, prefix=cls.PREFIX_USER)
    
    @classmethod
    def page_key(cls, path: str, query_params: Optional[dict] = None, user_id: Optional[int] = None) -> str:
        """مفتاح صفحة"""
        parts: list = [path]
        if query_params:
            parts.append(str(query_params))
        if user_id:
            parts.append(f'u{user_id}')
        return cls.make_key(*parts, prefix=cls.PREFIX_PAGE)
    
    @classmethod
    def query_key(cls, model_name: str, filters: Optional[dict] = None, *extra) -> str:
        """مفتاح استعلام"""
        parts: list = [model_name]
        if filters:
            parts.append(str(filters))
        parts.extend(extra)
        return cls.make_key(*parts, prefix=cls.PREFIX_QUERY)
    
    @classmethod
    def dashboard_key(cls, user_id: Optional[int] = None, showroom_id: Optional[int] = None) -> str:
        """مفتاح لوحة التحكم"""
        parts: list = []
        if user_id:
            parts.append(f'u{user_id}')
        if showroom_id:
            parts.append(f's{showroom_id}')
        return cls.make_key(*parts, prefix=cls.PREFIX_DASHBOARD)


# =============================================================================
# Cache Decorators
# =============================================================================

def cache_result(
    timeout: int = 300,
    key_prefix: str = 'func',
    version: int = 1,
    vary_on_user: bool = False
):
    """
    Decorator لتخزين نتيجة الدالة في الكاش
    
    Usage:
        @cache_result(timeout=600, key_prefix='products')
        def get_products():
            return Product.objects.all()
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # بناء المفتاح
            key_parts = [key_prefix, func.__name__, str(version)]
            
            # إضافة المعاملات للمفتاح
            if args:
                args_hash = hashlib.md5(str(args).encode()).hexdigest()[:12]
                key_parts.append(args_hash)
            if kwargs:
                kwargs_hash = hashlib.md5(str(sorted(kwargs.items())).encode()).hexdigest()[:12]
                key_parts.append(kwargs_hash)
            
            # إضافة المستخدم إذا مطلوب
            if vary_on_user:
                request = args[0] if args and hasattr(args[0], 'user') else kwargs.get('request')
                if request and hasattr(request, 'user') and request.user.is_authenticated:
                    key_parts.append(f'u{request.user.pk}')
            
            cache_key = ':'.join(key_parts)
            
            # محاولة الحصول من الكاش
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return result
            
            # تنفيذ الدالة وتخزين النتيجة
            result = func(*args, **kwargs)
            
            # تحويل QuerySet إلى قائمة
            if hasattr(result, '__iter__') and hasattr(result, 'query'):
                result = list(result)
            
            cache.set(cache_key, result, timeout)
            logger.debug(f"Cache MISS: {cache_key}")
            
            return result
        
        # إضافة دالة لإبطال الكاش
        def invalidate(*args, **kwargs):
            key_parts = [key_prefix, func.__name__, str(version)]
            if args:
                args_hash = hashlib.md5(str(args).encode()).hexdigest()[:12]
                key_parts.append(args_hash)
            if kwargs:
                kwargs_hash = hashlib.md5(str(sorted(kwargs.items())).encode()).hexdigest()[:12]
                key_parts.append(kwargs_hash)
            cache_key = ':'.join(key_parts)
            cache.delete(cache_key)
        
        wrapper.invalidate = invalidate
        return wrapper
    return decorator


def cache_page_fragment(
    timeout: int = 300,
    fragment_name: str = 'default',
    vary_on_args: Optional[list] = None
):
    """
    Decorator لتخزين جزء من الصفحة
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            # بناء المفتاح
            key_parts = ['fragment', fragment_name]
            
            if vary_on_args:
                for arg in vary_on_args:
                    if arg in kwargs:
                        key_parts.append(str(kwargs[arg]))
            
            if request.user.is_authenticated:
                key_parts.append(f'u{request.user.pk}')
            
            cache_key = ':'.join(key_parts)
            
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            result = func(request, *args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


# =============================================================================
# Cache Invalidation
# =============================================================================

class CacheInvalidator:
    """
    نظام إبطال الكاش
    """
    
    # ربط النماذج بالـ patterns المرتبطة
    MODEL_CACHE_PATTERNS = {
        'Product': ['query:product:*', 'dashboard:*', 'page:/inventory/*'],
        'Invoice': ['query:invoice:*', 'dashboard:*', 'page:/sales/*', 'report:sales:*'],
        'PurchaseBill': ['query:purchase:*', 'dashboard:*', 'page:/purchases/*'],
        'Customer': ['query:customer:*', 'page:/crm/*'],
        'Supplier': ['query:supplier:*', 'page:/purchases/*'],
        'Employee': ['query:employee:*', 'page:/hr/*'],
    }
    
    @classmethod
    def invalidate_for_model(cls, model_name: str):
        """إبطال الكاش المرتبط بنموذج"""
        patterns = cls.MODEL_CACHE_PATTERNS.get(model_name, [])
        
        for pattern in patterns:
            cls.invalidate_pattern(pattern)
    
    @classmethod
    def invalidate_pattern(cls, pattern: str):
        """إبطال الكاش بنمط معين"""
        try:
            if hasattr(cache, '_cache') and hasattr(cache._cache, 'keys'):
                # Redis
                from django_redis import get_redis_connection
                redis_conn = get_redis_connection("default")
                keys = redis_conn.keys(f"*{pattern.replace('*', '')}*")
                if keys:
                    redis_conn.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} cache keys for pattern: {pattern}")
            else:
                # LocMem - لا يدعم pattern deletion
                logger.debug(f"Pattern invalidation not supported for current cache backend")
        except Exception as e:
            logger.warning(f"Cache invalidation failed for pattern {pattern}: {e}")
    
    @classmethod
    def invalidate_all(cls):
        """إبطال كل الكاش"""
        try:
            cache.clear()
            logger.info("All cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear all cache: {e}")
    
    @classmethod
    def invalidate_user_cache(cls, user_id: int):
        """إبطال كاش مستخدم معين"""
        pattern = f"user:{user_id}:*"
        cls.invalidate_pattern(pattern)


# =============================================================================
# Cache Warming
# =============================================================================

class CacheWarmer:
    """
    تسخين الكاش مسبقاً
    """
    
    @staticmethod
    def warm_dashboard_cache():
        """تسخين كاش لوحة التحكم"""
        from core.views import _get_dashboard_kpis
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # تسخين للمسؤولين فقط
        for user in User.objects.filter(is_staff=True, is_active=True)[:10]:
            try:
                _get_dashboard_kpis(user)
                logger.info(f"Warmed dashboard cache for user {user.pk}")
            except Exception as e:
                logger.warning(f"Failed to warm cache for user {user.pk}: {e}")
    
    @staticmethod
    def warm_common_queries():
        """تسخين الاستعلامات الشائعة"""
        try:
            from inventory.models import Product
            from sales.models import Invoice
            
            # المنتجات النشطة
            products = list(Product.objects.filter(is_active=True)[:100])
            cache.set('query:products:active:top100', products, 600)
            
            # آخر الفواتير
            invoices = list(Invoice.objects.order_by('-date')[:50])
            cache.set('query:invoices:recent:50', invoices, 300)
            
            logger.info("Common queries cache warmed")
        except Exception as e:
            logger.warning(f"Failed to warm common queries: {e}")


# =============================================================================
# Cache Stats
# =============================================================================

class CacheStats:
    """
    إحصائيات الكاش
    """
    
    _hits = 0
    _misses = 0
    
    @classmethod
    def record_hit(cls):
        cls._hits += 1
    
    @classmethod
    def record_miss(cls):
        cls._misses += 1
    
    @classmethod
    def get_stats(cls) -> dict:
        total = cls._hits + cls._misses
        hit_rate = (cls._hits / total * 100) if total > 0 else 0
        
        return {
            'hits': cls._hits,
            'misses': cls._misses,
            'total': total,
            'hit_rate': f"{hit_rate:.1f}%",
        }
    
    @classmethod
    def reset(cls):
        cls._hits = 0
        cls._misses = 0


# =============================================================================
# Template Fragment Caching Helper
# =============================================================================

def get_cached_template_fragment(
    fragment_name: str,
    timeout: int = 300,
    vary_on: Optional[list] = None,
    render_func: Optional[Callable] = None
) -> Optional[str]:
    """
    الحصول على جزء قالب مخزن أو تصييره
    
    Usage in views:
        cached_html = get_cached_template_fragment(
            'sidebar_menu',
            timeout=600,
            vary_on=[request.user.pk],
            render_func=lambda: render_to_string('partials/_sidebar.html', context)
        )
    """
    key_parts = ['fragment', fragment_name]
    if vary_on:
        key_parts.extend(str(v) for v in vary_on)
    cache_key = ':'.join(key_parts)
    
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    if render_func:
        result = render_func()
        cache.set(cache_key, result, timeout)
        return result
    
    return None


# =============================================================================
# Signals for Auto-invalidation
# =============================================================================

def setup_cache_invalidation_signals():
    """
    إعداد إشارات إبطال الكاش التلقائي
    """
    from django.db.models.signals import post_save, post_delete
    
    def invalidate_on_change(sender, **kwargs):
        model_name = sender.__name__
        CacheInvalidator.invalidate_for_model(model_name)
    
    # ربط الإشارات للنماذج المهمة
    from inventory.models import Product
    from sales.models import Invoice
    from purchases.models import PurchaseBill
    
    for model in [Product, Invoice, PurchaseBill]:
        post_save.connect(invalidate_on_change, sender=model)
        post_delete.connect(invalidate_on_change, sender=model)
