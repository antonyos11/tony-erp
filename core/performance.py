"""
وحدة تحسين الأداء الشاملة لنظام Tony ERP
Performance Optimization Module
"""

from functools import wraps
from django.core.cache import cache
from django.db import connection
from django.conf import settings
import time
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Query Optimization Decorators
# =============================================================================

def cached_query(timeout=300, key_prefix='query'):
    """
    ديكوراتور لتخزين نتائج الاستعلامات في الكاش
    
    Usage:
        @cached_query(timeout=600, key_prefix='products')
        def get_products_list(category_id):
            return Product.objects.filter(category_id=category_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # بناء مفتاح الكاش
            cache_key = f"{key_prefix}:{func.__name__}:{hashlib.md5(str(args).encode() + str(kwargs).encode()).hexdigest()[:16]}"
            
            # محاولة الحصول من الكاش
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # تنفيذ الاستعلام وتخزينه
            result = func(*args, **kwargs)
            
            # تحويل QuerySet إلى قائمة قبل التخزين
            if hasattr(result, '__iter__') and hasattr(result, 'query'):
                result = list(result)
            
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def invalidate_cache_on_save(cache_keys):
    """
    ديكوراتور لإبطال الكاش عند حفظ نموذج
    
    Usage:
        @invalidate_cache_on_save(['products:*', 'inventory:*'])
        def save(self, *args, **kwargs):
            super().save(*args, **kwargs)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            for pattern in cache_keys:
                if pattern.endswith('*'):
                    # حذف بنمط (يحتاج Redis)
                    try:
                        from django_redis import get_redis_connection
                        redis_conn = get_redis_connection("default")
                        keys = redis_conn.keys(f"*{pattern[:-1]}*")
                        if keys:
                            redis_conn.delete(*keys)
                    except Exception:
                        pass
                else:
                    cache.delete(pattern)
            return result
        return wrapper
    return decorator


# =============================================================================
# Database Query Optimizer
# =============================================================================

class QueryOptimizer:
    """
    محلل وأداة تحسين الاستعلامات
    """
    
    @staticmethod
    def analyze_queryset(queryset, name=""):
        """
        تحليل استعلام وإرجاع معلومات الأداء
        """
        if not settings.DEBUG:
            return None
        
        start_time = time.time()
        query_count_before = len(connection.queries)
        
        # تنفيذ الاستعلام
        result = list(queryset)
        
        end_time = time.time()
        query_count_after = len(connection.queries)
        
        return {
            'name': name,
            'count': len(result),
            'queries': query_count_after - query_count_before,
            'time_ms': (end_time - start_time) * 1000,
            'sql': str(queryset.query) if hasattr(queryset, 'query') else None,
        }
    
    @staticmethod
    def suggest_optimizations(queryset):
        """
        اقتراح تحسينات للاستعلام
        """
        suggestions = []
        
        # فحص select_related
        if hasattr(queryset, 'model'):
            model = queryset.model
            fk_fields = []
            for field in model._meta.fields:
                if field.is_relation and field.many_to_one:
                    fk_fields.append(field.name)
            
            if fk_fields:
                suggestions.append({
                    'type': 'select_related',
                    'message': f'استخدم select_related للحقول: {", ".join(fk_fields)}',
                    'priority': 'high'
                })
        
        # فحص prefetch_related
        if hasattr(queryset, 'model'):
            m2m_fields = []
            for field in model._meta.many_to_many:
                m2m_fields.append(field.name)
            
            if m2m_fields:
                suggestions.append({
                    'type': 'prefetch_related',
                    'message': f'استخدم prefetch_related للعلاقات: {", ".join(m2m_fields)}',
                    'priority': 'high'
                })
        
        return suggestions


# =============================================================================
# Response Optimization
# =============================================================================

class LazyResponse:
    """
    استجابة كسولة لتحميل البيانات عند الحاجة فقط
    """
    
    def __init__(self, queryset, serializer=None, page_size=20):
        self.queryset = queryset
        self.serializer = serializer
        self.page_size = page_size
        self._data = None
        self._count = None
    
    @property
    def data(self):
        if self._data is None:
            if self.serializer:
                self._data = self.serializer(self.queryset[:self.page_size], many=True).data
            else:
                self._data = list(self.queryset[:self.page_size])
        return self._data
    
    @property
    def count(self):
        if self._count is None:
            self._count = self.queryset.count()
        return self._count


# =============================================================================
# Template Optimization
# =============================================================================

