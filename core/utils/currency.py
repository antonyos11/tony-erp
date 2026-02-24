from __future__ import annotations
from functools import lru_cache
from typing import Optional, Tuple
from django.conf import settings

# واجهة مساعدة موحدة لجلب العملة الافتراضية مع كاش مبسط
# تعتمد على أن نموذج Currency يوفّر get_default() ويُحدّث الكاش عند الحفظ

@lru_cache(maxsize=1)
def _get_db_default_raw() -> Optional[object]:
    try:
        from core.models import Currency  # import متأخر
        return Currency.get_default()
    except Exception:
        return None

def invalidate_currency_cache():
    _get_db_default_raw.cache_clear()

def get_default_currency() -> Tuple[str, str]:
    """إرجاع (code, symbol) بالترتيب. يسقط إلى الإعدادات إن تعذر جلب قاعدة البيانات."""
    cur = _get_db_default_raw()
    if cur and getattr(cur, 'code', None):
        code = cur.code
        sym = getattr(cur, 'symbol', '') or getattr(settings, 'DEFAULT_CURRENCY_SYMBOL', code)
        return code, sym
    # fallback settings
    code = getattr(settings, 'DEFAULT_CURRENCY', 'CUR')
    sym = getattr(settings, 'DEFAULT_CURRENCY_SYMBOL', code)
    return code, sym

def get_currency_symbol() -> str:
    return get_default_currency()[1]

__all__ = [
    'get_default_currency',
    'get_currency_symbol',
    'invalidate_currency_cache',
]
