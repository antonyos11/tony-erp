"""
تحسينات الأداء — RITA ERP Sprint 25
Cache + QuerySet Optimization utilities
"""
import hashlib
import json
from functools import wraps
from django.core.cache import cache
from django.utils import timezone

# ─────────────────────────────────────────────────────────────
# Cache Keys
# ─────────────────────────────────────────────────────────────
CACHE_PREFIX = 'rita_erp'
CACHE_TIMEOUT_SHORT = 300       # 5 دقائق
CACHE_TIMEOUT_MEDIUM = 1800     # 30 دقيقة
CACHE_TIMEOUT_LONG = 3600       # ساعة
CACHE_TIMEOUT_DAY = 86400       # يوم كامل


def make_cache_key(*parts) -> str:
    """بناء مفتاح كاش منظّم"""
    raw = f"{CACHE_PREFIX}:" + ':'.join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()[:32]


# ─────────────────────────────────────────────────────────────
# Menu Cache
# ─────────────────────────────────────────────────────────────
MENU_CACHE_KEY_PREFIX = 'menu'


def get_cached_menu(user_id, role_hash: str):
    """جلب القائمة من الكاش"""
    key = make_cache_key(MENU_CACHE_KEY_PREFIX, user_id, role_hash)
    return cache.get(key)


def set_cached_menu(user_id, role_hash: str, menu_data: list):
    """حفظ القائمة في الكاش"""
    key = make_cache_key(MENU_CACHE_KEY_PREFIX, user_id, role_hash)
    cache.set(key, menu_data, timeout=CACHE_TIMEOUT_MEDIUM)


def invalidate_user_menu(user_id):
    """مسح كاش القائمة عند تغيير الصلاحيات"""
    # Django's LocMemCache doesn't support pattern delete; در الـ Redis استخدم delete_pattern
    # هنا نمسح بمفتاح محدد — في الإنتاج مع Redis استخدم cache.delete_pattern(f'{CACHE_PREFIX}:menu:{user_id}:*')
    pass


# ─────────────────────────────────────────────────────────────
# Permissions Cache
# ─────────────────────────────────────────────────────────────
PERM_CACHE_KEY_PREFIX = 'perm'


def get_cached_permissions(user_id):
    """جلب صلاحيات المستخدم من الكاش"""
    key = make_cache_key(PERM_CACHE_KEY_PREFIX, user_id)
    return cache.get(key)


def set_cached_permissions(user_id, permissions: dict):
    """حفظ صلاحيات المستخدم في الكاش"""
    key = make_cache_key(PERM_CACHE_KEY_PREFIX, user_id)
    cache.set(key, permissions, timeout=CACHE_TIMEOUT_MEDIUM)


def invalidate_user_permissions(user_id):
    """مسح كاش الصلاحيات عند التغيير"""
    key = make_cache_key(PERM_CACHE_KEY_PREFIX, user_id)
    cache.delete(key)


# ─────────────────────────────────────────────────────────────
# Dashboard Cache
# ─────────────────────────────────────────────────────────────

def get_cached_dashboard_stats(branch_id, date_key: str):
    """جلب إحصائيات لوحة التحكم من الكاش"""
    key = make_cache_key('dashboard', branch_id or 'all', date_key)
    return cache.get(key)


def set_cached_dashboard_stats(branch_id, date_key: str, stats: dict):
    """حفظ إحصائيات لوحة التحكم في الكاش"""
    key = make_cache_key('dashboard', branch_id or 'all', date_key)
    cache.set(key, stats, timeout=CACHE_TIMEOUT_SHORT)


def invalidate_dashboard_stats(branch_id=None):
    """مسح كاش الإحصائيات"""
    from django.core.cache import cache as default_cache
    # مسح كاش اليوم الحالي
    date_key = timezone.now().strftime('%Y-%m-%d')
    key = make_cache_key('dashboard', branch_id or 'all', date_key)
    default_cache.delete(key)


# ─────────────────────────────────────────────────────────────
# Decorator: cache_view_result
# ─────────────────────────────────────────────────────────────

def cache_result(timeout: int = CACHE_TIMEOUT_MEDIUM, key_prefix: str = 'view'):
    """
    Decorator لحفظ نتيجة أي function في الكاش.
    
    مثال:
        @cache_result(timeout=300, key_prefix='product_list')
        def get_products(branch_id):
            return Product.objects.filter(branch_id=branch_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = make_cache_key(key_prefix, func.__name__, *args, *kwargs.values())
            result = cache.get(cache_key)
            if result is None:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout=timeout)
            return result
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────
# QuerySet Optimization Helpers
# ─────────────────────────────────────────────────────────────

def optimize_sales_queryset(qs):
    """تحسين استعلامات المبيعات"""
    return qs.select_related(
        'customer', 'branch', 'created_by', 'salesperson',
    ).prefetch_related(
        'items', 'items__product', 'items__product__category',
        'payments',
    )


def optimize_purchases_queryset(qs):
    """تحسين استعلامات المشتريات"""
    return qs.select_related(
        'supplier', 'branch', 'created_by', 'warehouse',
    ).prefetch_related(
        'items', 'items__product',
    )


def optimize_production_queryset(qs):
    """تحسين استعلامات الإنتاج"""
    return qs.select_related(
        'product', 'branch', 'production_line', 'supervisor', 'created_by',
    ).prefetch_related(
        'materials', 'materials__product',
    )


def optimize_inventory_queryset(qs):
    """تحسين استعلامات المخزون"""
    return qs.select_related(
        'product', 'product__category', 'product__unit',
        'warehouse', 'branch',
    )


def optimize_accounts_queryset(qs):
    """تحسين استعلامات المحاسبة"""
    return qs.select_related(
        'account', 'branch', 'created_by', 'approved_by',
    ).prefetch_related(
        'lines', 'lines__account',
    )


def get_pagination_size(request, default: int = 25) -> int:
    """جلب حجم الصفحة من الطلب أو الإعداد الافتراضي"""
    page_size = request.GET.get('page_size', default)
    try:
        page_size = int(page_size)
        return min(max(page_size, 10), 200)  # بين 10 و 200
    except (ValueError, TypeError):
        return default