def optimize_context(context, max_items=100):
    """
    تحسين سياق القالب بتقليل البيانات الكبيرة
    """
    optimized = {}
    for key, value in context.items():
        if hasattr(value, '__iter__') and hasattr(value, '__len__'):
            if len(value) > max_items:
                optimized[key] = list(value)[:max_items]
                optimized[f'{key}_truncated'] = True
                optimized[f'{key}_total'] = len(value)
            else:
                optimized[key] = value
        else:
            optimized[key] = value
    return optimized


# =============================================================================
# Performance Monitoring
# =============================================================================

class PerformanceMetrics:
    """
    جمع وتحليل مقاييس الأداء
    """
    
    _metrics = {}
    
    @classmethod
    def record(cls, name, value, unit='ms'):
        """تسجيل قيمة أداء"""
        if name not in cls._metrics:
            cls._metrics[name] = {
                'values': [],
                'unit': unit,
                'count': 0,
                'total': 0,
                'min': float('inf'),
                'max': 0,
            }
        
        metric = cls._metrics[name]
        metric['values'].append(value)
        metric['count'] += 1
        metric['total'] += value
        metric['min'] = min(metric['min'], value)
        metric['max'] = max(metric['max'], value)
        
        # الاحتفاظ بآخر 1000 قيمة فقط
        if len(metric['values']) > 1000:
            metric['values'] = metric['values'][-1000:]
    
    @classmethod
    def get_summary(cls, name=None):
        """الحصول على ملخص المقاييس"""
        if name:
            metric = cls._metrics.get(name, {})
            if metric:
                return {
                    'name': name,
                    'count': metric['count'],
                    'avg': metric['total'] / metric['count'] if metric['count'] > 0 else 0,
                    'min': metric['min'] if metric['min'] != float('inf') else 0,
                    'max': metric['max'],
                    'unit': metric['unit'],
                }
            return None
        
        return {name: cls.get_summary(name) for name in cls._metrics}
    
    @classmethod
    def reset(cls, name=None):
        """إعادة تعيين المقاييس"""
        if name:
            cls._metrics.pop(name, None)
        else:
            cls._metrics.clear()


# =============================================================================
# Bulk Operations Helper
# =============================================================================

def bulk_update_or_create(model, objects, unique_fields, update_fields, batch_size=500):
    """
    تحديث أو إنشاء مجموعة كبيرة من الكائنات بكفاءة
    
    Usage:
        bulk_update_or_create(
            Product,
            products_list,
            unique_fields=['sku'],
            update_fields=['name', 'price', 'stock'],
            batch_size=1000
        )
    """
    from django.db import transaction
    
    existing = {}
    filter_kwargs = {}
    
    # بناء فلتر للكائنات الموجودة
    for obj in objects:
        key = tuple(getattr(obj, f) for f in unique_fields)
        existing[key] = obj
    
    # جلب الموجود من قاعدة البيانات
    db_objects = model.objects.filter(**filter_kwargs)
    db_existing = {
        tuple(getattr(obj, f) for f in unique_fields): obj
        for obj in db_objects
    }
    
    to_create = []
    to_update = []
    
    for key, obj in existing.items():
        if key in db_existing:
            db_obj = db_existing[key]
            for field in update_fields:
                setattr(db_obj, field, getattr(obj, field))
            to_update.append(db_obj)
        else:
            to_create.append(obj)
    
    with transaction.atomic():
        # إنشاء الجديد
        if to_create:
            model.objects.bulk_create(to_create, batch_size=batch_size)
        
        # تحديث الموجود
        if to_update:
            model.objects.bulk_update(to_update, update_fields, batch_size=batch_size)
    
    return {
        'created': len(to_create),
        'updated': len(to_update),
    }


# =============================================================================
# Memory Optimization
# =============================================================================

def chunked_queryset(queryset, chunk_size=1000):
    """
    تقسيم استعلام كبير إلى أجزاء لتوفير الذاكرة
    
    Usage:
        for chunk in chunked_queryset(Product.objects.all(), 500):
            for product in chunk:
                process(product)
    """
    pk = 0
    while True:
        chunk = list(queryset.filter(pk__gt=pk).order_by('pk')[:chunk_size])
        if not chunk:
            break
        yield chunk
        pk = chunk[-1].pk


def stream_large_queryset(queryset, chunk_size=2000):
    """
    بث استعلام كبير بدون تحميل كل البيانات في الذاكرة
    """
    for chunk in chunked_queryset(queryset, chunk_size):
        for item in chunk:
            yield item
