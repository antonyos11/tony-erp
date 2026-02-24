from __future__ import annotations
from django import template
from django.conf import settings
from core.utils.currency import get_default_currency
from decimal import Decimal, InvalidOperation
from django.utils.formats import number_format  # retained (not used after refactor but kept minimal change)
from functools import lru_cache
import re

register = template.Library()


def _coerce_decimal(value):
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None

@register.filter(name="money")
def money(value, arg: str | None = None):
    """
    تنسيق مبلغ مالي بشكل قياسي:
      {{ amount|money }}              -> 1,234.50 ﷼
      {{ amount|money:"USD" }}        -> 1,234.50 $ (أو رمز حسب التعيين)

    arg يمكن أن يكون:
      - كود عملة (USD, EGP, EGP ...)
      - رمز عملة مباشر ("$")
      - سلسلة مركبة "USD:$" لتحديد الرمز يدوياً

    يعتمد على الإعدادات:
      DEFAULT_CURRENCY, DEFAULT_CURRENCY_SYMBOL
    """
    dec_value = _coerce_decimal(value)
    if dec_value is None:
        return "-"

    currency_code, currency_symbol = get_default_currency()
    decimals = getattr(settings, 'DEFAULT_MONEY_DECIMALS', 2)

    if arg:
        main_part = arg
        if '|' in arg:
            main_part, maybe_dec = arg.split('|', 1)
            maybe_dec = maybe_dec.strip()
            if maybe_dec.isdigit():
                try:
                    decimals = max(0, min(6, int(maybe_dec)))
                except ValueError:
                    pass
        main_part = main_part.strip()
        if main_part:
            if ':' in main_part:
                cc, cs = main_part.split(':', 1)
                if cc:
                    currency_code = cc.upper()
                if cs:
                    currency_symbol = cs
            else:
                if main_part.isdigit():
                    decimals = max(0, min(6, int(main_part)))
                else:
                    if len(main_part) <= 3 and main_part.isalpha():
                        currency_code = main_part.upper()
                    else:
                        currency_symbol = main_part

    if not currency_symbol:
        currency_symbol = currency_code

    # quantize pattern
    if decimals > 0:
        quant = '0.' + ('0' * decimals)
    else:
        quant = '0'
    try:
        dec_value = dec_value.quantize(Decimal(quant))
    except Exception:
        pass

    @lru_cache(maxsize=4096)
    def _fmt_cache(val: str, d: int):
        fmt = f",.{d}f" if d > 0 else ",.0f"
        return format(Decimal(val), fmt)
    formatted_num = _fmt_cache(str(dec_value), decimals)
    return f"{formatted_num} {currency_symbol}".strip()


@register.filter(name="money_plain")
def money_plain(value, arg: str | None = None):
    """نفس فلتر money لكن بدون إرجاع رمز العملة (أرقام فقط منسقة). arg يمكن أن يكون رقم المنازل العشرية."""
    dec_value = _coerce_decimal(value)
    if dec_value is None:
        return "-"
    decimals = 2
    if arg and arg.isdigit():
        try:
            decimals = max(0, min(6, int(arg)))
        except ValueError:
            pass
    if decimals > 0:
        quant = '0.' + ('0' * decimals)
    else:
        quant = '0'
    try:
        dec_value = dec_value.quantize(Decimal(quant))
    except Exception:
        pass
    @lru_cache(maxsize=2048)
    def _fmt_plain(val: str, d: int):
        fmt = f",.{d}f" if d > 0 else ",.0f"
        return format(Decimal(val), fmt)
    return _fmt_plain(str(dec_value), decimals)


@register.filter(name="money_compact")
def money_compact(value, arg: str | None = None):
    """تنسيق مالي مع إخفاء .00 النهائية. يدعم نفس صيغة arg لفلتر money (عملة|منازل).
    أمثلة:
      {{ v|money_compact }} -> 1,234.50 ﷼ أو 1,234 ﷼ إذا بدون كسور فعلية
      {{ v|money_compact:'|0' }} يجبر بدون كسور
      {{ v|money_compact:'USD|3' }} ثلاث منازل + USD
    """
    raw = money(value, arg)
    # حاول إزالة .00 فقط إذا كانت في نهاية الجزء الرقمي
    if raw:
        parts = raw.split()
        if parts:
            num = parts[0]
            if num.endswith('.00'):
                num = num[:-3]
            elif re.match(r'^[-+]?[0-9]{1,3}(?:,[0-9]{3})*\.[0-9]+$', num):
                # إزالة أصفار زائدة في نهاية الكسور
                integer, frac = num.split('.', 1)
                frac = frac.rstrip('0')
                if not frac:
                    num = integer
                else:
                    num = f"{integer}.{frac}"
            parts[0] = num
            return ' '.join(p for p in parts if p)
    return raw


@register.simple_tag(takes_context=True)
def money_ctx(context, value, arg: str | None = None):
    """Format using active currency from context (ACTIVE_CURRENCY_CODE/SYMBOL).
    arg can still override decimals (e.g. '|0' or '0').
    Does not allow changing currency code (context wins) unless arg has explicit symbol override ':SYM'.
    """
    code = context.get('ACTIVE_CURRENCY_CODE', getattr(settings, 'DEFAULT_CURRENCY', 'CUR'))
    sym = context.get('ACTIVE_CURRENCY_SYMBOL', getattr(settings, 'DEFAULT_CURRENCY_SYMBOL', code))
    # If arg supplies only decimals like '|0' or '0'
    final_arg = None
    if arg:
        a = arg.strip()
        if ':' in a:  # allow code:symbol|decimals pattern; replace code part with context code
            main = a
            decimals_part = ''
            if '|' in a:
                main, decimals_part = a.split('|', 1)
            _, custom_sym = main.split(':', 1)
            if '|' in a:
                final_arg = f"{code}:{custom_sym}|{decimals_part}".rstrip('|')
            else:
                final_arg = f"{code}:{custom_sym}"
        else:
            # digits or |digits forms
            if a.startswith('|') or a.isdigit():
                final_arg = f"{code}:{sym}{a}" if a.startswith('|') else f"{code}:{sym}|{a}" if a.isdigit() else None
            else:
                final_arg = f"{code}:{sym}"
    if final_arg is None:
        final_arg = f"{code}:{sym}"
    return money(value, final_arg)
